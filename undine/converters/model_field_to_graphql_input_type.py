from __future__ import annotations

from django.db import models
from graphql import GraphQLBoolean, GraphQLFloat, GraphQLInputType, GraphQLInt, GraphQLScalarType, GraphQLString

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
    "convert_model_field_to_graphql_input_type",
]


convert_model_field_to_graphql_input_type = TypeDispatcher[models.Field, GraphQLInputType]()


@convert_model_field_to_graphql_input_type.register
def _(_: models.CharField | models.TextField) -> GraphQLScalarType:
    # TODO: enums
    return GraphQLString


@convert_model_field_to_graphql_input_type.register
def _(_: models.BooleanField) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_model_field_to_graphql_input_type.register
def _(_: models.IntegerField) -> GraphQLScalarType:
    return GraphQLInt


@convert_model_field_to_graphql_input_type.register
def _(_: models.FloatField) -> GraphQLScalarType:
    return GraphQLFloat


@convert_model_field_to_graphql_input_type.register
def _(_: models.DecimalField) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_model_field_to_graphql_input_type.register
def _(_: models.DateField) -> GraphQLScalarType:
    return GraphQLDate


@convert_model_field_to_graphql_input_type.register
def _(_: models.DateTimeField) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_model_field_to_graphql_input_type.register
def _(_: models.TimeField) -> GraphQLScalarType:
    return GraphQLTime


@convert_model_field_to_graphql_input_type.register
def _(_: models.DurationField) -> GraphQLScalarType:
    return GraphQLDuration


@convert_model_field_to_graphql_input_type.register
def _(_: models.UUIDField) -> GraphQLScalarType:
    return GraphQLUUID


@convert_model_field_to_graphql_input_type.register
def _(_: models.EmailField) -> GraphQLScalarType:
    return GraphQLEmail


@convert_model_field_to_graphql_input_type.register
def _(_: models.URLField) -> GraphQLScalarType:
    return GraphQLURL


@convert_model_field_to_graphql_input_type.register
def _(_: models.BinaryField) -> GraphQLScalarType:
    return GraphQLBase64


@convert_model_field_to_graphql_input_type.register
def _(_: models.JSONField) -> GraphQLScalarType:
    return GraphQLJSON


@convert_model_field_to_graphql_input_type.register
def _(_: models.FileField) -> GraphQLScalarType:
    return GraphQLFile
