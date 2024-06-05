from __future__ import annotations

import datetime

import pytest

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.duration import duration_scalar


@pytest.mark.parametrize("func", [duration_scalar.parse, duration_scalar.serialize])
def test_scalar__duration__unsupported_type(func) -> None:
    msg = "'Duration' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__duration__parse__int() -> None:
    assert duration_scalar.parse(1) == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__str() -> None:
    assert duration_scalar.parse("1") == datetime.timedelta(seconds=1)


def test_scalar__duration__parse__str__conversion_error() -> None:
    msg = "'Duration' cannot represent value 'hello world': Value is not a valid integer"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        duration_scalar.parse("hello world")


def test_scalar__duration__serialize__timedelta() -> None:
    assert duration_scalar.serialize(datetime.timedelta(seconds=1)) == 1


def test_scalar__duration__serialize__timedelta__fractional_seconds() -> None:
    # Default implementation serialize_durations to an int seconds, so it doesn't support fractional seconds.
    value = datetime.timedelta(seconds=1, milliseconds=1, microseconds=1)
    assert duration_scalar.serialize(value) == 1


def test_scalar__duration__serialize__int() -> None:
    assert duration_scalar.serialize(1) == 1


def test_scalar__duration__serialize__str() -> None:
    assert duration_scalar.serialize("1") == 1


def test_scalar__duration__serialize__str__conversion_error() -> None:
    msg = "'Duration' cannot represent value 'hello world': Value is not a valid integer"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        duration_scalar.serialize("hello world")
