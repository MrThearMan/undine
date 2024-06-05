from __future__ import annotations

from decimal import Decimal

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.decimal import decimal_scalar


@pytest.mark.parametrize("func", [decimal_scalar.parse, decimal_scalar.serialize])
def test_scalar__decimal__unsupported_type(func) -> None:
    msg = "'Decimal' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__decimal__parse__int() -> None:
    assert decimal_scalar.parse(1) == Decimal(1)


def test_scalar__decimal__parse__str() -> None:
    assert decimal_scalar.parse("1") == Decimal(1)


def test_scalar__decimal__parse__conversion_error() -> None:
    msg = "'Decimal' cannot represent value 'hello world': Value is not a valid decimal"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        decimal_scalar.parse("hello world")


def test_scalar__decimal__serialize__decimal() -> None:
    assert decimal_scalar.serialize(Decimal(1)) == "1"


def test_scalar__decimal__serialize__int() -> None:
    assert decimal_scalar.serialize(1) == "1"


def test_scalar__decimal__serialize__str() -> None:
    assert decimal_scalar.serialize("1") == "1"


def test_scalar__decimal__serialize__conversion_error() -> None:
    msg = "'Decimal' cannot represent value 'hello world': Value is not a valid decimal"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        decimal_scalar.serialize("hello world")
