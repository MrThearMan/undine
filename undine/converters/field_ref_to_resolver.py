from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLFieldResolver

from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.resolvers import function_field_resolver, is_pk_property, model_field_resolver

__all__ = [
    "convert_field_ref_to_resolver",
]


convert_field_ref_to_resolver = TypeDispatcher[FieldRef, GraphQLFieldResolver]()


@convert_field_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return function_field_resolver(ref)


@convert_field_ref_to_resolver.register
def _(ref: property, **kwargs: Any) -> GraphQLFieldResolver:
    if is_pk_property(ref):
        return model_field_resolver(name="pk")
    return model_field_resolver(name=ref.fget.__name__)


@convert_field_ref_to_resolver.register
def _(ref: models.Field, **kwargs: Any) -> GraphQLFieldResolver:
    return model_field_resolver(name=ref.name)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.model_graphql import ModelGQLType
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_field_ref_to_resolver.register
    def _(_: type[ModelGQLType], *, many: bool, name: str) -> GraphQLFieldResolver:
        return model_field_resolver(name=name, many=many)

    @convert_field_ref_to_resolver.register
    def _(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLFieldResolver:
        return convert_field_ref_to_resolver(ref.get_type(), **kwargs)

    @convert_field_ref_to_resolver.register
    def _(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
        return model_field_resolver(name=ref.name)
