import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.json import parse_json


def test_scalar__json__parse__dict():
    assert parse_json({"foo": "bar"}) == {"foo": "bar"}


def test_scalar__json__parse__str():
    assert parse_json('{"foo": "bar"}') == {"foo": "bar"}


def test_scalar__json__parse__conversion_error():
    msg = "JSON cannot represent value '{\"foo\": ': Expecting value: line 1 column 9 (char 8)"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_json('{"foo": ')


def test_scalar__json__parse__unsupported_type():
    msg = "JSON cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_json(1.2)
