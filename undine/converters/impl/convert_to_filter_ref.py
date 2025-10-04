from __future__ import annotations

import itertools
from contextlib import suppress
from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel
from django.db.models import F, Model, Q
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.query_utils import DeferredAttribute
from graphql import GraphQLInputType

from undine import Filter
from undine.converters import convert_to_filter_ref, convert_to_graphql_type
from undine.dataclasses import UnionFilterRef
from undine.typing import CombinableExpression, DjangoExpression, GQLInfo, ModelField
from undine.utils.model_utils import determine_output_field, get_model_field
from undine.utils.reflection import is_subclass


@convert_to_filter_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]

    models = caller.filterset.__models__
    if len(models) == 1:
        field = get_model_field(model=models[0], lookup=ref)
        return convert_to_filter_ref(field, **kwargs)

    fields_by_model: dict[type[Model], GraphQLInputType] = {}
    for model in caller.filterset.__models__:
        field = get_model_field(model=model, lookup=ref)
        fields_by_model[model] = convert_to_graphql_type(field, model=model, is_input=True)

    for (model_1, field_1), (model_2, field_2) in itertools.combinations(fields_by_model.items(), 2):
        if field_1 != field_2:
            msg = (
                f"Field '{ref}' is of type '{field_1}' on model '{model_1.__name__}' "
                f"but of type '{field_2}' on model '{model_2.__name__}'. "
                f"Field '{ref}' cannot be used to a UnionFilter"
            )
            raise ValueError(msg)  # TODO: Custom error

    return UnionFilterRef(ref=ref, models=tuple(models))


@convert_to_filter_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    return convert_to_filter_ref(caller.field_name, **kwargs)


@convert_to_filter_ref.register
def _(_: F, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]
    return convert_to_filter_ref(caller.field_name, **kwargs)


@convert_to_filter_ref.register
def _(ref: ModelField, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]

    models = caller.filterset.__models__
    if len(models) != 1:
        msg = "Cannot use model reference when filterset defined for multiple models"
        raise ValueError(msg)  # TODO: Custom error

    if not is_subclass(models[0], ref.model):
        msg = f"Model field {ref} not found from model {models[0]}"
        raise ValueError(msg)  # TODO: Custom error

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
    caller: Filter = kwargs["caller"]

    user_func = caller.aliases_func

    def aliases(root: Filter, info: GQLInfo, *, value: bool) -> dict[str, DjangoExpression]:
        results: dict[str, DjangoExpression] = {}
        if user_func is not None:
            results |= user_func(root, info, value=value)

        results[root.name] = ref
        return results

    caller.aliases_func = aliases
    return ref


@convert_to_filter_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]

    models = caller.filterset.__models__
    if len(models) == 1:
        determine_output_field(ref, model=models[0])
    else:
        fields_by_model: dict[type[Model], ModelField] = {}
        for model in models:
            determine_output_field(ref, model=model)
            fields_by_model[model] = ref.output_field
            del ref.output_field

        for (model_1, field_1), (model_2, field_2) in itertools.combinations(fields_by_model.items(), 2):
            if field_1.__class__ is not field_2.__class__:
                msg = (
                    f"Output field of expression {ref} is '{field_1}' on model '{model_1.__name__}' "
                    f"but '{field_2}' on model '{model_2.__name__}'. "
                    f"Expression {ref} cannot be used on a UnionFilter"
                )
                raise ValueError(msg)  # TODO: Custom error

    user_func = caller.aliases_func

    def aliases(root: Filter, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]:
        results: dict[str, DjangoExpression] = {}
        if user_func is not None:
            results |= user_func(root, info, value=value)

        results[root.name] = ref
        return results

    caller.aliases_func = aliases
    return ref


@convert_to_filter_ref.register
def _(ref: GenericRel, **kwargs: Any) -> Any:
    return convert_to_filter_ref(ref.field)


@convert_to_filter_ref.register  # Required for Django<5.1
def _(ref: GenericForeignKey, **kwargs: Any) -> Any:
    caller: Filter = kwargs["caller"]

    models = caller.filterset.__models__
    if len(models) != 1:
        msg = "Cannot use model reference when filterset defined for multiple models"
        raise ValueError(msg)  # TODO: Custom error

    if not is_subclass(models[0], ref.model):
        msg = f"Model field {ref} not found from model {models[0]}"
        raise ValueError(msg)  # TODO: Custom error

    return ref


with suppress(ImportError):
    from undine.utils.full_text_search import PostgresFTS

    @convert_to_filter_ref.register
    def _(ref: PostgresFTS, **kwargs: Any) -> Any:
        caller: Filter = kwargs["caller"]

        user_func = caller.aliases_func

        def aliases(root: Filter, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]:
            results: dict[str, DjangoExpression] = {}
            if user_func is not None:
                results |= user_func(root, info, value=value)

            lang = ref.get_search_language(info)
            key = ref.get_vector_alias_key(root, lang)
            results[key] = ref.vectors[lang.name]
            return results

        caller.aliases_func = aliases
        return ref
