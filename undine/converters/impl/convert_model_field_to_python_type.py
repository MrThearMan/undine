from __future__ import annotations

import datetime
import uuid
from contextlib import suppress
from decimal import Decimal
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
from django.db.models import (
    BigIntegerField,
    BinaryField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    DurationField,
    FileField,
    FloatField,
    ImageField,
    IntegerField,
    JSONField,
    TextField,
    TimeField,
    UUIDField,
)
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.converters import convert_model_field_to_python_type
from undine.typing import ToManyField, ToOneField
from undine.utils.model_fields import TextChoicesField


@convert_model_field_to_python_type.register
def _(_: CharField | TextField, **kwargs: Any) -> type:
    # CharField might have an enum, but we cannot access it anymore.
    return str


@convert_model_field_to_python_type.register
def _(ref: TextChoicesField, **kwargs: Any) -> type:
    return ref.choices_enum


@convert_model_field_to_python_type.register
def _(_: BooleanField, **kwargs: Any) -> type:
    return bool


@convert_model_field_to_python_type.register
def _(_: IntegerField | BigIntegerField, **kwargs: Any) -> type:
    return int


@convert_model_field_to_python_type.register
def _(_: FloatField, **kwargs: Any) -> type:
    return float


@convert_model_field_to_python_type.register
def _(_: DecimalField, **kwargs: Any) -> type:
    return Decimal


@convert_model_field_to_python_type.register
def _(_: DateField, **kwargs: Any) -> type:
    return datetime.date


@convert_model_field_to_python_type.register
def _(_: DateTimeField, **kwargs: Any) -> type:
    return datetime.datetime


@convert_model_field_to_python_type.register
def _(_: TimeField, **kwargs: Any) -> type:
    return datetime.time


@convert_model_field_to_python_type.register
def _(_: DurationField, **kwargs: Any) -> type:
    return datetime.timedelta


@convert_model_field_to_python_type.register
def _(_: BinaryField, **kwargs: Any) -> type:
    return bytes


@convert_model_field_to_python_type.register
def _(_: UUIDField, **kwargs: Any) -> type:
    return uuid.UUID


@convert_model_field_to_python_type.register
def _(_: FileField, **kwargs: Any) -> type:
    return str


@convert_model_field_to_python_type.register
def _(_: ImageField, **kwargs: Any) -> type:
    return str


@convert_model_field_to_python_type.register
def _(_: JSONField, **kwargs: Any) -> type:
    return dict[str, str]


@convert_model_field_to_python_type.register
def _(ref: ToManyField, **kwargs: Any) -> type:
    generic_type = convert_model_field_to_python_type(ref.target_field, **kwargs)
    return list.__class_getitem__(generic_type)


@convert_model_field_to_python_type.register
def _(ref: ToOneField, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.target_field, **kwargs)


@convert_model_field_to_python_type.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.field, **kwargs)


@convert_model_field_to_python_type.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.rel, **kwargs)


@convert_model_field_to_python_type.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.related, **kwargs)


@convert_model_field_to_python_type.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_model_field_to_python_type.register
def _(ref: GenericRelation, **kwargs: Any) -> type:
    generic_type = convert_model_field_to_python_type(ref.target_field, **kwargs)
    return list.__class_getitem__(generic_type)


@convert_model_field_to_python_type.register
def _(ref: GenericRel, **kwargs: Any) -> type:
    return convert_model_field_to_python_type(ref.field)


@convert_model_field_to_python_type.register
def _(ref: GenericForeignKey, **kwargs: Any) -> type:
    field = ref.model._meta.get_field(ref.fk_field)
    return convert_model_field_to_python_type(field)


with suppress(ImportError):
    from django.contrib.postgres.fields import ArrayField, HStoreField

    @convert_model_field_to_python_type.register
    def _(ref: HStoreField, **kwargs: Any) -> type:
        return dict[str, str]

    @convert_model_field_to_python_type.register
    def _(ref: ArrayField, **kwargs: Any) -> type:
        item_type = convert_model_field_to_python_type(ref.base_field, **kwargs)
        return list.__class_getitem__(item_type)


with suppress(ImportError):
    from django.db.models import GeneratedField

    @convert_model_field_to_python_type.register
    def _(ref: GeneratedField, **kwargs: Any) -> type:
        return convert_model_field_to_python_type(ref.output_field, **kwargs)
