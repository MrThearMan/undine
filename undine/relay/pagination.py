from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING

from django.db.models import F, ManyToManyField, ManyToManyRel, OrderBy, Window
from django.db.models.functions import RowNumber

from undine.dataclasses import PaginationCut, PaginationPage
from undine.optimizer.prefetch_hack import register_for_prefetch_hack
from undine.pagination import PaginationHandler, _add_total_count, validate_page_size
from undine.settings import undine_settings

from .cursors import OrderingDescriptor, decode_cursor, encode_cursor, order_by_list_to_ordering_descriptors
from .validation import validate_after_and_end, validate_first, validate_last

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from undine import GQLInfo
    from undine.optimizer import OptimizationData
    from undine.typing import TModel, ToManyField


class CursorPaginationHandler(PaginationHandler):
    """
    Handles keyset (a.k.a. "row value") based cursor pagination of a queryset.

    A cursor encodes the ordering values of the row it points to instead of the row's index,
    so rows added or removed between page queries cannot shift the page boundaries.
    """

    def __init__(
        self,
        *,
        typename: str,
        after: str | None = None,
        before: str | None = None,
        first: int | None = None,
        last: int | None = None,
        page_size: int | None = None,
    ) -> None:
        """
        Create a new CursorPaginationHandler.

        :param typename: The typename of the GraphQL type to paginate.
        :param after: Cursor value for the last item in the previous page.
        :param before: Cursor value for the first item in the next page.
        :param first: Number of item to return from the start.
        :param last: Number of item to return from the end (after applying `first`).
        :param page_size: Maximum limit for the number of item that can be requested in a page.
                          No limit if `None`.
        """
        self.typename = typename
        self.after = after
        self.before = before
        self.first = first
        self.last = last
        self.page_size = page_size

        self.descriptors: list[OrderingDescriptor] = []
        self.reversed_ordering: bool = False
        self.total_count: int | None = None
        self.requires_total_count: bool = False
        self.optimization_data: OptimizationData | None = None

        self.validate_arguments()

    def validate_arguments(self) -> None:
        validate_page_size(page_size=self.page_size)

        validate_after_and_end(after=self.after, before=self.before)
        validate_first(first=self.first, last=self.last, before=self.before, page_size=self.page_size)
        validate_last(last=self.last, after=self.after, page_size=self.page_size)

        if self.first is None and self.last is None and isinstance(self.page_size, int):
            if self.before is None:
                self.first = self.page_size
            else:
                self.last = self.page_size

    # Top-level pagination

    def paginate_queryset(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        # Total count must be resolved before the cursor filters are applied,
        # otherwise it would only count the rows remaining after the cursor.
        if self.requires_total_count:
            self.total_count = queryset.count()

        queryset = self.apply_cursor_filters(queryset)
        return self.apply_pagination(queryset, info)

    def apply_pagination(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        # A single extra row is fetched so that the presence of a next/previous page can be detected.
        if self.first is not None:
            return queryset[: self.first + 1]

        if self.last is not None:
            # Since we don't know the size of the queryset, we can't do `qs[size-self.last:]`.
            # Since QuerySets don's support negative indexes, we can't do `qs[-self.last:]`.
            # Instead, we reverse the queryset and filter from the end.
            # We then re-reverse it in `get_page`.
            return queryset.reverse()[: self.last + 1]

        return queryset

    def cut_to_page(self, instances: list[TModel]) -> PaginationCut[TModel]:
        """
        Cut the fetched rows down to the requested page.

        A single extra row is fetched in each direction, so a page that is longer than requested
        proves that another page exists on that side.
        """
        # 'before' and 'after' are both exclusive, so by having them we can assume
        # there is a previous or next page respectively
        has_next_page = self.before is not None
        has_previous_page = self.after is not None

        if self.last is not None:
            instances.reverse()

        if self.last is not None and len(instances) > self.last:
            has_previous_page = True
            instances = instances[-self.last :]

        elif self.first is not None and len(instances) > self.first:
            has_next_page = True
            instances = instances[: self.first]

        return PaginationCut(
            instances=instances,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
        )

    def get_page(self, instances: list[TModel]) -> PaginationPage[TModel]:
        cut = self.cut_to_page(instances)

        cursors: list[str] = []

        for instance in cut.instances:
            cursor = encode_cursor(instance, typename=self.typename, descriptors=self.descriptors)
            cursors.append(cursor)

        return PaginationPage(
            instances=cut.instances,
            cursors=cursors,
            total_count=self.total_count or 0,
            has_next_page=cut.has_next_page,
            has_previous_page=cut.has_previous_page,
        )

    # Prefetch pagination

    def paginate_prefetch_queryset(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet:
        if isinstance(field, ManyToManyField | ManyToManyRel):
            register_for_prefetch_hack(queryset, field)

        # Total count must be resolved before the cursor filters are applied,
        # otherwise it would only count the rows remaining after the cursor.
        if self.requires_total_count:
            queryset = _add_total_count(queryset, field.remote_field.name)

        queryset = self.apply_cursor_filters(queryset)
        return self.apply_prefetch_pagination(queryset, field, info)

    def apply_prefetch_pagination(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet:
        """
        Limit the number of rows per prefetch partition using a window function.

        A prefetch runs a single query for all parent rows, so slicing would limit the
        total number of rows instead of the number of rows for each parent.
        """
        order_by: list[OrderBy]

        # A single extra row is fetched so that the presence of a next/previous page can be detected.
        if self.first is not None:
            order_by = [copy(descriptor.order_by) for descriptor in self.descriptors]
            row_number = Window(expression=RowNumber(), partition_by=F(field.remote_field.name), order_by=order_by)
            queryset = queryset.alias(**{undine_settings.PAGINATION_INDEX_KEY: row_number})
            return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__lte": self.first + 1})

        if self.last is not None:
            # Add row numbers in reverse order so that we can starting from the beginning of the queryset.
            order_by = [copy(descriptor.order_by).reverse_ordering() for descriptor in self.descriptors]  # type: ignore[misc]
            row_number = Window(expression=RowNumber(), partition_by=F(field.remote_field.name), order_by=order_by)
            queryset = queryset.alias(**{undine_settings.PAGINATION_INDEX_KEY: row_number})
            return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__lte": self.last + 1})

        return queryset

    def get_prefetch_page(self, instances: list[TModel]) -> PaginationPage[TModel]:
        total_count: int = 0
        if instances:
            total_count = getattr(instances[0], undine_settings.PAGINATION_TOTAL_COUNT_KEY, 0) or 0

        # 'before' and 'after' are both exclusive, so by having them we can assume
        # there is a previous or next page respectively
        has_next_page = self.before is not None
        has_previous_page = self.after is not None

        if self.last is not None and len(instances) > self.last:
            has_previous_page = True
            instances = instances[-self.last :]

        elif self.first is not None and len(instances) > self.first:
            has_next_page = True
            instances = instances[: self.first]

        return PaginationPage(
            instances=instances,
            cursors=[
                encode_cursor(
                    instance,
                    typename=self.typename,
                    descriptors=self.descriptors,
                )
                for instance in instances
            ],
            total_count=total_count,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
        )

    # Helpers

    def optimize(self, optimization_data: OptimizationData, info: GQLInfo) -> None:
        model = optimization_data.model

        descriptors = order_by_list_to_ordering_descriptors(
            optimization_data.order_by,
            model=model,
            annotations=optimization_data.annotations,
            only_fields=optimization_data.only_fields,
        )

        primary_key_in_ordering = any(descriptor.is_primary_key for descriptor in descriptors)
        if not primary_key_in_ordering:
            optimization_data.only_fields.add("pk")
            optimization_data.order_by.append(OrderBy(F("pk")))
            descriptors.append(
                OrderingDescriptor(
                    attname="pk",
                    order_by=OrderBy(F("pk")),
                    output_field=model._meta.pk,  # type: ignore[arg-type]
                    maybe_null=False,
                    is_primary_key=True,
                ),
            )

        self.descriptors = descriptors

    def apply_cursor_filters(self, queryset: QuerySet) -> QuerySet:
        """Limit the queryset to the rows between the `after` and `before` cursors."""
        if self.after is not None:
            ftr = decode_cursor(self.after, typename=self.typename, descriptors=self.descriptors, kind="after")
            queryset = queryset.filter(ftr)

        if self.before is not None:
            ftr = decode_cursor(self.before, typename=self.typename, descriptors=self.descriptors, kind="before")
            queryset = queryset.filter(ftr)

        return queryset
