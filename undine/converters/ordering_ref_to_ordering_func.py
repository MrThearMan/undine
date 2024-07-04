from __future__ import annotations

from types import FunctionType

from django.db import models

from undine.typing import GetExprFunc, OrderingRef
from undine.utils import TypeDispatcher, function_field_resolver
from undine.utils.resolvers import FieldResolver

__all__ = [
    "convert_ordering_ref_to_ordering_func",
]


convert_ordering_ref_to_ordering_func = TypeDispatcher[OrderingRef, GetExprFunc]()


@convert_ordering_ref_to_ordering_func.register
def _(ref: FunctionType) -> GetExprFunc:
    return function_field_resolver(ref)


@convert_ordering_ref_to_ordering_func.register
def _(ref: models.Expression | models.F) -> GetExprFunc:
    return FieldResolver(lambda: ref)


@convert_ordering_ref_to_ordering_func.register
def _(ref: models.Field) -> GetExprFunc:
    return FieldResolver(lambda: models.F(ref.name))
