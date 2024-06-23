# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLAbstractType, GraphQLError, GraphQLOutputType, GraphQLResolveInfo, GraphQLUnionType

from undine.parsers import parse_return_annotation
from undine.typing import Ref
from undine.utils import TypeMapper, dotpath, name_to_pascal_case

from .field_to_graphql import convert_field_to_graphql_type
from .type_to_graphql import convert_type_to_graphql_type

__all__ = [
    "convert_ref_to_field_type",
]


convert_ref_to_field_type = TypeMapper[Ref, GraphQLOutputType]()


@convert_ref_to_field_type.register
def convert_function(ref: FunctionType) -> GraphQLOutputType:
    annotation = parse_return_annotation(ref, level=2)
    return convert_type_to_graphql_type(annotation)


@convert_ref_to_field_type.register
def convert_property(ref: property) -> GraphQLOutputType:
    annotation = parse_return_annotation(ref.fget, level=2)
    return convert_type_to_graphql_type(annotation)


@convert_ref_to_field_type.register
def convert_model_field(ref: models.Field) -> GraphQLOutputType:
    return convert_field_to_graphql_type(ref)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_ref_to_field_type.register
    def convert_model_node(ref: type[ModelGQLType]) -> GraphQLOutputType:
        return ref.__get_object_type__()

    @convert_ref_to_field_type.register
    def convert_deferred_type(ref: DeferredModelGQLType) -> GraphQLOutputType:
        return convert_model_node(ref.get_type())

    @convert_ref_to_field_type.register
    def convert_deferred_type_union(ref: DeferredModelGQLTypeUnion) -> GraphQLOutputType:
        type_map = {model_type.__model__: convert_ref_to_field_type(model_type) for model_type in ref.get_types()}

        def resolve_type(obj: type[models.Model], info: GraphQLResolveInfo, _type: GraphQLAbstractType) -> Any:
            nonlocal type_map

            object_type = type_map.get(obj.__class__)
            if object_type is None:
                msg = f"Union '{ref.name}' doesn't contain a type for model '{dotpath(obj.__class__)}'."
                raise GraphQLError(msg)

            return object_type.name

        return GraphQLUnionType(
            name=f"{ref.model.__name__}{name_to_pascal_case(ref.name)}",
            types=list(type_map.values()),
            resolve_type=resolve_type,
        )
