from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING, Any

from undine.settings import undine_settings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from types import FunctionType

__all__ = [
    "comma_sep_str",
    "dotpath",
    "get_docstring",
    "to_camel_case",
    "to_pascal_case",
    "to_schema_name",
    "to_snake_case",
]


def to_camel_case(string: str) -> str:
    """Convert string from `snake_case` or `PascalCase` to `camelCase`."""
    if not string:
        return ""

    words = string.split("_")

    # No underscores, should be camelCase or PascalCase
    if len(words) == 1:
        return string[0].lower() + string[1:]

    text = words[0]
    for word in words[1:]:
        text += word.capitalize()
    return text


def to_pascal_case(string: str) -> str:
    """Convert string from `snake_case` or `camelCase` to `PascalCase`."""
    if not string:
        return ""

    words = string.split("_")

    # No underscores, should be camelCase or PascalCase
    if len(words) == 1:
        return string[0].upper() + string[1:]

    text = ""
    for word in words:
        text += word.capitalize()
    return text


def to_snake_case(string: str) -> str:
    """Convert string from `camelCase` or `PascalCase` to `snake_case`."""
    text: str = ""
    for char in string:
        if char.isupper() and text:
            text += "_"
        text += char.lower()
    return text


def dotpath(obj: type | FunctionType | Callable[..., Any]) -> str:
    """Get the 'dotpath import path' of the given object."""
    return f"{obj.__module__}.{obj.__qualname__}"


def to_schema_name(name: str) -> str:
    """Convert the given name to camelCase if using camelCased schema names."""
    if undine_settings.CAMEL_CASE_SCHEMA_FIELDS:
        return to_camel_case(name)
    return name  # pragma: no cover


def get_docstring(ref: Any) -> str | None:
    """Get the docstring of the given object, if it has one."""
    docstring = getattr(ref, "__doc__", None)
    if docstring is None:
        return None
    return cleandoc(docstring).strip() or None


def comma_sep_str(values: Iterable[Any], *, last_sep: str = "&", quote: bool = False) -> str:
    """
    Return a comma separated string of the given values,
    with the value of `last_sep` before the last value.
    Remove any empty values.

    >>> comma_sep_str(["foo", "bar", "baz"])
    "foo, bar & baz"

    >>> comma_sep_str(["foo", "bar", "baz"], last_sep="or", quote=True)
    "'foo', 'bar' or 'baz'"
    """
    string: str = ""
    previous_value: str = ""
    values_iter = iter(values)
    try:
        while True:
            value = str(next(values_iter))
            if not value:
                continue
            if previous_value:
                if string:
                    string += ", "
                string += f"'{previous_value}'" if quote else previous_value
            previous_value = value
    except StopIteration:
        if string:
            string += f" {last_sep} "
        string += f"'{previous_value}'" if quote else previous_value

    return string
