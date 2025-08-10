from __future__ import annotations

import datetime
import decimal
import uuid
from enum import Enum
from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
from django.db.models import F, Model, TextChoices
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute

from undine import Input, MutationType
from undine.converters import convert_to_input_ref, is_many
from undine.dataclasses import LazyLambda, TypeRef
from undine.exceptions import InvalidInputMutationTypeError
from undine.typing import GenericField, Lambda, ModelField, MutationKind, RelatedField, RelationType
from undine.utils.model_utils import (
    generic_foreign_key_for_generic_relation,
    get_instance_or_raise,
    get_instances_or_raise,
    get_model_field,
    get_related_name,
)


@convert_to_input_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=caller.field_name)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: F, **kwargs: Any) -> Any:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=ref.name)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: ModelField, **kwargs: Any) -> Any:
    return ref


@convert_to_input_ref.register
def _(ref: type[Model], **kwargs: Any) -> Any:
    caller: Input = kwargs["caller"]

    user_func = caller.convertion_func

    if is_many(ref, model=caller.mutation_type.__model__, name=caller.field_name):

        def convert_many(inpt: Input, value: list[Any]) -> list[Model]:
            instances = get_instances_or_raise(model=ref, pks=set(value))
            if user_func is not None:
                return user_func(inpt, instances)
            return instances

        caller.convertion_func = convert_many
        return ref

    def convert_single(inpt: Input, value: Any) -> Model:
        instance = get_instance_or_raise(model=ref, pk=value)
        if user_func is not None:
            return user_func(inpt, instance)
        return instance

    caller.convertion_func = convert_single
    return ref


@convert_to_input_ref.register
def _(ref: DeferredAttribute | ForwardManyToOneDescriptor, **kwargs: Any) -> Any:
    return ref.field


@convert_to_input_ref.register
def _(ref: ReverseManyToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_input_ref(ref.rel, **kwargs)


@convert_to_input_ref.register
def _(ref: ReverseOneToOneDescriptor, **kwargs: Any) -> Any:
    return convert_to_input_ref(ref.related, **kwargs)


@convert_to_input_ref.register
def _(ref: ManyToManyDescriptor, **kwargs: Any) -> Any:
    return convert_to_input_ref(ref.rel if ref.reverse else ref.field, **kwargs)


@convert_to_input_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: Input = kwargs["caller"]
    field = get_model_field(model=caller.mutation_type.__model__, lookup=ref)
    return convert_to_input_ref(field, **kwargs)


@convert_to_input_ref.register
def _(ref: Lambda, **kwargs: Any) -> Any:
    return LazyLambda(callback=ref)


@convert_to_input_ref.register
def _(ref: type[str], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[bool], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[int], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[float], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[decimal.Decimal], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.datetime], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.date], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.time], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[datetime.timedelta], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[uuid.UUID], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[Enum], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[TextChoices], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[list], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: type[dict], **kwargs: Any) -> Any:
    return TypeRef(value=ref)


@convert_to_input_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_to_input_ref.register
def _(ref: type[MutationType], **kwargs: Any) -> Any:
    if ref.__kind__ != MutationKind.related:
        raise InvalidInputMutationTypeError(ref=ref, kind=ref.__kind__)

    caller: Input = kwargs["caller"]

    # Remove the Input for the reverse relation from the MutationType used as the Input for this one.
    model = caller.mutation_type.__model__
    field: RelatedField | GenericField = get_model_field(model=model, lookup=caller.field_name)  # type: ignore[assignment]

    relation_type = RelationType.for_related_field(field)

    if relation_type.is_generic_relation:
        reverse_field_name: str = generic_foreign_key_for_generic_relation(field).name  # type: ignore[arg-type]
        ref.__input_map__.pop(reverse_field_name, None)

    elif not relation_type.is_generic_foreign_key:
        reverse_field_name = get_related_name(field.remote_field)  # type: ignore[arg-type]
        ref.__input_map__.pop(reverse_field_name, None)

    return ref


@convert_to_input_ref.register
def _(ref: GenericRelation, **kwargs: Any) -> Any:
    return ref


@convert_to_input_ref.register
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return ref.field


@convert_to_input_ref.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    return ref
