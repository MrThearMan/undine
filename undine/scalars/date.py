import datetime
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.text import dotpath

__all__ = [
    "GraphQLDate",
    "parse_date",
]


error_wrapper = handle_conversion_errors("Date")
parse_date = FunctionDispatcher[Any, datetime.date](wrapper=error_wrapper)


@parse_date.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_date.register
def _(input_value: datetime.date) -> datetime.date:
    return input_value


@parse_date.register
def _(input_value: datetime.datetime) -> datetime.date:
    return input_value.date()


@parse_date.register
def _(input_value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(input_value)
    except ValueError:
        return datetime.datetime.fromisoformat(input_value).date()


@error_wrapper
def serialize(output_value: Any) -> str:
    return parse_date(output_value).isoformat()


GraphQLDate = GraphQLScalarType(
    name="Date",
    description=(
        "The `Date` scalar type represents a Date "
        "value as specified by [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601). "
        "It maps to the Python `datetime.date` type."
    ),
    serialize=serialize,
    parse_value=parse_date,
)
