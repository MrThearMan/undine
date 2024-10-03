from __future__ import annotations

from typing import Any

from django.db import models

from undine.typing import InputRef, TypeRef
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "is_input_only",
]


is_input_only = FunctionDispatcher[InputRef, bool]()
"""Determine whether a the reference is input-only or not."""


@is_input_only.register
def _(_: models.Field, **kwargs: Any) -> bool:
    return False


@is_input_only.register
def _(_: TypeRef, **kwargs: Any) -> bool:
    return True


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.mutation import MutationType

    @is_input_only.register
    def _(_: type[MutationType], **kwargs: Any) -> bool:
        return False

    @is_input_only.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        return False
