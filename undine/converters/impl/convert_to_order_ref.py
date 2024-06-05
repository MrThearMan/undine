from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
from django.db.models import F
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute, Q

from undine import Order
from undine.converters import convert_to_order_ref
from undine.typing import CombinableExpression, ModelField
from undine.utils.model_utils import determine_output_field, get_model_field


@convert_to_order_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.orderset.__model__, lookup=ref)
    return F(field.name)


@convert_to_order_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]
    field = get_model_field(model=caller.orderset.__model__, lookup=caller.field_name)
    return F(field.name)


@convert_to_order_ref.register
def _(ref: F | Q, **kwargs: Any) -> Any:
    return ref


@convert_to_order_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]
    determine_output_field(ref, model=caller.orderset.__model__)
    return ref


@convert_to_order_ref.register
def _(ref: ModelField, **kwargs: Any) -> Any:
    return F(ref.name)


@convert_to_order_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.field, **kwargs)


@convert_to_order_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.rel, **kwargs)


@convert_to_order_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.related, **kwargs)


@convert_to_order_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_order_ref.register
def _(ref: GenericRelation, **kwargs: Any) -> Any:
    return F(ref.name)


@convert_to_order_ref.register
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.field)


@convert_to_order_ref.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    return F(ref.name)
