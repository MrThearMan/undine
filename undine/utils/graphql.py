"""Utils that should be sorted into different files later."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import GraphQLList, GraphQLNonNull

if TYPE_CHECKING:
    from undine.typing import TGraphQLType


__all__ = [
    "maybe_list_or_non_null",
]


def maybe_list_or_non_null(graphql_type: TGraphQLType, *, many: bool, required: bool) -> TGraphQLType:
    """Wrap the given GraphQL type as a list of non-null items and/or non-null if needed."""
    if many is True and not isinstance(graphql_type, GraphQLList):
        if not isinstance(graphql_type, GraphQLNonNull):
            graphql_type = GraphQLNonNull(graphql_type)
        graphql_type = GraphQLList(graphql_type)
    if required is True and not isinstance(graphql_type, GraphQLNonNull):
        graphql_type = GraphQLNonNull(graphql_type)
    return graphql_type
