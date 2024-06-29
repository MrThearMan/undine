# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLArgument, GraphQLArgumentMap

from undine.parsers import docstring_parser, parse_parameters
from undine.typing import Ref
from undine.utils import TypeDispatcher, get_schema_name

from .type_to_graphql_input_type import convert_type_to_graphql_input_type

__all__ = [
    "convert_ref_to_graphql_argument_map",
]


convert_ref_to_graphql_argument_map = TypeDispatcher[Ref, GraphQLArgumentMap]()


@convert_ref_to_graphql_argument_map.register
def convert_function(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref, depth=2)
    docstring = getattr(ref, "__doc__", "")
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


@convert_ref_to_graphql_argument_map.register
def convert_property(ref: property, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_ref_to_graphql_argument_map.register
def convert_model_field(ref: models.Field, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_ref_to_graphql_argument_map.register
    def convert_model_node(ref: type[ModelGQLType], *, many: bool, top_level: bool) -> GraphQLArgumentMap:
        if many:
            return {name: ftr.as_argument() for name, ftr in ref.__filters__.items()}
        if top_level:
            return ref.__lookup_argument__
        return {}

    @convert_ref_to_graphql_argument_map.register
    def convert_deferred_type(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLArgumentMap:
        return convert_ref_to_graphql_argument_map(ref.get_type(), **kwargs)

    @convert_ref_to_graphql_argument_map.register
    def convert_deferred_type_union(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLArgumentMap:
        # TODO: Union args?
        return {}
