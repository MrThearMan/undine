from __future__ import annotations

from types import FunctionType
from typing import Any, Never

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db.models import F
from graphql import GraphQLFieldResolver, GraphQLID, GraphQLType, GraphQLWrappingType

from undine import Calculation, Field, QueryType
from undine.converters import convert_to_field_resolver
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.exceptions import FunctionDispatcherError, RegistryMissingTypeError
from undine.relay import Connection
from undine.resolvers import (
    GlobalIDResolver,
    ModelAttributeResolver,
    ModelGenericForeignKeyResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedConnectionResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
)
from undine.resolvers.query import FieldFunctionResolver
from undine.typing import CombinableExpression, ModelField, ToManyField, ToOneField


@convert_to_field_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return FieldFunctionResolver(func=ref, field=caller)


@convert_to_field_resolver.register
def _(_: ModelField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelAttributeResolver(field=caller)


@convert_to_field_resolver.register
def _(_: ToOneField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelSingleRelatedFieldResolver(field=caller)


@convert_to_field_resolver.register
def _(_: ToManyField, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelManyRelatedFieldResolver(field=caller)


@convert_to_field_resolver.register
def _(_: CombinableExpression | F, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelAttributeResolver(field=caller)


@convert_to_field_resolver.register
def _(ref: LazyRelation, **kwargs: Any) -> GraphQLFieldResolver:
    try:
        value = ref.get_type()
    except RegistryMissingTypeError:
        value = ref.field

    return convert_to_field_resolver(value, **kwargs)


@convert_to_field_resolver.register
def _(ref: LazyGenericForeignKey, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_to_field_resolver(ref.field, **kwargs)


@convert_to_field_resolver.register
def _(ref: LazyLambda, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_to_field_resolver(ref.callback(), **kwargs)


@convert_to_field_resolver.register
def _(_: type[Calculation], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelAttributeResolver(field=caller, static=False)


@convert_to_field_resolver.register
def _(ref: TypeRef, **kwargs: Any) -> Never:
    caller: Field = kwargs["caller"]
    msg = f"Must define a custom resolve for '{caller.name}' since using python type '{ref.value}' as a reference."
    raise FunctionDispatcherError(msg)


@convert_to_field_resolver.register
def _(ref: GraphQLType, **kwargs: Any) -> Never:
    caller: Field = kwargs["caller"]
    msg = f"Must define a custom resolve for '{caller.name}' since using GraphQLType '{ref}' as a reference."
    raise FunctionDispatcherError(msg)


@convert_to_field_resolver.register
def _(ref: GraphQLWrappingType, **kwargs: Any) -> GraphQLFieldResolver:
    return convert_to_field_resolver(ref.of_type, **kwargs)


@convert_to_field_resolver.register
def _(_: GraphQLID, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return GlobalIDResolver(typename=caller.query_type.__schema_name__)


@convert_to_field_resolver.register
def _(_: GenericForeignKey, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelGenericForeignKeyResolver(field=caller)


@convert_to_field_resolver.register
def _(_: GenericRelation, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return ModelManyRelatedFieldResolver(field=caller)


@convert_to_field_resolver.register
def _(ref: type[QueryType], **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    if caller.many:
        return NestedQueryTypeManyResolver(field=caller, query_type=ref)
    return NestedQueryTypeSingleResolver(field=caller, query_type=ref)


@convert_to_field_resolver.register
def _(ref: Connection, **kwargs: Any) -> GraphQLFieldResolver:
    caller: Field = kwargs["caller"]
    return NestedConnectionResolver(connection=ref, field=caller)
