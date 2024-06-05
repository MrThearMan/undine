from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey

from undine import MutationType
from undine.converters import is_input_hidden
from undine.dataclasses import LazyLambda, TypeRef
from undine.typing import ModelField
from undine.utils.reflection import get_signature


@is_input_hidden.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    return ref.hidden


@is_input_hidden.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return False


@is_input_hidden.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_input_hidden.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    sig = get_signature(ref)
    # Has user input if function has three arguments: `(root: Model, info: GQLInfo, value: Any)`
    return len(sig.parameters) != 3  # noqa: PLR2004


@is_input_hidden.register
def _(_: type[MutationType], **kwargs: Any) -> bool:
    return False


@is_input_hidden.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> bool:
    return ref.hidden
