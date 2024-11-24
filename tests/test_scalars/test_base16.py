from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.base16 import parse_base16, serialize


@pytest.mark.parametrize("func", [parse_base16, serialize])
def test_scalar__base16__parse__bytes(func):
    assert func(b"68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


@pytest.mark.parametrize("func", [parse_base16, serialize])
def test_scalar__base16__parse__str(func):
    assert func("68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


@pytest.mark.parametrize("func", [parse_base16, serialize])
def test_scalar__base16__parse__conversion_error(func):
    msg = "'Base16' cannot represent value 'hello world': Non-base16 digit found"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_base16, serialize])
def test_scalar__base16__parse__empty(func):
    assert func(b"") == ""


@pytest.mark.parametrize("func", [parse_base16, serialize])
def test_scalar__base16__parse__unsupported_type(func):
    msg = "'Base16' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1)
