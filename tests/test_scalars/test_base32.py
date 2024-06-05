from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.base32 import base32_scalar


@pytest.mark.parametrize("func", [base32_scalar.parse, base32_scalar.serialize])
def test_scalar__base32__unsupported_type(func) -> None:
    msg = "'Base32' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1)


@pytest.mark.parametrize("func", [base32_scalar.parse, base32_scalar.serialize])
def test_scalar__base32__str(func) -> None:
    assert func("NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


@pytest.mark.parametrize("func", [base32_scalar.parse, base32_scalar.serialize])
def test_scalar__base32__conversion_error(func) -> None:
    msg = "'Base32' cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func("hello world")


def test_scalar__base32__serialize__bytes() -> None:
    assert base32_scalar.serialize(b"NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


def test_scalar__base32__serialize__empty() -> None:
    assert base32_scalar.serialize(b"") == ""
