from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from types import FunctionType, SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Iterable, Protocol, TypeAlias, TypedDict, TypeVar, Union

from django.db import models
from django.db.models import Field, ForeignObjectRel, Manager, Model, Q, QuerySet
from django.db.models.fields.related_descriptors import (
    create_forward_many_to_many_manager,
    create_reverse_many_to_one_manager,
)
from graphql import FieldNode, SelectionNode, Undefined

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.db.models.sql import Query

    from undine.optimizer.optimizer import QueryOptimizer
    from undine.types import DeferredModelGQLType, DeferredModelGQLTypeUnion, ModelGQLType


__all__ = [
    "DispatchProtocol",
    "DispatchWrapper",
    "DocstringParserProtocol",
    "FieldParams",
    "From",
    "ManyToManyManager",
    "OneToManyManager",
    "Parameter",
    "Ref",
    "T",
    "To",
    "ToManyField",
    "ToOneField",
]


T = TypeVar("T")
From = TypeVar("From")
To = TypeVar("To")

Ref: TypeAlias = Union[
    models.Field,  #
    FunctionType,
    property,
    type["ModelGQLType"],
    "DeferredModelGQLType",
    "DeferredModelGQLTypeUnion",
]

ToOneField: TypeAlias = models.OneToOneField | models.OneToOneRel | models.ForeignKey
ToManyField: TypeAlias = models.ManyToManyField | models.ManyToManyRel | models.ManyToOneRel


class FieldParams(TypedDict):
    description: str | None
    deprecation_reason: str | None
    extensions: dict[str, Any] | None
    nullable: bool
    many: bool


@dataclass
class Parameter:
    name: str
    annotation: type
    default_value: Any = Undefined


class DocstringParserProtocol(Protocol):
    @classmethod
    def parse_body(cls, docstring: str) -> str: ...

    @classmethod
    def parse_arg_descriptions(cls, docstring: str) -> dict[str, str]: ...

    @classmethod
    def parse_return_description(cls, docstring: str) -> str: ...

    @classmethod
    def parse_raise_descriptions(cls, docstring: str) -> dict[str, str]: ...

    @classmethod
    def parse_deprecations(cls, docstring: str) -> dict[str, str]: ...


class DispatchProtocol(Protocol[From, To]):
    def __call__(self, key: From, **kwargs: Any) -> To: ...


DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]

_rel_mock = SimpleNamespace(field=SimpleNamespace(null=True))
OneToManyManager: TypeAlias = create_reverse_many_to_one_manager(models.Manager, _rel_mock)
ManyToManyManager: TypeAlias = create_forward_many_to_many_manager(models.Manager, _rel_mock, True)  # noqa: FBT003
RelatedManager: TypeAlias = Union[OneToManyManager, ManyToManyManager]

TModel = TypeVar("TModel", bound=Model)
PK: TypeAlias = Any

ModelField: TypeAlias = Union[Field, ForeignObjectRel, "GenericForeignKey"]

QuerySetResolver: TypeAlias = Callable[..., Union[QuerySet, Manager, None]]
ModelResolver: TypeAlias = Callable[..., Union[Model, None]]
Expr: TypeAlias = Union[models.Expression, models.F, models.Q]


@dataclasses.dataclass
class GraphQLFilterInfo:
    model_type: type[ModelGQLType]
    filters: dict[str, Q] = dataclasses.field(default_factory=dict)
    distinct: bool = False
    children: dict[str, GraphQLFilterInfo] = dataclasses.field(default_factory=dict)


class ExpressionKind(Protocol):
    def resolve_expression(  # noqa: PLR0913
        self,
        query: Query,
        allow_joins: bool,  # noqa: FBT001
        reuse: set[str] | None,
        summarize: bool,  # noqa: FBT001
        for_save: bool,  # noqa: FBT001
    ) -> ExpressionKind: ...


class ManualOptimizerMethod(Protocol):
    def __call__(self, queryset: QuerySet, optimizer: QueryOptimizer, **kwargs: Any) -> QuerySet: ...


Selections = Iterable[SelectionNode | FieldNode]
