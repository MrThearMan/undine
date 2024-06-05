from __future__ import annotations

import math
from typing import Any, NoReturn

from graphql import GraphQLScalarType
from graphql.type.scalars import GRAPHQL_MAX_INT, GRAPHQL_MIN_INT

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLAny",
    "parse_any",
]


error_wrapper = handle_conversion_errors("Any")
parse_any = FunctionDispatcher[Any, Any](wrapper=error_wrapper)


@parse_any.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_any.register
def _(input_value: str | bool | None) -> Any:  # noqa: FBT001
    return input_value


@parse_any.register
def _(input_value: bytes) -> Any:
    return input_value.decode(encoding="utf-8")


@parse_any.register
def _(input_value: int) -> Any:
    if not (GRAPHQL_MIN_INT <= input_value <= GRAPHQL_MAX_INT):
        msg = "GraphQL integers cannot represent non 32-bit signed integer value."
        raise ValueError(msg)
    return input_value


@parse_any.register
def _(input_value: float) -> Any:
    if not math.isfinite(input_value):
        msg = "GraphQL floats cannot represent 'inf' or 'NaN' values."
        raise ValueError(msg)
    return input_value


@parse_any.register
def _(input_value: list) -> Any:
    for value in input_value:
        parse_any(value)
    return input_value


@parse_any.register
def _(input_value: dict) -> Any:
    for value in input_value.values():
        parse_any(value)
    return input_value


@error_wrapper
def serialize(output_value: Any) -> Any:
    return parse_any(output_value)


GraphQLAny = GraphQLScalarType(
    name="Any",
    description="The `Any` scalar type can be anything. It is used e.g. for type unions.",
    serialize=serialize,
    parse_value=parse_any,
)
