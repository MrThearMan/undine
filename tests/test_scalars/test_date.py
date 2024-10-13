import datetime

import pytest

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.date import parse_date


def test_scalar__date__parse__datetime():
    assert parse_date(datetime.datetime(2022, 1, 1, 12, 15, 30)) == datetime.date(2022, 1, 1)


def test_scalar__date__parse__date():
    assert parse_date(datetime.date(2022, 1, 1)) == datetime.date(2022, 1, 1)


def test_scalar__date__parse__str__date():
    assert parse_date("2022-01-01") == datetime.date(2022, 1, 1)


def test_scalar__date__parse__str__datetime():
    assert parse_date("2022-01-01T12:15:30") == datetime.date(2022, 1, 1)


def test_scalar__date__parse__conversion_error():
    msg = "Date cannot represent value 'hello world': Invalid isoformat string: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_date("hello world")


def test_scalar__date__parse__unsupported_type():
    msg = "Date cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_date(1)
