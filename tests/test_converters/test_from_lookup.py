from __future__ import annotations

from typing import NamedTuple

import pytest
from graphql import GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString

from tests.helpers import parametrize_helper
from undine.converters import convert_lookup_to_graphql_type
from undine.scalars import GraphQLDate, GraphQLJSON, GraphQLTime
from undine.typing import GraphQLInputOutputType


class Params(NamedTuple):
    value: str
    default_type: type | None
    expected: GraphQLInputOutputType


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "exact": Params(
                value="exact",
                default_type=str,
                expected=GraphQLString,
            ),
            "iexact": Params(
                value="iexact",
                default_type=str,
                expected=GraphQLString,
            ),
            "contains": Params(
                value="contains",
                default_type=str,
                expected=GraphQLString,
            ),
            "icontains": Params(
                value="icontains",
                default_type=str,
                expected=GraphQLString,
            ),
            "startswith": Params(
                value="startswith",
                default_type=str,
                expected=GraphQLString,
            ),
            "istartswith": Params(
                value="istartswith",
                default_type=str,
                expected=GraphQLString,
            ),
            "endswith": Params(
                value="endswith",
                default_type=str,
                expected=GraphQLString,
            ),
            "iendswith": Params(
                value="iendswith",
                default_type=str,
                expected=GraphQLString,
            ),
            "regex": Params(
                value="regex",
                default_type=str,
                expected=GraphQLString,
            ),
            "iregex": Params(
                value="iregex",
                default_type=str,
                expected=GraphQLString,
            ),
            "isnull": Params(
                value="isnull",
                default_type=None,
                expected=GraphQLBoolean,
            ),
            "lt": Params(
                value="lt",
                default_type=int,
                expected=GraphQLInt,
            ),
            "lte": Params(
                value="lte",
                default_type=int,
                expected=GraphQLInt,
            ),
            "gt": Params(
                value="gt",
                default_type=int,
                expected=GraphQLInt,
            ),
            "gte": Params(
                value="gte",
                default_type=int,
                expected=GraphQLInt,
            ),
            "day": Params(
                value="day",
                default_type=None,
                expected=GraphQLInt,
            ),
            "month": Params(
                value="month",
                default_type=None,
                expected=GraphQLInt,
            ),
            "year": Params(
                value="year",
                default_type=None,
                expected=GraphQLInt,
            ),
            "iso_week_day": Params(
                value="iso_week_day",
                default_type=None,
                expected=GraphQLInt,
            ),
            "iso_year": Params(
                value="iso_year",
                default_type=None,
                expected=GraphQLInt,
            ),
            "week_day": Params(
                value="week_day",
                default_type=None,
                expected=GraphQLInt,
            ),
            "week": Params(
                value="week",
                default_type=None,
                expected=GraphQLInt,
            ),
            "hour": Params(
                value="hour",
                default_type=None,
                expected=GraphQLInt,
            ),
            "minute": Params(
                value="minute",
                default_type=None,
                expected=GraphQLInt,
            ),
            "second": Params(
                value="second",
                default_type=None,
                expected=GraphQLInt,
            ),
            "microsecond": Params(
                value="microsecond",
                default_type=None,
                expected=GraphQLInt,
            ),
            "quarter": Params(
                value="quarter",
                default_type=None,
                expected=GraphQLInt,
            ),
            "in": Params(
                value="in",
                default_type=str,
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "range": Params(
                value="range",
                default_type=int,
                expected=GraphQLList(GraphQLNonNull(GraphQLInt)),
            ),
            "date": Params(
                value="date",
                default_type=str,
                expected=GraphQLDate,
            ),
            "time": Params(
                value="time",
                default_type=str,
                expected=GraphQLTime,
            ),
            "contained_by dict": Params(
                value="contained_by",
                default_type=dict[str, str],
                expected=GraphQLJSON,
            ),
            "contained_by list": Params(
                value="contained_by",
                default_type=list[str],
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "overlap list": Params(
                value="overlap",
                default_type=list[str],
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "overlap dict": Params(
                value="overlap",
                default_type=dict[str, str],
                expected=GraphQLJSON,
            ),
            "has_key": Params(
                value="has_key",
                default_type=str,
                expected=GraphQLString,
            ),
            "has_any_keys": Params(
                value="has_any_keys",
                default_type=list[str],
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "has_keys": Params(
                value="has_keys",
                default_type=list[str],
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "keys": Params(
                value="keys",
                default_type=str,
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "values": Params(
                value="values",
                default_type=str,
                expected=GraphQLList(GraphQLNonNull(GraphQLString)),
            ),
            "unaccent": Params(
                value="unaccent",
                default_type=str,
                expected=GraphQLString,
            ),
            "trigram_similar": Params(
                value="trigram_similar",
                default_type=str,
                expected=GraphQLString,
            ),
            "trigram_word_similar": Params(
                value="trigram_word_similar",
                default_type=str,
                expected=GraphQLString,
            ),
            "trigram_strict_word_similar": Params(
                value="trigram_strict_word_similar",
                default_type=str,
                expected=GraphQLString,
            ),
            # TODO: Range field lookups
        },
    ),
)
def test_convert_lookup_to_graphql_type(value, default_type, expected):
    assert convert_lookup_to_graphql_type(value, default_type=default_type) == expected
