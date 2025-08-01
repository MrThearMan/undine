from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Field, ForeignKey, Model, OneToOneField, OneToOneRel
from graphql import Undefined

from undine import MutationType
from undine.converters import convert_to_default_value
from undine.dataclasses import LazyLambda, TypeRef
from undine.typing import ToManyField


@convert_to_default_value.register
def _(ref: Field, **kwargs: Any) -> Any:
    if ref.has_default() and not callable(ref.default):
        return ref.default
    if ref.null:
        return None
    if ref.blank and ref.empty_strings_allowed:
        return ""
    return Undefined


@convert_to_default_value.register
def _(ref: OneToOneField | ForeignKey, **kwargs: Any) -> Any:
    if ref.null:
        return None
    return Undefined


@convert_to_default_value.register
def _(_: OneToOneRel | ToManyField, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: GenericForeignKey, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: TypeRef, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: LazyLambda, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: FunctionType, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: type[MutationType], **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: type[Model], **kwargs: Any) -> Any:
    return Undefined
