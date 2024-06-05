from __future__ import annotations

from typing import Any, Literal

from django.db.models.constants import LOOKUP_SEP
from graphql import GraphQLBoolean, GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLString, GraphQLType

from undine.converters import convert_lookup_to_graphql_type, convert_to_graphql_type, convert_to_python_type
from undine.exceptions import FunctionDispatcherError


@convert_lookup_to_graphql_type.register
def _(lookup: str, **kwargs: Any) -> GraphQLType:
    if LOOKUP_SEP not in lookup:
        msg = f"Could not find a matching GraphQL type for lookup: '{lookup}'."
        raise FunctionDispatcherError(msg)

    transform, rest = lookup.split(LOOKUP_SEP, maxsplit=1)

    transform_graphql_type = convert_lookup_to_graphql_type(transform, **kwargs)
    transform_python_type = convert_to_python_type(transform_graphql_type)

    kwargs["default_type"] = transform_python_type

    return convert_lookup_to_graphql_type(rest, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["exact"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["endswith", "startswith"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    return convert_to_graphql_type(default_type, **kwargs)


@convert_lookup_to_graphql_type.register
def _(_: Literal["contains"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    many = kwargs["many"]
    if many:
        default_type = list.__class_getitem__(default_type)
    return convert_to_graphql_type(default_type, **kwargs)


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
    from undine.scalars import GraphQLDate

    return GraphQLDate


@convert_lookup_to_graphql_type.register
def _(_: Literal["time"], **kwargs: Any) -> GraphQLType:
    from undine.scalars import GraphQLTime

    return GraphQLTime


@convert_lookup_to_graphql_type.register
def _(_: Literal["contained_by", "overlap"], **kwargs: Any) -> GraphQLType:
    default_type = kwargs["default_type"]
    many = kwargs["many"]
    if many:
        default_type = list.__class_getitem__(default_type)
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
) -> GraphQLType:
    return GraphQLBoolean
