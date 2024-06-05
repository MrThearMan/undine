from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db.models import Field, ForeignObjectRel
from graphql import Undefined

from undine.dataclasses import TypeRef
from undine.typing import InputRef
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "convert_to_default_value",
]


convert_to_default_value = FunctionDispatcher[InputRef, Any]()
"""
Convert the 'undine.Input' reference to its default value.

Positional arguments:
 - ref: The reference to check.
"""


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
def _(_: ForeignObjectRel, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: TypeRef, **kwargs: Any) -> Any:
    return Undefined


@convert_to_default_value.register
def _(_: FunctionType, **kwargs: Any) -> Any:
    return Undefined


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType

    @convert_to_default_value.register
    def _(_: type[MutationType], **kwargs: Any) -> Any:
        return Undefined

    @convert_to_default_value.register
    def _(_: GenericForeignKey, **kwargs: Any) -> Any:
        return Undefined
