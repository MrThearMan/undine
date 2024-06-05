from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import TYPE_CHECKING, Any, get_args, get_origin

from django.db.models import F, Field, ManyToManyRel, ManyToOneRel, OneToOneRel
from graphql import GraphQLNonNull, GraphQLType

from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
from undine.typing import CombinableExpression, FieldRef
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.model_utils import get_model_field

if TYPE_CHECKING:
    from undine import Field as UndineField

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
def _(ref: Field, **kwargs: Any) -> bool:
    return getattr(ref, "null", False)


@is_field_nullable.register
def _(_: OneToOneRel, **kwargs: Any) -> bool:
    return True


@is_field_nullable.register
def _(_: ManyToOneRel | ManyToManyRel, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(ref: CombinableExpression, **kwargs: Any) -> bool:
    return is_field_nullable(ref.output_field, **kwargs)


@is_field_nullable.register
def _(_: F, **kwargs: Any) -> bool:
    return True


@is_field_nullable.register
def _(ref: LazyQueryType, **kwargs: Any) -> bool:
    return is_field_nullable(ref.field, **kwargs)


@is_field_nullable.register
def _(_: LazyQueryTypeUnion, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(_: LazyLambdaQueryType, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(ref: TypeRef, **kwargs: Any) -> bool:
    origin = get_origin(ref.value)

    if origin is not UnionType:
        return False

    args = get_args(ref.value)
    return NoneType in args


@is_field_nullable.register
def _(ref: Calculated, **kwargs: Any) -> bool:
    return is_field_nullable(TypeRef(value=ref.return_annotation))


@is_field_nullable.register
def _(ref: GraphQLType, **kwargs: Any) -> bool:
    return not isinstance(ref, GraphQLNonNull)


def load_deferred_converters() -> None:
    # See. `undine.apps.UndineConfig.load_deferred_converters()` for explanation.
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

    from undine import QueryType
    from undine.parsers import parse_return_annotation
    from undine.relay import Connection

    @is_field_nullable.register
    def _(ref: FunctionType, **kwargs: Any) -> bool:
        annotation = parse_return_annotation(ref)
        if not isinstance(annotation, UnionType):
            return False
        return NoneType in get_args(annotation)

    @is_field_nullable.register
    def _(_: type[QueryType], **kwargs: Any) -> bool:
        caller: UndineField = kwargs["caller"]
        field = get_model_field(model=caller.query_type.__model__, lookup=caller.name)
        return is_field_nullable(field, **kwargs)

    @is_field_nullable.register
    def _(_: GenericForeignKey, **kwargs: Any) -> bool:
        return False

    @is_field_nullable.register
    def _(_: GenericRelation, **kwargs: Any) -> bool:
        # Reverse relations are always nullable (Django can't enforce that a
        # foreign key on the related model points to this model).
        return True

    @is_field_nullable.register
    def _(ref: Connection, **kwargs: Any) -> bool:
        return False
