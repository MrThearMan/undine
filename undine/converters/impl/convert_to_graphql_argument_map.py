from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import F
from graphql import (
    GraphQLArgument,
    GraphQLArgumentMap,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLString,
    GraphQLType,
)

from undine import Calculation, InterfaceType, MutationType, QueryType, UnionType
from undine.converters import convert_to_graphql_argument_map, convert_to_graphql_type
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.exceptions import RegistryMissingTypeError
from undine.parsers import docstring_parser, parse_is_nullable, parse_parameters
from undine.relay import Connection, Node
from undine.settings import undine_settings
from undine.typing import CombinableExpression, ModelField, RelatedField
from undine.utils.model_utils import get_model_field
from undine.utils.text import get_docstring, to_schema_name

# --- Python types -------------------------------------------------------------------------------------------------


@convert_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref)
    docstring = get_docstring(ref)
    arg_descriptions = docstring_parser.parse_arg_descriptions(docstring)
    deprecation_descriptions = docstring_parser.parse_deprecations(docstring)

    arguments: GraphQLArgumentMap = {}
    kwargs["is_input"] = True
    for param in params:
        graphql_type = convert_to_graphql_type(param.annotation, **kwargs)
        nullable = parse_is_nullable(param.annotation)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        arguments[to_schema_name(param.name)] = GraphQLArgument(
            graphql_type,
            default_value=param.default_value,
            description=arg_descriptions.get(param.name),
            deprecation_reason=deprecation_descriptions.get(param.name),
            out_name=param.name,
        )

    return arguments


# --- Model fields -------------------------------------------------------------------------------------------------


@convert_to_graphql_argument_map.register
def _(_: ModelField | CombinableExpression | F, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(_: RelatedField, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> GraphQLArgumentMap:  # pragma: no cover
    return {}


# --- Custom types -------------------------------------------------------------------------------------------------


@convert_to_graphql_argument_map.register
def _(ref: type[QueryType], **kwargs: Any) -> GraphQLArgumentMap:
    if not kwargs["many"]:
        if not kwargs.get("entrypoint"):
            return {}

        field = get_model_field(model=ref.__model__, lookup="pk")
        input_type = convert_to_graphql_type(field, model=ref.__model__)
        input_type = GraphQLNonNull(input_type)
        return {"pk": GraphQLArgument(input_type, out_name="pk")}

    arguments: GraphQLArgumentMap = {}

    if ref.__filterset__:
        input_type = ref.__filterset__.__input_type__()
        arguments[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY] = GraphQLArgument(input_type)

    if ref.__orderset__:
        enum_type = ref.__orderset__.__enum_type__()
        input_type = GraphQLList(GraphQLNonNull(enum_type))
        arguments[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY] = GraphQLArgument(input_type)

    return arguments


@convert_to_graphql_argument_map.register
def _(ref: type[MutationType], **kwargs: Any) -> GraphQLArgumentMap:
    input_type = ref.__input_type__()

    arguments: GraphQLArgumentMap = {}

    arg_type: GraphQLInputType = GraphQLNonNull(input_type)
    if kwargs["many"]:
        arg_type = GraphQLNonNull(GraphQLList(arg_type))

    arguments[undine_settings.MUTATION_INPUT_DATA_KEY] = GraphQLArgument(arg_type)
    return arguments


@convert_to_graphql_argument_map.register
def _(ref: type[UnionType], **kwargs: Any) -> GraphQLArgumentMap:
    kwargs["many"] = True

    arguments: GraphQLArgumentMap = {}

    for model, query_type in ref.__query_types_by_model__.items():
        args = convert_to_graphql_argument_map(query_type, **kwargs)

        if undine_settings.QUERY_TYPE_FILTER_INPUT_KEY in args:
            filter_key = f"{undine_settings.QUERY_TYPE_FILTER_INPUT_KEY}{model.__name__}"
            arguments[filter_key] = args[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY]

        if undine_settings.QUERY_TYPE_ORDER_INPUT_KEY in args:
            order_by_key = f"{undine_settings.QUERY_TYPE_ORDER_INPUT_KEY}{model.__name__}"
            arguments[order_by_key] = args[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY]

    return arguments


@convert_to_graphql_argument_map.register
def _(ref: LazyRelation, **kwargs: Any) -> GraphQLArgumentMap:
    try:
        value = ref.get_type()
    except RegistryMissingTypeError:
        value = ref.field

    return convert_to_graphql_argument_map(value, **kwargs)


@convert_to_graphql_argument_map.register
def _(_: LazyGenericForeignKey, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(ref: LazyLambda, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_to_graphql_argument_map(ref.callback(), **kwargs)


@convert_to_graphql_argument_map.register
def _(_: TypeRef, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(ref: type[Calculation], **kwargs: Any) -> GraphQLArgumentMap:
    arguments: GraphQLArgumentMap = {}

    for arg in ref.__arguments__.values():
        arguments[arg.schema_name] = arg.as_graphql_argument()

    return arguments


@convert_to_graphql_argument_map.register
def _(ref: Connection, **kwargs: Any) -> GraphQLArgumentMap:
    kwargs["many"] = True
    arguments = convert_to_graphql_argument_map(ref.query_type, **kwargs)

    return {
        "after": GraphQLArgument(
            GraphQLString,
            description="Only return items in the connection that come after this cursor.",
            out_name="after",
        ),
        "before": GraphQLArgument(
            GraphQLString,
            description="Only return items in the connection that come before this cursor.",
            out_name="before",
        ),
        "first": GraphQLArgument(
            GraphQLInt,
            description="Number of items to return from the start.",
            out_name="first",
        ),
        "last": GraphQLArgument(
            GraphQLInt,
            description="Number of items to return from the end (after evaluating first).",
            out_name="last",
        ),
        "offset": GraphQLArgument(
            GraphQLInt,
            description="Number of items to skip from the start.",
            out_name="offset",
        ),
        **arguments,
    }


@convert_to_graphql_argument_map.register
def _(ref: type[InterfaceType], **kwargs: Any) -> GraphQLArgumentMap:
    kwargs["many"] = True

    arguments: GraphQLArgumentMap = {}

    for query_type in ref.__concrete_implementations__():
        model = query_type.__model__
        args = convert_to_graphql_argument_map(query_type, **kwargs)

        if undine_settings.QUERY_TYPE_FILTER_INPUT_KEY in args:
            filter_key = f"{undine_settings.QUERY_TYPE_FILTER_INPUT_KEY}{model.__name__}"
            arguments[filter_key] = args[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY]

        if undine_settings.QUERY_TYPE_ORDER_INPUT_KEY in args:
            order_by_key = f"{undine_settings.QUERY_TYPE_ORDER_INPUT_KEY}{model.__name__}"
            arguments[order_by_key] = args[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY]

    return arguments


@convert_to_graphql_argument_map.register
def _(ref: type[Node], **kwargs: Any) -> GraphQLArgumentMap:
    return {
        ref.id.schema_name: GraphQLArgument(
            ref.id.output_type,  # type: ignore[arg-type]
            description=ref.id.description,
            out_name=ref.id.name,
        ),
    }


# --- GraphQL types ------------------------------------------------------------------------------------------------


@convert_to_graphql_argument_map.register
def _(_: GraphQLType, **kwargs: Any) -> GraphQLArgumentMap:
    return {}
