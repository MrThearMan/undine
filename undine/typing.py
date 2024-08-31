from __future__ import annotations

import dataclasses
import typing
from dataclasses import dataclass
from types import FunctionType, SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, Protocol, TypeAlias, TypedDict, TypeVar, Union

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from django.db import models
from django.db.models import Field, ForeignObjectRel, Manager, Model, QuerySet
from django.db.models.fields.related_descriptors import (
    create_forward_many_to_many_manager,
    create_reverse_many_to_one_manager,
)
from graphql import FieldNode, GraphQLResolveInfo, SelectionNode, Undefined

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
    from django.db.models.sql import Query

    from undine import ModelGQLMutation, ModelGQLType
    from undine.utils.defer import DeferredModelGQLType, DeferredModelGQLTypeUnion


__all__ = [
    "DispatchProtocol",
    "DispatchWrapper",
    "DocstringParserProtocol",
    "FieldParams",
    "FieldRef",
    "From",
    "ManyToManyManager",
    "OneToManyManager",
    "Parameter",
    "Self",
    "T",
    "To",
    "ToManyField",
    "ToOneField",
]


T = TypeVar("T")
From = TypeVar("From")
To = TypeVar("To")


class FieldParams(TypedDict):
    description: str | None
    deprecation_reason: str | None
    extensions: dict[str, Any] | None
    nullable: bool
    many: bool


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    annotation: type
    default_value: Any = Undefined


@typing.runtime_checkable
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


class ExpressionKind(Protocol):
    def resolve_expression(  # noqa: PLR0913
        self,
        query: Query,
        allow_joins: bool,  # noqa: FBT001
        reuse: set[str] | None,
        summarize: bool,  # noqa: FBT001
        for_save: bool,  # noqa: FBT001
    ) -> ExpressionKind: ...


class DispatchProtocol(Protocol[From, To]):
    def __call__(self, key: From, **kwargs: Any) -> To: ...


DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]

_rel_mock = SimpleNamespace(field=SimpleNamespace(null=True))
OneToManyManager: TypeAlias = create_reverse_many_to_one_manager(models.Manager, _rel_mock)
ManyToManyManager: TypeAlias = create_forward_many_to_many_manager(models.Manager, _rel_mock, True)  # noqa: FBT003
RelatedManager: TypeAlias = Union[OneToManyManager, ManyToManyManager]

EntrypointRef: TypeAlias = Union[
    type["ModelGQLType"],
    type["ModelGQLMutation"],
    FunctionType,
]
FieldRef: TypeAlias = Union[
    models.Field,
    type["ModelGQLType"],
    "DeferredModelGQLType",
    "DeferredModelGQLTypeUnion",
    models.Expression,
    models.Subquery,
    FunctionType,
]
FilterRef: TypeAlias = Union[
    models.Field,
    models.Q,
    models.Expression,
    models.Subquery,
    FunctionType,
]
OrderingRef: TypeAlias = Union[
    models.F,
    models.Expression,
]
InputRef: TypeAlias = Union[
    models.Field,
    type["ModelGQLMutation"],
]

Ref: TypeAlias = FieldRef | FilterRef | OrderingRef | InputRef

Root: TypeAlias = Any
ToOneField: TypeAlias = models.OneToOneField | models.OneToOneRel | models.ForeignKey
ToManyField: TypeAlias = models.ManyToManyField | models.ManyToManyRel | models.ManyToOneRel
RelatedField: TypeAlias = Union[ToOneField, ToManyField, "GenericRelation", "GenericForeignKey"]
ModelField: TypeAlias = Union[Field, ForeignObjectRel, "GenericForeignKey"]
QuerySetResolver: TypeAlias = Callable[..., Union[QuerySet, Manager, None]]
ModelResolver: TypeAlias = Callable[..., Union[Model, None]]
MutationResolver: TypeAlias = Callable[[Root, GraphQLResolveInfo, dict[str, Any]], Model]
Expr: TypeAlias = Union[models.Expression, models.F, models.Q, models.Subquery]
FilterFunc: TypeAlias = Callable[[Root, GraphQLResolveInfo, Any], models.Q]
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]
MutationKind: TypeAlias = Literal["create", "update", "delete", "custom"]
JsonType: TypeAlias = dict[str, Any] | list[dict[str, Any]]


@dataclass
class GraphQLFilterInfo:
    model_type: type[ModelGQLType]
    filters: models.Q | None = None
    distinct: bool = False
    aliases: dict[str, models.Expression | models.Subquery] = dataclasses.field(default_factory=dict)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    children: dict[str, GraphQLFilterInfo] = dataclasses.field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FilterResults:
    q: models.Q
    distinct: bool
    aliases: dict[str, models.Expression | models.Subquery]


@dataclass(frozen=True, slots=True)
class OrderingResults:
    order_by: list[models.OrderBy]


@dataclass(frozen=True, slots=True)
class GraphQLParams:
    query: str
    variables: dict[str, Any] | None
    operation_name: str | None
    extensions: dict[str, Any] | None


empty = object()

TModel = TypeVar("TModel", bound=models.Model)
MutationInputType = JsonType | models.Model | list[models.Model] | None
PostSaveHandler = Callable[[models.Model], Any]
