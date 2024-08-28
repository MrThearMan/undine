from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import Any, get_args

from django.db import models

from undine.parsers import parse_return_annotation
from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher

__all__ = [
    "is_field_ref_nullable",
]


is_field_ref_nullable = TypeDispatcher[FieldRef, bool]()


@is_field_ref_nullable.register
def _(_: Any) -> bool:
    return False


@is_field_ref_nullable.register
def _(ref: FunctionType) -> bool:
    annotation = parse_return_annotation(ref)
    if not isinstance(annotation, UnionType):
        return False
    return NoneType in get_args(annotation)


@is_field_ref_nullable.register
def _(ref: models.Field) -> bool:
    return getattr(ref, "null", False)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @is_field_ref_nullable.register
    def _(ref: DeferredModelGQLType) -> bool:
        return ref.nullable

    @is_field_ref_nullable.register
    def _(_: DeferredModelGQLTypeUnion) -> bool:
        return False

    @is_field_ref_nullable.register
    def _(_: GenericForeignKey) -> bool:
        return False
