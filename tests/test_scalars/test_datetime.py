from __future__ import annotations

import datetime

import pytest
from django.utils.timezone import get_default_timezone

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.datetime import datetime_scalar

UTC = get_default_timezone()


@pytest.mark.parametrize("func", [datetime_scalar.parse, datetime_scalar.serialize])
def test_scalar__datetime__unsupported_type(func) -> None:
    msg = "'DateTime' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1)


def test_scalar__datetime__parse__str() -> None:
    assert datetime_scalar.parse("2022-01-01T12:15:30") == datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=UTC)


def test_scalar__datetime__parse__str__has_timezone() -> None:
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    value = datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)
    assert datetime_scalar.parse("2022-01-01T12:15:30+02:00") == value


def test_scalar__datetime__parse__str__not_use_tz(settings) -> None:
    settings.USE_TZ = False
    assert datetime_scalar.parse("2022-01-01T12:15:30") == datetime.datetime(2022, 1, 1, 12, 15, 30)  # noqa: DTZ001


def test_scalar__datetime__parse__str__not_use_tz__has_timezone(settings) -> None:
    settings.USE_TZ = False
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    value = datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)
    assert datetime_scalar.parse("2022-01-01T12:15:30+02:00") == value


def test_scalar__datetime__parse__str__conversion_error() -> None:
    msg = "'DateTime' cannot represent value 'hello world': Value is not a valid datetime"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        datetime_scalar.parse("hello world")


def test_scalar__datetime__parse__str__invalid_datetime() -> None:
    msg = "'DateTime' cannot represent value '2022-50-01T12:15:30': month must be in 1..12"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        datetime_scalar.parse("2022-50-01T12:15:30")


def test_scalar__datetime__serialize__str() -> None:
    assert datetime_scalar.serialize("2022-01-01T12:15:30") == "2022-01-01T12:15:30+00:00"


def test_scalar__datetime__serialize__str__has_timezone() -> None:
    assert datetime_scalar.serialize("2022-01-01T12:15:30+02:00") == "2022-01-01T12:15:30+02:00"


def test_scalar__datetime__serialize__str__no_use_tz(settings) -> None:
    settings.USE_TZ = False
    assert datetime_scalar.serialize("2022-01-01T12:15:30") == "2022-01-01T12:15:30"


def test_scalar__datetime__serialize__str__no_use_tz__has_timezone(settings) -> None:
    settings.USE_TZ = False
    assert datetime_scalar.serialize("2022-01-01T12:15:30+02:00") == "2022-01-01T12:15:30+02:00"


def test_scalar__datetime__serialize__str__conversion_error() -> None:
    msg = "'DateTime' cannot represent value 'hello world': Value is not a valid datetime"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        datetime_scalar.serialize("hello world")


def test_scalar__datetime__serialize__datetime() -> None:
    value = datetime.datetime(2022, 1, 1, 12, 15, 30)  # noqa: DTZ001
    assert datetime_scalar.serialize(value) == "2022-01-01T12:15:30"


def test_scalar__datetime__serialize__datetime__has_timezone() -> None:
    tzinfo = datetime.timezone(datetime.timedelta(hours=2))
    value = datetime.datetime(2022, 1, 1, 12, 15, 30, tzinfo=tzinfo)
    assert datetime_scalar.serialize(value) == "2022-01-01T12:15:30+02:00"
