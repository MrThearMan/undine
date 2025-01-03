from __future__ import annotations

import datetime
import decimal
import uuid
from enum import Enum
from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db.models import F, TextChoices
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.dataclasses import TypeRef
from undine.typing import InputRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Input

__all__ = [
    "convert_to_input_ref",
]


convert_to_input_ref = FunctionDispatcher[Any, InputRef]()
"""
Convert the given value to a reference that 'undine.Input' can deal with.

Positional arguments:
 - ref: The value to convert.

Keyword arguments:
 - caller: The 'undine.Input' instance that is calling this function.
"""


@convert_to_input_ref.register
def _(_: None, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.name)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: F, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=ref.name)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: ModelField, **kwargs: Any) -> InputRef:
    return ref


@convert_to_input_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> InputRef:
    return ref.field


@convert_to_input_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> InputRef:
    return convert_to_input_ref(ref.rel, **kwargs)


@convert_to_input_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> InputRef:
    return convert_to_input_ref(ref.related, **kwargs)


@convert_to_input_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> InputRef:
    return convert_to_input_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_input_ref.register
def _(ref: str, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    if ref == "self":
        return caller.mutation_type
    field = get_model_field(model=caller.mutation_type.__model__, lookup=ref)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: type[str], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[bool], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[int], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[float], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[decimal.Decimal], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.datetime], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.date], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.time], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.timedelta], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[uuid.UUID], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[Enum], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[TextChoices], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[list], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[dict], **kwargs: Any) -> InputRef:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: FunctionType, **kwargs: Any) -> InputRef:
    return ref


def load_deferred() -> None:
    # See. `undine.apps.UndineConfig.load_deferred()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    from undine import MutationType

    @convert_to_input_ref.register
    def _(ref: type[MutationType], **kwargs: Any) -> InputRef:
        return ref

    @convert_to_input_ref.register
    def _(ref: GenericRelation, **kwargs: Any) -> InputRef:
        return ref

    @convert_to_input_ref.register
    def _(ref: GenericRel, **kwargs: Any) -> InputRef:
        return ref.field

    @convert_to_input_ref.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> InputRef:
        return ref
