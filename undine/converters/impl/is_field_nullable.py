from __future__ import annotations

from types import FunctionType, NoneType, UnionType
from typing import Any, get_args, get_origin

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db.models import F, Field, ManyToManyRel, ManyToOneRel, OneToOneRel, Q
from graphql import GraphQLNonNull, GraphQLType

from undine import Calculation, QueryType
from undine import Field as UndineField
from undine.converters import is_field_nullable
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.parsers import parse_return_annotation
from undine.relay import Connection
from undine.typing import CombinableExpression
from undine.utils.model_utils import get_model_field


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
    caller: UndineField = kwargs["caller"]
    field = get_model_field(model=caller.query_type.__model__, lookup=caller.field_name)
    return is_field_nullable(field, **kwargs)


@is_field_nullable.register
def _(_: Q, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(ref: LazyRelation, **kwargs: Any) -> bool:
    return is_field_nullable(ref.field, **kwargs)


@is_field_nullable.register
def _(_: LazyGenericForeignKey, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(ref: TypeRef, **kwargs: Any) -> bool:
    origin = get_origin(ref.value)

    if origin is not UnionType:
        return False

    args = get_args(ref.value)
    return NoneType in args


@is_field_nullable.register
def _(ref: type[Calculation], **kwargs: Any) -> bool:
    return is_field_nullable(TypeRef(value=ref.__returns__))


@is_field_nullable.register
def _(ref: GraphQLType, **kwargs: Any) -> bool:
    return not isinstance(ref, GraphQLNonNull)


@is_field_nullable.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    annotation = parse_return_annotation(ref)
    if not isinstance(annotation, UnionType):
        return False
    return NoneType in get_args(annotation)


@is_field_nullable.register
def _(_: type[QueryType], **kwargs: Any) -> bool:
    caller: UndineField = kwargs["caller"]
    field = get_model_field(model=caller.query_type.__model__, lookup=caller.field_name)
    return is_field_nullable(field, **kwargs)


@is_field_nullable.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> bool:
    return False


@is_field_nullable.register
def _(_: GenericRelation, **kwargs: Any) -> bool:
    # Reverse relations are always nullable (Django can't enforce that a
    # foreign key on the related model points to this model).
    return True


@is_field_nullable.register
def _(_: Connection, **kwargs: Any) -> bool:
    return False
