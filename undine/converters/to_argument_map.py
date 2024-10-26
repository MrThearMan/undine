from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLArgument, GraphQLArgumentMap, GraphQLList, GraphQLNonNull

from undine.converters.to_graphql_type import convert_to_graphql_type
from undine.parsers import docstring_parser, parse_parameters
from undine.settings import undine_settings
from undine.typing import CombinableExpression, EntrypointRef, FieldRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_utils import get_model_field
from undine.utils.text import get_docstring, get_schema_name

__all__ = [
    "convert_to_graphql_argument_map",
]


convert_to_graphql_argument_map = FunctionDispatcher[EntrypointRef | FieldRef, GraphQLArgumentMap]()
"""
Parse a GraphQLArgumentMap from the given undine.Entrypoint or undine.Field reference.

:param ref: The reference to convert.
:param many: Whether the argument map is for a list field.
:param entrypoint. (Optional) Whether the argument map is for an entrypoint. Defaults to `False`.
"""


@convert_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref)
    docstring = get_docstring(ref)
    arg_descriptions = docstring_parser.parse_arg_descriptions(docstring)
    deprecation_descriptions = docstring_parser.parse_deprecations(docstring)

    arguments: GraphQLArgumentMap = {}
    for param in params:
        graphql_type, nullable = convert_to_graphql_type(param.annotation, return_nullable=True)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        arguments[get_schema_name(param.name)] = GraphQLArgument(
            type_=graphql_type,
            default_value=param.default_value,
            description=arg_descriptions.get(param.name),
            deprecation_reason=deprecation_descriptions.get(param.name),
        )

    return arguments


@convert_to_graphql_argument_map.register
def _(_: ModelField | CombinableExpression, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_to_graphql_argument_map(ref.get_type(), **kwargs)


@convert_to_graphql_argument_map.register
def _(_: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from undine import MutationType, QueryType

    @convert_to_graphql_argument_map.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLArgumentMap:
        if kwargs.get("entrypoint", False):
            if kwargs["many"]:
                return convert_to_graphql_argument_map(ref, many=True)

            field = get_model_field(model=ref.__model__, lookup=ref.__lookup_field__)
            input_type = convert_to_graphql_type(field, model=ref.__model__)
            return {get_schema_name(ref.__lookup_field__): GraphQLArgument(input_type)}

        if not kwargs["many"]:
            return {}

        arguments: GraphQLArgumentMap = {}

        if ref.__filterset__:
            input_type = ref.__filterset__.__input_type__()
            arguments[undine_settings.FILTER_INPUT_TYPE_KEY] = GraphQLArgument(input_type)

        if ref.__orderset__:
            enum_type = ref.__orderset__.__enum_type__()
            enum_type = GraphQLList(GraphQLNonNull(enum_type))
            arguments[undine_settings.ORDER_BY_INPUT_TYPE_KEY] = GraphQLArgument(enum_type)

        return arguments

    @convert_to_graphql_argument_map.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLArgumentMap:
        if kwargs["many"]:
            pass  # TODO:

        input_type = ref.__input_type__()
        input_type = GraphQLNonNull(input_type)
        return {undine_settings.MUTATION_INPUT_KEY: GraphQLArgument(input_type)}
