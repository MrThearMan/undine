from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Model
from graphql import Undefined

from undine import Input, MutationType
from undine.converters import is_input_required
from undine.dataclasses import LazyLambda, TypeRef
from undine.exceptions import ModelFieldError
from undine.parsers import parse_is_nullable, parse_parameters
from undine.typing import ModelField, MutationKind
from undine.utils.graphql.utils import is_non_null_default_value
from undine.utils.model_utils import get_model_field, has_default, is_to_many


@is_input_required.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]

    is_primary_key = bool(getattr(ref, "primary_key", False))
    is_nullable = bool(getattr(ref, "null", True))
    is_to_many_field = is_to_many(ref)
    has_non_null_default_value = is_non_null_default_value(caller.default_value)
    has_field_default = has_default(ref)

    match caller.mutation_type.__kind__:
        case MutationKind.create:
            if is_to_many_field:
                return False
            if is_nullable:
                return False
            if has_non_null_default_value:
                return True
            return not has_field_default

        case MutationKind.update | MutationKind.delete:
            return is_primary_key

        case MutationKind.custom:
            return True

        case MutationKind.related:
            return False

        case _:  # pragma: no cover
            return False


@is_input_required.register
def _(_: type[Model], **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]

    try:
        field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.field_name)
    except ModelFieldError:
        return True

    return is_input_required(field, **kwargs)


@is_input_required.register
def _(ref: TypeRef, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]

    # GraphQL doesn't differentiate between null and required.
    nullable = parse_is_nullable(ref.value, is_input=True, total=ref.total)
    if nullable:
        return False

    if is_non_null_default_value(caller.default_value):
        return True

    return caller.mutation_type.__kind__ in {MutationKind.create, MutationKind.custom}


@is_input_required.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_input_required.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    parameters = parse_parameters(ref)
    first_param_default_value = next((param.default_value for param in parameters), Undefined)
    return is_non_null_default_value(first_param_default_value)


@is_input_required.register
def _(_: type[MutationType], **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.field_name)
    return is_input_required(field, caller=caller)


@is_input_required.register
def _(_: GenericForeignKey, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    return caller.mutation_type.__kind__ == MutationKind.create
