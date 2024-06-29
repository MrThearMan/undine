import base64
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher

__all__ = [
    "GraphQLBase16",
    "parse_base16",
]


error_wrapper = handle_conversion_errors("Base16")
parse_base16 = TypeDispatcher[Any, str](wrapper=error_wrapper)


@parse_base16.register
def _(input_value: bytes) -> str:
    return base64.b16decode(input_value).decode()


@parse_base16.register
def _(input_value: str) -> str:
    return base64.b16decode(input_value.encode()).decode()


@error_wrapper
def serialize(output_value: Any) -> str:
    return base64.b16encode(parse_base16(output_value).encode()).decode()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> str:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_base16(value)


GraphQLBase16 = GraphQLScalarType(
    name="Base16",
    description="The `Base16` scalar type represents a base16-encoded String.",
    serialize=serialize,
    parse_value=parse_base16,
    parse_literal=parse_literal,
)
