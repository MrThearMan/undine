from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.parsers import parse_first_param_type, parse_return_annotation
from undine.typing import CombinableExpression, ToManyField, ToOneField
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "convert_to_python_type",
]

convert_to_python_type = FunctionDispatcher[Any, type]()
"""
Convert the given value to a python type.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - is_input: (Optional) Whether the type is for an input or output. Defaults to `False`.
"""


@convert_to_python_type.register
def _(_: models.CharField | models.TextField, **kwargs: Any) -> type:
    return str


@convert_to_python_type.register
def _(_: models.BooleanField, **kwargs: Any) -> type:
    return bool


@convert_to_python_type.register
def _(_: models.IntegerField | models.BigIntegerField, **kwargs: Any) -> type:
    return int


@convert_to_python_type.register
def _(_: models.FloatField, **kwargs: Any) -> type:
    return float


@convert_to_python_type.register
def _(_: models.DecimalField, **kwargs: Any) -> type:
    return Decimal


@convert_to_python_type.register
def _(_: models.DateField, **kwargs: Any) -> type:
    return datetime.date


@convert_to_python_type.register
def _(_: models.DateTimeField, **kwargs: Any) -> type:
    return datetime.datetime


@convert_to_python_type.register
def _(_: models.TimeField, **kwargs: Any) -> type:
    return datetime.time


@convert_to_python_type.register
def _(_: models.DurationField, **kwargs: Any) -> type:
    return datetime.timedelta


@convert_to_python_type.register
def _(_: models.BinaryField, **kwargs: Any) -> type:
    return bytes


@convert_to_python_type.register
def _(_: models.UUIDField, **kwargs: Any) -> type:
    return uuid.UUID


@convert_to_python_type.register
def _(ref: ToManyField, **kwargs: Any) -> type:
    generic_type = convert_to_python_type(ref.target_field, **kwargs)
    return list.__class_getitem__(generic_type)


@convert_to_python_type.register
def _(ref: ToOneField, **kwargs: Any) -> type:
    return convert_to_python_type(ref.target_field, **kwargs)


@convert_to_python_type.register
def _(_: models.Q, **kwargs: Any) -> type:
    return bool


@convert_to_python_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> type:
    return convert_to_python_type(ref.output_field, **kwargs)


@convert_to_python_type.register
def _(ref: FunctionType, **kwargs: Any) -> type:
    is_input = kwargs.get("is_input", False)
    return parse_first_param_type(ref) if is_input else parse_return_annotation(ref)


@convert_to_python_type.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> type:
    return convert_to_python_type(ref.field, **kwargs)


@convert_to_python_type.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> type:
    return convert_to_python_type(ref.rel, **kwargs)


@convert_to_python_type.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> type:
    return convert_to_python_type(ref.related, **kwargs)


@convert_to_python_type.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> type:
    return convert_to_python_type(ref.rel if ref.reverse else ref.field, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    @convert_to_python_type.register
    def _(ref: GenericRelation, **kwargs: Any) -> type:
        generic_type = convert_to_python_type(ref.target_field, **kwargs)
        return list.__class_getitem__(generic_type)

    @convert_to_python_type.register
    def _(ref: GenericRel, **kwargs: Any) -> type:
        return convert_to_python_type(ref.field)

    @convert_to_python_type.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> type:
        field = ref.model._meta.get_field(ref.fk_field)
        return convert_to_python_type(field)
