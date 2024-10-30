from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import TYPE_CHECKING, Any, get_args

from django.db import models

from undine.typing import CombinableExpression, FieldRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Field

__all__ = [
    "is_field_nullable",
]


is_field_nullable = FunctionDispatcher[FieldRef, bool]()
"""
Determine whether the 'undine.Field' reference indicates a nullable input.

Positional arguments:
 - ref: The reference to check.

Keyword arguments:
 - caller: The 'undine.Field' instance that is calling this function.
"""


@is_field_nullable.register
def _(ref: models.Field, **kwargs: Any) -> bool:
    return getattr(ref, "null", False)


@is_field_nullable.register
def _(_: models.OneToOneRel, **kwargs: Any) -> bool:
    return True


@is_field_nullable.register
def _(_: models.ManyToOneRel | models.ManyToManyRel, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(ref: CombinableExpression, **kwargs: Any) -> bool:
    return is_field_nullable(ref.output_field, **kwargs)


@is_field_nullable.register
def _(ref: LazyQueryType, **kwargs: Any) -> bool:
    return is_field_nullable(ref.field, **kwargs)


@is_field_nullable.register
def _(_: LazyQueryTypeUnion, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(_: LazyLambdaQueryType, **kwargs: Any) -> bool:
    return False


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine import QueryType
    from undine.parsers import parse_return_annotation

    @is_field_nullable.register
    def _(ref: FunctionType, **kwargs: Any) -> bool:
        annotation = parse_return_annotation(ref)
        if not isinstance(annotation, UnionType):
            return False
        return NoneType in get_args(annotation)

    @is_field_nullable.register
    def _(_: type[QueryType], **kwargs: Any) -> bool:
        caller: Field = kwargs["caller"]
        field = get_model_field(model=caller.owner.__model__, lookup=caller.name)
        return is_field_nullable(field, **kwargs)

    @is_field_nullable.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        return False

    @is_field_nullable.register
    def _(_: GenericRelation, **kwargs: Any) -> bool:
        # Reverse relations are always nullable (Django can't enforce that a
        # foreign key on the related model points to this model).
        return True
