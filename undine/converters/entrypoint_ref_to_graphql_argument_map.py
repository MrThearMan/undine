from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLNonNull

from undine.settings import undine_settings
from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher

from .field_ref_to_graphql_argument_map import convert_field_ref_to_graphql_argument_map

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

        return ref.__lookup_argument_map__

    @convert_entrypoint_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLArgumentMap:
        return {
            undine_settings.MUTATION_INPUT_TYPE_KEY: GraphQLArgument(GraphQLNonNull(ref.__input_object__)),
        }
