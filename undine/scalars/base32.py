import base64
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.utils.dispatcher import TypeDispatcher
from undine.utils.error_helpers import handle_conversion_errors
from undine.utils.text import dotpath

__all__ = [
    "GraphQLBase32",
    "parse_base32",
]


error_wrapper = handle_conversion_errors("Base32")
parse_base32 = TypeDispatcher[Any, str](wrapper=error_wrapper)


@parse_base32.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_base32.register
def _(input_value: str) -> str:
    # Validates string is base32 encoded
    base64.b32decode(input_value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return input_value


@parse_base32.register
def _(input_value: bytes) -> str:
    # Validates string is base32 encoded
    base64.b32decode(input_value).decode(encoding="utf-8")
    return input_value.decode(encoding="utf-8")


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_base32(output_value)


GraphQLBase32 = GraphQLScalarType(
    name="Base32",
    description="The `Base32` scalar type represents a base32-encoded String.",
    serialize=serialize,
    parse_value=parse_base32,
)
