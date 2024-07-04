from __future__ import annotations

import re

import pytest
from graphql import GRAPHQL_MAX_INT, GRAPHQL_MIN_INT

from undine.errors import GraphQLConversionError
from undine.scalars.any import parse_any


@pytest.mark.parametrize("value", ["foo", ""])
def test_scalar__any__parse__str(value):
    assert parse_any(value) == value


@pytest.mark.parametrize("value", [True, False])
def test_scalar__any__parse__bool(value):
    assert parse_any(value) is value


def test_scalar__any__parse__none():
    assert parse_any(None) is None


def test_scalar__any__parse__bytes():
    assert parse_any(b"hello world") == "hello world"


@pytest.mark.parametrize("value", [1, 2, -1, 0])
def test_scalar__any__parse__int(value):
    assert parse_any(value) is value


def test_scalar__any__parse__too_high():
    msg = "Any cannot represent value 2147483648: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any(GRAPHQL_MAX_INT + 1)


def test_scalar__any__parse__too_low():
    msg = "Any cannot represent value -2147483649: GraphQL integers cannot represent non 32-bit signed integer value."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any(GRAPHQL_MIN_INT - 1)


@pytest.mark.parametrize("value", [1.0, -1.0, 0.3, 1.3e-3, 1.3e3, -1.3e3])
def test_scalar__any__parse__float(value):
    assert parse_any(value) is value


def test_scalar__any__parse__float__inf():
    msg = "Any cannot represent value inf: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any(float("inf"))


def test_scalar__any__parse__float__nan():
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any(float("nan"))


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
def test_scalar__any__parse__list(value):
    assert parse_any(value) is value


def test_scalar__any__parse__list__value_error():
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any([float("nan")])


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
def test_scalar__any__parse__dict(value):
    assert parse_any(value) is value


def test_scalar__any__parse__dict__value_error():
    msg = "Any cannot represent value nan: GraphQL floats cannot represent 'inf' or 'NaN' values."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any({"foo": float("nan")})


def test_scalar__any__parse__unsupported_type():
    msg = "Any cannot represent value <object instance>: Type 'builtins.object' is not supported"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_any(object())
