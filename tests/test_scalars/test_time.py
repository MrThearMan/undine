from __future__ import annotations

import datetime

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.time import time_scalar


@pytest.mark.parametrize("func", [time_scalar.parse, time_scalar.serialize])
def test_scalar__time__unsupported_type(func) -> None:
    msg = "'Time' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__time__parse__str() -> None:
    assert time_scalar.parse("01:02:03") == datetime.time(1, 2, 3)


def test_scalar__time__parse__str__has_timezone() -> None:
    # Timezones for times are ignored.
    assert time_scalar.parse("12:15:30+02:00") == datetime.time(12, 15, 30)


def test_scalar__time__parse__invalid_time() -> None:
    msg = "'Time' cannot represent value '01:02:99': second must be in 0..59"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg, from_start=True)):
        time_scalar.parse("01:02:99")


def test_scalar__time__parse__str__conversion_error() -> None:
    msg = "'Time' cannot represent value 'hello world': Value is not a valid time"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        time_scalar.parse("hello world")


def test_scalar__time__serialize__time() -> None:
    value = datetime.time(1, 2, 3)
    assert time_scalar.serialize(value) == "01:02:03"


def test_scalar__time__serialize__time__has_timezone() -> None:
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    # Timezones for times are ignored.
    value = datetime.time(1, 2, 3, tzinfo=tzinfo)
    assert time_scalar.serialize(value) == "01:02:03"


def test_scalar__time__serialize__datetime() -> None:
    value = datetime.datetime(2021, 1, 1, 1, 2, 3)  # noqa: DTZ001
    assert time_scalar.serialize(value) == "01:02:03"


def test_scalar__time__serialize__datetime__has_timezone() -> None:
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    # Timezones for times are ignored.
    value = datetime.datetime(2021, 1, 1, 1, 2, 3, tzinfo=tzinfo)
    assert time_scalar.serialize(value) == "01:02:03"


def test_scalar__time__serialize__str() -> None:
    assert time_scalar.serialize("01:02:03") == "01:02:03"


def test_scalar__time__serialize__str__has_timezone() -> None:
    # Timezones for times are ignored.
    assert time_scalar.serialize("01:02:03+02:00") == "01:02:03"


def test_scalar__time__serialize__str__conversion_error() -> None:
    msg = "'Time' cannot represent value 'hello world': Value is not a valid time"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        time_scalar.serialize("hello world")


def test_scalar__time__serialize__str__invalid_time() -> None:
    msg = "'Time' cannot represent value '01:02:99': second must be in 0..59"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg, from_start=True)):
        time_scalar.serialize("01:02:99")
