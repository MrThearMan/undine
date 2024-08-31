from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLNonNull

from undine.parsers import parse_model_field
from undine.settings import undine_settings
from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import get_schema_name

from .field_ref_to_graphql_argument_map import convert_field_ref_to_graphql_argument_map
from .model_field_to_graphql_input_type import convert_model_field_to_graphql_input_type

__all__ = [
    "convert_entrypoint_ref_to_graphql_argument_map",
]


convert_entrypoint_ref_to_graphql_argument_map = TypeDispatcher[FieldRef, GraphQLArgumentMap]()


@convert_entrypoint_ref_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    many: bool = kwargs["many"]
    return convert_field_ref_to_graphql_argument_map(ref, many=many)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLMutation, ModelGQLType

    @convert_entrypoint_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> GraphQLArgumentMap:
        many: bool = kwargs["many"]
        if many:
            return convert_field_ref_to_graphql_argument_map(ref, many=many)

        field: models.Field = (
            ref.__model__._meta.pk
            if ref.__lookup_field__ == "pk"
            else parse_model_field(model=ref.__model__, lookup=ref.__lookup_field__)
        )
        field_name: str = "pk" if field.primary_key and undine_settings.USE_PK_FIELD_NAME else field.name
        return {get_schema_name(field_name): GraphQLArgument(convert_model_field_to_graphql_input_type(field))}

    @convert_entrypoint_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLArgumentMap:
        return {
            undine_settings.MUTATION_INPUT_TYPE_KEY: GraphQLArgument(GraphQLNonNull(ref.__input_type__)),
        }
