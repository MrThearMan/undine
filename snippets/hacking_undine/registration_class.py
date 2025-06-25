from typing import Any

from graphql import GraphQLInputType, GraphQLOutputType, GraphQLString

from undine.converters import convert_to_graphql_type


@convert_to_graphql_type.register
def _(ref: type[str], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString
