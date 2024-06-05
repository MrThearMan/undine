import base64
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLBase64",
    "parse_base64",
]


error_wrapper = handle_conversion_errors("Base64")
parse_base64: TypeMapper[Any, str]
parse_base64 = TypeMapper("parse_base64", wrapper=error_wrapper)


@parse_base64.register
def _(input_value: bytes) -> str:
    return base64.b64decode(input_value).decode()


@parse_base64.register
def _(input_value: str) -> str:
    return base64.b64decode(input_value.encode()).decode()


@error_wrapper
def serialize(output_value: Any) -> str:
    return base64.b64encode(parse_base64(output_value).encode()).decode()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> str:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_base64(value)


GraphQLBase64 = GraphQLScalarType(
    name="Base64",
    description="The `Base64` scalar type represents a base64-encoded String.",
    serialize=serialize,
    parse_value=parse_base64,
    parse_literal=parse_literal,
)
