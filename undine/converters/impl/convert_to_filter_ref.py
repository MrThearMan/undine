from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.db.models import F, Q
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine import Filter
from undine.converters import convert_to_filter_ref
from undine.typing import CombinableExpression, ModelField
from undine.utils.model_utils import determine_output_field, get_model_field


@convert_to_filter_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=ref)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=caller.field_name)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(_: F, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    field = get_model_field(model=caller.filterset.__model__, lookup=caller.field_name)
    return convert_to_filter_ref(field, **kwargs)


@convert_to_filter_ref.register
def _(ref: ModelField, **kwargs: Any) -> Any:
    return ref


@convert_to_filter_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.field)


@convert_to_filter_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.rel, **kwargs)


@convert_to_filter_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.related, **kwargs)


@convert_to_filter_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_filter_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_to_filter_ref.register
def _(ref: Q, **kwargs: Any) -> Any:
    return ref


@convert_to_filter_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    determine_output_field(ref, model=caller.filterset.__model__)
    return ref


@convert_to_filter_ref.register
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.field)


@convert_to_filter_ref.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    return ref
