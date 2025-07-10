from typing import Any

from django.db.models import CharField, TextField
from graphql import GraphQLInputType, GraphQLOutputType, GraphQLString

from undine.converters import convert_to_graphql_type


@convert_to_graphql_type.register
def _(_: CharField | TextField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString
