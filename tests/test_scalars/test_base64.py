from __future__ import annotations

import re

import pytest

from undine.errors import GraphQLConversionError
from undine.scalars.base64 import parse_base64


def test_scalar__base64__parse__bytes():
    assert parse_base64(b"aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


def test_scalar__base64__parse__str():
    assert parse_base64("aGVsbG8gd29ybGQ=") == "aGVsbG8gd29ybGQ="


def test_scalar__base64__parse__conversion_error():
    msg = "Base64 cannot represent value 'hello world': Incorrect padding"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_base64("hello world")


def test_scalar__base64__parse__empty():
    assert parse_base64(b"") == ""


def test_scalar__base64__parse__unsupported_type():
    msg = "Base64 cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_base64(1)
