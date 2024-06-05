# ruff: noqa: DTZ001
import datetime

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.datetime import parse_datetime, serialize


def test_scalar__datetime__parse__datetime():
    assert parse_datetime(datetime.datetime(2022, 1, 1, 12, 15, 30)) == datetime.datetime(2022, 1, 1, 12, 15, 30)


def test_scalar__datetime__parse__str():
    assert parse_datetime("2022-01-01T12:15:30") == datetime.datetime(2022, 1, 1, 12, 15, 30)


def test_scalar__datetime__parse__str__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert parse_datetime("2022-01-01T12:15:30+02:00") == datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)


@pytest.mark.parametrize("func", [parse_datetime, serialize])
def test_scalar__datetime__parse__conversion_error(func):
    msg = "'DateTime' cannot represent value 'hello world': Invalid isoformat string: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func("hello world")


@pytest.mark.parametrize("func", [parse_datetime, serialize])
def test_scalar__datetime__parse__unsupported_type(func):
    msg = "'DateTime' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(1)


def test_scalar__datetime__serialize__datetime():
    assert serialize(datetime.datetime(2022, 1, 1, 12, 15, 30)) == "2022-01-01T12:15:30"


def test_scalar__datetime__serialize__datetime__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert serialize(datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)) == "2022-01-01T12:15:30+02:00"


def test_scalar__datetime__serialize__str():
    assert serialize("2022-01-01T12:15:30") == "2022-01-01T12:15:30"


def test_scalar__datetime__serialize__str__tzinfo():
    assert serialize("2022-01-01T12:15:30+02:00") == "2022-01-01T12:15:30+02:00"
