# ruff: noqa: TCH001, TCH002, TCH003
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

from undine.typing import Ref, ToManyField, ToOneField
from undine.utils import TypeDispatcher

__all__ = [
    "convert_to_ref",
]


convert_to_ref = TypeDispatcher[Any, Ref]()


@convert_to_ref.register
def convert_function_or_property(ref: FunctionType | property) -> Any:
    return ref


@convert_to_ref.register
def convert_partial(ref: partial) -> Any:
    while True:
        if hasattr(ref, "__wrapped__"):  # Wrapped with functools.wraps
            ref = ref.__wrapped__
            continue
        if isinstance(ref, partial):
            ref = ref.func
            continue
        return convert_to_ref(ref)


@convert_to_ref.register
def convert_staticmethod(ref: staticmethod) -> Any:
    return convert_to_ref(ref.__func__)


@convert_to_ref.register
def convert_deferred_attribute(ref: DeferredAttribute) -> Any:
    return convert_to_ref(ref.field)


@convert_to_ref.register
def convert_forward_descriptors(ref: ForwardManyToOneDescriptor | ManyToManyDescriptor) -> Any:
    return convert_to_ref(ref.field)


@convert_to_ref.register
def convert_reverse_to_one_descriptor(ref: ReverseOneToOneDescriptor) -> Any:
    return convert_to_ref(ref.related)


@convert_to_ref.register
def convert_reverse_to_many_descriptors(ref: ReverseManyToOneDescriptor) -> Any:
    return convert_to_ref(ref.field)


@convert_to_ref.register
def convert_model_rel(ref: ForeignObjectRel) -> Any:
    return convert_to_ref(ref.target_field)


@convert_to_ref.register
def convert_model_field(ref: models.Field) -> Any:
    return ref


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType

    @convert_to_ref.register
    def convert_to_one_field(ref: ToOneField) -> Any:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_ref.register
    def convert_to_many_field(ref: ToManyField) -> Any:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_ref.register
    def convert_model_node(ref: type[ModelGQLType]) -> Any:
        return ref

    @convert_to_ref.register
    def convert_to_generic_relation(ref: GenericRelation) -> Any:
        return DeferredModelGQLType.for_related_field(ref)

    @convert_to_ref.register
    def convert_generic_foreign_key(ref: GenericForeignKey) -> Any:
        return DeferredModelGQLTypeUnion.for_generic_foreign_key(ref)
