from typing import Any, Literal

from graphql import GraphQLInputType, GraphQLOutputType, GraphQLString

from undine.converters import convert_to_graphql_type


@convert_to_graphql_type.register
def _(_: Literal["foo", "bar"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString
