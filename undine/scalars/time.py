import datetime
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLTime",
    "parse_time",
]


error_wrapper = handle_conversion_errors("Time")
parse_time = TypeMapper[Any, datetime.time](wrapper=error_wrapper)


@parse_time.register
def _(input_value: datetime.time) -> datetime.time:
    return input_value


@parse_time.register
def _(input_value: str) -> datetime.time:
    return datetime.time.fromisoformat(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_time(output_value).isoformat()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> datetime.time:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_time(value)


GraphQLTime = GraphQLScalarType(
    name="Time",
    description=(
        "The `Time` scalar type represents a Time value as "
        "specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.time` type."
    ),
    serialize=serialize,
    parse_value=parse_time,
    parse_literal=parse_literal,
)
