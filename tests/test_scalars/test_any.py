from __future__ import annotations

import pytest
from graphql import GRAPHQL_MAX_INT, GRAPHQL_MIN_INT

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.any import parse_any, serialize


@pytest.mark.parametrize("func", [parse_any, serialize])
@pytest.mark.parametrize("value", ["foo", ""])
def test_scalar__any__parse__str(func, value):
    assert func(value) == value


@pytest.mark.parametrize("func", [parse_any, serialize])
@pytest.mark.parametrize("value", [True, False])
def test_scalar__any__parse__bool(func, value):
    assert func(value) is value


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__none(func):
    assert func(None) is None


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__bytes(func):
    assert func(b"hello world") == "hello world"


@pytest.mark.parametrize("func", [parse_any, serialize])
@pytest.mark.parametrize("value", [1, 2, -1, 0])
def test_scalar__any__parse__int(func, value):
    assert func(value) is value


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__too_high(func):
    msg = "Any cannot represent value 2147483648: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(GRAPHQL_MAX_INT + 1)


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__too_low(func):
    msg = "Any cannot represent value -2147483649: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(GRAPHQL_MIN_INT - 1)


@pytest.mark.parametrize("func", [parse_any, serialize])
@pytest.mark.parametrize("value", [1.0, -1.0, 0.3, 1.3e-3, 1.3e3, -1.3e3])
def test_scalar__any__parse__float(func, value):
    assert func(value) is value


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__float__inf(func):
    msg = "Any cannot represent value inf: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(float("inf"))


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__float__nan(func):
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(float("nan"))


@pytest.mark.parametrize("func", [parse_any, serialize])
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
def test_scalar__any__parse__list(func, value):
    assert func(value) is value


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__list__value_error(func):
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func([float("nan")])


@pytest.mark.parametrize("func", [parse_any, serialize])
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
def test_scalar__any__parse__dict(func, value):
    assert func(value) is value


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__dict__value_error(func):
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func({"foo": float("nan")})


@pytest.mark.parametrize("func", [parse_any, serialize])
def test_scalar__any__parse__unsupported_type(func):
    msg = "Any cannot represent value <object instance>: Type 'builtins.object' is not supported"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        func(object())
