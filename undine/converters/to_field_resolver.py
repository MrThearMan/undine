from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from graphql import GraphQLFieldResolver

from undine.resolvers import FunctionResolver, ModelFieldResolver, ModelManyRelatedResolver
from undine.typing import CombinableExpression, FieldRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyQueryType, LazyQueryTypeUnion

if TYPE_CHECKING:
    from undine import Field

__all__ = [
    "convert_field_ref_to_resolver",
]


convert_field_ref_to_resolver = FunctionDispatcher[FieldRef, GraphQLFieldResolver]()
"""
Convert the given 'undine.Field' reference to a field resolver function.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - caller: The 'undine.Field' instance that is calling this function.
"""


@convert_field_ref_to_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    return FunctionResolver.adapt(ref)


@convert_field_ref_to_resolver.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    if caller.many:
        return ModelManyRelatedResolver(name=caller.name)
    return ModelFieldResolver(name=caller.name)


@convert_field_ref_to_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    # Expressions and subqueries will be annotated to the queryset by the optimizer.
    return ModelFieldResolver(name=caller.name)


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.get_type(), **kwargs)


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.field, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.query import QueryType

    @convert_field_ref_to_resolver.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLFieldResolver:
        return ModelFieldResolver(name=ref.name)

    @convert_field_ref_to_resolver.register
    def _(_: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        if caller.many:
            return ModelManyRelatedResolver(name=caller.name)
        return ModelFieldResolver(name=caller.name)
