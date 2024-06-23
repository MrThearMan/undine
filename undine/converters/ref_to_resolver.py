# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from graphql import GraphQLFieldResolver, GraphQLResolveInfo

from undine.typing import Ref
from undine.utils import TypeMapper, is_pk_property, model_attr_resolver, model_to_many_resolver

__all__ = [
    "convert_ref_to_resolver",
]


convert_ref_to_resolver = TypeMapper[Ref, GraphQLFieldResolver]()


@convert_ref_to_resolver.register
def parse_function(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_ref_to_resolver.register
def parse_property(ref: property, **kwargs: Any) -> Any:
    if is_pk_property(ref):
        return model_attr_resolver(name="pk")
    return model_attr_resolver(name=ref.fget.__name__)


@convert_ref_to_resolver.register
def parse_field(ref: models.Field, **kwargs: Any) -> Any:
    return model_attr_resolver(name=ref.name)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_ref_to_resolver.register
    def parse_model_node(ref: type[ModelGQLType], *, many: bool, top_level: bool, name: str) -> Any:
        # TODO: Run all accessors through the ModelGQLType, even if fields on other models.
        #  This way filtering is applied, and hooks can be used for permissions, etc.
        if top_level:
            return ref.__resolve_many__ if many else ref.__resolve_one__
        return model_to_many_resolver(name=name) if many else model_attr_resolver(name=name)

    @convert_ref_to_resolver.register
    def parse_deferred_type(ref: DeferredModelGQLType, **kwargs: Any) -> Any:
        return parse_model_node(ref.get_type(), **kwargs)

    @convert_ref_to_resolver.register
    def parse_deferred_type_union(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> Any:
        def resolve(obj: type[models.Model], info: GraphQLResolveInfo, **kw: Any) -> Any:
            return getattr(obj, ref.name, None)

        return resolve
