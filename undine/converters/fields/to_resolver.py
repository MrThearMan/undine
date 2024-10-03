from __future__ import annotations

from types import FunctionType
from typing import Any

from graphql import GraphQLFieldResolver

from undine.resolvers import FieldResolver, ModelFieldResolver, ModelManyRelatedResolver
from undine.typing import CombinableExpression, FieldRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyQueryType, LazyQueryTypeUnion

__all__ = [
    "convert_field_ref_to_resolver",
]


convert_field_ref_to_resolver = FunctionDispatcher[FieldRef, GraphQLFieldResolver]()
"""Convert the Undine Field reference to a GraphQL field resolver."""


@convert_field_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return FieldResolver.from_func(ref)


@convert_field_ref_to_resolver.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLFieldResolver:
    return ModelFieldResolver(name=ref.name)


@convert_field_ref_to_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> GraphQLFieldResolver:
    return ModelFieldResolver(name=kwargs["name"])


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.get_type(), **kwargs)


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.field, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.query import QueryType

    @convert_field_ref_to_resolver.register
    def _(_: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
        if kwargs["many"]:
            return ModelManyRelatedResolver(name=kwargs["name"])
        return ModelFieldResolver(name=kwargs["name"])
