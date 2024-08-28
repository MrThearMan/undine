from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from undine.typing import FilterFunc, FilterRef
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.resolvers import FieldResolver, function_field_resolver

__all__ = [
    "convert_filter_ref_to_filter_func",
]


convert_filter_ref_to_filter_func = TypeDispatcher[FilterRef, FilterFunc]()


@convert_filter_ref_to_filter_func.register
def _(ref: FunctionType, **kwargs: Any) -> FilterFunc:
    return function_field_resolver(ref)


@convert_filter_ref_to_filter_func.register
def _(ref: models.Field, **kwargs: Any) -> FilterFunc:
    lookup_expr: str = kwargs["lookup_expr"]
    lookup = f"{ref.name}{LOOKUP_SEP}{lookup_expr}"
    return FieldResolver(lambda value: models.Q(**{lookup: value}))  # type: ignore[return-value]


@convert_filter_ref_to_filter_func.register
def _(ref: models.Q, **kwargs: Any) -> FilterFunc:
    return FieldResolver(lambda value: ref if value else ~ref)  # type: ignore[return-value]


@convert_filter_ref_to_filter_func.register
def _(_: models.Expression | models.Subquery, **kwargs: Any) -> FilterFunc:
    # The expression or subquery should be aliased in the queryset to the given name.
    lookup_expr: str = kwargs["lookup_expr"]
    name: str = kwargs["name"]
    lookup = f"{name}{LOOKUP_SEP}{lookup_expr}"
    return FieldResolver(lambda value: models.Q(**{lookup: value}))  # type: ignore[return-value]
