from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.parsers import parse_model_field
from undine.typing import InputRef
from undine.utils.dispatcher import TypeDispatcher

if TYPE_CHECKING:
    from undine.fields import Input


__all__ = [
    "convert_to_input_ref",
]


convert_to_input_ref = TypeDispatcher[Any, InputRef]()


@convert_to_input_ref.register
def _(ref: str, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    if ref == "self":
        return caller.owner
    return parse_model_field(model=caller.owner.__model__, lookup=ref)


@convert_to_input_ref.register
def _(_: None, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    return parse_model_field(model=caller.owner.__model__, lookup=caller.name)


@convert_to_input_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> InputRef:
    return ref.field


@convert_to_input_ref.register
def _(ref: models.Field, **kwargs: Any) -> InputRef:
    return ref


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.

    from undine import ModelGQLMutation

    @convert_to_input_ref.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> InputRef:
        # TODO: When using mutation as input, should support MutationHandler fully:
        #  - can link existing elements (only pk provided)
        #  - can create new elements (no pk provided)
        #  - can update existing elements (pk and other data provided)
        return ref
