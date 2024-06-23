# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from functools import wraps
from typing import Callable

from django.db import models
from graphql import (
    GraphQLBoolean,
    GraphQLFloat,
    GraphQLInt,
    GraphQLNonNull,
    GraphQLOutputType,
    GraphQLScalarType,
    GraphQLString,
)

from undine.scalars import (
    GraphQLBase64,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLEmail,
    GraphQLJSON,
    GraphQLTime,
    GraphQLUpload,
    GraphQLURL,
    GraphQLUUID,
)
from undine.utils import TypeMapper

__all__ = [
    "convert_field_to_graphql_type",
]


def wrapper(func: Callable[..., GraphQLOutputType]) -> Callable[..., GraphQLOutputType]:
    @wraps(func)
    def inner(field: models.Field) -> GraphQLOutputType:
        result = func(field)
        return result if field.null else GraphQLNonNull(result)

    return inner


convert_field_to_graphql_type = TypeMapper[models.Field, GraphQLOutputType](wrapper=wrapper)


@convert_field_to_graphql_type.register
def convert_char_field(field: models.CharField | models.TextField) -> GraphQLScalarType:
    # TODO: enums
    return GraphQLString


@convert_field_to_graphql_type.register
def convert_boolean_field(field: models.BooleanField) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_field_to_graphql_type.register
def convert_integer_field(field: models.IntegerField) -> GraphQLScalarType:
    return GraphQLInt


@convert_field_to_graphql_type.register
def convert_float_field(field: models.FloatField) -> GraphQLScalarType:
    return GraphQLFloat


@convert_field_to_graphql_type.register
def convert_decimal_field(field: models.DecimalField) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_field_to_graphql_type.register
def convert_date_field(field: models.DateField) -> GraphQLScalarType:
    return GraphQLDate


@convert_field_to_graphql_type.register
def convert_datetime_field(field: models.DateTimeField) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_field_to_graphql_type.register
def convert_time_field(field: models.TimeField) -> GraphQLScalarType:
    return GraphQLTime


@convert_field_to_graphql_type.register
def convert_duration_field(field: models.DurationField) -> GraphQLScalarType:
    return GraphQLDuration


@convert_field_to_graphql_type.register
def convert_uuid_field(field: models.UUIDField) -> GraphQLScalarType:
    return GraphQLUUID


@convert_field_to_graphql_type.register
def convert_email_field(field: models.EmailField) -> GraphQLScalarType:
    return GraphQLEmail


@convert_field_to_graphql_type.register
def convert_url_field(field: models.URLField) -> GraphQLScalarType:
    return GraphQLURL


@convert_field_to_graphql_type.register
def convert_binary_field(field: models.BinaryField) -> GraphQLScalarType:
    return GraphQLBase64


@convert_field_to_graphql_type.register
def convert_json_field(field: models.JSONField) -> GraphQLScalarType:
    return GraphQLJSON


@convert_field_to_graphql_type.register
def convert_file_field(field: models.FileField) -> GraphQLScalarType:
    return GraphQLUpload
