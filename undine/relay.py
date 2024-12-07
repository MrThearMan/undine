from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString

from undine.settings import undine_settings
from undine.utils.graphql import get_or_create_interface_type, get_or_create_object_type

if TYPE_CHECKING:
    from undine import QueryType

__all__ = [
    "Connection",
    "Node",
]


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
        self.query_type = query_type
        self.max_limit = max_limit
