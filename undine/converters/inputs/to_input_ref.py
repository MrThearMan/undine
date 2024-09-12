from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.query_utils import DeferredAttribute

from undine.typing import InputRef, ModelField, TypeRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine.fields import Input


__all__ = [
    "convert_to_input_ref",
]


convert_to_input_ref = TypeDispatcher[Any, InputRef]()
"""Convert the given value to a Undine Input reference."""


@convert_to_input_ref.register
def _(ref: str | type[str], **kwargs: Any) -> InputRef:
    if ref is str:
        return TypeRef(ref=ref)
    caller: Input = kwargs["caller"]
    if ref == "self":
        return caller.owner
    return get_model_field(model=caller.owner.__model__, lookup=ref)


@convert_to_input_ref.register
def _(_: None, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    return get_model_field(model=caller.owner.__model__, lookup=caller.name)


@convert_to_input_ref.register
def _(ref: models.F, **kwargs: Any) -> InputRef:
    caller: Input = kwargs["caller"]
    return get_model_field(model=caller.owner.__model__, lookup=ref.name)


@convert_to_input_ref.register
def _(ref: ModelField, **kwargs: Any) -> InputRef:
    return ref


@convert_to_input_ref.register
def _(ref: DeferredAttribute, **kwargs: Any) -> InputRef:
    return ref.field


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine import ModelGQLMutation

    @convert_to_input_ref.register
    def _(ref: type[ModelGQLMutation], **kwargs: Any) -> InputRef:
        return ref


@convert_to_input_ref.register
def _(
    ref: (
        bool
        | int
        | float
        | Decimal
        | datetime.datetime
        | datetime.date
        | datetime.time
        | datetime.timedelta
        | uuid.UUID
        | Enum
        | list
        | dict
    ),
    **kwargs: Any,
) -> InputRef:
    return TypeRef(ref=ref)  # type: ignore[return-value]
