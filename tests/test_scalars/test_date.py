from __future__ import annotations

import datetime

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.date import date_scalar


@pytest.mark.parametrize("func", [date_scalar.parse, date_scalar.serialize])
def test_scalar__date__unsupported_type(func) -> None:
    msg = "'Date' cannot represent value 1: Type 'builtins.int' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1)


def test_scalar__date__parse__str__date() -> None:
    assert date_scalar.parse("2022-01-01") == datetime.date(2022, 1, 1)


def test_scalar__date__parse__str__date__invalid_date() -> None:
    msg = "'Date' cannot represent value '2022-50-01': month must be in 1..12"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.parse("2022-50-01")


def test_scalar__date__parse__str__datetime() -> None:
    msg = "'Date' cannot represent value '2022-01-01T12:15:30': Value is not a valid date"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.parse("2022-01-01T12:15:30")


def test_scalar__date__parse__str__conversion_error() -> None:
    msg = "'Date' cannot represent value 'hello world': Value is not a valid date"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.parse("hello world")


def test_scalar__date__serialize__date() -> None:
    value = datetime.date(2022, 1, 1)
    assert date_scalar.serialize(value) == "2022-01-01"


def test_scalar__date__serialize__datetime() -> None:
    value = datetime.datetime(2022, 1, 1, 12, 15, 30)  # noqa: DTZ001
    assert date_scalar.serialize(value) == "2022-01-01"


def test_scalar__date__serialize__str__date() -> None:
    assert date_scalar.serialize("2022-01-01") == "2022-01-01"


def test_scalar__date__serialize__str__date__invalid() -> None:
    msg = "'Date' cannot represent value '2022-50-01': month must be in 1..12"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.serialize("2022-50-01")


def test_scalar__date__serialize__str__datetime() -> None:
    msg = "'Date' cannot represent value '2022-01-01T12:15:30': Value is not a valid date"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.serialize("2022-01-01T12:15:30")


def test_scalar__date__serialize__str__conversion_error() -> None:
    msg = "'Date' cannot represent value 'hello world': Value is not a valid date"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        date_scalar.serialize("hello world")
