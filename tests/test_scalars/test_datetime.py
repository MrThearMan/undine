import datetime
import re

import pytest

from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.datetime import parse_datetime


def test_scalar__datetime__parse__datetime():
    assert parse_datetime(datetime.datetime(2022, 1, 1, 12, 15, 30)) == datetime.datetime(2022, 1, 1, 12, 15, 30)


def test_scalar__datetime__parse__str():
    assert parse_datetime("2022-01-01T12:15:30") == datetime.datetime(2022, 1, 1, 12, 15, 30)


def test_scalar__datetime__parse__str__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert parse_datetime("2022-01-01T12:15:30+02:00") == datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)


def test_scalar__datetime__parse__conversion_error():
    msg = "DateTime cannot represent value 'hello world': Invalid isoformat string: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_datetime("hello world")


def test_scalar__datetime__parse__unsupported_type():
    msg = "DateTime cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_datetime(1)
