from __future__ import annotations

from typing import Any, Literal

from graphql import GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString, GraphQLType

from undine.scalars import GraphQLDate, GraphQLTime
from undine.utils.function_dispatcher import FunctionDispatcher

from .to_graphql_type import convert_to_graphql_type

__all__ = [
    "convert_lookup_to_graphql_type",
]


convert_lookup_to_graphql_type = FunctionDispatcher[str, GraphQLType]()
"""
Convert the given lookup to a GraphQL input type.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - default_type: Default python type to use for the lookup.
"""


@convert_lookup_to_graphql_type.register
def _(_: Literal["exact"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "endswith",
        "regex",
        "startswith",
    ],
    **kwargs: Any,
) -> GraphQLType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(_: Literal["contains"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "icontains",
        "iendswith",
        "iexact",
        "iregex",
        "istartswith",
    ],
    **kwargs: Any,
) -> GraphQLType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "gt",
        "gte",
        "lt",
        "lte",
    ],
    **kwargs: Any,
) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["isnull"], **kwargs: Any) -> GraphQLType:
    return GraphQLBoolean


@convert_lookup_to_graphql_type.register
def _(_: Literal["in", "range"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    type_ = list.__class_getitem__(default_type)
    return convert_to_graphql_type(type_, **kwargs)


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "day",
        "hour",
        "iso_week_day",
        "iso_year",
        "microsecond",
        "minute",
        "month",
        "quarter",
        "second",
        "week",
        "week_day",
        "year",
    ],
    **kwargs: Any,
) -> GraphQLType:
    return GraphQLInt


@convert_lookup_to_graphql_type.register
def _(_: Literal["date"], **kwargs: Any) -> GraphQLType:
    return GraphQLDate


@convert_lookup_to_graphql_type.register
def _(_: Literal["time"], **kwargs: Any) -> GraphQLType:
    return GraphQLTime


@convert_lookup_to_graphql_type.register
def _(_: Literal["contained_by", "overlap"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["len"], **kwargs: Any) -> GraphQLType:
    return GraphQLInt


@convert_lookup_to_graphql_type.register
def _(_: Literal["has_key"], **kwargs: Any) -> GraphQLType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "has_any_keys",
        "has_keys",
        "keys",
        "values",
    ],
    **kwargs: Any,
) -> GraphQLType:
    return GraphQLList(GraphQLNonNull(GraphQLString))


@convert_lookup_to_graphql_type.register
def _(_: Literal["unaccent"], **kwargs: Any) -> GraphQLType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "trigram_similar",
        "trigram_word_similar",
        "trigram_strict_word_similar",
    ],
    **kwargs: Any,
) -> GraphQLType:
    return GraphQLString
