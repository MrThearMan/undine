from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.parsers import parse_model_field
from undine.typing import OrderingRef
from undine.utils.dispatcher import TypeDispatcher

if TYPE_CHECKING:
    from undine.fields import Ordering


__all__ = [
    "convert_to_ordering_ref",
]


convert_to_ordering_ref = TypeDispatcher[Any, OrderingRef]()


@convert_to_ordering_ref.register
def _(ref: str, **kwargs: Any) -> OrderingRef:
    caller: Ordering = kwargs["caller"]
    field = parse_model_field(model=caller.owner.__model__, lookup=ref)
    return models.F(field.name)


@convert_to_ordering_ref.register
def _(_: None, **kwargs: Any) -> OrderingRef:
    caller: Ordering = kwargs["caller"]
    field = parse_model_field(model=caller.owner.__model__, lookup=caller.name)
    return models.F(field.name)


@convert_to_ordering_ref.register
def _(ref: models.Expression | models.F | models.Subquery, **kwargs: Any) -> OrderingRef:
    return ref


@convert_to_ordering_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> OrderingRef:
    return models.F(ref.field.name)


@convert_to_ordering_ref.register
def _(ref: models.Field, **kwargs: Any) -> OrderingRef:
    return models.F(ref.name)
