import datetime

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.duration import parse_duration


def test_scalar__duration__parse__timedelta():
    assert parse_duration(datetime.timedelta(seconds=1)) == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__int():
    assert parse_duration(1) == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__str():
    assert parse_duration("1") == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__conversion_error():
    msg = "Duration cannot represent value 'hello world': invalid literal for int() with base 10: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_duration("hello world")


def test_scalar__duration__parse__unsupported_type():
    msg = "Duration cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_duration(1.2)
