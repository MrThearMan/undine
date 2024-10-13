from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.base16 import parse_base16


def test_scalar__base16__parse__bytes():
    assert parse_base16(b"68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


def test_scalar__base16__parse__str():
    assert parse_base16("68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


def test_scalar__base16__parse__conversion_error():
    msg = "Base16 cannot represent value 'hello world': Non-base16 digit found"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_base16("hello world")


def test_scalar__base16__parse__empty():
    assert parse_base16(b"") == ""


def test_scalar__base16__parse__unsupported_type():
    msg = "Base16 cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_base16(1)
