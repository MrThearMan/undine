from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import InputRef
from undine.utils.defer import DeferredModelField
from undine.utils.dispatcher import TypeDispatcher

__all__ = [
    "convert_to_input_ref",
]


convert_to_input_ref = TypeDispatcher[Any, InputRef]()


@convert_to_input_ref.register
def _(ref: DeferredAttribute) -> InputRef:
    return convert_to_input_ref(ref.field)


@convert_to_input_ref.register
def _(ref: models.Field) -> InputRef:
    return ref


@convert_to_input_ref.register
def _(ref: str) -> InputRef:
    if ref == "self":
        return "self"
    return DeferredModelField.from_lookup(ref)


@convert_to_input_ref.register
def _(_: None) -> InputRef:
    return DeferredModelField.from_none()


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine.model_graphql import ModelGQLMutation

    @convert_to_input_ref.register
    def _(ref: type[ModelGQLMutation]) -> InputRef:
        # TODO: When using mutation as input, should support MutationHandler fully:
        #  - can link existing elements (only pk provided)
        #  - can create new elements (no pk provided)
        #  - can update existing elements (pk and other data provided)
        return ref

    @convert_to_input_ref.register
    def _(ref: GenericRelation, **kwargs: Any) -> InputRef:
        return ref

    @convert_to_input_ref.register
    def _(ref: GenericForeignKey, **kwargs: Any) -> InputRef:
        return ref
