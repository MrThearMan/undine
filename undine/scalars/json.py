import json
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLJSON",
    "parse_json",
]


error_wrapper = handle_conversion_errors("JSON")
parse_json = TypeMapper[Any, dict](wrapper=error_wrapper)


@parse_json.register
def _(input_value: dict) -> dict:
    return input_value


@parse_json.register
def _(input_value: str) -> dict:
    return json.loads(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return json.dumps(parse_json(output_value), default=str)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> dict:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_json(value)


GraphQLJSON = GraphQLScalarType(
    name="JSON",
    description="The `JSON` scalar type represents a JSON serializable object. It maps to the Python `dict` type.",
    serialize=serialize,
    parse_value=parse_json,
    parse_literal=parse_literal,
)
