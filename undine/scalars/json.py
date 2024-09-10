from __future__ import annotations

import json
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLJSON",
    "parse_json",
]


error_wrapper = handle_conversion_errors("JSON")
parse_json = TypeDispatcher[Any, dict](wrapper=error_wrapper)


@parse_json.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_json.register
def _(input_value: dict) -> dict:
    return input_value


@parse_json.register
def _(input_value: str | bytes) -> dict:
    return json.loads(input_value)


@error_wrapper
def serialize(output_value: Any) -> dict:
    return parse_json(output_value)


GraphQLJSON = GraphQLScalarType(
    name="JSON",
    description="The `JSON` scalar type represents a JSON serializable object. It maps to the Python `dict` type.",
    serialize=serialize,
    parse_value=parse_json,
)
