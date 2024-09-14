from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, OrderingRef
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine.fields import Ordering


__all__ = [
    "convert_to_ordering_ref",
]


convert_to_ordering_ref = FunctionDispatcher[Any, OrderingRef]()
"""Convert the given value to a Undine Ordering reference."""


@convert_to_ordering_ref.register
def _(ref: str, **kwargs: Any) -> OrderingRef:
    caller: Ordering = kwargs["caller"]
    field = get_model_field(model=caller.owner.__model__, lookup=ref)
    return models.F(field.name)


@convert_to_ordering_ref.register
def _(_: None, **kwargs: Any) -> OrderingRef:
    caller: Ordering = kwargs["caller"]
    field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
    return models.F(field.name)


@convert_to_ordering_ref.register
def _(ref: CombinableExpression | models.F, **kwargs: Any) -> OrderingRef:
    return ref


@convert_to_ordering_ref.register
def _(ref: models.Field, **kwargs: Any) -> OrderingRef:
    return models.F(ref.name)


@convert_to_ordering_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> OrderingRef:
    return models.F(ref.field.name)
