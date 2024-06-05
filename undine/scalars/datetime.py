import datetime
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLDateTime",
    "parse_datetime",
]


error_wrapper = handle_conversion_errors("DateTime")
parse_datetime: TypeMapper[Any, datetime.datetime]
parse_datetime = TypeMapper("parse_datetime", wrapper=error_wrapper)


@parse_datetime.register
def _(input_value: datetime.datetime) -> datetime.datetime:
    return input_value


@parse_datetime.register
def _(input_value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_datetime(output_value).isoformat()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> datetime.datetime:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_datetime(value)


GraphQLDateTime = GraphQLScalarType(
    name="DateTime",
    description=(
        "The `DateTime` scalar type represents a DateTime "
        "value as specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.datetime` type."
    ),
    serialize=serialize,
    parse_value=parse_datetime,
    parse_literal=parse_literal,
)
