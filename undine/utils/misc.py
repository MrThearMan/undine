from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeGuard

from django.db import models

if TYPE_CHECKING:
    from types import FunctionType

__all__ = [
    "dotpath",
    "is_pk_property",
]


def dotpath(obj: type | FunctionType) -> str:
    """Get the dotpath of the given object."""
    return f"{obj.__module__}.{obj.__qualname__}"


def is_pk_property(ref: Any) -> TypeGuard[property]:
    """Check is the given value is the Django Model 'pk' property."""
    return isinstance(ref, property) and ref.fget == models.Model._get_pk_val  # noqa: SLF001
