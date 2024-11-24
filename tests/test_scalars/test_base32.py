from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.base32 import parse_base32, serialize


@pytest.mark.parametrize("func", [parse_base32, serialize])
def test_scalar__base32__parse__bytes(func):
    assert func(b"NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


@pytest.mark.parametrize("func", [parse_base32, serialize])
def test_scalar__base32__parse__str(func):
    assert func("NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


@pytest.mark.parametrize("func", [parse_base32, serialize])
def test_scalar__base32__parse__conversion_error(func):
    msg = "'Base32' cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_base32, serialize])
def test_scalar__base32__parse__empty(func):
    assert func(b"") == ""


@pytest.mark.parametrize("func", [parse_base32, serialize])
def test_scalar__base32__parse__unsupported_type(func):
    msg = "'Base32' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1)
