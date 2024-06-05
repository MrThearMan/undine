from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.base16 import base16_scalar


@pytest.mark.parametrize("func", [base16_scalar.parse, base16_scalar.serialize])
def test_scalar__base16__unsupported_type(func) -> None:
    msg = "'Base16' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1)


@pytest.mark.parametrize("func", [base16_scalar.parse, base16_scalar.serialize])
def test_scalar__base16__str(func) -> None:
    assert func("68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


@pytest.mark.parametrize("func", [base16_scalar.parse, base16_scalar.serialize])
def test_scalar__base16__conversion_error(func) -> None:
    msg = "'Base16' cannot represent value 'hello world': Non-base16 digit found"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")


def test_scalar__base16__serialize__bytes() -> None:
    assert base16_scalar.serialize(b"68656C6C6F20776F726C64") == "68656C6C6F20776F726C64"


def test_scalar__base16__serialize__bytes__empty() -> None:
    assert base16_scalar.serialize(b"") == ""
