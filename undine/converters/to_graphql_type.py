from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, get_args

from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLField,
    GraphQLFloat,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLScalarType,
    GraphQLString,
)

from undine.errors.exceptions import TypeDispatcherError
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
def _(_: type[str], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLString


@convert_type_to_graphql_type.register
def _(_: type[bool], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_type_to_graphql_type.register
def _(_: type[int], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLInt


@convert_type_to_graphql_type.register
def _(_: type[float], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLFloat


@convert_type_to_graphql_type.register
def _(_: type[Decimal], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_type_to_graphql_type.register
def _(_: type[datetime.datetime], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_type_to_graphql_type.register
def _(_: type[datetime.date], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLDate


@convert_type_to_graphql_type.register
def _(_: type[datetime.time], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLTime


@convert_type_to_graphql_type.register
def _(_: type[datetime.timedelta], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLDuration


@convert_type_to_graphql_type.register
def _(_: type[uuid.UUID], **kwargs: Any) -> GraphQLScalarType:
    return GraphQLUUID


@convert_type_to_graphql_type.register
def _(ref: type[Enum], **kwargs: Any) -> GraphQLEnumType:
    return GraphQLEnumType(name=ref.__name__, values=ref, description=get_docstring(ref))


@convert_type_to_graphql_type.register
def _(_: type, **kwargs: Any) -> GraphQLScalarType:
    return GraphQLAny


@convert_type_to_graphql_type.register
def _(ref: type[list], **kwargs: Any) -> GraphQLList:
    args = get_args(ref)
    # For lists without type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)

    graphql_type, nullable = convert_type_to_graphql_type(args[0], return_nullable=True)
    if not nullable:
        graphql_type = GraphQLNonNull(graphql_type)
    return GraphQLList(graphql_type)


@convert_type_to_graphql_type.register
def _(ref: type[dict], **kwargs: Any) -> GraphQLObjectType | GraphQLInputObjectType:
    if type(ref) is not TypedDictType:
        msg = f"Can only convert TypedDicts, got {type(ref)}."
        raise TypeDispatcherError(msg)

    ref: TypedDictType
    module_globals = vars(__import__(ref.__module__))
    is_input = kwargs.get("is_input", False)

    fields: dict[str, GraphQLField | GraphQLInputField] = {}
    for key, value in ref.__annotations__.items():
        evaluated_type = eval_type(value, globals_=module_globals)
        graphql_type, nullable = convert_type_to_graphql_type(evaluated_type, return_nullable=True)
        if not nullable:
            graphql_type = GraphQLNonNull(graphql_type)

        if is_input:
            fields[key] = GraphQLInputField(graphql_type)
        else:
            fields[key] = GraphQLField(graphql_type)

    if is_input:
        return GraphQLInputObjectType(name=ref.__name__, fields=fields)
    return GraphQLObjectType(name=ref.__name__, fields=fields)
