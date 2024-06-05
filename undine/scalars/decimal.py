from __future__ import annotations

from decimal import Decimal, InvalidOperation
from inspect import cleandoc

from undine.exceptions import GraphQLScalarInvalidValueError

from ._definition import ScalarType

__all__ = [
    "GraphQLDecimal",
    "decimal_scalar",
]


decimal_scalar: ScalarType[Decimal, str] = ScalarType(
    name="Decimal",
    description=cleandoc(
        """
        Represents a number as a string for correctly rounded floating point arithmetic.
        Maps to the Python `decimal.Decimal` type.
        """
    ),
)

GraphQLDecimal = decimal_scalar.as_graphql_scalar()


@decimal_scalar.parse.register
def _(value: int) -> Decimal:
    return Decimal(value)


@decimal_scalar.parse.register
def _(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise GraphQLScalarInvalidValueError(typename="decimal") from error


@decimal_scalar.serialize.register
def _(value: int) -> str:
    return str(Decimal(value))


@decimal_scalar.serialize.register
def _(value: str) -> str:
    try:
        parsed_value = Decimal(value)
    except InvalidOperation as error:
        raise GraphQLScalarInvalidValueError(typename="decimal") from error

    return str(parsed_value)


@decimal_scalar.serialize.register
def _(value: Decimal) -> str:
    return str(value)
