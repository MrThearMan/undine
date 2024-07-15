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
    GraphQLFile,
    GraphQLJSON,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.utils.dispatcher import TypeDispatcher

__all__ = [
    "convert_model_field_to_graphql_output_type",
]


def wrapper(func: Callable[..., GraphQLOutputType]) -> Callable[..., GraphQLOutputType]:
    @wraps(func)
    def inner(field: models.Field) -> GraphQLOutputType:
        result = func(field)
        return result if field.null else GraphQLNonNull(result)

    return inner


convert_model_field_to_graphql_output_type = TypeDispatcher[models.Field, GraphQLOutputType](wrapper=wrapper)


@convert_model_field_to_graphql_output_type.register
def _(_: models.CharField | models.TextField) -> GraphQLScalarType:
    # TODO: enums
    return GraphQLString


@convert_model_field_to_graphql_output_type.register
def _(_: models.BooleanField) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_model_field_to_graphql_output_type.register
def _(_: models.IntegerField) -> GraphQLScalarType:
    return GraphQLInt


@convert_model_field_to_graphql_output_type.register
def _(_: models.FloatField) -> GraphQLScalarType:
    return GraphQLFloat


@convert_model_field_to_graphql_output_type.register
def _(_: models.DecimalField) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_model_field_to_graphql_output_type.register
def _(_: models.DateField) -> GraphQLScalarType:
    return GraphQLDate


@convert_model_field_to_graphql_output_type.register
def _(_: models.DateTimeField) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_model_field_to_graphql_output_type.register
def _(_: models.TimeField) -> GraphQLScalarType:
    return GraphQLTime


@convert_model_field_to_graphql_output_type.register
def _(_: models.DurationField) -> GraphQLScalarType:
    return GraphQLDuration


@convert_model_field_to_graphql_output_type.register
def _(_: models.UUIDField) -> GraphQLScalarType:
    return GraphQLUUID


@convert_model_field_to_graphql_output_type.register
def _(_: models.EmailField) -> GraphQLScalarType:
    return GraphQLEmail


@convert_model_field_to_graphql_output_type.register
def _(_: models.URLField) -> GraphQLScalarType:
    return GraphQLURL


@convert_model_field_to_graphql_output_type.register
def _(_: models.BinaryField) -> GraphQLScalarType:
    return GraphQLBase64


@convert_model_field_to_graphql_output_type.register
def _(_: models.JSONField) -> GraphQLScalarType:
    return GraphQLJSON


@convert_model_field_to_graphql_output_type.register
def _(_: models.FileField) -> GraphQLScalarType:
    return GraphQLFile
