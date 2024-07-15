from __future__ import annotations

from functools import partial
from types import FunctionType
from typing import Any

from django.db import models
from django.db.models import ForeignObjectRel
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.typing import FieldRef, ToManyField, ToOneField
from undine.utils.defer import DeferredModelField, DeferredModelGQLType, DeferredModelGQLTypeUnion
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.reflection import get_wrapped

__all__ = [
    "convert_to_field_ref",
]


convert_to_field_ref = TypeDispatcher[Any, FieldRef]()


@convert_to_field_ref.register
def _(ref: FunctionType) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: property) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: partial) -> FieldRef:
    return get_wrapped(ref)


@convert_to_field_ref.register
def _(ref: staticmethod | classmethod) -> FieldRef:
    return ref.__func__  # type: ignore[return-value]


@convert_to_field_ref.register
def _(ref: DeferredAttribute) -> FieldRef:
    return convert_to_field_ref(ref.field)


@convert_to_field_ref.register
def _(ref: ForwardManyToOneDescriptor | ManyToManyDescriptor) -> FieldRef:
    return convert_to_field_ref(ref.field)


@convert_to_field_ref.register
def _(ref: ReverseOneToOneDescriptor) -> FieldRef:
    return convert_to_field_ref(ref.related)


@convert_to_field_ref.register
def _(ref: ReverseManyToOneDescriptor) -> FieldRef:
    return convert_to_field_ref(ref.field)


@convert_to_field_ref.register
def _(ref: ForeignObjectRel) -> FieldRef:
    return convert_to_field_ref(ref.target_field)


@convert_to_field_ref.register
def _(ref: models.Field) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: str) -> FieldRef:
    if ref == "self":
        return "self"
    return DeferredModelField.from_lookup(ref)


@convert_to_field_ref.register
def _(_: None) -> FieldRef:
    return DeferredModelField.from_none()


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine.model_graphql import ModelGQLType

    @convert_to_field_ref.register
    def _(ref: ToOneField) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: ToManyField) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: type[ModelGQLType]) -> FieldRef:
        return ref

    @convert_to_field_ref.register
    def _(ref: GenericRelation) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: GenericForeignKey) -> FieldRef:
        return DeferredModelGQLTypeUnion.for_generic_foreign_key(ref)
