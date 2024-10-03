from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, OrderRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Order

__all__ = [
    "convert_to_order_ref",
]


convert_to_order_ref = FunctionDispatcher[Any, OrderRef]()
"""Convert the given value to a undine.Order reference."""


@convert_to_order_ref.register
def _(ref: str, **kwargs: Any) -> OrderRef:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.owner.__model__, lookup=ref)
    return models.F(field.name)


@convert_to_order_ref.register
def _(_: None, **kwargs: Any) -> OrderRef:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
    return models.F(field.name)


@convert_to_order_ref.register
def _(ref: CombinableExpression | models.F, **kwargs: Any) -> OrderRef:
    return ref


@convert_to_order_ref.register
def _(ref: models.Field, **kwargs: Any) -> OrderRef:
    return models.F(ref.name)


@convert_to_order_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> OrderRef:
    return models.F(ref.field.name)
