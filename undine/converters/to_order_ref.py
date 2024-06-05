from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db.models import F
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, ModelField, OrderRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Order

__all__ = [
    "convert_to_order_ref",
]


convert_to_order_ref = FunctionDispatcher[Any, OrderRef]()
"""
Convert the given value to a reference that 'undine.Order' can deal with.

Positional arguments:
 - ref: The value to convert.

Keyword arguments:
 - caller: The 'undine.Order' instance that is calling this function.
"""


@convert_to_order_ref.register
def _(ref: str, **kwargs: Any) -> OrderRef:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.orderset.__model__, lookup=ref)
    return F(field.name)


@convert_to_order_ref.register
def _(_: None, **kwargs: Any) -> OrderRef:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.orderset.__model__, lookup=caller.name)
    return F(field.name)


@convert_to_order_ref.register
def _(ref: CombinableExpression | F, **kwargs: Any) -> OrderRef:
    return ref


@convert_to_order_ref.register
def _(ref: ModelField, **kwargs: Any) -> OrderRef:
    return F(ref.name)


@convert_to_order_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> OrderRef:
    return convert_to_order_ref(ref.field, **kwargs)


@convert_to_order_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> OrderRef:
    return convert_to_order_ref(ref.rel, **kwargs)


@convert_to_order_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> OrderRef:
    return convert_to_order_ref(ref.related, **kwargs)


@convert_to_order_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> OrderRef:
    return convert_to_order_ref(ref.rel if ref.reverse else ref.field, **kwargs)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation

    @convert_to_order_ref.register
    def _(ref: GenericRelation, **kwargs: Any) -> OrderRef:
        return F(ref.name)

    @convert_to_order_ref.register
    def _(ref: GenericRel, **kwargs: Any) -> OrderRef:
        return convert_to_order_ref(ref.field)

    @convert_to_order_ref.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> OrderRef:
        return F(ref.name)
