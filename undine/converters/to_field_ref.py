from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, FieldRef, Lambda, ToManyField, ToOneField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Field


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
def _(ref: str, **kwargs: Any) -> FieldRef:
    caller: Field = kwargs["caller"]
    if ref == "self":
        return caller.owner
    field = get_model_field(model=caller.owner.__model__, lookup=ref)
    return convert_to_field_ref(field, **kwargs)


@convert_to_field_ref.register
def _(_: None, **kwargs: Any) -> FieldRef:
    caller: Field = kwargs["caller"]
    field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
    return convert_to_field_ref(field, **kwargs)


@convert_to_field_ref.register
def _(ref: FunctionType, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: Lambda, **kwargs: Any) -> FieldRef:
    return LazyLambdaQueryType(callback=ref)


@convert_to_field_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: models.Field, **kwargs: Any) -> FieldRef:
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


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine.query import QueryType

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
