from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.base64 import parse_base64, serialize


@pytest.mark.parametrize("func", [parse_base64, serialize])
def test_scalar__base64__parse__bytes(func):
    assert func(b"aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


@pytest.mark.parametrize("func", [parse_base64, serialize])
def test_scalar__base64__parse__str(func):
    assert func("aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


@pytest.mark.parametrize("func", [parse_base64, serialize])
def test_scalar__base64__parse__conversion_error(func):
    msg = "'Base64' cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_base64, serialize])
def test_scalar__base64__parse__empty(func):
    assert func(b"") == ""


@pytest.mark.parametrize("func", [parse_base64, serialize])
def test_scalar__base64__parse__unsupported_type(func):
    msg = "'Base64' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1)
