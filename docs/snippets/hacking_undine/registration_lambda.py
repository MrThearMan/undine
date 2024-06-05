from typing import Any

from graphql import GraphQLInputType, GraphQLOutputType, GraphQLString

from undine.converters import convert_to_graphql_type
from undine.typing import Lambda


@convert_to_graphql_type.register
def _(_: Lambda, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString
