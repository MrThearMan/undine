from __future__ import annotations

from types import FunctionType, GenericAlias
from typing import Any, get_origin

from django.db import models

from undine.parsers import parse_return_annotation
from undine.typing import CombinableExpression, ModelField
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion
from undine.utils.model_utils import get_model_field

__all__ = [
    "is_many",
]


is_many = TypeDispatcher[Any, bool]()
"""Determine whether a the reference returns a list of objects or not."""


@is_many.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    annotation = parse_return_annotation(ref)
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation)
    return isinstance(annotation, type) and issubclass(annotation, list)


@is_many.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    return bool(ref.many_to_many) or bool(ref.one_to_many)


@is_many.register
def _(_: CombinableExpression, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(ref: LazyModelGQLType, **kwargs: Any) -> bool:
    return is_many(ref.field)


@is_many.register
def _(_: LazyModelGQLTypeUnion, **kwargs: Any) -> bool:
    return False


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import ModelGQLMutation, ModelGQLType

    @is_many.register
    def _(_: ModelGQLType, **kwargs: Any) -> bool:
        model: type[models.Model] = kwargs["model"]
        name: str = kwargs["name"]
        field = get_model_field(model=model, lookup=name)
        return is_many(field, **kwargs)

    @is_many.register
    def _(_: ModelGQLMutation, **kwargs: Any) -> bool:
        model: type[models.Model] = kwargs["model"]
        name: str = kwargs["name"]
        field = get_model_field(model=model, lookup=name)
        return is_many(field, **kwargs)

    @is_many.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        return False
