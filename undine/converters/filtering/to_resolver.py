from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from undine.resolvers import FunctionResolver
from undine.typing import CombinableExpression, FilterRef, FilterResolverFunc, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "convert_filter_ref_to_filter_resolver",
]


convert_filter_ref_to_filter_resolver = FunctionDispatcher[FilterRef, FilterResolverFunc]()
"""Convert the Undine Filter reference to a Filter resolver function."""


@convert_filter_ref_to_filter_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> FilterResolverFunc:
    return FunctionResolver.adapt(ref)


@convert_filter_ref_to_filter_resolver.register
def _(ref: ModelField, **kwargs: Any) -> FilterResolverFunc:
    lookup_expr: str = kwargs["lookup_expr"]
    lookup = f"{ref.name}{LOOKUP_SEP}{lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))


@convert_filter_ref_to_filter_resolver.register
def _(ref: models.Q, **kwargs: Any) -> FilterResolverFunc:
    return FunctionResolver(lambda value: ref if value else ~ref)


@convert_filter_ref_to_filter_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> FilterResolverFunc:
    # The expression or subquery should be aliased in the queryset to the given name.
    lookup_expr: str = kwargs["lookup_expr"]
    name: str = kwargs["name"]
    lookup = f"{name}{LOOKUP_SEP}{lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))
