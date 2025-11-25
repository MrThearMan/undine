from __future__ import annotations

import base64

from graphql import GraphQLBoolean, GraphQLField, GraphQLID, GraphQLNonNull, GraphQLString
from graphql.type.scalars import serialize_id

from undine import InterfaceField, InterfaceType, QueryType, UnionType
from undine.pagination import PaginationHandler
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.reflection import is_subclass

__all__ = [
    "Connection",
    "Node",
    "PageInfoType",
    "cursor_to_offset",
    "decode_base64",
    "encode_base64",
    "from_global_id",
    "offset_to_cursor",
    "to_global_id",
]


class Node(InterfaceType):
    """An interface for objects with Global IDs."""

    id = InterfaceField(GraphQLNonNull(GraphQLID), description="The Global ID of an object.", field_name="pk")


class Connection:
    """A wrapper for paginating a `QueryType` using Relay Connections."""

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
        Create a new Connection.

        :param ref: The `QueryType`, `UnionType`, or `InterfaceType` to use.
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
        return typename, int(object_id)
    return typename, object_id


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
