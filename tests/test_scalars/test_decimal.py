import re
from decimal import Decimal

import pytest

from undine.errors import GraphQLConversionError
from undine.scalars.decimal import parse_decimal


def test_scalar__decimal__parse__decimal():
    assert parse_decimal(Decimal("1")) == Decimal("1")


def test_scalar__decimal__parse__int():
    assert parse_decimal(1) == Decimal("1")


def test_scalar__decimal__parse__str():
    assert parse_decimal("1") == Decimal("1")


def test_scalar__decimal__parse__conversion_error():
    msg = "Decimal cannot represent value 'hello world': invalid string literal"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_decimal("hello world")


def test_scalar__decimal__parse__unsupported_type():
    msg = "Decimal cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_decimal(1.2)
