from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, get_args

from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLFloat,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
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
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import get_docstring

__all__ = [
    "convert_type_to_graphql_output_type",
]


def null_hook(result: GraphQLOutputType, nullable: bool) -> Any:  # noqa: FBT001
    return result if nullable else GraphQLNonNull(result)


convert_type_to_graphql_output_type = TypeDispatcher[type, GraphQLOutputType](
    union_default=type, process_nullable=null_hook
)


@convert_type_to_graphql_output_type.register
def _(_: type[str]) -> GraphQLScalarType:
    return GraphQLString


@convert_type_to_graphql_output_type.register
def _(_: type[bool]) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_type_to_graphql_output_type.register
def _(_: type[int]) -> GraphQLScalarType:
    return GraphQLInt


@convert_type_to_graphql_output_type.register
def _(_: type[float]) -> GraphQLScalarType:
    return GraphQLFloat


@convert_type_to_graphql_output_type.register
def _(_: type[Decimal]) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_type_to_graphql_output_type.register
def _(_: type[datetime.datetime]) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_type_to_graphql_output_type.register
def _(_: type[datetime.date]) -> GraphQLScalarType:
    return GraphQLDate


@convert_type_to_graphql_output_type.register
def _(_: type[datetime.time]) -> GraphQLScalarType:
    return GraphQLTime


@convert_type_to_graphql_output_type.register
def _(_: type[datetime.timedelta]) -> GraphQLScalarType:
    return GraphQLDuration


@convert_type_to_graphql_output_type.register
def _(_: type[uuid.UUID]) -> GraphQLScalarType:
    return GraphQLUUID


@convert_type_to_graphql_output_type.register
def _(enum: type[Enum]) -> GraphQLEnumType:
    """Return a GraphQLEnumType for a given type."""
    return GraphQLEnumType(name=enum.__name__, values=enum, description=get_docstring(enum))


@convert_type_to_graphql_output_type.register
def _(_: type) -> GraphQLScalarType:
    return GraphQLAny


@convert_type_to_graphql_output_type.register
def _(items: type[list]) -> GraphQLList:
    args = get_args(items)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)
    return GraphQLList(convert_type_to_graphql_output_type(args[0]))
