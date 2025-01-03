from __future__ import annotations

from types import FunctionType
from typing import Any

from undine.dataclasses import TypeRef
from undine.typing import InputRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "is_input_hidden",
]


is_input_hidden = FunctionDispatcher[InputRef, bool]()
"""
Determine whether the 'undine.Input' reference indicates a hidden input.

Positional arguments:
 - ref: The reference to check.
"""


@is_input_hidden.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    return ref.hidden


@is_input_hidden.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return False


@is_input_hidden.register
def _(_: FunctionType, **kwargs: Any) -> bool:
    return True


def load_deferred() -> None:
    # See. `undine.apps.UndineConfig.load_deferred()` for explanation
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType

    @is_input_hidden.register
    def _(_: type[MutationType], **kwargs: Any) -> bool:
        return False

    @is_input_hidden.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> bool:
        return ref.hidden
