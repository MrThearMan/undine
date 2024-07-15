from __future__ import annotations

from functools import partial
from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import FilterRef
from undine.utils.defer import DeferredModelField
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.reflection import get_wrapped

__all__ = [
    "convert_to_filter_ref",
]


convert_to_filter_ref = TypeDispatcher[Any, FilterRef]()


@convert_to_filter_ref.register
def _(ref: str) -> FilterRef:
    if ref == "self":
        return "self"
    return DeferredModelField.from_lookup(ref)


@convert_to_filter_ref.register
def _(_: None) -> FilterRef:
    return DeferredModelField.from_none()


@convert_to_filter_ref.register
def _(ref: FunctionType) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: partial) -> FilterRef:
    return get_wrapped(ref)


@convert_to_filter_ref.register
def _(ref: staticmethod | classmethod) -> FilterRef:
    return ref.__func__  # type: ignore[return-value]


@convert_to_filter_ref.register
def _(ref: models.Q | models.Expression | models.Subquery) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: DeferredAttribute) -> FilterRef:
    return convert_to_filter_ref(ref.field)


@convert_to_filter_ref.register
def _(ref: models.Field) -> FilterRef:
    return ref
