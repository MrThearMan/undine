from decimal import Decimal

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.decimal import parse_decimal, serialize


def test_scalar__decimal__parse__decimal():
    assert parse_decimal(Decimal(1)) == Decimal(1)


def test_scalar__decimal__parse__int():
    assert parse_decimal(1) == Decimal(1)


def test_scalar__decimal__parse__str():
    assert parse_decimal("1") == Decimal(1)


@pytest.mark.parametrize("func", [parse_decimal, serialize])
def test_scalar__decimal__parse__conversion_error(func):
    msg = "'Decimal' cannot represent value 'hello world': invalid string literal"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_decimal, serialize])
def test_scalar__decimal__parse__unsupported_type(func):
    msg = "'Decimal' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__decimal__serialize__decimal():
    assert serialize(Decimal(1)) == "1"


def test_scalar__decimal__serialize__int():
    assert serialize(1) == "1"


def test_scalar__decimal__serialize__str():
    assert serialize("1") == "1"
