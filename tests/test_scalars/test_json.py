import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.json import parse_json, serialize


@pytest.mark.parametrize("func", [parse_json, serialize])
def test_scalar__json__parse__dict(func):
    assert func({"foo": "bar"}) == {"foo": "bar"}


@pytest.mark.parametrize("func", [parse_json, serialize])
def test_scalar__json__parse__str(func):
    assert func('{"foo": "bar"}') == {"foo": "bar"}


@pytest.mark.parametrize("func", [parse_json, serialize])
def test_scalar__json__parse__conversion_error(func):
    msg = "'JSON' cannot represent value '{\"foo\": ': Expecting value: line 1 column 9 (char 8)"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func('{"foo": ')


@pytest.mark.parametrize("func", [parse_json, serialize])
def test_scalar__json__parse__unsupported_type(func):
    msg = "'JSON' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)
