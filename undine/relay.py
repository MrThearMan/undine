from __future__ import annotations

import base64
from copy import copy
from typing import TYPE_CHECKING

from django.db.models import F, OuterRef, QuerySet, Subquery, Value, Window
from django.db.models.functions import Greatest, Least, RowNumber
from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString
from graphql.type.scalars import serialize_id

from undine.dataclasses import ValidatedPaginationArgs
from undine.errors.exceptions import ConnectionQueryTypeNotNodeError, PaginationArgumentValidationError
from undine.optimizer.prefetch_hack import register_for_prefetch_hack
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_interface_type, get_or_create_object_type
from undine.utils.model_utils import SubqueryCount

if TYPE_CHECKING:
    from undine import QueryType
    from undine.typing import CombinableExpression, ToManyField

__all__ = [
    "Connection",
    "Node",
    "PageInfoType",
    "PaginationHandler",
    "cursor_to_offset",
    "decode_base64",
    "encode_base64",
    "from_global_id",
    "offset_to_cursor",
    "to_global_id",
]


class PaginationHandler:
    """Handles pagination for Relay Connection based on the given arguments."""

    def __init__(
        self,
        *,
        typename: str,
        after: str | None = None,
        before: str | None = None,
        first: int | None = None,
        last: int | None = None,
        offset: int | None = None,
        max_limit: int | None = None,
    ) -> None:
        """
        Create a new PaginationHandler.

        :param first: Number of item to return from the start.
        :param last: Number of item to return from the end (after applying `first`).
        :param after: Cursor value for the last item in the previous page.
        :param before: Cursor value for the first item in the next page.
        :param offset: Number of item to skip from the start.
        :param max_limit: Maximum limit for the number of item that can be requested in a page. No limit if `None`.
        """
        validated_args = self.validate(
            typename=typename,
            first=first,
            last=last,
            offset=offset,
            after_cursor=after,
            before_cursor=before,
            max_limit=max_limit,
        )

        self.after = validated_args.after
        """The index after which to start (exclusive)."""

        self.before = validated_args.before
        """The index before which to stop (exclusive)."""

        self.first = validated_args.first
        """The number of items to return from the start."""

        self.last = validated_args.last
        """The number of items to return from the end (after evaluating first)."""

        self.max_limit = max_limit
        """Maximum limit for the number of item that can be requested in a page. No limit if `None`."""

        # Modified in `paginate_queryset` or `paginate_prefetch_queryset` if needed.
        self.total_count: int | None = None
        """The total number of items that can be paginated."""

        # Modified during optimization based on connection params.
        self.requires_total_count: bool = False
        """Whether the total count is required for this query."""

    @staticmethod
    def validate(  # noqa: C901, PLR0912
        *,
        typename: str,
        first: int | None,
        last: int | None,
        offset: int | None,
        after_cursor: str | None,
        before_cursor: str | None,
        max_limit: int | None,
    ) -> ValidatedPaginationArgs:
        """Validate the given pagination arguments and return the validated arguments."""
        try:
            after = cursor_to_offset(typename, after_cursor) if after_cursor is not None else None
        except Exception as error:
            msg = f"Argument 'after' is not a valid cursor for type '{typename}'."
            raise PaginationArgumentValidationError(msg) from error

        try:
            before = cursor_to_offset(typename, before_cursor) if before_cursor is not None else None
        except Exception as error:
            msg = f"Argument 'before' is not a valid cursor for type '{typename}'."
            raise PaginationArgumentValidationError(msg) from error

        if max_limit is not None and (not isinstance(max_limit, int) or max_limit < 1):
            msg = f"`max_limit` must be `None` or a positive integer, got: {max_limit!r}"
            raise PaginationArgumentValidationError(msg)

        if first is not None:
            if not isinstance(first, int) or first <= 0:
                msg = "Argument 'first' must be a positive integer."
                raise PaginationArgumentValidationError(msg)

            if isinstance(max_limit, int) and first > max_limit:
                msg = f"Requesting first {first} records exceeds the limit of {max_limit}."
                raise PaginationArgumentValidationError(msg)

        if last is not None:
            if not isinstance(last, int) or last <= 0:
                msg = "Argument 'last' must be a positive integer."
                raise PaginationArgumentValidationError(msg)

            if isinstance(max_limit, int) and last > max_limit:
                msg = f"Requesting last {last} records exceeds the limit of {max_limit}."
                raise PaginationArgumentValidationError(msg)

        if isinstance(max_limit, int) and first is None and last is None:
            first = max_limit

        if offset is not None:
            if after is not None or before is not None:
                msg = "Can only use either `offset` or `before`/`after` for pagination."
                raise PaginationArgumentValidationError(msg)
            if not isinstance(offset, int) or offset < 0:
                msg = "Argument `offset` must be a positive integer."
                raise PaginationArgumentValidationError(msg)

            # Convert offset to after cursor value. Note that after cursor dictates
            # a value _after_ which results should be returned, so we need to subtract
            # 1 from the offset to get the correct cursor value.
            if offset > 0:  # ignore zero offset
                after = offset - 1

        if after is not None and (not isinstance(after, int) or after < 0):
            msg = "The node pointed with `after` does not exist."
            raise PaginationArgumentValidationError(msg)

        if before is not None and (not isinstance(before, int) or before < 0):
            msg = "The node pointed with `before` does not exist."
            raise PaginationArgumentValidationError(msg)

        if after is not None and before is not None and after >= before:
            msg = "The node pointed with `after` must be before the node pointed with `before`."
            raise PaginationArgumentValidationError(msg)

        # Since `after` is also exclusive, we need to add 1 to it, so that slicing works correctly.
        if after is not None:
            after += 1

        return ValidatedPaginationArgs(after=after, before=before, first=first, last=last)

    def paginate_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Paginate a top-level queryset using queryset slicing.

        Pagination arguments are stored in the queryset's hints.

        This function is based on the Relay pagination algorithm.
        See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm
        """
        if self.requires_total_count:
            self.total_count = queryset.count()

        start: int = 0
        stop: int | None = self.total_count

        if self.after is not None:
            start = self.after if stop is None else min(self.after, stop)

        if self.before is not None:
            stop = self.before if stop is None else min(self.before, stop)

        if self.first is not None:
            stop = start + self.first if stop is None else min(start + self.first, stop)

        if self.last is not None:
            if stop is None:
                if self.total_count is None:
                    self.total_count = queryset.count()
                stop = self.total_count
            start = max(stop - self.last, start)

        queryset._hints[undine_settings.CONNECTION_TOTAL_COUNT_KEY] = self.total_count
        queryset._hints[undine_settings.CONNECTION_START_INDEX_KEY] = start
        queryset._hints[undine_settings.CONNECTION_STOP_INDEX_KEY] = stop
        return queryset[start:stop]

    def paginate_prefetch_queryset(self, queryset: QuerySet, related_field: ToManyField) -> QuerySet:
        """
        Paginate a prefetch queryset using a window function partitioned by the given related field.

        Pagination arguments are annotated to the queryset, since they are calculated in the database.
        There is the issue that they might not be available if the queryset is empty after pagination,
        but since they can be different for each prefetch parition, we cannot do anything about that.

        This function is based on the Relay pagination algorithm.
        See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm
        """
        related_name = related_field.remote_field.name

        start: CombinableExpression = Value(0)
        stop: CombinableExpression | None = None
        total_count: Subquery | None = None

        if self.requires_total_count:
            total_count = total_count_subquery(queryset, related_name)

        if self.after is not None:
            start = Value(self.after)

        if self.before is not None:
            stop = Value(self.before)

        if self.first is not None:
            stop = start + Value(self.first) if stop is None else Least(start + Value(self.first), stop)

        if self.last is not None:
            if stop is None:
                stop = total_count = total_count_subquery(queryset, related_name)
            start = Greatest(stop - Value(self.last), start)

        register_for_prefetch_hack(queryset, related_field)

        queryset = add_partition_index(queryset, related_name)

        queryset = queryset.annotate(**{undine_settings.CONNECTION_START_INDEX_KEY: start}).filter(
            **{f"{undine_settings.CONNECTION_INDEX_KEY}__gte": F(undine_settings.CONNECTION_START_INDEX_KEY)},
        )

        if stop is not None:
            queryset = queryset.annotate(**{undine_settings.CONNECTION_STOP_INDEX_KEY: stop}).filter(
                **{f"{undine_settings.CONNECTION_INDEX_KEY}__lt": F(undine_settings.CONNECTION_STOP_INDEX_KEY)},
            )

        if total_count is not None:
            queryset = queryset.annotate(**{undine_settings.CONNECTION_TOTAL_COUNT_KEY: total_count})

        return queryset


Node = get_or_create_interface_type(
    name="Node",
    description="An interface for objects with Global IDs.",
    fields={
        "id": GraphQLField(
            GraphQLNonNull(GraphQLID),
            description="The Global ID of an object.",
        ),
    },
)
"""The Relay `Node` interface."""


class Connection:
    """A Relay `Connection` for a list of Nodes."""

    def __init__(
        self,
        query_type: type[QueryType],
        *,
        max_limit: int | None = undine_settings.CONNECTION_MAX_LIMIT,
        pagination_handler: type[PaginationHandler] = PaginationHandler,
    ) -> None:
        """
        Create a new Connection.

        :param query_type: `QueryType` to use for the connection.
        :param max_limit: Maximum number of items to return in a page. No limit if `None`.
        :param pagination_handler: Handler to use for pagination.
        """
        if Node not in query_type.__interfaces__:
            raise ConnectionQueryTypeNotNodeError(query_type=query_type)

        self.query_type = query_type
        self.max_limit = max_limit
        self.pagination_handler = pagination_handler


def total_count_subquery(queryset: QuerySet, related_name: str) -> SubqueryCount:
    """Get a subquery for calculating total count, partitioned by the given related name."""
    return SubqueryCount(queryset=queryset.filter(**{related_name: OuterRef(related_name)}))


def add_partition_index(queryset: QuerySet, related_name: str) -> QuerySet:
    """Add an index to each instance in the queryset, paritioned by the given related name."""
    return queryset.alias(
        **{
            undine_settings.CONNECTION_INDEX_KEY: (
                Window(
                    expression=RowNumber(),
                    partition_by=F(related_name),
                    order_by=queryset.query.order_by or copy(queryset.model._meta.ordering),
                )
                - Value(1)  # Start from zero.
            ),
        },
    )


def encode_base64(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_base64(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")


def offset_to_cursor(typename: str, offset: int) -> str:
    """Create the cursor string from an offset."""
    return encode_base64(f"connection:{typename}:{offset}")


def cursor_to_offset(typename: str, cursor: str) -> int:
    """Extract the offset from the cursor string."""
    return int(decode_base64(cursor).removeprefix(f"connection:{typename}:"))


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
        object_id = int(object_id)
    return typename, object_id


PageInfoType = get_or_create_object_type(
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
