from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, FilterRef, ModelField
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine.fields import Filter


__all__ = [
    "convert_to_filter_ref",
]


convert_to_filter_ref = TypeDispatcher[Any, FilterRef]()
"""Convert the given value to a Undine Filter reference."""


@convert_to_filter_ref.register
def _(ref: str, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    return get_model_field(model=caller.owner.__model__, lookup=ref)


@convert_to_filter_ref.register
def _(_: None, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    return get_model_field(model=caller.owner.__model__, lookup=caller.name)


@convert_to_filter_ref.register
def _(ref: models.F, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    return get_model_field(model=caller.owner.__model__, lookup=ref.name)


@convert_to_filter_ref.register
def _(ref: ModelField, **kwargs: Any) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> FilterRef:
    return ref.field


@convert_to_filter_ref.register
def _(ref: FunctionType, **kwargs: Any) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: CombinableExpression | models.Q, **kwargs: Any) -> FilterRef:
    return ref
