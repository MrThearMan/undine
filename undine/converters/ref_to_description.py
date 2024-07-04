from __future__ import annotations

from typing import Any

from django.db import models

from undine.parsers import docstring_parser
from undine.typing import Ref
from undine.utils import TypeDispatcher, get_docstring

__all__ = [
    "convert_ref_to_field_description",
]


convert_ref_to_field_description = TypeDispatcher[Ref, str | None]()


@convert_ref_to_field_description.register
def _(ref: Any) -> Any:
    docstring = get_docstring(ref)
    return docstring_parser.parse_body(docstring)


@convert_ref_to_field_description.register
def _(ref: models.Field) -> Any:
    return getattr(ref, "help_text", None)


@convert_ref_to_field_description.register
def _(_: models.Expression | models.F | models.Q | models.Subquery) -> Any:
    return None


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion

    @convert_ref_to_field_description.register
    def _(ref: DeferredModelGQLType) -> Any:
        return ref.description

    @convert_ref_to_field_description.register
    def _(ref: DeferredModelGQLTypeUnion) -> Any:
        return ref.description
