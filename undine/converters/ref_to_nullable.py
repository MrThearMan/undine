# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import Any, get_args

from django.db import models

from undine.parsers import parse_return_annotation
from undine.typing import Ref
from undine.utils import TypeDispatcher

__all__ = [
    "is_ref_nullable",
]


is_ref_nullable = TypeDispatcher[Ref, bool]()


@is_ref_nullable.register
def convert_default(ref: Any) -> bool:
    return False


@is_ref_nullable.register
def convert_function(ref: FunctionType) -> bool:
    annotation = parse_return_annotation(ref, depth=2)
    if not isinstance(annotation, UnionType):
        return False
    return NoneType in get_args(annotation)


@is_ref_nullable.register
def convert_property(ref: property) -> bool:
    annotation = parse_return_annotation(ref.fget, depth=2)  # type: ignore[arg-type]
    if not isinstance(annotation, UnionType):
        return False
    return NoneType in get_args(annotation)


@is_ref_nullable.register
def convert_model_field(ref: models.Field) -> bool:
    return getattr(ref, "null", False)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @is_ref_nullable.register
    def convert_deferred_type(ref: DeferredModelGQLType) -> bool:
        return ref.nullable

    @is_ref_nullable.register
    def convert_deferred_type_union(ref: DeferredModelGQLTypeUnion) -> bool:
        return False
