import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.url import parse_url, serialize


@pytest.mark.parametrize("func", [parse_url, serialize])
def test_scalar__url__parse__str(func):
    assert func("https://example.com/hello") == "https://example.com/hello"


@pytest.mark.parametrize("func", [parse_url, serialize])
def test_scalar__url__parse__str__not_valid(func):
    msg = "URL cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_url, serialize])
def test_scalar__url__parse__unsupported_type(func):
    msg = "URL cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)
