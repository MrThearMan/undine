from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLList, GraphQLNonNull

from undine.converters.to_graphql_type import convert_type_to_graphql_type
from undine.parsers import docstring_parser, parse_parameters
from undine.settings import undine_settings
from undine.typing import CombinableExpression, FieldRef, ModelField
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion
from undine.utils.text import get_docstring, get_schema_name

__all__ = [
    "convert_field_ref_to_graphql_argument_map",
]


convert_field_ref_to_graphql_argument_map = FunctionDispatcher[FieldRef, GraphQLArgumentMap]()
"""Parse a GraphQL argument map from the given Undine Field reference."""


@convert_field_ref_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref)
    docstring = get_docstring(ref)
    arg_descriptions = docstring_parser.parse_arg_descriptions(docstring)
    deprecation_descriptions = docstring_parser.parse_deprecations(docstring)

    arguments: GraphQLArgumentMap = {}
    for param in params:
        graphql_type, nullable = convert_type_to_graphql_type(param.annotation, return_nullable=True)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        arguments[get_schema_name(param.name)] = GraphQLArgument(
            type_=graphql_type,
            default_value=param.default_value,
            description=arg_descriptions.get(param.name),
            deprecation_reason=deprecation_descriptions.get(param.name),
        )

    return arguments


@convert_field_ref_to_graphql_argument_map.register
def _(_: ModelField | CombinableExpression, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_field_ref_to_graphql_argument_map.register
def _(ref: LazyModelGQLType, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_field_ref_to_graphql_argument_map(ref.get_type(), **kwargs)


@convert_field_ref_to_graphql_argument_map.register
def _(ref: LazyModelGQLTypeUnion, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLType

    @convert_field_ref_to_graphql_argument_map.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> GraphQLArgumentMap:
        if not kwargs["many"]:
            return {}

        arguments: GraphQLArgumentMap = {}
        if ref.__filters__:
            input_type = ref.__filters__.__input_type__()
            arguments[undine_settings.FILTER_INPUT_TYPE_KEY] = GraphQLArgument(input_type)
        if ref.__ordering__:
            enum_type = ref.__ordering__.__enum_type__()
            enum_type = GraphQLList(GraphQLNonNull(enum_type))
            arguments[undine_settings.ORDER_BY_INPUT_TYPE_KEY] = GraphQLArgument(enum_type)
        return arguments
