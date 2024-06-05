from decimal import Decimal
from typing import Any

from graphql import GraphQLScalarType, Undefined, ValueNode

from undine.errors import handle_conversion_errors
from undine.utils import TypeMapper

__all__ = [
    "GraphQLDecimal",
    "parse_decimal",
]


error_wrapper = handle_conversion_errors("Decimal")
parse_decimal: TypeMapper[Any, Decimal]
parse_decimal = TypeMapper("parse_decimal", wrapper=error_wrapper)


@parse_decimal.register
def _(input_value: Decimal) -> Decimal:
    return input_value


@parse_decimal.register
def _(input_value: int) -> Decimal:
    return Decimal(input_value)


@parse_decimal.register
def _(input_value: str) -> Decimal:
    return Decimal(input_value)


@error_wrapper
def serialize(output_value: Any) -> str:
    return str(parse_decimal(output_value))


@error_wrapper
def parse_literal(value_node: ValueNode, _variables: Any = None) -> Decimal:
    value: Any = getattr(value_node, "value", Undefined)
    return parse_decimal(value)


GraphQLDecimal = GraphQLScalarType(
    name="Decimal",
    description=(
        "The `Decimal` scalar represents a number for "
        "correctly rounded floating point arithmetic. "
        "It maps to the Python `decimal.Decimal` type."
    ),
    serialize=serialize,
    parse_value=parse_decimal,
    parse_literal=parse_literal,
)
