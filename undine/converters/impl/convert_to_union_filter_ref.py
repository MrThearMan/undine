from __future__ import annotations

import itertools
from types import FunctionType
from typing import Any

from django.db.models import F, Model, Q
from graphql import GraphQLInputType

from undine import UnionFilter
from undine.converters import convert_to_graphql_type, convert_to_union_filter_ref
from undine.typing import CombinableExpression, DjangoExpression, GQLInfo, ModelField
from undine.utils.model_utils import determine_output_field, get_model_field


@convert_to_union_filter_ref.register
def _(ref: str, **kwargs: Any) -> Any:
    caller: UnionFilter = kwargs["caller"]

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

    return ref


@convert_to_union_filter_ref.register
def _(_: None, **kwargs: Any) -> Any:
    caller: UnionFilter = kwargs["caller"]
    return convert_to_union_filter_ref(caller.field_name, **kwargs)


@convert_to_union_filter_ref.register
def _(_: F, **kwargs: Any) -> Any:
    caller: UnionFilter = kwargs["caller"]
    return convert_to_union_filter_ref(caller.field_name, **kwargs)


@convert_to_union_filter_ref.register
def _(ref: FunctionType, **kwargs: Any) -> Any:
    return ref


@convert_to_union_filter_ref.register
def _(ref: Q, **kwargs: Any) -> Any:
    caller: UnionFilter = kwargs["caller"]

    user_func = caller.aliases_func

    def aliases(root: UnionFilter, info: GQLInfo, *, value: bool) -> dict[str, DjangoExpression]:
        results: dict[str, DjangoExpression] = {}
        if user_func is not None:
            results |= user_func(root, info, value=value)

        results[root.name] = ref
        return results

    caller.aliases_func = aliases
    return ref


@convert_to_union_filter_ref.register
def _(ref: CombinableExpression, **kwargs: Any) -> Any:
    caller: UnionFilter = kwargs["caller"]

    if not hasattr(ref, "output_field"):
        fields_by_model: dict[type[Model], ModelField] = {}
        for model in caller.filterset.__models__:
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

    def aliases(root: UnionFilter, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]:
        results: dict[str, DjangoExpression] = {}
        if user_func is not None:
            results |= user_func(root, info, value=value)

        results[root.name] = ref
        return results

    caller.aliases_func = aliases
    return ref
