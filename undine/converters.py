from __future__ import annotations

import datetime  # noqa: TCH003
import uuid  # noqa: TCH003
from decimal import Decimal  # noqa: TCH003
from enum import Enum  # noqa: TCH003
from functools import wraps
from typing import TYPE_CHECKING, Callable, Unpack, get_args

from graphql import (
    GraphQLArgument,
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLField,
    GraphQLFloat,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLString,
)

from undine.scalars import GraphQLDate, GraphQLDateTime, GraphQLDecimal, GraphQLDuration, GraphQLTime, GraphQLUUID
from undine.scalars.any import GraphQLAny
from undine.utils import TypeMapper

if TYPE_CHECKING:
    from django.db import models

    from undine.typing import ArgumentVariables


__all__ = [
    "convert_to_graphql_type",
    "get_argument_type",
]


def non_null_hook(nullable: bool):  # noqa: ANN202, FBT001
    def decorator(func: Callable[[type], GraphQLOutputType]) -> Callable[[type], GraphQLOutputType]:
        @wraps(func)
        def wrapper(type_: type) -> GraphQLOutputType:
            result = func(type_)
            return result if nullable else GraphQLNonNull(result)

        return wrapper

    return decorator


convert_to_graphql_type: TypeMapper[type, GraphQLOutputType]
convert_to_graphql_type = TypeMapper("convert_to_graphql_type", default_type=type, null_hook=non_null_hook)


def get_argument_type(arg: type, **kwargs: Unpack[ArgumentVariables]) -> GraphQLArgument:
    """Return a GraphQLArgument for a given type."""
    return GraphQLArgument(convert_to_graphql_type(arg), **kwargs)


@convert_to_graphql_type.register
def convert_to_graphql_string(_: type[str]) -> GraphQLString:
    return GraphQLString


@convert_to_graphql_type.register
def convert_to_graphql_boolean(_: type[bool]) -> GraphQLBoolean:
    return GraphQLBoolean


@convert_to_graphql_type.register
def convert_to_graphql_int(_: type[int]) -> GraphQLInt:
    return GraphQLInt


@convert_to_graphql_type.register
def convert_to_graphql_float(_: type[float]) -> GraphQLFloat:
    return GraphQLFloat


@convert_to_graphql_type.register
def convert_to_graphql_decimal(_: type[Decimal]) -> GraphQLDecimal:
    return GraphQLDecimal


@convert_to_graphql_type.register
def convert_to_graphql_datetime(_: type[datetime.datetime]) -> GraphQLDateTime:
    return GraphQLDateTime


@convert_to_graphql_type.register
def convert_to_graphql_date(_: type[datetime.date]) -> GraphQLDate:
    return GraphQLDate


@convert_to_graphql_type.register
def convert_to_graphql_time(_: type[datetime.time]) -> GraphQLTime:
    return GraphQLTime


@convert_to_graphql_type.register
def convert_to_graphql_duration(_: type[datetime.timedelta]) -> GraphQLDuration:
    return GraphQLDuration


def convert_to_graphql_uuid(_: type[uuid.UUID]) -> GraphQLUUID:
    return GraphQLUUID


@convert_to_graphql_type.register
def convert_to_graphql_enum(enum: type[Enum]) -> GraphQLEnumType:
    """Return a GraphQLEnumType for a given type."""
    return GraphQLEnumType(
        name=enum.__name__,
        values=enum,
        description=enum.__doc__,
        # TODO: add deprecation reason
    )


@convert_to_graphql_type.register
def convert_to_graphql_any(_: type) -> GraphQLAny:
    return GraphQLAny


@convert_to_graphql_type.register
def convert_to_graphql_list(items: type[list]) -> GraphQLList:
    args = get_args(items)
    # For lists wihtout type, or with a union type, default to any.
    if len(args) != 1:
        return GraphQLList(GraphQLAny)
    return GraphQLList(convert_to_graphql_type(args[0]))


@convert_to_graphql_type.register
def convert_to_graphql_model(model: type[models.Model]) -> GraphQLObjectType:
    """Return a GraphQLObjectType for a given Django model."""
    return GraphQLObjectType(
        name=model.__name__,
        fields={
            field.name: GraphQLField(
                convert_to_graphql_field(field),
                # args: Optional[GraphQLArgumentMap] = None,
                # resolve: Optional["GraphQLFieldResolver"] = None,
                # subscribe: Optional["GraphQLFieldResolver"] = None,
                # description: Optional[str] = None,
                # deprecation_reason: Optional[str] = None,
                # extensions: Optional[Dict[str, Any]] = None,
                # ast_node: Optional[FieldDefinitionNode] = None,
            )
            for field in model._meta.get_fields(include_hidden=True)
        },
    )


convert_to_graphql_field: TypeMapper[models.CharField, GraphQLOutputType]
convert_to_graphql_field = TypeMapper("convert_to_graphql_field")


@convert_to_graphql_type.register
def convert_charfield(model: models.CharField) -> GraphQLString:
    return GraphQLString


@convert_to_graphql_type.register
def convert_integerfield(model: models.IntegerField) -> GraphQLInt:
    return GraphQLInt


@convert_to_graphql_type.register
def convert_floatfield(model: models.FloatField) -> GraphQLFloat:
    return GraphQLFloat


@convert_to_graphql_type.register
def convert_decimalfield(model: models.DecimalField) -> GraphQLDecimal:
    return GraphQLDecimal


@convert_to_graphql_type.register
def convert_datefield(model: models.DateField) -> GraphQLDate:
    return GraphQLDate


@convert_to_graphql_type.register
def convert_datetimefield(model: models.DateTimeField) -> GraphQLDateTime:
    return GraphQLDateTime


@convert_to_graphql_type.register
def convert_timefield(model: models.TimeField) -> GraphQLTime:
    return GraphQLTime


@convert_to_graphql_type.register
def convert_uuidfield(model: models.UUIDField) -> GraphQLUUID:
    return GraphQLUUID
