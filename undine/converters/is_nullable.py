from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import get_args

from django.db import models

from undine.parsers import parse_return_annotation
from undine.typing import CombinableExpression, FieldRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyQueryType, LazyQueryTypeUnion

__all__ = [
    "is_field_nullable",
]


is_field_nullable = FunctionDispatcher[FieldRef, bool]()
"""
Determine whether the undine.Field reference is considered nullable.

:param ref: The reference to check.
"""


@is_field_nullable.register
def _(ref: FunctionType) -> bool:
    annotation = parse_return_annotation(ref)
    if not isinstance(annotation, UnionType):
        return False
    return NoneType in get_args(annotation)


@is_field_nullable.register
def _(ref: models.Field) -> bool:
    return getattr(ref, "null", False)


@is_field_nullable.register
def _(_: models.OneToOneRel) -> bool:
    return True


@is_field_nullable.register
def _(_: models.ManyToOneRel | models.ManyToManyRel) -> bool:
    return False


@is_field_nullable.register
def _(ref: CombinableExpression) -> bool:
    return is_field_nullable(ref.output_field)


@is_field_nullable.register
def _(ref: LazyQueryType) -> bool:
    return is_field_nullable(ref.field)


@is_field_nullable.register
def _(_: LazyQueryTypeUnion) -> bool:
    return False


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    @is_field_nullable.register
    def _(_: GenericForeignKey) -> bool:
        return False

    @is_field_nullable.register
    def _(_: GenericRelation) -> bool:
        return True
