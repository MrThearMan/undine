from __future__ import annotations

from typing import Any, Literal

from django.db.models.constants import LOOKUP_SEP
from graphql import (
    GraphQLBoolean,
    GraphQLInputType,
    GraphQLInt,
    GraphQLList,
    GraphQLNonNull,
    GraphQLOutputType,
    GraphQLString,
)

from undine.converters import convert_lookup_to_graphql_type
from undine.exceptions import FunctionDispatcherError
from undine.scalars import GraphQLDate, GraphQLTime


@convert_lookup_to_graphql_type.register
def _(lookup: str, **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if LOOKUP_SEP not in lookup:
        msg = f"Could not find a matching GraphQL type for lookup: '{lookup}'."
        raise FunctionDispatcherError(msg)

    transform, rest = lookup.split(LOOKUP_SEP, maxsplit=1)
    kwargs["default_type"] = convert_lookup_to_graphql_type(transform, **kwargs)
    return convert_lookup_to_graphql_type(rest, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["exact"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return kwargs["default_type"]


@convert_lookup_to_graphql_type.register
def _(_: Literal["endswith", "startswith"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return kwargs["default_type"]


@convert_lookup_to_graphql_type.register
def _(_: Literal["contains"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return kwargs["default_type"]


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "icontains",
        "iendswith",
        "iexact",
        "iregex",
        "istartswith",
        "regex",
    ],
    **kwargs: Any,
) -> GraphQLInputType | GraphQLOutputType:
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
) -> GraphQLInputType | GraphQLOutputType:
    return kwargs["default_type"]


@convert_lookup_to_graphql_type.register
def _(_: Literal["isnull"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean


@convert_lookup_to_graphql_type.register
def _(_: Literal["in", "range"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    if isinstance(kwargs["default_type"], GraphQLList):
        return kwargs["default_type"]
    return GraphQLList(GraphQLNonNull(kwargs["default_type"]))


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
) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLInt


@convert_lookup_to_graphql_type.register
def _(_: Literal["date"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLDate


@convert_lookup_to_graphql_type.register
def _(_: Literal["time"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLTime


@convert_lookup_to_graphql_type.register
def _(_: Literal["contained_by", "overlap"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return kwargs["default_type"]


@convert_lookup_to_graphql_type.register
def _(_: Literal["len"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLInt


@convert_lookup_to_graphql_type.register
def _(_: Literal["has_key"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
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
) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLList(GraphQLNonNull(GraphQLString))


@convert_lookup_to_graphql_type.register
def _(_: Literal["unaccent"], **kwargs: Any) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "trigram_similar",
        "trigram_word_similar",
        "trigram_strict_word_similar",
    ],
    **kwargs: Any,
) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLString


@convert_lookup_to_graphql_type.register
def _(
    _: Literal[
        "isempty",
        "lower_inc",
        "lower_inf",
        "upper_inc",
        "upper_inf",
    ],
    **kwargs: Any,
) -> GraphQLInputType | GraphQLOutputType:
    return GraphQLBoolean
