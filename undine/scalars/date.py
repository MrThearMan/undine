import datetime
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher

__all__ = [
    "GraphQLDate",
    "parse_date",
]


error_wrapper = handle_conversion_errors("Date")
parse_date = TypeDispatcher[Any, datetime.date](wrapper=error_wrapper)


@parse_date.register
def _(input_value: datetime.date) -> datetime.date:
    return input_value


@parse_date.register
def _(input_value: datetime.datetime) -> datetime.date:
    return input_value.date()


@parse_date.register
def _(input_value: str) -> datetime.date:
    return datetime.date.fromisoformat(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_date(output_value).isoformat()


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> datetime.date:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_date(value)


GraphQLDate = GraphQLScalarType(
    name="Date",
    description=(
        "The `Date` scalar type represents a Date "
        "value as specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.date` type."
    ),
    serialize=serialize,
    parse_value=parse_date,
    parse_literal=parse_literal,
)
