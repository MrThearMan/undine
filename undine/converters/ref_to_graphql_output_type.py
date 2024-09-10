from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLError, GraphQLOutputType, GraphQLUnionType

from undine.parsers import parse_return_annotation
from undine.typing import CombinableExpression, EntrypointRef, FilterRef, GQLInfo, ModelField
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion
from undine.utils.text import dotpath, to_pascal_case

from . import convert_model_field_to_graphql_type
from .to_graphql_type import convert_type_to_graphql_type

__all__ = [
    "convert_ref_to_graphql_output_type",
]


convert_ref_to_graphql_output_type = TypeDispatcher[FilterRef | EntrypointRef, GraphQLOutputType]()
"""Convert the given reference to a GraphQL output type."""


@convert_ref_to_graphql_output_type.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLOutputType:
    annotation = parse_return_annotation(ref)
    return convert_type_to_graphql_type(annotation)


@convert_ref_to_graphql_output_type.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLOutputType:
    return convert_model_field_to_graphql_type(ref)


@convert_ref_to_graphql_output_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> GraphQLOutputType:
    return convert_model_field_to_graphql_type(ref.output_field)


@convert_ref_to_graphql_output_type.register
def _(ref: LazyModelGQLType, **kwargs: Any) -> GraphQLOutputType:
    return convert_ref_to_graphql_output_type(ref.get_type(), **kwargs)


@convert_ref_to_graphql_output_type.register
def _(ref: LazyModelGQLTypeUnion, **kwargs: Any) -> GraphQLOutputType:
    type_map = {model_type.__model__: convert_ref_to_graphql_output_type(model_type) for model_type in ref.get_types()}

    def resolve_type(obj: type[models.Model], info: GQLInfo, union_type: GraphQLUnionType) -> Any:
        nonlocal type_map

        object_type = type_map.get(obj.__class__)
        if object_type is None:
            msg = f"Union '{ref.field.name}' doesn't contain a type for model '{dotpath(obj.__class__)}'."
            raise GraphQLError(msg)

        return object_type.name

    return GraphQLUnionType(
        name=f"{ref.field.model.__name__}{to_pascal_case(ref.field.name)}",
        types=list(type_map.values()),
        resolve_type=resolve_type,  # type: ignore[arg-type]
    )


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLMutation, ModelGQLType

    @convert_ref_to_graphql_output_type.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> GraphQLOutputType:
        return ref.__output_type__()

    @convert_ref_to_graphql_output_type.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> GraphQLOutputType:
        return ref.__output_type__()
