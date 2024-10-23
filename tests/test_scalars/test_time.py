import datetime

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.time import parse_time, serialize


def test_scalar__time__parse__time():
    assert parse_time(datetime.time(1, 2, 3)) == datetime.time(1, 2, 3)


def test_scalar__time__parse__str():
    assert parse_time("01:02:03") == datetime.time(1, 2, 3)


def test_scalar__time__parse__str__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert parse_time("12:15:30+02:00") == datetime.time(12, 15, 30, tzinfo=tzinfo)


@pytest.mark.parametrize("func", [parse_time, serialize])
def test_scalar__time__parse__conversion_error(func):
    msg = "Time cannot represent value 'hello world': Invalid isoformat string: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_time, serialize])
def test_scalar__time__parse__unsupported_type(func):
    msg = "Time cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__time__serialize__time():
    assert serialize(datetime.time(1, 2, 3)) == "01:02:03"


def test_scalar__time__serialize__time__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert serialize(datetime.time(1, 2, 3, tzinfo=tzinfo)) == "01:02:03+02:00"


def test_scalar__time__serialize__str():
    assert serialize("01:02:03") == "01:02:03"


def test_scalar__time__serialize__str__tzinfo():
    assert serialize("01:02:03+02:00") == "01:02:03+02:00"
