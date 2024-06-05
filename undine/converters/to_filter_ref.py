from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db.models import F, Q
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine.typing import CombinableExpression, FilterRef, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Filter

__all__ = [
    "convert_to_filter_ref",
]


convert_to_filter_ref = FunctionDispatcher[Any, FilterRef]()
"""
Convert the given value to a reference that 'undine.Filter' can deal with.

Positional arguments:
 - ref: The value to convert.

Keyword arguments:
 - caller: The 'undine.Filter' instance that is calling this function.
"""


@convert_to_filter_ref.register
def _(ref: str, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=ref)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(_: None, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=caller.field_name)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(ref: F, **kwargs: Any) -> FilterRef:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=ref.name)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(ref: ModelField, **kwargs: Any) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> FilterRef:
    return ref.field


@convert_to_filter_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> FilterRef:
    return convert_to_filter_ref(ref.rel, **kwargs)


@convert_to_filter_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> FilterRef:
    return convert_to_filter_ref(ref.related, **kwargs)


@convert_to_filter_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> FilterRef:
    return convert_to_filter_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_filter_ref.register
def _(ref: FunctionType, **kwargs: Any) -> FilterRef:
    return ref


@convert_to_filter_ref.register
def _(ref: CombinableExpression | Q, **kwargs: Any) -> FilterRef:
    return ref


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel

    @convert_to_filter_ref.register
    def _(ref: GenericRel, **kwargs: Any) -> FilterRef:
        return convert_to_filter_ref(ref.field)

    @convert_to_filter_ref.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> FilterRef:
        return ref
