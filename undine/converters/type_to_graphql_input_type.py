from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import get_args

from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLFloat,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
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
from undine.utils import TypeDispatcher, get_docstring

__all__ = [
    "convert_type_to_graphql_input_type",
]


convert_type_to_graphql_input_type = TypeDispatcher[type, GraphQLInputType](union_default=type)


@convert_type_to_graphql_input_type.register
def _(_: type[str]) -> GraphQLScalarType:
    return GraphQLString


@convert_type_to_graphql_input_type.register
def _(_: type[bool]) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_type_to_graphql_input_type.register
def _(_: type[int]) -> GraphQLScalarType:
    return GraphQLInt


@convert_type_to_graphql_input_type.register
def _(_: type[float]) -> GraphQLScalarType:
    return GraphQLFloat


@convert_type_to_graphql_input_type.register
def _(_: type[Decimal]) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_type_to_graphql_input_type.register
def _(_: type[datetime.datetime]) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_type_to_graphql_input_type.register
def _(_: type[datetime.date]) -> GraphQLScalarType:
    return GraphQLDate


@convert_type_to_graphql_input_type.register
def _(_: type[datetime.time]) -> GraphQLScalarType:
    return GraphQLTime


@convert_type_to_graphql_input_type.register
def _(_: type[datetime.timedelta]) -> GraphQLScalarType:
    return GraphQLDuration


@convert_type_to_graphql_input_type.register
def _(_: type[uuid.UUID]) -> GraphQLScalarType:
    return GraphQLUUID


@convert_type_to_graphql_input_type.register
def _(enum: type[Enum]) -> GraphQLEnumType:
    return GraphQLEnumType(name=enum.__name__, values=enum, description=get_docstring(enum))


@convert_type_to_graphql_input_type.register
def _(_: type) -> GraphQLScalarType:
    return GraphQLAny


@convert_type_to_graphql_input_type.register
def _(items: type[list]) -> GraphQLList:
    args = get_args(items)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)
    return GraphQLList(convert_type_to_graphql_input_type(args[0]))
