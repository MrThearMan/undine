from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db.models import Field, ForeignKey, Model, OneToOneField, OneToOneRel
from graphql import Undefined

from undine import Input, MutationType
from undine.converters import convert_to_default_value
from undine.dataclasses import LazyLambda, TypeRef
from undine.exceptions import ModelFieldDoesNotExistError
from undine.typing import ToManyField
from undine.utils.model_utils import get_model_field


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
def _(_: GenericRelation, **kwargs: Any) -> Any:
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
    caller: Input = kwargs["caller"]

    try:
        field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.field_name)
    except ModelFieldDoesNotExistError:
        return Undefined

    return convert_to_default_value(field, **kwargs)
