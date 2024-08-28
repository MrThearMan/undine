import datetime
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.utils.dispatcher import TypeDispatcher
from undine.utils.error_helpers import handle_conversion_errors
from undine.utils.text import dotpath

__all__ = [
    "GraphQLDateTime",
    "parse_datetime",
]


error_wrapper = handle_conversion_errors("DateTime")
parse_datetime = TypeDispatcher[Any, datetime.datetime](wrapper=error_wrapper)


@parse_datetime.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_datetime.register
def _(input_value: datetime.datetime) -> datetime.datetime:
    return input_value


@parse_datetime.register
def _(input_value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_datetime(output_value).isoformat()


GraphQLDateTime = GraphQLScalarType(
    name="DateTime",
    description=(
        "The `DateTime` scalar type represents a DateTime "
        "value as specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.datetime` type."
    ),
    serialize=serialize,
    parse_value=parse_datetime,
)
