from __future__ import annotations

from types import FunctionType
from typing import Any

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP

from undine import Filter
from undine.converters import convert_to_filter_resolver
from undine.resolvers import FilterFunctionResolver, FilterModelFieldResolver, FilterQExpressionResolver
from undine.typing import CombinableExpression, GraphQLFilterResolver, ModelField


@convert_to_filter_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFilterResolver:
    return FilterFunctionResolver(func=ref)


@convert_to_filter_resolver.register
def _(_: ModelField, **kwargs: Any) -> GraphQLFilterResolver:
    caller: Filter = kwargs["caller"]
    lookup = f"{caller.field_name}{LOOKUP_SEP}{caller.lookup}"
    return FilterModelFieldResolver(lookup=lookup)


@convert_to_filter_resolver.register
def _(ref: Q, **kwargs: Any) -> GraphQLFilterResolver:
    return FilterQExpressionResolver(q_expression=ref)


@convert_to_filter_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> GraphQLFilterResolver:
    # The expression or subquery should be aliased in the queryset.
    caller: Filter = kwargs["caller"]
    lookup = f"{caller.field_name}{LOOKUP_SEP}{caller.lookup}"
    return FilterModelFieldResolver(lookup=lookup)


@convert_to_filter_resolver.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> GraphQLFilterResolver:
    caller: Filter = kwargs["caller"]
    lookup = f"{caller.field_name}{LOOKUP_SEP}{caller.lookup}"
    return FilterModelFieldResolver(lookup=lookup)
