from typing import Any

from django.db.models import BooleanField, NullBooleanField
from graphql import GraphQLBoolean, GraphQLInputType, GraphQLOutputType

from undine.converters import convert_to_graphql_type


@convert_to_graphql_type.register
def _(ref: BooleanField, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean


# Uses the implementation for BooleanField, since NullBooleanField inherits from BooleanField.
convert_to_graphql_type(NullBooleanField())
