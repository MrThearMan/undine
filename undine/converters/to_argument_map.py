from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db.models import F
from graphql import (
    GraphQLArgument,
    GraphQLArgumentMap,
    GraphQLBoolean,
    GraphQLEnumValue,
    GraphQLID,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLString,
    GraphQLType,
)

from undine.converters.to_graphql_type import convert_to_graphql_type
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.parsers import docstring_parser, parse_parameters
from undine.settings import undine_settings
from undine.typing import CombinableExpression, EntrypointRef, FieldRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.graphql import get_or_create_graphql_enum
from undine.utils.model_utils import get_model_field
from undine.utils.text import get_docstring, to_schema_name

__all__ = [
    "convert_to_graphql_argument_map",
]


convert_to_graphql_argument_map = FunctionDispatcher[EntrypointRef | FieldRef, GraphQLArgumentMap]()
"""
Parse a GraphQLArgumentMap from the given 'undine.Entrypoint' or 'undine.Field' reference.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - many: Whether the argument map is for a list field.
 - entrypoint: (Optional) Whether the argument map is for an entrypoint. Interpret as `False` if missing.
"""


@convert_to_graphql_argument_map.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLArgumentMap:
    params = parse_parameters(ref)
    docstring = get_docstring(ref)
    arg_descriptions = docstring_parser.parse_arg_descriptions(docstring)
    deprecation_descriptions = docstring_parser.parse_deprecations(docstring)

    arguments: GraphQLArgumentMap = {}
    kwargs["is_input"] = True
    for param in params:
        graphql_type, nullable = convert_to_graphql_type(param.annotation, return_nullable=True, **kwargs)
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


@convert_to_graphql_argument_map.register
def _(_: ModelField | CombinableExpression | F, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_to_graphql_argument_map(ref.get_type(), **kwargs)


@convert_to_graphql_argument_map.register
def _(_: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


@convert_to_graphql_argument_map.register
def _(ref: LazyLambdaQueryType, **kwargs: Any) -> GraphQLArgumentMap:
    return convert_to_graphql_argument_map(ref.callback(), **kwargs)


@convert_to_graphql_argument_map.register
def _(ref: Calculated, **kwargs: Any) -> GraphQLArgumentMap:
    arguments: GraphQLArgumentMap = {}
    kwargs["is_input"] = True
    for param in ref.parameters:
        graphql_type, nullable = convert_to_graphql_type(param.annotation, return_nullable=True, **kwargs)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        arguments[to_schema_name(param.name)] = GraphQLArgument(
            graphql_type,
            default_value=param.default_value,
            description=param.docstring,
            out_name=param.name,
        )

    return arguments


@convert_to_graphql_argument_map.register
def _(_: GraphQLType, **kwargs: Any) -> GraphQLArgumentMap:
    return {}


def load_deferred() -> None:  # noqa: C901
    # See. `undine.apps.UndineConfig.load_deferred()` for explanation.
    from undine import MutationType, QueryType
    from undine.relay import Connection, Node

    @convert_to_graphql_argument_map.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLArgumentMap:
        if not kwargs["many"]:
            if not kwargs.get("entrypoint", False):
                return {}

            # TODO: Suport custom lookups, e.g. GlobalID.
            field = get_model_field(model=ref.__model__, lookup="pk")
            input_type = convert_to_graphql_type(field, model=ref.__model__)
            input_type = GraphQLNonNull(input_type)
            return {"pk": GraphQLArgument(input_type, out_name="pk")}

        arguments: GraphQLArgumentMap = {}

        if ref.__filterset__:
            input_type = ref.__filterset__.__input_type__()
            arguments[undine_settings.FILTER_INPUT_TYPE_KEY] = GraphQLArgument(input_type)

        if ref.__orderset__:
            input_type = ref.__orderset__.__input_type__()
            arguments[undine_settings.ORDER_BY_INPUT_TYPE_KEY] = GraphQLArgument(input_type)

        return arguments

    @convert_to_graphql_argument_map.register
    def _(ref: type[MutationType], **kwargs: Any) -> GraphQLArgumentMap:
        input_type = ref.__input_type__()
        if not isinstance(input_type, GraphQLNonNull):
            input_type = GraphQLNonNull(input_type)

        arguments: GraphQLArgumentMap = {}

        if kwargs["many"]:
            if ref.__mutation_kind__ == "create":
                arguments["batchSize"] = GraphQLArgument(
                    GraphQLInt,
                    default_value=None,
                    description=(
                        "How many objects are created in a single query. "
                        "The default is to create all objects in one batch, "
                        "except for SQLite where the default is such that "
                        "at most 999 variables per query are used."
                    ),
                    out_name="batch_size",
                )
                arguments["ignoreConflicts"] = GraphQLArgument(
                    GraphQLBoolean,
                    default_value=False,
                    description=(
                        "When set to `True`, tells the database to ignore failure to insert any rows "
                        "that fail constraints such as duplicate unique values. "
                        "Using this parameter prevents Django from setting the primary key for created objects, "
                        "meaning they must be queried separately afterward. "
                        "May not be used together with `updateConflicts`. "
                        "Not supported on Oracle."
                    ),
                    out_name="ignore_conflicts",
                )
                arguments["updateConflicts"] = GraphQLArgument(
                    GraphQLBoolean,
                    default_value=False,
                    description=(
                        "When set to `True`, tells the database to update an existing row if a row insertion "
                        "fails due to a conflict such as duplicate unique values. "
                        "Must also provide `updateFields` and `uniqueFields` "
                        "(latter only supported for PostgreSQL and SQLite). "
                        "May not be used together with `ignoreConflicts`. "
                        "Not supported on Oracle."
                    ),
                    out_name="update_conflicts",
                )

                enum = get_or_create_graphql_enum(
                    name=f"{ref.__typename__}BulkCreateField",
                    values={
                        to_schema_name(key): GraphQLEnumValue(
                            value=key,
                            description=inpt.description,
                            deprecation_reason=inpt.deprecation_reason,
                        )
                        for key, inpt in ref.__input_map__.items()
                        if not inpt.input_only and not inpt.hidden
                    },
                )

                arguments["updateFields"] = GraphQLArgument(
                    GraphQLList(GraphQLNonNull(enum)),
                    default_value=None,
                    description=(
                        "List of fields to update when a row insertion fails due to a conflict. "
                        "Must be provided if `updateConflicts` is `True`."
                    ),
                    out_name="update_fields",
                )
                arguments["uniqueFields"] = GraphQLArgument(
                    GraphQLList(GraphQLNonNull(enum)),
                    default_value=None,
                    description=(
                        "List of fields that all need to be unique for a new row to be inserted. "
                        "Must be provided on PostgreSQL and SQLite if `updateConflicts` is `True`."
                    ),
                    out_name="unique_fields",
                )

            elif ref.__mutation_kind__ == "update":
                arguments["batchSize"] = GraphQLArgument(
                    GraphQLInt,
                    default_value=None,
                    description=(
                        "How many objects are updated in a single query. "
                        "The default is to update all objects in one batch, "
                        "except for SQLite and Oracle which have restrictions "
                        "on the number of variables used in a query."
                    ),
                    out_name="batch_size",
                )

            input_type = GraphQLNonNull(GraphQLList(input_type))

        arguments[undine_settings.MUTATION_INPUT_KEY] = GraphQLArgument(input_type)
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
                description="Nuber of items to return from the end (after evaluating first).",
                out_name="last",
            ),
            "offset": GraphQLArgument(
                GraphQLInt,
                description="Number of items to skip from the start. Cannot be used together with `after` or `before`.",
                out_name="offset",
            ),
            **arguments,
        }

    @convert_to_graphql_argument_map.register
    def _(_: Node, **kwargs: Any) -> GraphQLArgumentMap:
        return {
            "id": GraphQLArgument(
                GraphQLNonNull(GraphQLID),
                description="The Global ID of for an object.",
                out_name="id",
            ),
        }
