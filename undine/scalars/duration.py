import datetime
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLDuration",
    "parse_timedelta",
]


error_wrapper = handle_conversion_errors("Duration")
parse_timedelta = TypeMapper[Any, datetime.timedelta](wrapper=error_wrapper)


@parse_timedelta.register
def _(input_value: datetime.timedelta) -> datetime.timedelta:
    return input_value


@parse_timedelta.register
def _(input_value: int) -> datetime.timedelta:
    return datetime.timedelta(seconds=input_value)


@parse_timedelta.register
def _(input_value: str) -> datetime.timedelta:
    return datetime.timedelta(seconds=int(input_value))


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(parse_timedelta(output_value).total_seconds())


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> datetime.timedelta:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_timedelta(value)


GraphQLDuration = GraphQLScalarType(
    name="Duration",
    description=(
        "The `Duration` scalar type represents a duration in seconds. "
        "It maps to the Python `datetime.timedelta` type."
    ),
    serialize=serialize,
    parse_value=parse_timedelta,
    parse_literal=parse_literal,
)
