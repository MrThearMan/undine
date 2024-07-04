from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLList, GraphQLNonNull

from undine.parsers import docstring_parser, parse_parameters
from undine.settings import undine_settings
from undine.typing import FieldRef
from undine.utils import TypeDispatcher, get_docstring, get_schema_name

from .type_to_graphql_input_type import convert_type_to_graphql_input_type

__all__ = [
    "convert_field_ref_to_graphql_argument_map",
]


convert_field_ref_to_graphql_argument_map = TypeDispatcher[FieldRef, GraphQLArgumentMap]()


@convert_field_ref_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref)
    docstring = get_docstring(ref)
    arg_descriptions = docstring_parser.parse_arg_descriptions(docstring)
    deprecation_descriptions = docstring_parser.parse_deprecations(docstring)
    return {
        get_schema_name(param.name): GraphQLArgument(
            type_=convert_type_to_graphql_input_type(param.annotation),
            default_value=param.default_value,
            description=arg_descriptions.get(param.name),
            deprecation_reason=deprecation_descriptions.get(param.name),
        )
        for param in params
    }


@convert_field_ref_to_graphql_argument_map.register
def _(_: property | models.Field, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.model_graphql import ModelGQLType
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_field_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLType], *, many: bool, top_level: bool) -> GraphQLArgumentMap:
        if many:
            arguments: GraphQLArgumentMap = {}
            if ref.__filters__:
                arguments[undine_settings.FILTER_INPUT_TYPE_KEY] = GraphQLArgument(
                    ref.__filters__.__input_object__,
                )
            if ref.__ordering__:
                arguments[undine_settings.ORDERING_INPUT_TYPE_KEY] = GraphQLArgument(
                    GraphQLList(GraphQLNonNull(ref.__ordering__.__ordering_enum__)),
                )
            return arguments

        if top_level:
            return ref.__lookup_argument_map__

        return {}

    @convert_field_ref_to_graphql_argument_map.register
    def _(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLArgumentMap:
        return convert_field_ref_to_graphql_argument_map(ref.get_type(), **kwargs)

    @convert_field_ref_to_graphql_argument_map.register
    def _(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLArgumentMap:
        return {}
