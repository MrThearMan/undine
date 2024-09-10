import datetime
import re

import pytest

from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.time import parse_time


def test_scalar__time__parse__time():
    assert parse_time(datetime.time(1, 2, 3)) == datetime.time(1, 2, 3)


def test_scalar__time__parse__str():
    assert parse_time("01:02:03") == datetime.time(1, 2, 3)


def test_scalar__time__parse__str__tzinfo():
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    assert parse_time("12:15:30+02:00") == datetime.time(12, 15, 30, tzinfo=tzinfo)


def test_scalar__time__parse__conversion_error():
    msg = "Time cannot represent value 'hello world': Invalid isoformat string: 'hello world'"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_time("hello world")


def test_scalar__time__parse__unsupported_type():
    msg = "Time cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_time(1.2)
