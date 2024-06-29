# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLFieldResolver

from undine.typing import Ref
from undine.utils import TypeDispatcher, function_resolver, is_pk_property, model_attr_resolver

__all__ = [
    "convert_ref_to_resolver",
]


convert_ref_to_resolver = TypeDispatcher[Ref, GraphQLFieldResolver]()


@convert_ref_to_resolver.register
def convert_function(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return function_resolver(ref)


@convert_ref_to_resolver.register
def convert_property(ref: property, **kwargs: Any) -> GraphQLFieldResolver:
    if is_pk_property(ref):
        return model_attr_resolver(name="pk")
    return model_attr_resolver(name=ref.fget.__name__)


@convert_ref_to_resolver.register
def convert_model_field(ref: models.Field, **kwargs: Any) -> GraphQLFieldResolver:
    return model_attr_resolver(name=ref.name)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_ref_to_resolver.register
    def convert_model_node(ref: type[ModelGQLType], *, many: bool, top_level: bool, name: str) -> GraphQLFieldResolver:
        if top_level:
            return ref.__resolve_many__ if many else ref.__resolve_one__
        return model_attr_resolver(name=name, many=many)

    @convert_ref_to_resolver.register
    def convert_deferred_type(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLFieldResolver:
        return convert_ref_to_resolver(ref.get_type(), **kwargs)

    @convert_ref_to_resolver.register
    def convert_deferred_type_union(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
        return model_attr_resolver(name=ref.name)
