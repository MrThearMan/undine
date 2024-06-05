from __future__ import annotations

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.json import json_scalar


@pytest.mark.parametrize("func", [json_scalar.parse, json_scalar.serialize])
def test_scalar__json__unsupported_type(func) -> None:
    msg = "'JSON' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__json__parse__dict() -> None:
    assert json_scalar.parse({"foo": "bar"}) == {"foo": "bar"}


def test_scalar__json__parse__str() -> None:
    assert json_scalar.parse('{"foo": "bar"}') == {"foo": "bar"}


def test_scalar__json__parse__str__not_dict() -> None:
    msg = "'JSON' cannot represent value '1': Value is not a valid JSON"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.parse("1")


def test_scalar__json__parse__str__conversion_error() -> None:
    msg = "'JSON' cannot represent value '{\"foo\": ': Expecting value: line 1 column 9 (char 8)"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.parse('{"foo": ')


def test_scalar__json__serialize__dict() -> None:
    assert json_scalar.serialize({"foo": "bar"}) == {"foo": "bar"}


def test_scalar__json__serialize__str() -> None:
    assert json_scalar.serialize('{"foo": "bar"}') == {"foo": "bar"}


def test_scalar__json__serialize__str__not_dict() -> None:
    msg = "'JSON' cannot represent value '1': Value is not a valid JSON"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.serialize("1")


def test_scalar__json__serialize__str__conversion_error() -> None:
    msg = "'JSON' cannot represent value '{\"foo\": ': Expecting value: line 1 column 9 (char 8)"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.serialize('{"foo": ')


def test_scalar__json__serialize__bytes() -> None:
    assert json_scalar.serialize(b'{"foo": "bar"}') == {"foo": "bar"}


def test_scalar__json__serialize__bytes__not_dict() -> None:
    msg = "'JSON' cannot represent value b'1': Value is not a valid JSON"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.serialize(b"1")


def test_scalar__json__serialize__bytes__conversion_error() -> None:
    msg = "'JSON' cannot represent value b'{\"foo\": ': Expecting value: line 1 column 9 (char 8)"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        json_scalar.serialize(b'{"foo": ')
