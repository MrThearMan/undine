from __future__ import annotations

from graphql import GraphQLBoolean, GraphQLField, GraphQLNonNull, GraphQLString

from undine import InterfaceType, QueryType, UnionType
from undine.settings import undine_settings
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type
from undine.utils.reflection import is_subclass

from .pagination import CursorPaginationHandler

__all__ = [
    "Connection",
    "PageInfoType",
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
        :param pagination_handler: Handler to use for pagination.
        :param description: Description for the created GraphQL type.
        """
        self.query_type: type[QueryType] | None = ref if is_subclass(ref, QueryType) else None
        self.union_type: type[UnionType] | None = ref if is_subclass(ref, UnionType) else None
        self.interface_type: type[InterfaceType] | None = ref if is_subclass(ref, InterfaceType) else None

        self.page_size = page_size
        self.pagination_handler = pagination_handler
        self.description = description


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
