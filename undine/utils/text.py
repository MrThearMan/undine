from __future__ import annotations

import re
from inspect import cleandoc
from typing import TYPE_CHECKING, Any, Callable, Iterable

from undine.errors.exceptions import SchemaNameValidationError
from undine.settings import undine_settings

if TYPE_CHECKING:
    from types import FunctionType

__all__ = [
    "comma_sep_str",
    "dotpath",
    "get_docstring",
    "get_schema_name",
    "to_camel_case",
    "to_pascal_case",
    "to_snake_case",
]

# fmt: off
ALLOWED_NAME = re.compile(
    r"^"          # Start of string
    r"[a-z]"      # First character must be a letter.
    r"(?:"        # Followed by (non-capturing group):
    r"[a-z0-9]"   # 1) Any number of letters or numbers
    r"|"          # OR
    r"(_[a-z])"   # 2) An underscore followed by a letter
    r")*"         # Zero or more of the above
    r"$",         # End of string
)
# fmt: on


def validate_name(name: str) -> str:
    """
    Check whether the name is valid.
    Valid names can be converted to 'camelCase' and back to 'snake_case' unambiguously.
    """
    if re.match(ALLOWED_NAME, name) is None:
        raise SchemaNameValidationError(name=name)
    return name


def to_camel_case(name: str, *, validate: bool = True) -> str:
    """
    Convert from snake_case to camelCase.
    By default, validates that 'name' can be converted back to snake_case unambiguously.
    """
    if validate and undine_settings.VALIDATE_NAMES_REVERSIBLE:
        validate_name(name)
    words = name.split("_")
    if len(words) == 1:
        return name
    text = words[0]
    for word in words[1:]:
        text += word.capitalize()
    return text


def to_pascal_case(name: str, *, validate: bool = True) -> str:
    """
    Convert from snake_case to PascalCase.
    By default, validates that 'name' can be converted back to snake_case unambiguously.
    """
    if validate and undine_settings.VALIDATE_NAMES_REVERSIBLE:
        validate_name(name)
    words = name.split("_")
    if len(words) == 1:
        return name.capitalize()
    text = ""
    for word in words:
        text += word.capitalize()
    return text


def to_snake_case(string: str) -> str:
    """
    Converts a camelCase string to snake case.
    It's expected that the input string was created
    by 'name_to_camel_case' with 'VALIDATE_NAMES_REVERSIBLE=True'.
    """
    text: str = ""
    for char in string:
        if char.isupper():
            text += "_"
        text += char.lower()
    return text


def dotpath(obj: type | FunctionType | Callable) -> str:
    """Get the dotpath of the given object."""
    return f"{obj.__module__}.{obj.__qualname__}"


def get_schema_name(name: str) -> str:
    if undine_settings.CAMEL_CASE_SCHEMA_FIELDS:
        return to_camel_case(name)
    return name  # pragma: no cover


def get_docstring(ref: Any) -> str | None:
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
