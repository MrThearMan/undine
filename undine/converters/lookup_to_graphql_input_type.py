from __future__ import annotations

from typing import Any, Literal

from graphql import GraphQLInputType

from undine.utils.function_dispatcher import FunctionDispatcher

from .to_graphql_type import convert_type_to_graphql_type

__all__ = [
    "convert_lookup_to_graphql_input_type",
]


convert_lookup_to_graphql_input_type = FunctionDispatcher[str, GraphQLInputType]()
"""Convert the given lookuup to a GraphQL input type."""


@convert_lookup_to_graphql_input_type.register
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
) -> GraphQLInputType:
    default_type = kwargs["default_type"]
    return convert_type_to_graphql_type(default_type, is_input=True)


@convert_lookup_to_graphql_input_type.register
def _(_: Literal["lt", "lte", "gt", "gte"], **kwargs: Any) -> GraphQLInputType:
    default_type = kwargs["default_type"]
    return convert_type_to_graphql_type(default_type, is_input=True)


@convert_lookup_to_graphql_input_type.register
def _(_: Literal["isnull"], **kwargs: Any) -> GraphQLInputType:
    return convert_type_to_graphql_type(bool, is_input=True)


@convert_lookup_to_graphql_input_type.register
def _(_: Literal["in", "range"], **kwargs: Any) -> GraphQLInputType:
    default_type = kwargs["default_type"]
    type_ = list.__class_getitem__(default_type)
    return convert_type_to_graphql_type(type_, is_input=True)


@convert_lookup_to_graphql_input_type.register
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
) -> GraphQLInputType:
    return convert_type_to_graphql_type(int, is_input=True)
