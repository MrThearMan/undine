from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import NOT_PROVIDED
from graphql import Undefined

from undine import Input, MutationType
from undine.converters import is_input_required
from undine.dataclasses import LazyLambda, TypeRef
from undine.parsers import parse_parameters
from undine.typing import ModelField, MutationKind
from undine.utils.model_utils import get_model_field


@is_input_required.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]

    is_primary_key = bool(getattr(ref, "primary_key", False))
    is_create_mutation = caller.mutation_type.__kind__ == MutationKind.create
    is_related_mutation = caller.mutation_type.__kind__ == MutationKind.related
    is_to_many_field = bool(ref.one_to_many) or bool(ref.many_to_many)
    is_nullable = bool(getattr(ref, "null", True))
    has_auto_default = bool(getattr(ref, "auto_now", False)) or bool(getattr(ref, "auto_now_add", False))
    has_default = has_auto_default or getattr(ref, "default", NOT_PROVIDED) is not NOT_PROVIDED

    if is_related_mutation:
        return False

    if is_create_mutation:
        return not is_to_many_field and not is_nullable and not has_default

    return is_primary_key


@is_input_required.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return False


@is_input_required.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_input_required.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    parameters = parse_parameters(ref)
    first_param_default_value = next((param.default_value for param in parameters), Undefined)
    return first_param_default_value is Undefined


@is_input_required.register
def _(_: type[MutationType], **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.name)
    return is_input_required(field, caller=caller)


@is_input_required.register
def _(_: GenericForeignKey, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    return caller.mutation_type.__kind__ == MutationKind.create
