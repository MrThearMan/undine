from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import (
    GraphQLError,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLResolveInfo,
    GraphQLUnionType,
)

from undine.parsers import parse_return_annotation
from undine.typing import Ref
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath, to_pascal_case

from .model_field_to_graphql_output_type import convert_model_field_to_graphql_output_type
from .type_to_graphql_output_type import convert_type_to_graphql_output_type

__all__ = [
    "convert_ref_to_graphql_output_type",
]


convert_ref_to_graphql_output_type = TypeDispatcher[Ref, GraphQLOutputType]()


@convert_ref_to_graphql_output_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLOutputType:
    annotation = parse_return_annotation(ref)
    return convert_type_to_graphql_output_type(annotation)


@convert_ref_to_graphql_output_type.register
def _(ref: property, **kwargs: Any) -> GraphQLOutputType:
    annotation = parse_return_annotation(ref.fget)
    return convert_type_to_graphql_output_type(annotation)


@convert_ref_to_graphql_output_type.register
def _(ref: models.Field, **kwargs: Any) -> GraphQLOutputType:
    return convert_model_field_to_graphql_output_type(ref)


def load_deferred_converters() -> None:  # noqa: C901
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.model_graphql import ModelGQLMutation, ModelGQLType
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_ref_to_graphql_output_type.register
    def _(ref: type[ModelGQLType], *, many: bool, nullable: bool) -> GraphQLOutputType:
        obj_type = ref.__object_type__
        if nullable is False:
            obj_type = GraphQLNonNull(obj_type)
        if many is True:
            obj_type = GraphQLNonNull(GraphQLList(obj_type))
        return obj_type

    @convert_ref_to_graphql_output_type.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLOutputType:
        return convert_ref_to_graphql_output_type(ref.__output_type__, **kwargs)

    @convert_ref_to_graphql_output_type.register
    def _(ref: GraphQLObjectType, **kwargs: Any) -> GraphQLOutputType:
        return ref

    @convert_ref_to_graphql_output_type.register
    def _(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLOutputType:
        return convert_ref_to_graphql_output_type(ref.get_type(), **kwargs)

    @convert_ref_to_graphql_output_type.register
    def _(ref: DeferredModelGQLTypeUnion, *, many: bool, nullable: bool) -> GraphQLOutputType:
        type_map = {
            model_type.__model__: convert_ref_to_graphql_output_type(model_type, many=False, nullable=True)
            for model_type in ref.get_types()
        }

        def resolve_type(obj: type[models.Model], info: GraphQLResolveInfo, union_type: GraphQLUnionType) -> Any:
            nonlocal type_map

            object_type = type_map.get(obj.__class__)
            if object_type is None:
                msg = f"Union '{ref.name}' doesn't contain a type for model '{dotpath(obj.__class__)}'."
                raise GraphQLError(msg)

            return object_type.name

        union_gql_type = GraphQLUnionType(
            name=f"{ref.model.__name__}{to_pascal_case(ref.name)}",
            types=list(type_map.values()),
            resolve_type=resolve_type,
        )

        if nullable is False:
            union_gql_type = GraphQLNonNull(union_gql_type)
        if many is True:
            union_gql_type = GraphQLNonNull(GraphQLList(union_gql_type))
        return union_gql_type
