from __future__ import annotations

import datetime
import decimal
import uuid
from enum import Enum
from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db.models import F, Field, TextChoices
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute
from graphql import GraphQLType

from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
from undine.typing import CombinableExpression, FieldRef, Lambda, ToManyField, ToOneField
from undine.utils.function_dispatcher import FunctionDispatcher

if TYPE_CHECKING:
    from undine import Field as UndineField
    from undine.optimizer.optimizer import OptimizationData

__all__ = [
    "convert_to_field_ref",
]


convert_to_field_ref = FunctionDispatcher[Any, FieldRef]()
"""
Convert the given value to a reference that 'undine.Field' can deal with.

Positional arguments:
 - ref: The value to convert.

Keyword arguments:
 - caller: The 'undine.Field' instance that is calling this function.
"""


@convert_to_field_ref.register
def _(ref: FunctionType, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: Lambda, **kwargs: Any) -> FieldRef:
    return LazyLambdaQueryType(callback=ref)


@convert_to_field_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> FieldRef:
    caller: UndineField = kwargs["caller"]

    def optimizer_func(field: UndineField, optimizer: OptimizationData) -> None:
        optimizer.annotations[field.name] = field.ref

    caller.optimizer_func = optimizer_func
    return ref


@convert_to_field_ref.register
def _(ref: F, **kwargs: Any) -> FieldRef:
    return convert_to_field_ref(ref.name, **kwargs)


@convert_to_field_ref.register
def _(ref: Field, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: ToOneField | ToManyField, **kwargs: Any) -> FieldRef:
    return LazyQueryType(field=ref)


@convert_to_field_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> FieldRef:
    return convert_to_field_ref(ref.field, **kwargs)


@convert_to_field_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> FieldRef:
    return convert_to_field_ref(ref.rel, **kwargs)


@convert_to_field_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> FieldRef:
    return convert_to_field_ref(ref.related, **kwargs)


@convert_to_field_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> FieldRef:
    return convert_to_field_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_field_ref.register
def _(ref: GraphQLType, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: type[str], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[bool], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[int], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[float], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[decimal.Decimal], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.datetime], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.date], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.time], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.timedelta], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[uuid.UUID], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[Enum], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[TextChoices], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[list], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[dict], **kwargs: Any) -> FieldRef:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: Calculated, **kwargs: Any) -> FieldRef:
    return ref


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine import QueryType
    from undine.relay import Connection
    from undine.utils.model_utils import get_model_field

    @convert_to_field_ref.register
    def _(ref: str, **kwargs: Any) -> FieldRef:
        caller: UndineField = kwargs["caller"]
        if ref == "self":
            return caller.query_type
        field = get_model_field(model=caller.query_type.__model__, lookup=ref)
        return convert_to_field_ref(field, **kwargs)

    @convert_to_field_ref.register
    def _(_: None, **kwargs: Any) -> FieldRef:
        caller: UndineField = kwargs["caller"]
        field = get_model_field(model=caller.query_type.__model__, lookup=caller.model_field_name)
        return convert_to_field_ref(field, **kwargs)

    @convert_to_field_ref.register
    def _(ref: type[QueryType], **kwargs: Any) -> FieldRef:
        return ref

    @convert_to_field_ref.register
    def _(ref: GenericRelation, **kwargs: Any) -> FieldRef:
        return LazyQueryType(field=ref)

    @convert_to_field_ref.register
    def _(ref: GenericRel, **kwargs: Any) -> FieldRef:
        return LazyQueryType(field=ref.field)

    @convert_to_field_ref.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> FieldRef:
        return LazyQueryTypeUnion(field=ref)

    @convert_to_field_ref.register
    def _(ref: Connection, **kwargs: Any) -> FieldRef:
        return ref
