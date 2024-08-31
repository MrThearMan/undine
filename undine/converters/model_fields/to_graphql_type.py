from __future__ import annotations

from django.db import models
from graphql import (
    GraphQLBoolean,
    GraphQLFloat,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
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
    "convert_model_field_to_graphql_type",
]


convert_model_field_to_graphql_type = TypeDispatcher[models.Field, GraphQLOutputType | GraphQLInputType]()
"""Convert the given model field to a GraphQL type."""


@convert_model_field_to_graphql_type.register
def _(_: models.CharField | models.TextField) -> GraphQLScalarType:
    # TODO: enums
    return GraphQLString


@convert_model_field_to_graphql_type.register
def _(_: models.BooleanField) -> GraphQLScalarType:
    return GraphQLBoolean


@convert_model_field_to_graphql_type.register
def _(_: models.IntegerField) -> GraphQLScalarType:
    return GraphQLInt


@convert_model_field_to_graphql_type.register
def _(_: models.FloatField) -> GraphQLScalarType:
    return GraphQLFloat


@convert_model_field_to_graphql_type.register
def _(_: models.DecimalField) -> GraphQLScalarType:
    return GraphQLDecimal


@convert_model_field_to_graphql_type.register
def _(_: models.DateField) -> GraphQLScalarType:
    return GraphQLDate


@convert_model_field_to_graphql_type.register
def _(_: models.DateTimeField) -> GraphQLScalarType:
    return GraphQLDateTime


@convert_model_field_to_graphql_type.register
def _(_: models.TimeField) -> GraphQLScalarType:
    return GraphQLTime


@convert_model_field_to_graphql_type.register
def _(_: models.DurationField) -> GraphQLScalarType:
    return GraphQLDuration


@convert_model_field_to_graphql_type.register
def _(_: models.UUIDField) -> GraphQLScalarType:
    return GraphQLUUID


@convert_model_field_to_graphql_type.register
def _(_: models.EmailField) -> GraphQLScalarType:
    return GraphQLEmail


@convert_model_field_to_graphql_type.register
def _(_: models.URLField) -> GraphQLScalarType:
    return GraphQLURL


@convert_model_field_to_graphql_type.register
def _(_: models.BinaryField) -> GraphQLScalarType:
    return GraphQLBase64


@convert_model_field_to_graphql_type.register
def _(_: models.JSONField) -> GraphQLScalarType:
    return GraphQLJSON


@convert_model_field_to_graphql_type.register
def _(_: models.FileField) -> GraphQLScalarType:
    return GraphQLFile


@convert_model_field_to_graphql_type.register
def _(ref: models.OneToOneField) -> GraphQLInputType:
    return convert_model_field_to_graphql_type(ref.target_field)


@convert_model_field_to_graphql_type.register
def _(ref: models.ForeignKey) -> GraphQLInputType:
    return convert_model_field_to_graphql_type(ref.target_field)


@convert_model_field_to_graphql_type.register
def _(ref: models.ManyToManyField) -> GraphQLInputType:
    type_ = convert_model_field_to_graphql_type(ref.target_field)
    return GraphQLList(GraphQLNonNull(type_))


@convert_model_field_to_graphql_type.register
def _(ref: models.OneToOneRel) -> GraphQLInputType:
    return convert_model_field_to_graphql_type(ref.target_field)


@convert_model_field_to_graphql_type.register
def _(ref: models.ManyToOneRel) -> GraphQLInputType:
    type_ = convert_model_field_to_graphql_type(ref.target_field)
    return GraphQLList(GraphQLNonNull(type_))


@convert_model_field_to_graphql_type.register
def _(ref: models.ManyToManyRel) -> GraphQLInputType:
    type_ = convert_model_field_to_graphql_type(ref.target_field)
    return GraphQLList(GraphQLNonNull(type_))


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    @convert_model_field_to_graphql_type.register
    def _(_: GenericForeignKey) -> GraphQLInputType:
        return GraphQLString  # TODO: hmm?

    @convert_model_field_to_graphql_type.register
    def _(ref: GenericRelation) -> GraphQLInputType:
        object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
        type_ = convert_model_field_to_graphql_type(object_id_field)
        return GraphQLList(type_)
