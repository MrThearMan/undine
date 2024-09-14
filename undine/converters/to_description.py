from __future__ import annotations

from typing import Any

from undine.parsers import docstring_parser
from undine.typing import Expr, ModelField, TypeRef
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion
from undine.utils.text import get_docstring

__all__ = [
    "convert_to_description",
]


convert_to_description = FunctionDispatcher[Any, str | None]()
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
def _(_: TypeRef) -> Any:
    return None


@convert_to_description.register
def _(ref: LazyModelGQLType) -> Any:
    return convert_to_description(ref.field)


@convert_to_description.register
def _(ref: LazyModelGQLTypeUnion) -> Any:
    return convert_to_description(ref.field)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.ready()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    @convert_to_description.register
    def _(_: GenericForeignKey) -> Any:
        return None
