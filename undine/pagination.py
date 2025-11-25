from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING

from django.db.models import F, ManyToManyField, ManyToManyRel, OuterRef, Value, Window
from django.db.models.functions import Greatest, RowNumber

from undine import InterfaceType, QueryType, UnionType
from undine.dataclasses import ValidatedPaginationArgs
from undine.exceptions import GraphQLPaginationArgumentValidationError
from undine.optimizer.prefetch_hack import register_for_prefetch_hack
from undine.settings import undine_settings
from undine.utils.model_utils import SubqueryCount
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from undine import GQLInfo
    from undine.typing import CombinableExpression, ToManyField


__all__ = [
    "OffsetPagination",
    "PaginationHandler",
]


class PaginationHandler:
    """Handles pagination of a queryset based on the given arguments."""

    def __init__(
        self,
        *,
        typename: str,
        after: str | None = None,
        before: str | None = None,
        first: int | None = None,
        last: int | None = None,
        offset: int | None = None,
        limit: int | None = None,
        page_size: int | None = None,
    ) -> None:
        """
        Create a new PaginationHandler.

        :param typename: The typename of the GraphQL type to paginate.
        :param first: Number of item to return from the start.
        :param last: Number of item to return from the end (after applying `first`).
        :param after: Cursor value for the last item in the previous page.
        :param before: Cursor value for the first item in the next page.
        :param offset: Number of item to skip from the start. No offset if `None`.
        :param limit: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        :param page_size: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        """
        validated_args = self.validate(
            typename=typename,
            first=first,
            last=last,
            after_cursor=after,
            before_cursor=before,
            offset=offset,
            limit=limit,
            page_size=page_size,
        )

        self.after = validated_args.after
        """The index after which to start (exclusive)."""

        self.before = validated_args.before
        """The index before which to stop (exclusive)."""

        self.first = validated_args.first
        """The number of items to return from the start."""

        self.last = validated_args.last
        """The number of items to return from the end (after evaluating first)."""

        self.page_size = page_size
        """Maximum number of item to return in a page. No limit if `None`."""

        # Calculated in `paginate_queryset` or `paginate_prefetch_queryset` if needed.
        self.start: int = 0
        """The index to start the pagination from."""

        # Calculated in `paginate_queryset` or `paginate_prefetch_queryset` if needed.
        self.stop: int | None = None
        """The index to stop the pagination at."""

        # Modified in `paginate_queryset` or `paginate_prefetch_queryset` if needed.
        self.total_count: int | None = None
        """The total number of items that can be paginated."""

        # Modified during optimization based on pagination params.
        self.requires_total_count: bool = False
        """Whether the total count is required for this query."""

    @staticmethod
    def validate(  # noqa: C901, PLR0912, PLR0915
        *,
        typename: str,
        #
        # Cursor based pagination
        first: int | None,
        last: int | None,
        after_cursor: str | None,
        before_cursor: str | None,
        #
        # Offset based pagination
        offset: int | None,
        limit: int | None,
        #
        # Page size
        page_size: int | None,
    ) -> ValidatedPaginationArgs:
        """Validate the given pagination arguments and return the validated arguments."""
        after: int | None = None
        before: int | None = None

        if after_cursor is not None:
            from undine.relay import cursor_to_offset  # noqa: PLC0415

            try:
                after = cursor_to_offset(typename, after_cursor)
            except Exception as error:
                msg = f"Argument 'after' is not a valid cursor for type '{typename}'."
                raise GraphQLPaginationArgumentValidationError(msg) from error

        if before_cursor is not None:
            from undine.relay import cursor_to_offset  # noqa: PLC0415

            try:
                before = cursor_to_offset(typename, before_cursor)
            except Exception as error:
                msg = f"Argument 'before' is not a valid cursor for type '{typename}'."
                raise GraphQLPaginationArgumentValidationError(msg) from error

        if page_size is not None and (not isinstance(page_size, int) or page_size < 1):
            msg = f"`page_size` must be `None` or a positive integer, got: {page_size!r}"
            raise GraphQLPaginationArgumentValidationError(msg)

        if first is not None:
            if not isinstance(first, int) or first <= 0:
                msg = "Argument 'first' must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg)

            if isinstance(page_size, int) and first > page_size:
                msg = f"Requesting first {first} records exceeds the maximum page size of {page_size}."
                raise GraphQLPaginationArgumentValidationError(msg)

        if last is not None:
            if not isinstance(last, int) or last <= 0:
                msg = "Argument 'last' must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg)

            if isinstance(page_size, int) and last > page_size:
                msg = f"Requesting last {last} records exceeds the maximum page size of {page_size}."
                raise GraphQLPaginationArgumentValidationError(msg)

        if offset is not None:
            if after is not None or before is not None:
                msg = "Can only use either `offset` or `before`/`after` for pagination."
                raise GraphQLPaginationArgumentValidationError(msg)

            if not isinstance(offset, int) or offset < 0:
                msg = "Argument `offset` must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg)

            # Convert offset to after cursor value. Note that after cursor dictates
            # a value _after_ which results should be returned, so we need to subtract
            # 1 from the offset to get the correct cursor value.
            if offset > 0:  # ignore zero offset
                after = offset - 1

        if limit is not None:
            if not isinstance(limit, int) or limit < 0:
                msg = "Argument `limit` must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg)

            if isinstance(page_size, int) and limit > page_size:
                msg = f"Requesting {limit} records exceeds the maximum page size of {page_size}."
                raise GraphQLPaginationArgumentValidationError(msg)

            # In offset pagination, limit is the same as requesting the first n items
            first = limit

        if isinstance(page_size, int) and first is None and last is None:
            first = page_size

        if after is not None and (not isinstance(after, int) or after < 0):
            msg = "The node pointed with `after` does not exist."
            raise GraphQLPaginationArgumentValidationError(msg)

        if before is not None and (not isinstance(before, int) or before < 0):
            msg = "The node pointed with `before` does not exist."
            raise GraphQLPaginationArgumentValidationError(msg)

        if after is not None and before is not None and after >= before:
            msg = "The node pointed with `after` must be before the node pointed with `before`."
            raise GraphQLPaginationArgumentValidationError(msg)

        # Since `after` is also exclusive, we need to add 1 to it, so that slicing works correctly.
        if after is not None:
            after += 1

        return ValidatedPaginationArgs(after=after, before=before, first=first, last=last)

    def paginate_queryset(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        """Paginate a top-level queryset."""
        self.calculate_pagination_arguments(queryset, info)
        return self.apply_pagination(queryset, info)

    def calculate_pagination_arguments(self, queryset: QuerySet, info: GQLInfo) -> None:
        """
        Calculates the pagination arguments for a top-level queryset.

        This function is based on the Relay pagination algorithm.
        See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm
        """
        if self.requires_total_count:
            self.total_count = queryset.count()

        if self.after is not None:
            self.start = self.after

        if self.before is not None:
            self.stop = self.before

        if self.first is not None:
            self.stop = self.start + self.first if self.stop is None else min(self.start + self.first, self.stop)

        if self.last is not None:
            if self.stop is None:
                if self.total_count is None:
                    self.total_count = queryset.count()
                self.stop = self.total_count
            self.start = max(self.stop - self.last, self.start)

    def apply_pagination(self, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        """Paginate a top-level queryset using queryset slicing."""
        return queryset[self.start : self.stop]

    def paginate_prefetch_queryset(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet:
        """Paginate a prefetch queryset."""
        self.calculate_prefetch_pagination_arguments(queryset, field, info)
        return self.apply_prefetch_pagination(queryset, field, info)

    def calculate_prefetch_pagination_arguments(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> None:
        """
        Calculates the pagination arguments for a prefetch queryset.

        This function is based on the Relay pagination algorithm.
        See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm
        """
        if self.requires_total_count:
            self.total_count = F(undine_settings.PAGINATION_TOTAL_COUNT_KEY)

        if self.after is not None:
            self.start = self.after

        if self.before is not None:
            self.stop = self.before

        if self.first is not None:
            self.stop = self.start + self.first if self.stop is None else min(self.start + self.first, self.stop)

        if self.last is not None:
            if self.stop is None:
                if self.total_count is None:
                    self.total_count = F(undine_settings.PAGINATION_TOTAL_COUNT_KEY)  # type: ignore[assignment]
                self.start = Greatest(self.total_count - Value(self.last), Value(self.start))  # type: ignore[assignment]
            else:
                self.start = max(self.stop - self.last, self.start)

    def apply_prefetch_pagination(self, queryset: QuerySet, field: ToManyField, info: GQLInfo) -> QuerySet:
        """
        Paginate a prefetch queryset using a window function partitioned by the given related field.

        Pagination arguments are annotated to the queryset, since they are calculated in the database.
        There is the issue that they might not be available if the queryset is empty after pagination,
        but since they can be different for each prefetch partition, we cannot do anything about that.
        """
        if isinstance(field, ManyToManyField | ManyToManyRel):
            register_for_prefetch_hack(queryset, field)

        related_name = field.remote_field.name

        if self.total_count is not None:
            queryset = _add_total_count(queryset, related_name)

        queryset = _add_partition_index(queryset, related_name)

        queryset = _add_start_index(queryset, self.start)
        queryset = _filter_by_start_index(queryset)

        if self.stop is not None:
            queryset = _add_stop_index(queryset, self.stop)
            queryset = _filter_by_stop_index(queryset)

        return queryset


class OffsetPagination:
    """A wrapper for paginating a `QueryType` using offset and limit."""

    def __init__(
        self,
        ref: type[QueryType | UnionType | InterfaceType],
        /,
        *,
        page_size: int | None = undine_settings.PAGINATION_PAGE_SIZE,
        pagination_handler: type[PaginationHandler] = PaginationHandler,
        description: str | None = None,
    ) -> None:
        """
        Create a new OffsetPagination.

        :param ref: The `QueryType`, `UnionType`, or `InterfaceType` to paginate.
        :param page_size: Maximum number of items to return in a page. No limit if `None`.
        :param pagination_handler: Handler to use for pagination.
        :param description: Description for the created GraphQL type.
        """
        self.query_type = ref if is_subclass(ref, QueryType) else None
        self.union_type = ref if is_subclass(ref, UnionType) else None
        self.interface_type = ref if is_subclass(ref, InterfaceType) else None

        self.page_size = page_size
        self.pagination_handler = pagination_handler
        self.description = description


def _add_partition_index(queryset: QuerySet, related_name: str) -> QuerySet:
    """Add an index to each instance in the queryset, partitioned by the given related name."""
    return queryset.alias(
        **{
            undine_settings.PAGINATION_INDEX_KEY: (
                Window(
                    expression=RowNumber(),
                    partition_by=F(related_name),
                    order_by=queryset.query.order_by or copy(queryset.model._meta.ordering) or None,
                )
                - Value(1)  # Start from zero.
            ),
        },
    )


def _add_total_count(queryset: QuerySet, related_name: str) -> QuerySet:
    """Add an annotation to the given queryset with the total count of objects in the queryset."""
    total_count = _total_count_subquery(queryset, related_name)
    return queryset.annotate(**{undine_settings.PAGINATION_TOTAL_COUNT_KEY: total_count})


def _total_count_subquery(queryset: QuerySet, related_name: str) -> SubqueryCount:
    """Get a subquery for calculating total count, partitioned by the given related name."""
    return SubqueryCount(queryset=queryset.filter(**{related_name: OuterRef(related_name)}))


def _add_start_index(queryset: QuerySet, start: int | CombinableExpression) -> QuerySet:
    """Add an annotation to the given queryset with the start index of the current page."""
    if isinstance(start, int):
        start = Value(start)
    return queryset.annotate(**{undine_settings.PAGINATION_START_INDEX_KEY: start})


def _filter_by_start_index(queryset: QuerySet) -> QuerySet:
    """Filter out all items before the start index of the current page."""
    start = F(undine_settings.PAGINATION_START_INDEX_KEY)
    return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__gte": start})


def _add_stop_index(queryset: QuerySet, stop: int | CombinableExpression) -> QuerySet:
    """Add an annotation to the given queryset with the stop index of the current page."""
    if isinstance(stop, int):
        stop = Value(stop)
    return queryset.annotate(**{undine_settings.PAGINATION_STOP_INDEX_KEY: stop})


def _filter_by_stop_index(queryset: QuerySet) -> QuerySet:
    """Filter out all items on or after the stop index of the current page."""
    stop = F(undine_settings.PAGINATION_STOP_INDEX_KEY)
    return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__lt": stop})
