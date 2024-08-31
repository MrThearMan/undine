from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import get_args

from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLField,
    GraphQLFloat,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLScalarType,
    GraphQLString,
)

from undine.scalars import (
    GraphQLAny,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLTime,
    GraphQLUUID,
)
from undine.typing import TypedDictType, eval_type
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import get_docstring

__all__ = [
    "convert_type_to_graphql_type",
]


convert_type_to_graphql_type = TypeDispatcher[type, GraphQLOutputType | GraphQLInputType](union_default=type)
"""Convert a regular Python type to a GraphQL type."""


@convert_type_to_graphql_type.register
def _(_: type[str]) -> GraphQLScalarType:
    return GraphQLString


@convert_type_to_graphql_type.register
def _(_: type[bool]) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_type_to_graphql_type.register
def _(_: type[int]) -> GraphQLScalarType:
    return GraphQLInt


@convert_type_to_graphql_type.register
def _(_: type[float]) -> GraphQLScalarType:
    return GraphQLFloat


@convert_type_to_graphql_type.register
def _(_: type[Decimal]) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_type_to_graphql_type.register
def _(_: type[datetime.datetime]) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_type_to_graphql_type.register
def _(_: type[datetime.date]) -> GraphQLScalarType:
    return GraphQLDate


@convert_type_to_graphql_type.register
def _(_: type[datetime.time]) -> GraphQLScalarType:
    return GraphQLTime


@convert_type_to_graphql_type.register
def _(_: type[datetime.timedelta]) -> GraphQLScalarType:
    return GraphQLDuration


@convert_type_to_graphql_type.register
def _(_: type[uuid.UUID]) -> GraphQLScalarType:
    return GraphQLUUID


@convert_type_to_graphql_type.register
def _(ref: type[Enum]) -> GraphQLEnumType:
    return GraphQLEnumType(name=ref.__name__, values=ref, description=get_docstring(ref))


@convert_type_to_graphql_type.register
def _(_: type) -> GraphQLScalarType:
    return GraphQLAny


@convert_type_to_graphql_type.register
def _(ref: type[list]) -> GraphQLList:
    args = get_args(ref)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)

    graphql_type, nullable = convert_type_to_graphql_type(args[0], return_nullable=True)
    if not nullable:
        graphql_type = GraphQLNonNull(graphql_type)
    return GraphQLList(graphql_type)


@convert_type_to_graphql_type.register
def _(ref: type[dict]) -> GraphQLObjectType:
    if type(ref) is not TypedDictType:
        msg = f"Can only convert TypedDicts, got {type(ref)}."
        raise TypeError(msg)  # TODO: Custom exception

    ref: TypedDictType
    module_globals = vars(__import__(ref.__module__))

    fields: dict[str, GraphQLField] = {}
    for key, value in ref.__annotations__.items():
        evaluated_type = eval_type(value, globals_=module_globals)
        graphql_type, nullable = convert_type_to_graphql_type(evaluated_type, return_nullable=True)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)
        fields[key] = GraphQLField(graphql_type)

    return GraphQLObjectType(name=ref.__name__, fields=fields)
