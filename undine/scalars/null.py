from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLNull",
    "parse_null",
]


error_wrapper = handle_conversion_errors("Null")
parse_null = FunctionDispatcher[Any, None](wrapper=error_wrapper)


@parse_null.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_null.register
def _(input_value: None) -> None:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> None:
    return parse_null(output_value)


GraphQLNull = GraphQLScalarType(
    name="Null",
    description="The `Null` scalar type represents an always null value. It maps to the Python `None` value.",
    serialize=serialize,
    parse_value=parse_null,
)
