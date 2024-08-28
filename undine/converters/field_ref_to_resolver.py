from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLFieldResolver

from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.resolvers import function_field_resolver, model_field_resolver

__all__ = [
    "convert_field_ref_to_resolver",
]


convert_field_ref_to_resolver = TypeDispatcher[FieldRef, GraphQLFieldResolver]()


@convert_field_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return function_field_resolver(ref)


@convert_field_ref_to_resolver.register
def _(ref: models.Field, **kwargs: Any) -> GraphQLFieldResolver:
    return model_field_resolver(name=ref.name)


@convert_field_ref_to_resolver.register
def _(ref: models.Expression | models.Subquery, **kwargs: Any) -> GraphQLFieldResolver:
    name: str = kwargs["name"]
    return model_field_resolver(name=name)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLType
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_field_ref_to_resolver.register
    def _(_: type[ModelGQLType], **kwargs: Any) -> GraphQLFieldResolver:
        name: str = kwargs["name"]
        many: bool = kwargs["many"]
        return model_field_resolver(name=name, many=many)

    @convert_field_ref_to_resolver.register
    def _(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLFieldResolver:
        name: str = kwargs["name"]
        many: bool = kwargs["many"]
        return convert_field_ref_to_resolver(ref.get_type(), many=many, name=name)

    @convert_field_ref_to_resolver.register
    def _(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
        return model_field_resolver(name=ref.name)
