# ruff: noqa: TCH001, TCH002, TCH003
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
from undine.utils import TypeDispatcher

__all__ = [
    "convert_type_to_graphql_input_type",
]


convert_type_to_graphql_input_type = TypeDispatcher[type, GraphQLInputType](union_default=type)


@convert_type_to_graphql_input_type.register
def convert_to_graphql_string(_: type[str]) -> GraphQLScalarType:
    return GraphQLString


@convert_type_to_graphql_input_type.register
def convert_to_graphql_boolean(_: type[bool]) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_type_to_graphql_input_type.register
def convert_to_graphql_int(_: type[int]) -> GraphQLScalarType:
    return GraphQLInt


@convert_type_to_graphql_input_type.register
def convert_to_graphql_float(_: type[float]) -> GraphQLScalarType:
    return GraphQLFloat


@convert_type_to_graphql_input_type.register
def convert_to_graphql_decimal(_: type[Decimal]) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_type_to_graphql_input_type.register
def convert_to_graphql_datetime(_: type[datetime.datetime]) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_type_to_graphql_input_type.register
def convert_to_graphql_date(_: type[datetime.date]) -> GraphQLScalarType:
    return GraphQLDate


@convert_type_to_graphql_input_type.register
def convert_to_graphql_time(_: type[datetime.time]) -> GraphQLScalarType:
    return GraphQLTime


@convert_type_to_graphql_input_type.register
def convert_to_graphql_duration(_: type[datetime.timedelta]) -> GraphQLScalarType:
    return GraphQLDuration


def convert_to_graphql_uuid(_: type[uuid.UUID]) -> GraphQLScalarType:
    return GraphQLUUID


@convert_type_to_graphql_input_type.register
def convert_to_graphql_enum(enum: type[Enum]) -> GraphQLEnumType:
    """Return a GraphQLEnumType for a given type."""
    return GraphQLEnumType(
        name=enum.__name__,
        values=enum,
        description=enum.__doc__,
        # TODO: add deprecation reason
    )


@convert_type_to_graphql_input_type.register
def convert_to_graphql_any(_: type) -> GraphQLScalarType:
    return GraphQLAny


@convert_type_to_graphql_input_type.register
def convert_to_graphql_list(items: type[list]) -> GraphQLList:
    args = get_args(items)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)
    return GraphQLList(convert_type_to_graphql_input_type(args[0]))
