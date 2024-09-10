from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLNonNull

from undine.converters.fields.to_argument_map import convert_field_ref_to_graphql_argument_map
from undine.converters.model_fields.to_graphql_type import convert_model_field_to_graphql_type
from undine.settings import undine_settings
from undine.typing import EntrypointRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.model_utils import get_model_field
from undine.utils.text import get_schema_name

__all__ = [
    "convert_entrypoint_ref_to_graphql_argument_map",
]


convert_entrypoint_ref_to_graphql_argument_map = TypeDispatcher[EntrypointRef, GraphQLArgumentMap]()
"""Parse a GraphQL argument map from the given Undine Entrypoint reference."""


@convert_entrypoint_ref_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_field_ref_to_graphql_argument_map(ref, many=kwargs["many"])


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLMutation, ModelGQLType

    @convert_entrypoint_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> GraphQLArgumentMap:
        if kwargs["many"]:
            return convert_field_ref_to_graphql_argument_map(ref, many=True)

        field = get_model_field(model=ref.__model__, lookup=ref.__lookup_field__)
        field_name = field.name
        if field.primary_key and undine_settings.USE_PK_FIELD_NAME:
            field_name = "pk"

        input_type = convert_model_field_to_graphql_type(field)
        return {get_schema_name(field_name): GraphQLArgument(input_type)}

    @convert_entrypoint_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLArgumentMap:
        input_type = ref.__input_type__(entrypoint=True)
        return {undine_settings.MUTATION_INPUT_TYPE_KEY: GraphQLArgument(GraphQLNonNull(input_type))}
