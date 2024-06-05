from __future__ import annotations

import datetime
import decimal
import uuid
from enum import Enum
from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
from django.db.models import F, Field, TextChoices
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute, Q
from graphql import GraphQLType

from undine import Calculation, QueryType
from undine import Field as UndineField
from undine.converters import convert_to_field_ref
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.optimizer.optimizer import OptimizationData
from undine.relay import Connection
from undine.typing import CombinableExpression, GQLInfo, Lambda, ToManyField, ToOneField
from undine.utils.graphql.utils import get_arguments, get_queried_field_name
from undine.utils.model_utils import determine_output_field, get_model_field


@convert_to_field_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]
    field = get_model_field(model=caller.query_type.__model__, lookup=caller.field_name)
    return convert_to_field_ref(field, **kwargs)


@convert_to_field_ref.register
def _(_: str, **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]
    field = get_model_field(model=caller.query_type.__model__, lookup=caller.field_name)
    return convert_to_field_ref(field, **kwargs)


@convert_to_field_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: Lambda, **kwargs: Any) -> Any:
    return LazyLambda(callback=ref)


@convert_to_field_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]
    determine_output_field(ref, model=caller.query_type.__model__)

    def optimizer_func(field: UndineField, data: OptimizationData, info: GQLInfo) -> None:
        data.annotations[field.name] = ref

    caller.optimizer_func = optimizer_func
    return ref


@convert_to_field_ref.register
def _(ref: Q, **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]

    def optimizer_func(field: UndineField, data: OptimizationData, info: GQLInfo) -> None:
        data.annotations[field.name] = ref

    caller.optimizer_func = optimizer_func
    return ref


@convert_to_field_ref.register
def _(ref: F, **kwargs: Any) -> Any:
    return convert_to_field_ref(ref.name, **kwargs)


@convert_to_field_ref.register
def _(ref: Field, **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: ToOneField | ToManyField, **kwargs: Any) -> Any:
    return LazyRelation(field=ref)


@convert_to_field_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_field_ref(ref.field, **kwargs)


@convert_to_field_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_field_ref(ref.rel, **kwargs)


@convert_to_field_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_field_ref(ref.related, **kwargs)


@convert_to_field_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> Any:
    return convert_to_field_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_field_ref.register
def _(ref: GraphQLType, **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: type[str], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[bool], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[int], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[float], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[decimal.Decimal], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.datetime], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.date], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.time], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[datetime.timedelta], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[uuid.UUID], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[Enum | TextChoices], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[list], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[dict], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_field_ref.register
def _(ref: type[Calculation], **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: type[QueryType], **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: GenericRelation, **kwargs: Any) -> Any:
    return LazyRelation(field=ref)


@convert_to_field_ref.register
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return LazyRelation(field=ref.field)


@convert_to_field_ref.register
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    return LazyGenericForeignKey(field=ref)


@convert_to_field_ref.register
def _(ref: Connection, **kwargs: Any) -> Any:
    return ref


@convert_to_field_ref.register
def _(ref: type[Calculation], **kwargs: Any) -> Any:
    caller: UndineField = kwargs["caller"]

    def optimizer_func(field: UndineField, data: OptimizationData, info: GQLInfo) -> None:
        arg_values = get_arguments(info)
        field_name = get_queried_field_name(field.name, info)
        calculation = ref(field_name, **arg_values)
        data.field_calculations.append(calculation)

    caller.optimizer_func = optimizer_func
    return ref
