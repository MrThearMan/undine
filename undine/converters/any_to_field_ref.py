from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models import ForeignObjectRel
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.parsers import parse_model_field
from undine.typing import FieldRef, ToManyField, ToOneField
from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion
from undine.utils.dispatcher import TypeDispatcher

if TYPE_CHECKING:
    from undine.fields import Field


__all__ = [
    "convert_to_field_ref",
]


convert_to_field_ref = TypeDispatcher[Any, FieldRef]()


@convert_to_field_ref.register
def _(ref: str, **kwargs: Any) -> FieldRef:
    caller: Field = kwargs["caller"]
    if ref == "self":
        return caller.owner
    return parse_model_field(model=caller.owner.__model__, lookup=ref)


@convert_to_field_ref.register
def _(_: None, **kwargs: Any) -> FieldRef:
    caller: Field = kwargs["caller"]
    return parse_model_field(model=caller.owner.__model__, lookup=caller.name)


@convert_to_field_ref.register
def _(ref: FunctionType, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: models.Expression | models.Subquery, **kwargs: Any) -> FieldRef:
    return ref


@convert_to_field_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> FieldRef:
    return ref.field


@convert_to_field_ref.register
def _(ref: ForwardManyToOneDescriptor | ManyToManyDescriptor, **kwargs: Any) -> FieldRef:
    return ref.field


@convert_to_field_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> FieldRef:
    return ref.related


@convert_to_field_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> FieldRef:
    return ref.field


@convert_to_field_ref.register
def _(ref: ForeignObjectRel, **kwargs: Any) -> FieldRef:
    return ref.target_field


@convert_to_field_ref.register
def _(ref: models.Field, **kwargs: Any) -> FieldRef:
    return ref


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine import ModelGQLType

    @convert_to_field_ref.register
    def _(ref: ToOneField, **kwargs: Any) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: ToManyField, **kwargs: Any) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: type[ModelGQLType], **kwargs: Any) -> FieldRef:
        return ref

    @convert_to_field_ref.register
    def _(ref: GenericRelation, **kwargs: Any) -> FieldRef:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_field_ref.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> FieldRef:
        return DeferredModelGQLTypeUnion.for_generic_foreign_key(ref)
