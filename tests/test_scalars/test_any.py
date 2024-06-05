from __future__ import annotations

import datetime
import uuid

import pytest
from graphql import GRAPHQL_MAX_INT, GRAPHQL_MIN_INT

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.any import any_scalar


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", ["foo", ""])
def test_scalar__any__str(func, value) -> None:
    assert func(value) == value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [True, False])
def test_scalar__any__bool(func, value) -> None:
    assert func(value) is value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__none(func) -> None:
    assert func(None) is None


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__bytes(func) -> None:
    assert func(b"hello world") == "hello world"


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [1, 2, -1, 0])
def test_scalar__any__int(func, value) -> None:
    assert func(value) is value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__too_high(func) -> None:
    msg = "'Any' cannot represent value 2147483648: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(GRAPHQL_MAX_INT + 1)


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__too_low(func) -> None:
    msg = "'Any' cannot represent value -2147483649: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(GRAPHQL_MIN_INT - 1)


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [1.0, -1.0, 0.3, 1.3e-3, 1.3e3, -1.3e3])
def test_scalar__any__float(func, value) -> None:
    assert func(value) is value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__float__inf(func) -> None:
    msg = "'Any' cannot represent value inf: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(float("inf"))


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__float__nan(func) -> None:
    msg = "'Any' cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(float("nan"))


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [datetime.datetime(2021, 1, 1)])  # noqa: DTZ001
def test_scalar__any__datetime(func, value) -> None:
    assert func(value) == value.isoformat()


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [datetime.date(2021, 1, 1)])
def test_scalar__any__date(func, value) -> None:
    assert func(value) == value.isoformat()


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [datetime.time()])
def test_scalar__any__time(func, value) -> None:
    assert func(value) == value.isoformat()


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize("value", [uuid.UUID("12345678-1234-5678-1234-567812345678")])
def test_scalar__any__uuid(func, value) -> None:
    assert func(value) == "12345678-1234-5678-1234-567812345678"


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize(
    "value",
    [
        ["foo", "bar"],
        [1, 2, 3],
        [True, False],
        [None],
        [{"foo": "bar"}],
    ],
)
def test_scalar__any__list(func, value) -> None:
    assert func(value) == value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__list__value_error(func) -> None:
    msg = "'Any' cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func([float("nan")])


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
@pytest.mark.parametrize(
    "value",
    [
        {"foo": "bar"},
        {"foo": 1},
        {"foo": True},
        {"foo": False},
        {"foo": None},
        {"foo": [1, 2, 3]},
        {"foo": {"bar": 1}},
    ],
)
def test_scalar__any__dict(func, value) -> None:
    assert func(value) == value


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__dict__value_error(func) -> None:
    msg = "'Any' cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func({"foo": float("nan")})


@pytest.mark.parametrize("func", [any_scalar.parse, any_scalar.serialize])
def test_scalar__any__unsupported_type(func) -> None:
    msg = "'Any' cannot represent value <object instance>: Type 'builtins.object' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(object())
