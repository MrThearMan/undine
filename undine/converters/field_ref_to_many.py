from __future__ import annotations

from types import FunctionType, GenericAlias
from typing import Any, get_origin

from django.db import models

from undine.parsers import parse_return_annotation
from undine.typing import FieldRef
from undine.utils.dispatcher import TypeDispatcher

__all__ = [
    "is_field_ref_many",
]


is_field_ref_many = TypeDispatcher[FieldRef, bool]()


@is_field_ref_many.register
def _(_: Any) -> bool:
    return False


@is_field_ref_many.register
def _(ref: FunctionType) -> bool:
    annotation = parse_return_annotation(ref)
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation)
    return isinstance(annotation, type) and issubclass(annotation, list)


@is_field_ref_many.register
def _(ref: models.Field) -> bool:
    return bool(ref.many_to_many or ref.one_to_many)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @is_field_ref_many.register
    def _(ref: DeferredModelGQLType) -> bool:
        return ref.many

    @is_field_ref_many.register
    def _(_: DeferredModelGQLTypeUnion) -> bool:
        return False

    @is_field_ref_many.register
    def _(_: GenericForeignKey) -> bool:
        return False
