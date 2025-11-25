from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey

from undine import Field as UndineField
from undine import InterfaceField, QueryType
from undine.converters import convert_to_field_complexity
from undine.dataclasses import LazyGenericForeignKey, LazyRelation
from undine.typing import ModelField, ToManyField, ToOneField
from undine.utils.model_utils import get_model_field


@convert_to_field_complexity.register
def _(_: Any, **kwargs: Any) -> int:
    return 0


@convert_to_field_complexity.register
def _(_: ModelField, **kwargs: Any) -> Any:
    return 0


@convert_to_field_complexity.register
def _(_: ToOneField | ToManyField, **kwargs: Any) -> Any:
    return 1


@convert_to_field_complexity.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> Any:
    return 1


@convert_to_field_complexity.register
def _(_: type[QueryType], **kwargs: Any) -> Any:
    return 1


@convert_to_field_complexity.register
def _(ref: LazyRelation, **kwargs: Any) -> Any:
    return convert_to_field_complexity(ref.field, **kwargs)


@convert_to_field_complexity.register
def _(ref: LazyGenericForeignKey, **kwargs: Any) -> Any:
    return convert_to_field_complexity(ref.field, **kwargs)


@convert_to_field_complexity.register
def _(_: InterfaceField, **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]
    field = get_model_field(model=caller.query_type.__model__, lookup=caller.field_name)
    return convert_to_field_complexity(field, **kwargs)
