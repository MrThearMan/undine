from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString

from undine.dataclasses import PaginationArgs
from undine.errors.exceptions import ConnectionQueryTypeNotNodeError, PaginationArgumentValidationError
from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_interface_type, get_or_create_object_type

if TYPE_CHECKING:
    from undine import QueryType

__all__ = [
    "Connection",
    "Node",
    "calculate_queryset_slice",
    "validate_pagination_args",
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


def validate_pagination_args(  # noqa: C901, PLR0912
    first: int | None,
    last: int | None,
    offset: int | None,
    after: str | None,
    before: str | None,
    max_limit: int | None = None,
) -> PaginationArgs:
    """
    Validate the pagination arguments and return a dictionary with the validated values.

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

    # `size` is added after the optimization is done.
    return PaginationArgs(after=after, before=before, first=first, last=last, max_limit=max_limit)


def calculate_queryset_slice(pagination_args: PaginationArgs) -> slice:
    """
    Calculate queryset slicing based on the provided arguments.
    Before this, the arguments should be validated so that:
     - `size` is not `None`
     - `first` and `last`, positive integers or `None`
     - `after` and `before` are non-negative integers or `None`
     - If both `after` and `before` are given, `after` is less than or equal to `before`

    This function is based on the Relay pagination algorithm.
    See. https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm

    :param pagination_args: The pagination arguments.
    """
    #
    # Start from form fetching max number of items.
    #
    start: int = 0
    stop: int = pagination_args.size
    #
    # If `after` is given, change the start index to `after`.
    # If `after` is greater than the current queryset size, change it to `size`.
    #
    if pagination_args.after is not None:
        start = min(pagination_args.after, stop)
    #
    # If `before` is given, change the stop index to `before`.
    # If `before` is greater than the current queryset size, change it to `size`.
    #
    if pagination_args.before is not None:
        stop = min(pagination_args.before, stop)
    #
    # If first is given, and it's smaller than the current queryset size,
    # change the stop index to `start + first`
    # -> Length becomes that of `first`, and the items after it have been removed.
    #
    if pagination_args.first is not None and pagination_args.first < (stop - start):
        stop = start + pagination_args.first
    #
    # If last is given, and it's smaller than the current queryset size,
    # change the start index to `stop - last`.
    # -> Length becomes that of `last`, and the items before it have been removed.
    #
    if pagination_args.last is not None and pagination_args.last < (stop - start):
        start = stop - pagination_args.last

    return slice(start, stop)


def encode_cursor(string: str) -> str:
    return base64.b64encode(string.encode("utf-8")).decode("ascii")


def decode_cursor(string: str) -> str:
    return base64.b64decode(string.encode("ascii")).decode("utf-8")


PREFIX = "arrayconnection:"


def offset_to_cursor(offset: int) -> str:
    """Create the cursor string from an offset."""
    return encode_cursor(f"{PREFIX}{offset}")


def cursor_to_offset(cursor: str) -> int:
    """Extract the offset from the cursor string."""
    return int(decode_cursor(cursor).removeprefix(PREFIX))


def to_global_id(typename: str, object_id: str | int) -> str:
    """
    Takes a typename and an object ID specific to that type,
    and returns a "Global ID" that is unique among all types.
    """
    return encode_cursor(f"{typename}:{GraphQLID.serialize(object_id)}")


def from_global_id(global_id: str) -> tuple[str, str | int]:
    """
    Takes the "Global ID" created by `to_global_id`,
    and returns the typename and object ID used to create it.
    """
    global_id = decode_cursor(global_id)
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
