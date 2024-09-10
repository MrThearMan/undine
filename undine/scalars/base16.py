import base64
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLBase16",
    "parse_base16",
]


error_wrapper = handle_conversion_errors("Base16")
parse_base16 = TypeDispatcher[Any, str](wrapper=error_wrapper)


@parse_base16.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_base16.register
def _(input_value: str) -> str:
    # Validates string is base16 encoded
    base64.b16decode(input_value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return input_value


@parse_base16.register
def _(input_value: bytes) -> str:
    # Validates string is base16 encoded
    base64.b16decode(input_value).decode(encoding="utf-8")
    return input_value.decode(encoding="utf-8")


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_base16(output_value)


GraphQLBase16 = GraphQLScalarType(
    name="Base16",
    description="The `Base16` scalar type represents a base16-encoded String.",
    serialize=serialize,
    parse_value=parse_base16,
)
