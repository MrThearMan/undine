from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine.typing import CombinableExpression, FieldRef, ModelField
from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.resolvers import function_field_resolver, model_field_resolver

__all__ = [
    "convert_field_ref_to_resolver",
]


convert_field_ref_to_resolver = TypeDispatcher[FieldRef, GraphQLFieldResolver]()
"""Convert the Undine Field reference to a GraphQL field resolver."""


@convert_field_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return function_field_resolver(ref)


@convert_field_ref_to_resolver.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLFieldResolver:
    return model_field_resolver(name=ref.name)


@convert_field_ref_to_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> GraphQLFieldResolver:
    return model_field_resolver(name=kwargs["name"])


@convert_field_ref_to_resolver.register
def _(ref: DeferredModelGQLType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.get_type(), **kwargs)


@convert_field_ref_to_resolver.register
def _(ref: DeferredModelGQLTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.field, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLType

    @convert_field_ref_to_resolver.register
    def _(_: type[ModelGQLType], **kwargs: Any) -> GraphQLFieldResolver:
        return model_field_resolver(name=kwargs["name"], many=kwargs["many"])
