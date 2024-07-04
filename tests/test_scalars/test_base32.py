from __future__ import annotations

import re

import pytest

from undine.errors import GraphQLConversionError
from undine.scalars.base32 import parse_base32


def test_scalar__base32__parse__bytes():
    assert parse_base32(b"NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


def test_scalar__base32__parse__str():
    assert parse_base32("NBSWY3DPEB3W64TMMQ======") == "NBSWY3DPEB3W64TMMQ======"


def test_scalar__base32__parse__conversion_error():
    msg = "Base32 cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_base32("hello world")


def test_scalar__base32__parse__empty():
    assert parse_base32(b"") == ""


def test_scalar__base32__parse__unsupported_type():
    msg = "Base32 cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_base32(1)
