import datetime

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.duration import parse_duration, serialize


def test_scalar__duration__parse__timedelta():
    assert parse_duration(datetime.timedelta(seconds=1)) == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__int():
    assert parse_duration(1) == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__str():
    assert parse_duration("1") == datetime.timedelta(seconds=1)


@pytest.mark.parametrize("func", [parse_duration, serialize])
def test_scalar__duration__parse__conversion_error(func):
    msg = "'Duration' cannot represent value 'hello world': invalid literal for int() with base 10: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_duration("hello world")


@pytest.mark.parametrize("func", [parse_duration, serialize])
def test_scalar__duration__parse__unsupported_type(func):
    msg = "'Duration' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__duration__serialize__timedelta():
    assert serialize(datetime.timedelta(seconds=1)) == 1


def test_scalar__duration__serialize__timedelta__microseconds():
    # Default implementation serializes to an int seconds, so it doesn't support milliseconds or microseconds.
    assert serialize(datetime.timedelta(seconds=1, milliseconds=1, microseconds=1)) == 1


def test_scalar__duration__serialize__int():
    assert serialize(1) == 1


def test_scalar__duration__serialize__str():
    assert serialize("1") == 1
