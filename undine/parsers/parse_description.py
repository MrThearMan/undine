from __future__ import annotations

from typing import Any

from undine.typing import Expr, ModelField, TypeRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.text import get_docstring

from .parse_docstring import docstring_parser

__all__ = [
    "parse_description",
]


parse_description = FunctionDispatcher[Any, str | None]()
"""Parse a description from the reference."""


@parse_description.register
def _(ref: Any) -> Any:
    docstring = get_docstring(ref)
    return docstring_parser.parse_body(docstring)


@parse_description.register
def _(ref: ModelField) -> Any:
    return getattr(ref, "help_text", None) or None


@parse_description.register
def _(_: Expr) -> Any:
    return None


@parse_description.register
def _(_: TypeRef) -> Any:
    return None


@parse_description.register
def _(ref: LazyQueryType) -> Any:
    return parse_description(ref.field)


@parse_description.register
def _(ref: LazyQueryTypeUnion) -> Any:
    return parse_description(ref.field)


@parse_description.register
def _(_: LazyLambdaQueryType) -> Any:
    return False
