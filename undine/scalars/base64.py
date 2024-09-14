import base64
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import FunctionDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLBase64",
    "parse_base64",
]


error_wrapper = handle_conversion_errors("Base64")
parse_base64 = FunctionDispatcher[Any, str](wrapper=error_wrapper)


@parse_base64.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_base64.register
def _(input_value: str) -> str:
    # Validates string is base64 encoded
    base64.b64decode(input_value.encode(encoding="utf-8")).decode(encoding="utf-8")
    return input_value


@parse_base64.register
def _(input_value: bytes) -> str:
    # Validates string is base64 encoded
    base64.b64decode(input_value).decode(encoding="utf-8")
    return input_value.decode(encoding="utf-8")


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_base64(output_value)


GraphQLBase64 = GraphQLScalarType(
    name="Base64",
    description="The `Base64` scalar type represents a base64-encoded String.",
    serialize=serialize,
    parse_value=parse_base64,
)
