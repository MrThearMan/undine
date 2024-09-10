import datetime
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLTime",
    "parse_time",
]


error_wrapper = handle_conversion_errors("Time")
parse_time = TypeDispatcher[Any, datetime.time](wrapper=error_wrapper)


@parse_time.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_time.register
def _(input_value: datetime.time) -> datetime.time:
    return input_value


@parse_time.register
def _(input_value: str) -> datetime.time:
    return datetime.time.fromisoformat(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_time(output_value).isoformat()


GraphQLTime = GraphQLScalarType(
    name="Time",
    description=(
        "The `Time` scalar type represents a Time value as "
        "specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.time` type."
    ),
    serialize=serialize,
    parse_value=parse_time,
)
