from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey

from undine import Input, MutationType
from undine.converters import is_input_only
from undine.dataclasses import LazyLambda, TypeRef
from undine.exceptions import ModelFieldError
from undine.typing import ModelField
from undine.utils.model_utils import get_model_field


@is_input_only.register
def _(_: ModelField, **kwargs: Any) -> bool:
    return False


@is_input_only.register
def _(_: TypeRef | FunctionType, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    try:
        field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.field_name)
    except ModelFieldError:
        return True
    return is_input_only(field)


@is_input_only.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_input_only.register
def _(_: type[MutationType], **kwargs: Any) -> bool:
    return False


@is_input_only.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> bool:
    return False
