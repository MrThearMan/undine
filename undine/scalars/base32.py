import base64
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLBase32",
    "parse_base32",
]


error_wrapper = handle_conversion_errors("Base32")
parse_base32 = TypeMapper[Any, str](wrapper=error_wrapper)


@parse_base32.register
def _(input_value: bytes) -> str:
    return base64.b32decode(input_value).decode()


@parse_base32.register
def _(input_value: str) -> str:
    return base64.b32decode(input_value.encode()).decode()


@error_wrapper
def serialize(output_value: Any) -> str:
    return base64.b32encode(parse_base32(output_value).encode()).decode()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> str:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_base32(value)


GraphQLBase32 = GraphQLScalarType(
    name="Base32",
    description="The `Base32` scalar type represents a base32-encoded String.",
    serialize=serialize,
    parse_value=parse_base32,
    parse_literal=parse_literal,
)
