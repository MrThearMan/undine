from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from undine.resolvers import FunctionResolver
from undine.typing import CombinableExpression, FilterRef, FilterResolverFunc, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher

if TYPE_CHECKING:
    from undine import Filter

__all__ = [
    "convert_filter_ref_to_filter_resolver",
]


convert_filter_ref_to_filter_resolver = FunctionDispatcher[FilterRef, FilterResolverFunc]()
"""
Convert the Undine Filter reference to a Filter resolver function.

:param ref: The reference to convert.
:param caller: The 'undine.Filter' instance that is calling this function.
"""


@convert_filter_ref_to_filter_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> FilterResolverFunc:
    return FunctionResolver.adapt(ref)


@convert_filter_ref_to_filter_resolver.register
def _(ref: ModelField, **kwargs: Any) -> FilterResolverFunc:
    caller: Filter = kwargs["caller"]
    lookup = f"{ref.name}{LOOKUP_SEP}{caller.lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))


@convert_filter_ref_to_filter_resolver.register
def _(ref: models.Q, **kwargs: Any) -> FilterResolverFunc:
    return FunctionResolver(lambda value: ref if value else ~ref)


@convert_filter_ref_to_filter_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> FilterResolverFunc:
    # The expression or subquery should be aliased in the queryset to the given name.
    caller: Filter = kwargs["caller"]
    lookup = f"{caller.name}{LOOKUP_SEP}{caller.lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))
