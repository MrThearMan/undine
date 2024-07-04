from __future__ import annotations

from functools import partial
from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import OrderingRef
from undine.utils import DeferredModelField, TypeDispatcher, get_wrapped

__all__ = [
    "convert_to_ordering_ref",
]


convert_to_ordering_ref = TypeDispatcher[Any, OrderingRef]()


@convert_to_ordering_ref.register
def _(ref: str) -> OrderingRef:
    return DeferredModelField.from_lookup(ref)


@convert_to_ordering_ref.register
def _(_: None) -> OrderingRef:
    return DeferredModelField.from_none()


@convert_to_ordering_ref.register
def _(ref: FunctionType) -> OrderingRef:
    return ref


@convert_to_ordering_ref.register
def _(ref: partial) -> OrderingRef:
    return get_wrapped(ref)


@convert_to_ordering_ref.register
def _(ref: staticmethod | classmethod) -> OrderingRef:
    return ref.__func__  # type: ignore[return-value]


@convert_to_ordering_ref.register
def _(ref: models.Expression | models.F) -> OrderingRef:
    return ref


@convert_to_ordering_ref.register
def _(ref: DeferredAttribute) -> OrderingRef:
    return ref.field


@convert_to_ordering_ref.register
def _(ref: models.Field) -> OrderingRef:
    return ref
