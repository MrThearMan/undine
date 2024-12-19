from __future__ import annotations

import base64
import dataclasses
from copy import copy
from typing import TYPE_CHECKING, Self

from django.db import models
from django.db.models.functions import Greatest, Least, RowNumber
from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString
from graphql.type.scalars import serialize_id

from undine.errors.exceptions import ConnectionQueryTypeNotNodeError, PaginationArgumentValidationError
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_interface_type, get_or_create_object_type
from undine.utils.model_utils import SubqueryCount

if TYPE_CHECKING:
    from undine import QueryType

__all__ = [
    "Connection",
    "Node",
    "PaginationArgs",
]


Node = get_or_create_interface_type(
    name="Node",
    description="An object with an ID",
    fields={
        "id": GraphQLField(
            GraphQLNonNull(GraphQLID),
            description="The ID of an object",
        ),
    },
)


class Connection:
    def __init__(
        self,
        query_type: type[QueryType],
        *,
        max_limit: int | None = undine_settings.CONNECTION_MAX_LIMIT,
    ) -> None:
        if Node not in query_type.__interfaces__:
            raise ConnectionQueryTypeNotNodeError(query_type=query_type)

        self.query_type = query_type
        self.max_limit = max_limit


@dataclasses.dataclass(slots=True)
class PaginationArgs:
    after: int | None
    """The index after which to start (exclusive)."""
    before: int | None
    """The index before which to stop (exclusive)."""
    first: int | None
    """The number of items to return from the start."""
    last: int | None
    """The number of items to return from the end (after evaluating first)."""
    max_limit: int | None
    """The maximum number of items allowed by the connection."""
    total_count: int | None = None
    """The total number of items that can be paginated."""

    @classmethod
    def from_connection_params(  # noqa: C901, PLR0912
        cls,
        first: int | None,
        last: int | None,
        offset: int | None,
        after: str | None,
        before: str | None,
        max_limit: int | None = None,
    ) -> Self:
        """
        Create pagination arguments from relay connection params while validating that the arguments are valid.

        :param first: Number of records to return from the beginning.
        :param last: Number of records to return from the end.
        :param offset: Number of records to skip from the beginning.
        :param after: Cursor value for the last record in the previous page.
        :param before: Cursor value for the first record in the next page.
        :param max_limit: Maximum limit for the number of records that can be requested.
        """
        after = cursor_to_offset(after) if after is not None else None
        before = cursor_to_offset(before) if before is not None else None

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

        if max_limit is not None and not isinstance(max_limit, int):
            msg = f"Pagination max limit must be None or an integer, but got: {max_limit!r}."
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

        # `total_count` is added after the optimization is done.
        return cls(after=after, before=before, first=first, last=last, max_limit=max_limit)

    def paginate_queryset(self, queryset: models.QuerySet) -> models.QuerySet:
        """
        Paginate a top-level queryset based on the given pagination arguments.

        Before this, the arguments should be validated so that:
         - `first` and `last` are positive integers or `None`
         - `after` and `before` are non-negative integers or `None`
         - If both `after` and `before` are given, `after` is less than or equal to `before`

        This function is based on the Relay pagination algorithm.
        See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm
        """
        if self.total_count is None:
            self.total_count = queryset.count()

        start: int = 0
        stop: int = self.total_count

        if self.after is not None:
            start = min(self.after, stop)
        if self.before is not None:
            stop = min(self.before, stop)
        if self.first is not None:
            stop = min(start + self.first, stop)
        if self.last is not None:
            start = max(stop - self.last, start)

        queryset._hints["_undine_total_count"] = self.total_count
        return queryset[start:stop]

    def paginate_prefetch_queryset(self, queryset: models.QuerySet, related_name: str) -> models.QuerySet:
        # TODO: Some optimizations here.

        start = models.Value(0)
        stop = models.F("_undine_total_count")

        queryset = queryset.annotate(
            _undine_total_count=SubqueryCount(
                queryset=queryset.filter(**{related_name: models.OuterRef(related_name)}),
            ),
        )

        if self.after is not None:
            start = Least(models.Value(self.after), stop)
        if self.before is not None:
            stop = Least(models.Value(self.before), stop)
        if self.first is not None:
            stop = Least(start + models.Value(self.first), stop)
        if self.last is not None:
            stop = Greatest(stop - models.Value(self.last), start)

        return queryset.annotate(
            _undine_pagination_start=start,
            _undine_pagination_stop=stop,
            _undine_pagination_index=(
                models.Window(
                    expression=RowNumber(),
                    partition_by=models.F(related_name),
                    order_by=queryset.query.order_by or copy(queryset.model._meta.ordering),
                )
                - models.Value(1)  # Start from zero.
            ),
        ).filter(
            _undine_pagination_index__gte=models.F("_undine_slice_start"),
            _undine_pagination_index__lt=models.F("_undine_slice_stop"),
        )


def encode_base64(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_base64(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")


def offset_to_cursor(offset: int) -> str:
    """Create the cursor string from an offset."""
    return encode_base64(f"{undine_settings.RELAY_CURSOR_PREFIX}:{offset}")


def cursor_to_offset(cursor: str) -> int:
    """Extract the offset from the cursor string."""
    return int(decode_base64(cursor).removeprefix(f"{undine_settings.RELAY_CURSOR_PREFIX}:"))


def to_global_id(typename: str, object_id: str | int) -> str:
    """
    Takes a typename and an object ID specific to that type,
    and returns a "Global ID" that is unique among all types.
    """
    return encode_base64(f"{typename}:{serialize_id(object_id)}")


def from_global_id(global_id: str) -> tuple[str, str | int]:
    """
    Takes the "Global ID" created by `to_global_id`,
    and returns the typename and object ID used to create it.
    """
    global_id = decode_base64(global_id)
    typename, object_id = global_id.split(":", 1)
    if object_id.isdigit():
        object_id = int(object_id)
    return typename, object_id


PageInfoType = get_or_create_object_type(
    name="PageInfo",
    description="Information about pagination in a connection.",
    fields={
        "hasNextPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="When paginating forwards, are there more items?",
        ),
        "hasPreviousPage": GraphQLField(
            GraphQLNonNull(GraphQLBoolean),
            description="When paginating backwards, are there more items?",
        ),
        "startCursor": GraphQLField(
            GraphQLString,  # null if no results
            description="When paginating backwards, the cursor to continue.",
        ),
        "endCursor": GraphQLField(
            GraphQLString,  # null if no results
            description="When paginating forwards, the cursor to continue.",
        ),
    },
)
