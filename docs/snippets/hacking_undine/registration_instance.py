from typing import Any

from graphql import GraphQLInputType, GraphQLOutputType

from undine.converters import convert_to_graphql_type
from undine.utils.model_utils import get_model_field


@convert_to_graphql_type.register
def _(ref: str, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    model_field = get_model_field(model=kwargs["model"], lookup=ref)
    return convert_to_graphql_type(model_field, **kwargs)
