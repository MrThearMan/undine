from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLNull",
    "parse_null",
]


error_wrapper = handle_conversion_errors("Null")
parse_null = TypeMapper[Any, None](wrapper=error_wrapper)


@parse_null.register
def _(input_value: None) -> None:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> None:
    if output_value is None:
        return
    msg = f"Null type cannot serialize non-null value: {output_value}"
    raise TypeError(msg)


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> None:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_null(value)


GraphQLNull = GraphQLScalarType(
    name="Null",
    description="The `Null` scalar type represents an always null value. It maps to the Python `None` value.",
    serialize=serialize,
    parse_value=parse_null,
    parse_literal=parse_literal,
)
