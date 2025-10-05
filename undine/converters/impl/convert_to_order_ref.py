from __future__ import annotations

import itertools
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.db.models import F, Model
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute, Q
from graphql import GraphQLInputType

from undine import Order
from undine.converters import convert_to_graphql_type, convert_to_order_ref
from undine.exceptions import UnionModelFieldDirectUsageError, UnionModelFieldMismatchError
from undine.typing import CombinableExpression, ModelField
from undine.utils.model_utils import determine_output_field, get_model_field


@convert_to_order_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]

    models = caller.orderset.__models__
    if len(models) == 1:
        get_model_field(model=caller.orderset.__models__[0], lookup=ref)
        return F(ref)

    fields_by_model: dict[type[Model], GraphQLInputType] = {}
    for model in caller.orderset.__models__:
        field = get_model_field(model=model, lookup=caller.field_name)
        fields_by_model[model] = convert_to_graphql_type(field, model=model, is_input=True)

    for (model_1, field_1), (model_2, field_2) in itertools.combinations(fields_by_model.items(), 2):
        if field_1 != field_2:
            raise UnionModelFieldMismatchError(
                ref=ref,
                type_1=field_1,
                model_1=model_1,
                type_2=field_2,
                model_2=model_2,
                kind="Order",
            )

    return F(ref)


@convert_to_order_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]
    return convert_to_order_ref(caller.field_name, **kwargs)


@convert_to_order_ref.register
def _(ref: F | Q, **kwargs: Any) -> Any:
    return ref


@convert_to_order_ref.register
def _(ref: ModelField, **kwargs: Any) -> Any:
    caller = kwargs["caller"]

    models = caller.orderset.__models__
    if len(models) != 1:
        raise UnionModelFieldDirectUsageError(kind="OrderSet")

    return F(ref.name)


@convert_to_order_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: Order = kwargs["caller"]
    models = caller.orderset.__models__

    if len(models) == 1:
        ref.output_field = determine_output_field(ref, model=caller.orderset.__models__[0])
        return ref

    fields_by_model: dict[type[Model], ModelField] = {}
    for model in models:
        fields_by_model[model] = determine_output_field(ref, model=model)

    for (model_1, field_1), (model_2, field_2) in itertools.combinations(fields_by_model.items(), 2):
        if field_1.__class__ is not field_2.__class__:
            raise UnionModelFieldMismatchError(
                ref=ref,
                type_1=field_1,
                model_1=model_1,
                type_2=field_2,
                model_2=model_2,
                kind="Order",
            )

    ref.output_field = next(iter(fields_by_model.values()))
    return ref


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
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return convert_to_order_ref(ref.field, **kwargs)


@convert_to_order_ref.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    caller = kwargs["caller"]

    models = caller.orderset.__models__
    if len(models) != 1:
        raise UnionModelFieldDirectUsageError(kind="OrderSet")

    return F(ref.name)
