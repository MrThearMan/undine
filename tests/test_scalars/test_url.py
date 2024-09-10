import re

import pytest

from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.url import parse_url


def test_scalar__url__parse__str():
    assert parse_url("https://example.com/hello") == "https://example.com/hello"


def test_scalar__url__parse__str__not_valid():
    msg = "URL cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_url("hello world")


def test_scalar__url__parse__unsupported_type():
    msg = "URL cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_url(1.2)
