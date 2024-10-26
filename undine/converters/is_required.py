from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
Determine whether the reference requires an input.

:param ref: The reference to check.
:param caller: The 'undine.Input' instance that is calling this function.
"""


@is_input_required.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    caller: Input = kwargs["caller"]
    is_primary_key = bool(getattr(ref, "primary_key", False))

    return is_primary_key or (  # Primary keys are always required.
        # Only create mutations can have required fields.
        caller.owner.__mutation_kind__ == "create"
        # Only non-'*-to-many' fields can be required.
        and not (bool(ref.one_to_many) or bool(ref.many_to_many))
        # Only non-null fields can be required.
        and not bool(getattr(ref, "null", True))
    )


@is_input_required.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return False


def load_deferred_converters() -> None:  # pragma: no cover
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.mutation import MutationType

    @is_input_required.register
    def _(_: type[MutationType], **kwargs: Any) -> bool:
        caller: Input = kwargs["caller"]
        field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
        return is_input_required(field, caller=caller)

    @is_input_required.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        caller: Input = kwargs["caller"]
        return caller.owner.__mutation_kind__ == "create"
