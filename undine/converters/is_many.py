from __future__ import annotations

from types import FunctionType, GenericAlias
from typing import Any, get_origin

from undine.dataclasses import TypeRef
from undine.typing import CombinableExpression, ModelField
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_utils import get_model_field

__all__ = [
    "is_many",
]


is_many = FunctionDispatcher[Any, bool]()
"""
Determine whether a reference returns a list of objects or not.

Positional arguments:
 - ref: The reference to look at.

Keyword arguments:
 - model: The model to use for the type.
 - name: The name of the field to check.
"""


@is_many.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    return bool(ref.many_to_many) or bool(ref.one_to_many)


@is_many.register
def _(ref: TypeRef, **kwargs: Any) -> bool:
    annotation = ref.value
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation)
    return isinstance(annotation, type) and issubclass(annotation, list)


@is_many.register
def _(ref: CombinableExpression, **kwargs: Any) -> bool:
    return is_many(ref.output_field)


@is_many.register
def _(ref: LazyQueryType, **kwargs: Any) -> bool:
    return is_many(ref.field)


@is_many.register
def _(_: LazyQueryTypeUnion, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(_: LazyLambdaQueryType, **kwargs: Any) -> bool:
    return False


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey

    from undine import MutationType, QueryType
    from undine.parsers import parse_return_annotation

    @is_many.register
    def _(ref: FunctionType, **kwargs: Any) -> bool:
        annotation = parse_return_annotation(ref)
        if isinstance(annotation, GenericAlias):
            annotation = get_origin(annotation)
        return isinstance(annotation, type) and issubclass(annotation, list)

    @is_many.register
    def _(_: type[QueryType], **kwargs: Any) -> bool:
        field = get_model_field(model=kwargs["model"], lookup=kwargs["name"])
        return is_many(field, **kwargs)

    @is_many.register
    def _(_: type[MutationType], **kwargs: Any) -> bool:
        field = get_model_field(model=kwargs["model"], lookup=kwargs["name"])
        return is_many(field, **kwargs)

    @is_many.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        return False
