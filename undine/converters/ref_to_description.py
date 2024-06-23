# ruff: noqa: TCH001, TCH002, TCH003
from __future__ import annotations

from typing import Any

from django.db import models

from undine.typing import Ref
from undine.utils import TypeMapper

__all__ = [
    "convert_ref_to_field_description",
]


convert_ref_to_field_description = TypeMapper[Ref, str]()


@convert_ref_to_field_description.register
def parse_default(ref: Any) -> Any:
    return getattr(ref, "__doc__", "")


@convert_ref_to_field_description.register
def parse_field(ref: models.Field) -> Any:
    return ref.help_text


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_ref_to_field_description.register
    def parse_deferred_type(ref: DeferredModelGQLType) -> Any:
        return ref.description

    @convert_ref_to_field_description.register
    def parse_deferred_type_union(ref: DeferredModelGQLTypeUnion) -> Any:
        return ref.description
