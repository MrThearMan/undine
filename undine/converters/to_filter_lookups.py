from __future__ import annotations

from typing import Any

from django.db.models import Field

from undine.typing import ModelField
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "convert_to_filter_lookups",
]


convert_to_filter_lookups = FunctionDispatcher[ModelField, list[str]]()
"""
Convert the given field to its lookups.

Positional arguments:
 - ref: The value to convert.
"""


# TODO: Filter out fields that don't make sense for filtering (e.g. FileFields or nonsensical lookups)


@convert_to_filter_lookups.register
def _(ref: Field, **kwargs: Any) -> list[str]:
    return list(ref.get_lookups())
