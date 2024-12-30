from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db.models import F
from graphql import GraphQLFieldResolver, GraphQLID, GraphQLType, GraphQLWrappingType

from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
from undine.errors.exceptions import FunctionDispatcherError
from undine.resolvers import (
    FunctionResolver,
    GlobalIDResolver,
    ModelFieldResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedConnectionResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
)
from undine.typing import CombinableExpression, FieldRef, ModelField, ToManyField, ToOneField
from undine.utils.function_dispatcher import FunctionDispatcher

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
    caller: Field = kwargs["caller"]
    return FunctionResolver(func=ref, field=caller)


@convert_field_ref_to_resolver.register
def _(_: ModelField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelFieldResolver(field=caller)


@convert_field_ref_to_resolver.register
def _(_: ToOneField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelSingleRelatedFieldResolver(field=caller)


@convert_field_ref_to_resolver.register
def _(_: ToManyField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelManyRelatedFieldResolver(field=caller)


@convert_field_ref_to_resolver.register
def _(_: CombinableExpression | F, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    # Expressions and subqueries will be annotated to the queryset by the optimizer.
    return ModelFieldResolver(field=caller)


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.get_type(), **kwargs)


@convert_field_ref_to_resolver.register
def _(ref: LazyQueryTypeUnion, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.field, **kwargs)


@convert_field_ref_to_resolver.register
def _(ref: LazyLambdaQueryType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.callback(), **kwargs)


@convert_field_ref_to_resolver.register
def _(_: Calculated, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    # It is exprected that the calculated value is annotated to the queryset in the calculation function.
    return ModelFieldResolver(field=caller)


@convert_field_ref_to_resolver.register
def _(ref: TypeRef, **kwargs: Any) -> None:
    caller: Field = kwargs["caller"]
    msg = f"Must define a custom resolve for '{caller.name}' since using python type '{ref.value}' as a reference."
    raise FunctionDispatcherError(msg)


@convert_field_ref_to_resolver.register
def _(ref: GraphQLType, **kwargs: Any) -> None:
    caller: Field = kwargs["caller"]
    msg = f"Must define a custom resolve for '{caller.name}' since using GraphQLType '{ref}' as a reference."
    raise FunctionDispatcherError(msg)


@convert_field_ref_to_resolver.register
def _(ref: GraphQLWrappingType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_field_ref_to_resolver(ref.of_type, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine import QueryType
    from undine.relay import Connection

    @convert_field_ref_to_resolver.register  # Required for Django<5.1
    def _(_: GenericForeignKey, **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        return ModelSingleRelatedFieldResolver(field=caller)

    @convert_field_ref_to_resolver.register
    def _(_: GenericRelation, **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        return ModelManyRelatedFieldResolver(field=caller)

    @convert_field_ref_to_resolver.register
    def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        if caller.many:
            return NestedQueryTypeManyResolver(field=caller, query_type=ref)
        return NestedQueryTypeSingleResolver(field=caller, query_type=ref)

    @convert_field_ref_to_resolver.register
    def _(ref: Connection, **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        return NestedConnectionResolver(connection=ref, field=caller)

    @convert_field_ref_to_resolver.register
    def _(_: GraphQLID, **kwargs: Any) -> GraphQLFieldResolver:
        caller: Field = kwargs["caller"]
        return GlobalIDResolver(typename=caller.query_type.__typename__)
