from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from django.db import models

from undine.typing import ToManyField, ToOneField
from undine.utils.dispatcher import TypeDispatcher

__all__ = [
    "convert_model_field_to_type",
]

convert_model_field_to_type = TypeDispatcher[models.Field, type]()
"""Convert the given model field to a python type."""


@convert_model_field_to_type.register
def _(_: models.CharField | models.TextField) -> type[str]:
    return str


@convert_model_field_to_type.register
def _(_: models.BooleanField) -> type[bool]:
    return bool


@convert_model_field_to_type.register
def _(_: models.IntegerField | models.BigIntegerField) -> type[int]:
    return int


@convert_model_field_to_type.register
def _(_: models.FloatField) -> type[float]:
    return float


@convert_model_field_to_type.register
def _(_: models.DecimalField) -> type[Decimal]:
    return Decimal


@convert_model_field_to_type.register
def _(_: models.DateField) -> type[datetime.date]:
    return datetime.date


@convert_model_field_to_type.register
def _(_: models.DateTimeField) -> type[datetime.datetime]:
    return datetime.datetime


@convert_model_field_to_type.register
def _(_: models.TimeField) -> type[datetime.time]:
    return datetime.time


@convert_model_field_to_type.register
def _(_: models.BinaryField) -> type[bytes]:
    return bytes


@convert_model_field_to_type.register
def _(_: models.DurationField) -> type[datetime.timedelta]:
    return datetime.timedelta


@convert_model_field_to_type.register
def _(_: models.UUIDField) -> type[uuid.UUID]:
    return uuid.UUID


@convert_model_field_to_type.register
def _(_: ToManyField) -> type[list]:
    return list


@convert_model_field_to_type.register
def _(_: ToOneField) -> type[int]:
    return int
