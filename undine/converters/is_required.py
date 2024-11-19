from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import NOT_PROVIDED

from undine.typing import InputRef, ModelField, TypeRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Input

__all__ = [
    "is_input_required",
]


is_input_required = FunctionDispatcher[InputRef, bool]()
"""
Determine whether the 'undine.Input' reference indicates a required input.

Positional arguments:
 - ref: The reference to check.

Keyword arguments:
 - caller: The 'undine.Input' instance that is calling this function.
"""


@is_input_required.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]

    is_primary_key = bool(getattr(ref, "primary_key", False))
    is_create_mutation = caller.owner.__mutation_kind__ == "create"
    is_to_many_field = bool(ref.one_to_many) or bool(ref.many_to_many)
    is_nullable = bool(getattr(ref, "null", True))
    has_auto_default = bool(getattr(ref, "auto_now", False)) or bool(getattr(ref, "auto_now_add", False))
    has_default = has_auto_default or getattr(ref, "default", NOT_PROVIDED) is not NOT_PROVIDED

    return is_primary_key or (is_create_mutation and not is_to_many_field and not is_nullable and not has_default)


@is_input_required.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return False


def load_deferred_converters() -> None:  # pragma: no cover
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType

    @is_input_required.register
    def _(_: type[MutationType], **kwargs: Any) -> bool:
        caller: Input = kwargs["caller"]
        field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
        return is_input_required(field, caller=caller)

    @is_input_required.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        caller: Input = kwargs["caller"]
        return caller.owner.__mutation_kind__ == "create"
