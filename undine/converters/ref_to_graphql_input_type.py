from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import (
    GraphQLBoolean,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLInputField,
    GraphQLInputObjectType,
    GraphQLInputType,
    GraphQLList,
    GraphQLNonNull,
)

from undine.parsers import parse_first_param_type
from undine.typing import CombinableExpression, FilterRef, InputRef, ModelField, TypeRef
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.model_utils import generic_relations_for_generic_foreign_key, get_model_field
from undine.utils.text import to_pascal_case

from .model_fields.to_graphql_type import convert_model_field_to_graphql_type
from .to_graphql_type import convert_type_to_graphql_type

__all__ = [
    "convert_ref_to_graphql_input_type",
]


convert_ref_to_graphql_input_type = FunctionDispatcher[FilterRef | InputRef, GraphQLInputType]()
"""Convert the given reference to a GraphQL input type."""


@convert_ref_to_graphql_input_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLInputType:
    annotation = parse_first_param_type(ref)
    return convert_type_to_graphql_type(annotation, is_input=True)


@convert_ref_to_graphql_input_type.register
def _(ref: TypeRef, **kwargs: Any) -> GraphQLInputType:
    return convert_type_to_graphql_type(ref.ref, is_input=True)


@convert_ref_to_graphql_input_type.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_type(ref)


@convert_ref_to_graphql_input_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_type(ref.output_field)


@convert_ref_to_graphql_input_type.register
def _(ref: str, **kwargs: Any) -> GraphQLInputType:
    model: type[models.Model] = kwargs["model"]
    model_field = get_model_field(model=model, lookup=ref)
    return convert_model_field_to_graphql_type(model_field)


@convert_ref_to_graphql_input_type.register
def _(ref: models.F, **kwargs: Any) -> GraphQLInputType:
    model: type[models.Model] = kwargs["model"]
    model_field = get_model_field(model=model, lookup=ref.name)
    return convert_model_field_to_graphql_type(model_field)


@convert_ref_to_graphql_input_type.register
def _(_: models.Q, **kwargs: Any) -> GraphQLInputType:
    return GraphQLBoolean


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine import ModelGQLMutation

    @convert_ref_to_graphql_input_type.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLInputType:
        return ref.__input_type__(entrypoint=False)

    @convert_ref_to_graphql_input_type.register
    def _(ref: GenericRelation, **kwargs: Any) -> GraphQLInputType:
        object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
        fk_type = convert_model_field_to_graphql_type(object_id_field)
        return GraphQLList(fk_type)

    @convert_ref_to_graphql_input_type.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLInputType:
        model: type[models.Model] = kwargs["model"]
        return GraphQLInputObjectType(
            name=f"{model.__name__}{to_pascal_case(ref.name)}Input",
            fields=lambda: {
                "typename": GraphQLInputField(
                    GraphQLNonNull(
                        GraphQLEnumType(
                            name=f"{model.__name__}{to_pascal_case(ref.name)}Enum",
                            values={
                                field.model.__name__: GraphQLEnumValue(value=field.model.__name__)
                                for field in generic_relations_for_generic_foreign_key(ref)
                            },
                        ),
                    )
                ),
                "pk": GraphQLInputField(
                    GraphQLNonNull(
                        convert_model_field_to_graphql_type(ref.model._meta.get_field(ref.fk_field)),
                    ),
                ),
            },
        )
