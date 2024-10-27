from __future__ import annotations

from types import FunctionType
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP

from undine.resolvers import FunctionResolver
from undine.typing import CombinableExpression, FilterRef, GraphQLFilterResolver, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher

if TYPE_CHECKING:
    from undine import Filter

__all__ = [
    "convert_filter_ref_to_filter_resolver",
]


convert_filter_ref_to_filter_resolver = FunctionDispatcher[FilterRef, GraphQLFilterResolver]()
"""
Convert the given 'undine.Filter' reference to a filter resolver function.

Positional arguments:
 - ref: The reference to convert.

Keyword arguments:
 - caller: The 'undine.Filter' instance that is calling this function.
"""


@convert_filter_ref_to_filter_resolver.register
def _(ref: FunctionType, **kwargs: Any) -> GraphQLFilterResolver:
    return FunctionResolver.adapt(ref)


@convert_filter_ref_to_filter_resolver.register
def _(ref: ModelField, **kwargs: Any) -> GraphQLFilterResolver:
    caller: Filter = kwargs["caller"]
    lookup = f"{ref.name}{LOOKUP_SEP}{caller.lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))


@convert_filter_ref_to_filter_resolver.register
def _(ref: models.Q, **kwargs: Any) -> GraphQLFilterResolver:
    return FunctionResolver(lambda value: ref if value else ~ref)


@convert_filter_ref_to_filter_resolver.register
def _(_: CombinableExpression, **kwargs: Any) -> GraphQLFilterResolver:
    # The expression or subquery should be aliased in the queryset to the given name.
    caller: Filter = kwargs["caller"]
    lookup = f"{caller.name}{LOOKUP_SEP}{caller.lookup_expr}"
    return FunctionResolver(lambda value: models.Q(**{lookup: value}))


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    @convert_filter_ref_to_filter_resolver.register  # Required for Django<5.1
    def _(ref: GenericForeignKey, **kwargs: Any) -> GraphQLFilterResolver:
        caller: Filter = kwargs["caller"]
        lookup = f"{ref.name}{LOOKUP_SEP}{caller.lookup_expr}"
        return FunctionResolver(lambda value: models.Q(**{lookup: value}))
