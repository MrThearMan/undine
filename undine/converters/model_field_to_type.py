# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from django.db import models

from undine.typing import ToManyField, ToOneField
from undine.utils import TypeDispatcher

__all__ = [
    "convert_model_field_to_type",
]

convert_model_field_to_type = TypeDispatcher[models.Field, type]()


@convert_model_field_to_type.register
def convert_char_field(field: models.CharField | models.TextField) -> type[str]:
    return str


@convert_model_field_to_type.register
def convert_boolean_field(field: models.BooleanField) -> type[bool]:
    return bool


@convert_model_field_to_type.register
def convert_integer_field(field: models.IntegerField | models.BigIntegerField) -> type[int]:
    return int


@convert_model_field_to_type.register
def convert_float_field(field: models.FloatField) -> type[float]:
    return float


@convert_model_field_to_type.register
def convert_decimal_field(field: models.DecimalField) -> type[Decimal]:
    return Decimal


@convert_model_field_to_type.register
def convert_date_field(field: models.DateField) -> type[datetime.date]:
    return datetime.date


@convert_model_field_to_type.register
def convert_datetime_field(field: models.DateTimeField) -> type[datetime.datetime]:
    return datetime.datetime


@convert_model_field_to_type.register
def convert_time_field(field: models.TimeField) -> type[datetime.time]:
    return datetime.time


@convert_model_field_to_type.register
def convert_binary_field(field: models.BinaryField) -> type[bytes]:
    return bytes


@convert_model_field_to_type.register
def convert_duration_field(field: models.DurationField) -> type[datetime.timedelta]:
    return datetime.timedelta


@convert_model_field_to_type.register
def convert_uuid_field(field: models.UUIDField) -> type[uuid.UUID]:
    return uuid.UUID


@convert_model_field_to_type.register
def convert_to_many_field(field: ToManyField) -> type[list]:
    return list


@convert_model_field_to_type.register
def convert_one_to_one_field(field: ToOneField) -> type[int]:
    return int
