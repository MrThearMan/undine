from __future__ import annotations

from types import FunctionType
from typing import Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from undine.typing import FilterFunc, FilterRef
from undine.utils import TypeDispatcher, function_field_resolver
from undine.utils.resolvers import FieldResolver

__all__ = [
    "convert_filter_ref_to_filter_func",
]


convert_filter_ref_to_filter_func = TypeDispatcher[FilterRef, FilterFunc]()


@convert_filter_ref_to_filter_func.register
def _(ref: FunctionType, **kwargs: Any) -> FilterFunc:
    return function_field_resolver(ref)


@convert_filter_ref_to_filter_func.register
def _(ref: models.Field, *, lookup_expr: str, name: str) -> FilterFunc:
    lookup = f"{ref.name}{LOOKUP_SEP}{lookup_expr}"
    return FieldResolver(lambda value: models.Q(**{lookup: value}))  # type: ignore[return-value]


@convert_filter_ref_to_filter_func.register
def _(ref: models.Q, **kwargs: Any) -> FilterFunc:
    return FieldResolver(lambda value: ref if value else ~ref)  # type: ignore[return-value]


@convert_filter_ref_to_filter_func.register
def _(_: models.Expression | models.Subquery, *, lookup_expr: str, name: str) -> FilterFunc:
    # The expression or subquery should be aliased in the queryset to the given name.
    lookup = f"{name}{LOOKUP_SEP}{lookup_expr}"
    return FieldResolver(lambda value: models.Q(**{lookup: value}))  # type: ignore[return-value]
