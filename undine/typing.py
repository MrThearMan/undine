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
from graphql import FieldNode, GraphQLObjectType, GraphQLResolveInfo, SelectionNode, Undefined

from undine.model_graphql import ModelGQLType

if TYPE_CHECKING:
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
    from django.db.models.sql import Query

    from undine.model_graphql import ModelGQLMutation
    from undine.utils.defer import (
        DeferredModelField,
        DeferredModelGQLMutation,
        DeferredModelGQLType,
        DeferredModelGQLTypeUnion,
    )


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


@dataclass(frozen=True)
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

FieldRef: TypeAlias = Union[
    models.Field,
    FunctionType,
    property,
    type["ModelGQLType"],
    "DeferredModelGQLType",
    "DeferredModelGQLTypeUnion",
    "DeferredModelField",
    Literal["self"],
]
FilterRef: TypeAlias = Union[
    models.Field,
    FunctionType,
    models.Q,
    models.Expression,
    models.Subquery,
    "DeferredModelField",
    Literal["self"],
]
OrderingRef: TypeAlias = Union[
    models.Field,
    models.Expression,
    models.F,
    FunctionType,
    "DeferredModelField",
    Literal["self"],
]
InputRef: TypeAlias = Union[
    models.Field,
    type["ModelGQLMutation"],
    "DeferredModelField",
    "DeferredModelGQLMutation",
    "GenericForeignKey",
    "GenericRelation",
    Literal["self"],
]
EntrypointRef: TypeAlias = Union[
    FunctionType,
    type["ModelGQLType"],
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
Expr: TypeAlias = Union[models.Expression, models.F, models.Q, models.Subquery]
FilterFunc: TypeAlias = Callable[[Root, GraphQLResolveInfo, Any], models.Q]
GetExprFunc: TypeAlias = Callable[[Root, GraphQLResolveInfo], ExpressionKind]
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]
MutationKind: TypeAlias = Literal["create", "update", "delete", "custom"]
MutationOutputType: TypeAlias = type[ModelGQLType] | GraphQLObjectType
JsonType: TypeAlias = dict[str, Any] | list[dict[str, Any]]


@dataclass
class GraphQLFilterInfo:
    model_type: type[ModelGQLType]
    filters: models.Q | None = None
    distinct: bool = False
    aliases: dict[str, models.Expression | models.Subquery] = dataclasses.field(default_factory=dict)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    children: dict[str, GraphQLFilterInfo] = dataclasses.field(default_factory=dict)


@dataclass(frozen=True)
class FilterResults:
    q: models.Q
    distinct: bool
    aliases: dict[str, models.Expression | models.Subquery]


@dataclass(frozen=True)
class OrderingResults:
    order_by: list[models.OrderBy]


@dataclass(frozen=True)
class GraphQLParams:
    query: str
    variables: dict[str, Any] | None
    operation_name: str | None
    extensions: dict[str, Any] | None


TModel = TypeVar("TModel", bound=models.Model)
MutationInputType = JsonType | models.Model | list[models.Model] | None
PostSaveHandler = Callable[[models.Model], Any]
