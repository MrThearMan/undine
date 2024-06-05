from __future__ import annotations

import datetime
import decimal
import uuid
from contextlib import suppress
from decimal import Decimal
from types import FunctionType, NoneType
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
    Q,
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
from graphql import GraphQLList, GraphQLNonNull, GraphQLScalarType

from undine.converters import convert_to_python_type
from undine.exceptions import FunctionDispatcherError
from undine.parsers import parse_first_param_type, parse_return_annotation
from undine.scalars import (
    GraphQLAny,
    GraphQLBase16,
    GraphQLBase32,
    GraphQLBase64,
    GraphQLBoolean,
    GraphQLDate,
    GraphQLDateTime,
    GraphQLDecimal,
    GraphQLDuration,
    GraphQLEmail,
    GraphQLFile,
    GraphQLFloat,
    GraphQLID,
    GraphQLImage,
    GraphQLInt,
    GraphQLJSON,
    GraphQLNull,
    GraphQLString,
    GraphQLTime,
    GraphQLURL,
    GraphQLUUID,
)
from undine.typing import CombinableExpression, ToManyField, ToOneField


@convert_to_python_type.register
def _(_: CharField | TextField, **kwargs: Any) -> type:
    return str


@convert_to_python_type.register
def _(_: BooleanField, **kwargs: Any) -> type:
    return bool


@convert_to_python_type.register
def _(_: IntegerField | BigIntegerField, **kwargs: Any) -> type:
    return int


@convert_to_python_type.register
def _(_: FloatField, **kwargs: Any) -> type:
    return float


@convert_to_python_type.register
def _(_: DecimalField, **kwargs: Any) -> type:
    return Decimal


@convert_to_python_type.register
def _(_: DateField, **kwargs: Any) -> type:
    return datetime.date


@convert_to_python_type.register
def _(_: DateTimeField, **kwargs: Any) -> type:
    return datetime.datetime


@convert_to_python_type.register
def _(_: TimeField, **kwargs: Any) -> type:
    return datetime.time


@convert_to_python_type.register
def _(_: DurationField, **kwargs: Any) -> type:
    return datetime.timedelta


@convert_to_python_type.register
def _(_: BinaryField, **kwargs: Any) -> type:
    return bytes


@convert_to_python_type.register
def _(_: UUIDField, **kwargs: Any) -> type:
    return uuid.UUID


@convert_to_python_type.register
def _(_: FileField, **kwargs: Any) -> type:
    return str


@convert_to_python_type.register
def _(_: ImageField, **kwargs: Any) -> type:
    return str


@convert_to_python_type.register
def _(_: JSONField, **kwargs: Any) -> type:
    return dict[str, str]


@convert_to_python_type.register
def _(ref: ToManyField, **kwargs: Any) -> type:
    generic_type = convert_to_python_type(ref.target_field, **kwargs)
    return list.__class_getitem__(generic_type)


@convert_to_python_type.register
def _(ref: ToOneField, **kwargs: Any) -> type:
    return convert_to_python_type(ref.target_field, **kwargs)


@convert_to_python_type.register
def _(_: Q, **kwargs: Any) -> type:
    return bool


@convert_to_python_type.register
def _(ref: CombinableExpression, **kwargs: Any) -> type:
    return convert_to_python_type(ref.output_field, **kwargs)


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


@convert_to_python_type.register
def _(ref: GraphQLNonNull, **kwargs: Any) -> type:
    return convert_to_python_type(ref.of_type, **kwargs)


@convert_to_python_type.register
def _(ref: GraphQLList, **kwargs: Any) -> type:
    item_type = convert_to_python_type(ref.of_type, **kwargs)
    return list.__class_getitem__(item_type)


@convert_to_python_type.register
def _(ref: FunctionType, **kwargs: Any) -> type:
    is_input = kwargs.get("is_input", False)
    return parse_first_param_type(ref) if is_input else parse_return_annotation(ref)


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


@convert_to_python_type.register
def _(ref: GraphQLScalarType, **kwargs: Any) -> type:  # noqa: PLR0911, PLR0912
    match ref.name:
        case GraphQLID.name | GraphQLString.name | GraphQLEmail.name | GraphQLURL.name:
            return str
        case GraphQLBoolean.name:
            return bool
        case GraphQLInt.name:
            return int
        case GraphQLFloat.name:
            return float
        case GraphQLDecimal.name:
            return decimal.Decimal
        case GraphQLDate.name:
            return datetime.date
        case GraphQLTime.name:
            return datetime.time
        case GraphQLDateTime.name:
            return datetime.datetime
        case GraphQLDuration.name:
            return datetime.timedelta
        case GraphQLUUID.name:
            return uuid.UUID
        case GraphQLAny.name:
            return Any
        case GraphQLNull.name:
            return NoneType
        case GraphQLJSON.name:
            return dict
        case GraphQLBase16.name | GraphQLBase32.name | GraphQLBase64.name:
            return bytes
        case GraphQLFile.name | GraphQLImage.name:
            return str

    msg = f"Unknown GraphQLScalarType: '{ref.name}'. Cannot find matching python type."
    raise FunctionDispatcherError(msg)


with suppress(ImportError):
    from django.contrib.postgres.fields import ArrayField, HStoreField

    @convert_to_python_type.register
    def _(ref: HStoreField, **kwargs: Any) -> type:
        return dict[str, str]

    @convert_to_python_type.register
    def _(ref: ArrayField, **kwargs: Any) -> type:
        item_type = convert_to_python_type(ref.base_field, **kwargs)
        return list.__class_getitem__(item_type)


with suppress(ImportError):
    from django.db.models import GeneratedField

    @convert_to_python_type.register
    def _(ref: GeneratedField, **kwargs: Any) -> type:
        return convert_to_python_type(ref.output_field, **kwargs)
