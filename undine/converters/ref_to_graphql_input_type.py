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
    GraphQLNonNull,
)

from undine.parsers import parse_first_param_type, parse_model_field
from undine.typing import Ref
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.reflection import generic_relations_for_generic_foreign_key
from undine.utils.text import to_pascal_case

from .model_field_to_graphql_input_type import convert_model_field_to_graphql_input_type
from .type_to_graphql_input_type import convert_type_to_graphql_input_type

__all__ = [
    "convert_ref_to_graphql_input_type",
]


convert_ref_to_graphql_input_type = TypeDispatcher[Ref, GraphQLInputType]()


@convert_ref_to_graphql_input_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLInputType:
    annotation = parse_first_param_type(ref)
    return convert_type_to_graphql_input_type(annotation)


@convert_ref_to_graphql_input_type.register
def _(ref: staticmethod | classmethod) -> GraphQLInputType:
    return convert_ref_to_graphql_input_type(ref.__func__)  # type: ignore[arg-type]


@convert_ref_to_graphql_input_type.register
def _(ref: models.Field, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_input_type(ref)


@convert_ref_to_graphql_input_type.register
def _(ref: str, *, model: type[models.Model]) -> GraphQLInputType:
    model_field = parse_model_field(model=model, lookup=ref)
    return convert_model_field_to_graphql_input_type(model_field)


@convert_ref_to_graphql_input_type.register
def _(ref: models.Q, **kwargs: Any) -> GraphQLInputType:
    return GraphQLBoolean


@convert_ref_to_graphql_input_type.register
def _(ref: models.Expression, **kwargs: Any) -> GraphQLInputType:
    return convert_model_field_to_graphql_input_type(ref.output_field)


@convert_ref_to_graphql_input_type.register
def _(ref: models.F, *, model: type[models.Model]) -> GraphQLInputType:
    model_field = parse_model_field(model=model, lookup=ref.name)
    return convert_model_field_to_graphql_input_type(model_field)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine.model_graphql import ModelGQLMutation

    @convert_ref_to_graphql_input_type.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLInputType:
        return ref.__input_object__

    @convert_ref_to_graphql_input_type.register
    def _(ref: GenericRelation, **kwargs: Any) -> GraphQLInputType:
        object_id_field = ref.related_model._meta.get_field(ref.object_id_field_name)
        return convert_model_field_to_graphql_input_type(object_id_field)

    @convert_ref_to_graphql_input_type.register
    def _(ref: GenericForeignKey, *, model: type[models.Model]) -> GraphQLInputType:
        # TODO: Maybe we could register mutations in a registry, and then
        #  use them to create a '@oneOf' input type with each of their input objects?
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
                        convert_model_field_to_graphql_input_type(ref.model._meta.get_field(ref.fk_field)),
                    ),
                ),
            },
        )
