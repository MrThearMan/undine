from __future__ import annotations

import base64
import dataclasses
import json
from copy import copy
from types import SimpleNamespace
from typing import TYPE_CHECKING, Unpack

from django.core.exceptions import FieldDoesNotExist
from django.db import router  # noqa: ICN003
from django.db.models import F, ManyToManyField, ManyToManyRel, OrderBy, Q, Value, Window
from django.db.models.constants import LOOKUP_SEP
from django.db.models.functions import Greatest, RowNumber
from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString
from graphql.type.scalars import serialize_id

from undine import InterfaceField, InterfaceType, QueryType, UnionType
from undine.dataclasses import PaginationPage, ValidatedPaginationArgs
from undine.exceptions import GraphQLPaginationArgumentValidationError, InterfaceFieldNodeIDError
from undine.optimizer.prefetch_hack import register_for_prefetch_hack
from undine.pagination import (
    PaginationHandler,
    _add_partition_index,
    _add_start_index,
    _add_stop_index,
    _add_total_count,
    _filter_by_start_index,
    _filter_by_stop_index,
    validate_page_size,
)
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.model_utils import determine_output_field, get_db_features, get_model_field
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.db.models import Field as DjangoField
    from django.db.models import Model, QuerySet

    from undine import Field, GQLInfo
    from undine.optimizer import OptimizationData
    from undine.typing import InterfaceFieldParams, TModel, ToManyField

__all__ = [
    "Connection",
    "Node",
    "NodeIDField",
    "PageInfoType",
]


class NodeIDField(InterfaceField):
    """Field for the `Node` interface that converts primary key into string ID."""

    def __init__(self, **kwargs: Unpack[InterfaceFieldParams]) -> None:
        ref = GraphQLNonNull(GraphQLID)
        kwargs.setdefault("description", "The Global ID of an object.")
        kwargs.setdefault("field_name", "pk")
        super().__init__(ref, **kwargs)

    def check_inheritance(self, field: Field | InterfaceField) -> None:
        # Node ID is special, since it converts any type of primary key into string,
        # so we can assume that it will work even given any model pk type.
        #
        # Guard against interface inheritance losing this check override.
        if isinstance(field, InterfaceField) and not isinstance(field, NodeIDField):
            raise InterfaceFieldNodeIDError(interface=field.interface_type)


class Node(InterfaceType):
    """An interface for objects with Global IDs."""

    id = NodeIDField()


PageInfoType = get_or_create_graphql_object_type(
    name="PageInfo",
    description="Information about the current state of the pagination.",
    fields={
        "hasNextPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="Are there more items after the current page?",
        ),
        "hasPreviousPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="Are there more items before the current page?",
        ),
        "startCursor": GraphQLField(
            GraphQLString,  # null if no results
            description=(
                "Value of the first cursor in the current page. "
                "Use as the value for the `before` argument to paginate backwards."
            ),
        ),
        "endCursor": GraphQLField(
            GraphQLString,  # null if no results
            description=(
                "Value of the last cursor in the current page. "
                "Use as the value for the `after` argument to paginate forwards."
            ),
        ),
    },
)


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

        self.ordering_descriptors: list[OrderingDescriptor] = []
        self.reversed_ordering: bool = False
        self.total_count: int | None = None
        self.requires_total_count: bool = False
        self.optimization_data: OptimizationData | None = None

        self.validate_arguments()

    def validate_arguments(self) -> None:
        validate_page_size(page_size=self.page_size)

        validate_after_and_end(after=self.after, before=self.before)
        validate_first(first=self.first, last=self.last, before=self.before, page_size=self.page_size)
        validate_last(last=self.last, first=self.first, after=self.after, page_size=self.page_size)

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

    def get_page(self, instances: list[TModel]) -> PaginationPage[TModel]:
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

        return PaginationPage(
            instances=instances,
            cursors=self.build_cursors(instances),
            total_count=self.total_count or 0,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
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
            order_by = [copy(descriptor.order_by) for descriptor in self.ordering_descriptors]
            queryset = _add_row_number(queryset, related_name=field.remote_field.name, order_by=order_by)
            return _filter_by_row_number(queryset, lte=self.first + 1)

        if self.last is not None:
            # Add row numbers in reverse order so that we can starting from the beginning of the queryset.
            order_by = [copy(descriptor.order_by).reverse_ordering() for descriptor in self.ordering_descriptors]  # type: ignore[misc]
            queryset = _add_row_number(queryset, related_name=field.remote_field.name, order_by=order_by)
            return _filter_by_row_number(queryset, lte=self.last + 1)

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
            cursors=self.build_cursors(instances),
            total_count=total_count,
            has_next_page=has_next_page,
            has_previous_page=has_previous_page,
        )

    # Helpers

    def optimize(self, optimization_data: OptimizationData, info: GQLInfo) -> None:
        model = optimization_data.model
        db_alias = router.db_for_read(model)
        nulls_first_by_default = get_db_features(db_alias).order_by_nulls_first

        descriptors: list[OrderingDescriptor] = []
        primary_key_in_ordering = False

        for index, order_by in enumerate(optimization_data.order_by):
            expression = order_by.expression
            nulls_first = _orders_nulls_first(order_by, nulls_first_by_default=nulls_first_by_default)

            # Expressions and subqueries
            if not isinstance(expression, F):
                key = f"{undine_settings.PAGINATION_ORDERING_KEY}_{index}"
                field: DjangoField = copy(determine_output_field(expression, model=model))
                field.attname = key

                optimization_data.annotations[key] = expression
                descriptors.append(
                    OrderingDescriptor(
                        attname=key,
                        order_by=order_by,
                        output_field=field,
                        maybe_null=field.null,
                        nulls_first=nulls_first,
                    ),
                )
                continue

            try:
                model_field: DjangoField = model._meta.get_field(expression.name)  # type: ignore[assignment]

            except FieldDoesNotExist:
                related_model_field: DjangoField = get_model_field(model=model, lookup=expression.name)  # type: ignore[assignment]

                # Fields from related models
                key = f"{undine_settings.PAGINATION_ORDERING_KEY}_{index}"
                optimization_data.annotations[key] = expression
                descriptors.append(
                    OrderingDescriptor(
                        attname=key,
                        order_by=order_by,
                        output_field=related_model_field,
                        maybe_null=related_model_field.null,
                        nulls_first=nulls_first,
                    ),
                )
                continue

            # Fields from the model itself
            primary_key_in_ordering |= model_field.primary_key
            attname = model_field.get_attname()

            optimization_data.only_fields.add(attname)
            descriptors.append(
                OrderingDescriptor(
                    attname=attname,
                    order_by=order_by,
                    output_field=model_field,
                    maybe_null=model_field.null,
                    nulls_first=nulls_first,
                ),
            )
            continue

        if not primary_key_in_ordering:
            optimization_data.only_fields.add("pk")
            optimization_data.order_by.append(OrderBy(F("pk")))
            descriptors.append(
                OrderingDescriptor(
                    attname="pk",
                    order_by=OrderBy(F("pk")),
                    output_field=model._meta.pk,  # type: ignore[arg-type]
                    maybe_null=False,
                ),
            )

        self.ordering_descriptors = descriptors

    def apply_cursor_filters(self, queryset: QuerySet) -> QuerySet:
        """Limit the queryset to the rows between the `after` and `before` cursors."""
        if self.after is not None:
            values = self.decode_cursor(self.after, argument_name="after")
            ftr = build_keyset_filter(self.ordering_descriptors, values, before=False)
            queryset = queryset.filter(ftr)

        if self.before is not None:
            values = self.decode_cursor(self.before, argument_name="before")
            ftr = build_keyset_filter(self.ordering_descriptors, values, before=True)
            queryset = queryset.filter(ftr)

        return queryset

    def decode_cursor(self, cursor: str, *, argument_name: str) -> list[Value | None]:
        """Decode the given cursor into values that can be compared against the queryset's ordering."""
        try:
            string_values = cursor_to_values(self.typename, cursor)
        except Exception as error:
            msg = f"Argument '{argument_name}' is not a valid cursor for type '{self.typename}'."
            raise GraphQLPaginationArgumentValidationError(msg) from error

        if len(string_values) != len(self.ordering_descriptors):
            msg = (
                f"Argument '{argument_name}' contains a cursor that was created for a different ordering. "
                f"Cursors are only valid for the ordering they were created with."
            )
            raise GraphQLPaginationArgumentValidationError(msg)

        values: list[Value | None] = []

        for descriptor, string_value in zip(self.ordering_descriptors, string_values, strict=True):
            if string_value is None:
                values.append(None)
                continue

            output_field = descriptor.output_field
            try:
                value = output_field.to_python(string_value)
            except Exception as error:
                msg = f"Argument '{argument_name}' is not a valid cursor for type '{self.typename}'."
                raise GraphQLPaginationArgumentValidationError(msg) from error

            values.append(Value(value, output_field=output_field))

        return values

    def build_cursors(self, instances: list[TModel]) -> list[str]:
        """Build a cursor for each of the given instances from their ordering values."""
        return [
            values_to_cursor(
                typename=self.typename,
                # TODO: This should likely store the attname or cursors could be confused.
                values=[descriptor.get_string_value(instance) for descriptor in self.ordering_descriptors],
            )
            for instance in instances
        ]


class Connection:
    """A wrapper for paginating a `QueryType` using Relay Connections."""

    def __init__(
        self,
        ref: type[QueryType | UnionType | InterfaceType],
        /,
        *,
        page_size: int | None = undine_settings.PAGINATION_PAGE_SIZE,
        pagination_handler: type[CursorPaginationHandler] = CursorPaginationHandler,
        description: str | None = None,
    ) -> None:
        """
        Create a new Connection.

        :param ref: The `QueryType`, `UnionType`, or `InterfaceType` to use.
        :param page_size: Maximum number of items to return in a page. No limit if `None`.
        :param pagination_handler: Handler to use for pagination. By default, `QueryType` connections
                                   use keyset cursors, while `UnionType` and `InterfaceType` connections
                                   use index based cursors.
        :param description: Description for the created GraphQL type.
        """
        self.query_type: type[QueryType] | None = ref if is_subclass(ref, QueryType) else None
        self.union_type: type[UnionType] | None = ref if is_subclass(ref, UnionType) else None
        self.interface_type: type[InterfaceType] | None = ref if is_subclass(ref, InterfaceType) else None

        self.page_size = page_size
        self.pagination_handler = pagination_handler
        self.description = description


class BasicCursorPaginationHandler(PaginationHandler):
    """Handles pagination of a queryset based on the given arguments."""

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
        Create a new BasicConnectionPaginationHandler.

        :param typename: The typename of the GraphQL type to paginate.
        :param first: Number of item to return from the start.
        :param last: Number of item to return from the end (after applying `first`).
        :param after: Cursor value for the last item in the previous page.
        :param before: Cursor value for the first item in the next page.
        :param page_size: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        """
        validated_args = self.validate_arguments(
            typename=typename,
            first=first,
            last=last,
            after_cursor=after,
            before_cursor=before,
            page_size=page_size,
        )

        self.typename = typename
        self.after = validated_args.after
        self.before = validated_args.before
        self.first = validated_args.first
        self.last = validated_args.last
        self.page_size = page_size

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

    def validate_arguments(
        self,
        *,
        typename: str,
        first: int | None,
        last: int | None,
        after_cursor: str | None,
        before_cursor: str | None,
        page_size: int | None,
    ) -> ValidatedPaginationArgs:
        """Validate the given pagination arguments and return the validated arguments."""
        after = convert_after_cursor(after_cursor=after_cursor, typename=typename)
        before = convert_before_cursor(before_cursor=before_cursor, typename=typename)

        validate_before_and_after_bounds(after=after, before=before)

        validate_page_size(page_size=page_size)

        if first is not None:
            if not isinstance(first, int) or first <= 0:
                msg = "Argument 'first' must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg)

            if isinstance(page_size, int) and first > page_size:
                msg = f"Requesting first {first} records exceeds the maximum page size of {page_size}."
                raise GraphQLPaginationArgumentValidationError(msg)

        if last is not None:
            if not isinstance(last, int) or last <= 0:
                msg1 = "Argument 'last' must be a positive integer."
                raise GraphQLPaginationArgumentValidationError(msg1)

            if isinstance(page_size, int) and last > page_size:
                msg1 = f"Requesting last {last} records exceeds the maximum page size of {page_size}."
                raise GraphQLPaginationArgumentValidationError(msg1)

        # When no other filtering is applied, the default is to request the first page.
        if isinstance(page_size, int) and first is None and last is None:
            first = page_size

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
            self.total_count = F(undine_settings.PAGINATION_TOTAL_COUNT_KEY)  # type: ignore[assignment]

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
                self.start = Greatest(self.total_count - Value(self.last), Value(self.start))  # type: ignore[assignment,operator]
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

    def handle_page_info_field(self, field_name: str) -> None:
        """Update pagination requirements based on a requested `PageInfo` field."""
        # To know if there is a next page, we must know the total count.
        if field_name != "hasNextPage":
            self.requires_total_count = True

    def get_page(self, instances: list[TModel]) -> PaginationPage[TModel]:
        """Build the page of results for a top-level connection from the fetched instances."""
        has_next_page = (
            False if self.stop is None else True if self.total_count is None else self.stop < self.total_count
        )
        return PaginationPage(
            instances=instances,
            cursors=[offset_to_cursor(self.typename, self.start + index) for index in range(len(instances))],
            total_count=self.total_count or 0,
            has_next_page=has_next_page,
            has_previous_page=self.start > 0,
        )

    def get_prefetch_page(self, instances: list[TModel]) -> PaginationPage[TModel]:
        """
        Build the page of results for a nested connection from the fetched instances.

        Pagination arguments are read from the instances, since they are calculated in the database.
        They might not be available if the queryset is empty after pagination, but since they can be
        different for each prefetch partition, we cannot do anything about that.
        """
        total_count: int | None = None
        start: int = 0
        stop: int | None = None

        if instances:
            total_count = getattr(instances[0], undine_settings.PAGINATION_TOTAL_COUNT_KEY, None)
            start = getattr(instances[0], undine_settings.PAGINATION_START_INDEX_KEY, 0)
            stop = getattr(instances[0], undine_settings.PAGINATION_STOP_INDEX_KEY, None)

        has_next_page = False if stop is None else True if total_count is None else stop < total_count
        return PaginationPage(
            instances=instances,
            cursors=[offset_to_cursor(self.typename, start + index) for index in range(len(instances))],
            total_count=total_count or 0,
            has_next_page=has_next_page,
            has_previous_page=start > 0,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class OrderingDescriptor:
    """Describes a single value the paginated queryset is ordered by."""

    attname: str
    """The name the ordering value can be read from on a fetched row, and filtered by on the queryset."""

    order_by: OrderBy
    """The resolved `ORDER BY` expression this describes."""

    output_field: DjangoField
    """The model field the ordering value is serialized and deserialized with."""

    maybe_null: bool = True
    """Whether the ordering value can be `None`. Assume it can unless known otherwise."""

    nulls_first: bool = False
    """Whether null values are ordered before non-null values."""

    def get_comparison(self, value: Value | None, *, before: bool) -> Q | None:
        """Build a condition matching all rows ordered before/after the given value."""
        if value is None:
            # Nothing is ordered before the first null value, or after the last null value,
            # so those cases need no condition at all. In the other direction, every
            # non-null value is on the correct side of the null value.
            if self.nulls_first ^ before:
                return Q((f"{self.attname}{LOOKUP_SEP}isnull", False))
            return None

        lookup = "lt" if self.order_by.descending ^ before else "gt"
        comparison = Q((f"{self.attname}{LOOKUP_SEP}{lookup}", value))

        # Null values are never matched by a `lt`/`gt` comparison, so they have to be added explicitly.
        if self.maybe_null and self.nulls_first == before:
            comparison |= Q((f"{self.attname}{LOOKUP_SEP}isnull", True))

        return comparison

    def get_equality(self, value: Value | None) -> Q:
        """Build a condition matching all rows with the given ordering value."""
        if value is None:
            return Q((f"{self.attname}{LOOKUP_SEP}isnull", True))
        return Q((f"{self.attname}{LOOKUP_SEP}exact", value))

    def get_string_value(self, instance: Model) -> str | None:
        """Serialize this ordering value of the given instance so that it can be placed in a cursor."""
        value = getattr(instance, self.attname)
        if value is None:
            return None

        if self.output_field.attname == self.attname:
            return self.output_field.value_to_string(instance)

        # `Field.value_to_string` reads the value from an object instead of taking it directly,
        # so if the ordering value is not available under the output field's attname on the
        # instance, a stand-in object is required.
        holder = SimpleNamespace(**{self.output_field.attname: value})
        return self.output_field.value_to_string(holder)  # type: ignore[arg-type]


@dataclasses.dataclass(frozen=True, slots=True)
class KeysetOrdering:
    """A queryset prepared for keyset pagination together with the ordering it will be paginated by."""

    queryset: QuerySet
    descriptors: list[OrderingDescriptor]


def encode_base64(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_base64(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")


def offset_to_cursor(typename: str, offset: int) -> str:
    """Create the cursor string from an offset."""
    return encode_base64(f"connection:{typename}:{offset}")


def cursor_to_offset(typename: str, cursor: str) -> int:
    """Extract the offset from the cursor string."""
    return int(_cursor_payload(typename, cursor))


def values_to_cursor(typename: str, values: list[str | None]) -> str:
    """Create the cursor string from the ordering values of a single row."""
    payload = json.dumps(values, separators=(",", ":"))
    return encode_base64(f"connection:{typename}:{payload}")


def cursor_to_values(typename: str, cursor: str) -> list[str | None]:
    """Extract the ordering values of a single row from the cursor string."""
    values = json.loads(_cursor_payload(typename, cursor))
    if not isinstance(values, list) or any(value is not None and not isinstance(value, str) for value in values):
        msg = "Cursor does not contain a list of ordering values."
        raise ValueError(msg)
    return values


def _cursor_payload(typename: str, cursor: str) -> str:
    """Decode the cursor string and verify that it was created for the given typename."""
    decoded = decode_base64(cursor)
    prefix = f"connection:{typename}:"
    if not decoded.startswith(prefix):
        msg = f"Cursor was not created for type '{typename}'."
        raise ValueError(msg)
    return decoded.removeprefix(prefix)


def to_global_id(typename: str, object_id: str | int) -> str:
    """
    Takes a typename and an object ID specific to that type,
    and returns a "Global ID" that is unique among all types.
    """
    return encode_base64(f"ID:{typename}:{serialize_id(object_id)}")


def from_global_id(global_id: str) -> tuple[str, str | int]:
    """
    Takes the "Global ID" created by `to_global_id`,
    and returns the typename and object ID used to create it.
    """
    global_id = decode_base64(global_id)
    _, typename, object_id = global_id.split(":")
    if object_id.isdigit():
        return typename, int(object_id)
    return typename, object_id


def build_keyset_filter(descriptors: list[OrderingDescriptor], values: list[Value | None], *, before: bool) -> Q:
    """
    Build a condition matching all rows ordered before/after the row the given values were taken from.

    Since ordering can span multiple values, this is built as a nested comparison, where each
    level only applies if all the previous ordering values were equal:
    `a > x OR (a = x AND (b > y OR (b = y AND ...)))`
    """
    condition: Q | None = None

    for descriptor, value in zip(reversed(descriptors), reversed(values), strict=True):
        comparison = descriptor.get_comparison(value, before=before)

        if condition is None:
            condition = comparison
            continue

        equality = descriptor.get_equality(value)
        condition = equality & condition if comparison is None else comparison | (equality & condition)

    return condition if condition is not None else Q()


def _orders_nulls_first(order_by: OrderBy, *, nulls_first_by_default: bool) -> bool:
    """Are null values ordered before non-null values by the given `ORDER BY` expression?"""
    if order_by.nulls_first:
        return True
    if order_by.nulls_last:
        return False
    # No explicit null placement, so the database's default placement is used.
    return nulls_first_by_default != bool(order_by.descending)


def _add_row_number(queryset: QuerySet, *, related_name: str, order_by: list[OrderBy]) -> QuerySet:
    """Number the rows of the queryset, starting from one, separately for each prefetch partition."""
    row_number = Window(expression=RowNumber(), partition_by=F(related_name), order_by=order_by)
    return queryset.alias(**{undine_settings.PAGINATION_INDEX_KEY: row_number})


def _filter_by_row_number(queryset: QuerySet, *, lte: int) -> QuerySet:
    """Limit each prefetch partition to the given number of rows."""
    return queryset.filter(**{f"{undine_settings.PAGINATION_INDEX_KEY}__lte": lte})


def convert_after_cursor(*, after_cursor: str | None, typename: str) -> int | None:
    if after_cursor is None:
        return None

    try:
        return cursor_to_offset(typename, after_cursor)
    except Exception as error:
        msg = f"Argument 'after' is not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg) from error


def convert_before_cursor(*, before_cursor: str | None, typename: str) -> int | None:
    if before_cursor is None:
        return None

    try:
        return cursor_to_offset(typename, before_cursor)
    except Exception as error:
        msg = f"Argument 'before' is not a valid cursor for type '{typename}'."
        raise GraphQLPaginationArgumentValidationError(msg) from error


def validate_after_and_end(*, after: str | None, before: str | None) -> None:
    if after is not None and before is not None:
        msg = (
            "Cannot use both 'after' and 'before' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_first(*, first: int | None, last: int | None, before: str | None, page_size: int | None) -> None:
    if first is None:
        return

    if not isinstance(first, int) or first <= 0:
        msg = "Argument 'first' must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg)

    if isinstance(page_size, int) and first > page_size:
        msg = f"Requesting first {first} records exceeds the maximum page size of {page_size}."
        raise GraphQLPaginationArgumentValidationError(msg)

    if last is not None:
        msg = (
            "Cannot use both 'first' and 'last' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)

    if before is not None:
        msg = (
            "Cannot use both 'first' and 'before' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_last(*, last: int | None, first: int | None, after: str | None, page_size: int | None) -> None:
    if last is None:
        return

    if not isinstance(last, int) or last <= 0:
        msg1 = "Argument 'last' must be a positive integer."
        raise GraphQLPaginationArgumentValidationError(msg1)

    if isinstance(page_size, int) and last > page_size:
        msg1 = f"Requesting last {last} records exceeds the maximum page size of {page_size}."
        raise GraphQLPaginationArgumentValidationError(msg1)

    if first is not None:
        msg = (
            "Cannot use both 'first' and 'last' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)

    if after is not None:
        msg = (
            "Cannot use both 'last' and 'after' arguments together. "
            "Use 'first' and 'after' to paginate forward, or 'last' and 'before' to paginate backward."
        )
        raise GraphQLPaginationArgumentValidationError(msg)


def validate_before_and_after_bounds(*, after: int | None, before: int | None) -> None:
    if after is not None and (not isinstance(after, int) or after < 0):
        msg = "The node pointed with `after` does not exist."
        raise GraphQLPaginationArgumentValidationError(msg)

    if before is not None and (not isinstance(before, int) or before < 0):
        msg = "The node pointed with `before` does not exist."
        raise GraphQLPaginationArgumentValidationError(msg)

    if after is not None and before is not None and after >= before:
        msg = "The node pointed with `after` must be before the node pointed with `before`."
        raise GraphQLPaginationArgumentValidationError(msg)
