import decimal
from typing import Any, NoReturn

from graphql import GraphQLScalarType

from undine.errors import handle_conversion_errors
from undine.utils import TypeDispatcher, dotpath

__all__ = [
    "GraphQLDecimal",
    "parse_decimal",
]


error_wrapper = handle_conversion_errors("Decimal")
parse_decimal = TypeDispatcher[Any, decimal.Decimal](wrapper=error_wrapper)


@parse_decimal.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not supported"
    raise ValueError(msg)


@parse_decimal.register
def _(input_value: decimal.Decimal) -> decimal.Decimal:
    return input_value


@parse_decimal.register
def _(input_value: int) -> decimal.Decimal:
    return decimal.Decimal(input_value)


@parse_decimal.register
def _(input_value: str) -> decimal.Decimal:
    try:
        return decimal.Decimal(input_value)
    except decimal.InvalidOperation as error:
        msg = "invalid string literal"
        raise ValueError(msg) from error


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(parse_decimal(output_value))


GraphQLDecimal = GraphQLScalarType(
    name="Decimal",
    description=(
        "The `Decimal` scalar represents a number for "
        "correctly rounded floating point arithmetic. "
        "It maps to the Python `decimal.Decimal` type."
    ),
    serialize=serialize,
    parse_value=parse_decimal,
)
