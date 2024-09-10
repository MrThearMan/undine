import datetime
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLDuration",
    "parse_duration",
]


error_wrapper = handle_conversion_errors("Duration")
parse_duration = TypeDispatcher[Any, datetime.timedelta](wrapper=error_wrapper)


@parse_duration.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_duration.register
def _(input_value: datetime.timedelta) -> datetime.timedelta:
    return input_value


@parse_duration.register
def _(input_value: int) -> datetime.timedelta:
    return datetime.timedelta(seconds=input_value)


@parse_duration.register
def _(input_value: str) -> datetime.timedelta:
    return datetime.timedelta(seconds=int(input_value))


@error_wrapper
def serialize(output_value: Any) -> int:
    return int(parse_duration(output_value).total_seconds())


GraphQLDuration = GraphQLScalarType(
    name="Duration",
    description=(
        "The `Duration` scalar type represents a duration in seconds. "
        "It maps to the Python `datetime.timedelta` type."
    ),
    serialize=serialize,
    parse_value=parse_duration,
)
