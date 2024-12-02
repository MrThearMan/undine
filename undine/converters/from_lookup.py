from __future__ import annotations

from typing import Any, Literal

from graphql import GraphQLBoolean, GraphQLInt

from undine.scalars import GraphQLDate, GraphQLTime
from undine.typing import GraphQLType
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
def _(
    _: Literal[
        "exact",
        "iexact",
        "contains",
        "icontains",
        "startswith",
        "istartswith",
        "endswith",
        "iendswith",
        "regex",
        "iregex",
    ],
    **kwargs: Any,
) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["lt", "lte", "gt", "gte"], **kwargs: Any) -> GraphQLType:
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
        "month",
        "year",
        "iso_week_day",
        "iso_year",
        "week_day",
        "week",
        "hour",
        "minute",
        "second",
        "microsecond",
        "quarter",
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
