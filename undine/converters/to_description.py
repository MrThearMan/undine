from __future__ import annotations

from typing import Any

from undine.parsers import docstring_parser
from undine.typing import Expr, ModelField
from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import get_docstring

__all__ = [
    "convert_to_description",
]


convert_to_description = TypeDispatcher[Any, str | None]()
"""Parse a description from the reference."""


@convert_to_description.register
def _(ref: Any) -> Any:
    docstring = get_docstring(ref)
    return docstring_parser.parse_body(docstring)


@convert_to_description.register
def _(ref: ModelField) -> Any:
    return getattr(ref, "help_text", None) or None


@convert_to_description.register
def _(_: Expr) -> Any:
    return None


@convert_to_description.register
def _(ref: DeferredModelGQLType) -> Any:
    return convert_to_description(ref.field)


@convert_to_description.register
def _(ref: DeferredModelGQLTypeUnion) -> Any:
    return convert_to_description(ref.field)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    @convert_to_description.register
    def _(_: GenericForeignKey) -> Any:
        return None
