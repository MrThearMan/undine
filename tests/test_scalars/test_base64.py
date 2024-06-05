from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.base64 import base64_scalar


@pytest.mark.parametrize("func", [base64_scalar.parse, base64_scalar.serialize])
def test_scalar__base64__unsupported_type(func) -> None:
    msg = "'Base64' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1)


@pytest.mark.parametrize("func", [base64_scalar.parse, base64_scalar.serialize])
def test_scalar__base64__str(func) -> None:
    assert func("aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


@pytest.mark.parametrize("func", [base64_scalar.parse, base64_scalar.serialize])
def test_scalar__base64__conversion_error(func) -> None:
    msg = "'Base64' cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")


def test_scalar__base64__serialize__bytes() -> None:
    assert base64_scalar.serialize(b"aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


def test_scalar__base64__serialize__empty() -> None:
    assert base64_scalar.serialize(b"") == ""
