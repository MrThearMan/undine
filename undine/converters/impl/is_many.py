from __future__ import annotations

from types import FunctionType, GenericAlias
from typing import Any, get_origin

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import F, Q, QuerySet
from graphql import GraphQLList, GraphQLNonNull, GraphQLType

from undine import Calculation, MutationType, QueryType, UnionType
from undine.converters import is_many
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.parsers import parse_return_annotation
from undine.relay import Connection
from undine.typing import CombinableExpression, ModelField
from undine.utils.model_utils import get_model_field


@is_many.register
def _(ref: ModelField, **kwargs: Any) -> bool:
    return bool(ref.many_to_many) or bool(ref.one_to_many)


@is_many.register
def _(ref: TypeRef, **kwargs: Any) -> bool:
    annotation = ref.value
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation)
    return isinstance(annotation, type) and issubclass(annotation, list | set | tuple | QuerySet)


@is_many.register
def _(ref: CombinableExpression, **kwargs: Any) -> bool:
    return is_many(ref.output_field)


@is_many.register
def _(_: F | Q, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(ref: LazyRelation, **kwargs: Any) -> bool:
    return is_many(ref.field)


@is_many.register
def _(_: LazyGenericForeignKey, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(_: LazyLambda, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(ref: type[Calculation], **kwargs: Any) -> bool:
    return is_many(TypeRef(value=ref.__returns__))


@is_many.register
def _(ref: GraphQLType, **kwargs: Any) -> bool:
    return isinstance(ref, GraphQLList) or (isinstance(ref, GraphQLNonNull) and isinstance(ref.of_type, GraphQLList))


@is_many.register
def _(ref: FunctionType, **kwargs: Any) -> bool:
    annotation = parse_return_annotation(ref)
    if isinstance(annotation, GenericAlias):
        annotation = get_origin(annotation)
    return isinstance(annotation, type) and issubclass(annotation, list | set | tuple | QuerySet)


@is_many.register
def _(_: type[QueryType], **kwargs: Any) -> bool:
    field = get_model_field(model=kwargs["model"], lookup=kwargs["name"])
    return is_many(field, **kwargs)


@is_many.register
def _(_: type[MutationType], **kwargs: Any) -> bool:
    field = get_model_field(model=kwargs["model"], lookup=kwargs["name"])
    return is_many(field, **kwargs)


@is_many.register  # Required for Django<5.1
def _(_: GenericForeignKey, **kwargs: Any) -> bool:
    return False


@is_many.register
def _(_: Connection, **kwargs: Any) -> bool:
    # Connection edges have many nodes, but the connection itself is a single node.
    return False


@is_many.register
def _(_: type[UnionType], **kwargs: Any) -> bool:
    # You always want multiple results from a union,
    # otherwise you should know its type beforehand.
    return True
