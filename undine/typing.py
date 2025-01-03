# ruff: noqa: FBT001, FBT002
"""Custom type definitions for the project."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping, MutableMapping
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Literal,
    NewType,
    Protocol,
    Self,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

# Sort separately due to being a private import
from typing import _eval_type  # isort: skip  # noqa: PLC2701
from typing import _GenericAlias  # isort: skip  # noqa: PLC2701
from typing import _TypedDictMeta  # isort: skip  # noqa: PLC2701

from django.core.handlers.wsgi import WSGIRequest
from django.db.models import (
    Expression,
    F,
    Field,
    ForeignKey,
    ForeignObjectRel,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneField,
    OneToOneRel,
    Q,
    QuerySet,
    Subquery,
)
from graphql import FieldNode, GraphQLInputType, GraphQLOutputType, GraphQLResolveInfo, GraphQLType, SelectionNode

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRel, GenericRelation
    from django.contrib.sessions.backends.base import SessionBase
    from django.db.models.sql import Query

    from undine import Field as UndineField
    from undine import Input, MutationType, QueryType
    from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
    from undine.optimizer.optimizer import OptimizationData
    from undine.relay import Connection, Node

__all__ = [
    "CalculationResolver",
    "CombinableExpression",
    "ConnectionDict",
    "DispatchCategory",
    "DispatchProtocol",
    "DispatchWrapper",
    "DjangoRequestProtocol",
    "DocstringParserProtocol",
    "EntrypointRef",
    "ExpressionLike",
    "FieldPermFunc",
    "FieldRef",
    "FilterRef",
    "GQLInfo",
    "GraphQLFilterResolver",
    "HttpMethod",
    "InputPermFunc",
    "InputRef",
    "JsonObject",
    "Lambda",
    "LiteralArg",
    "ModelField",
    "ModelManager",
    "MutationKind",
    "NodeDict",
    "OptimizerFunc",
    "OrderRef",
    "PageInfoDict",
    "ParametrizedType",
    "RelatedField",
    "RelatedManager",
    "Root",
    "Selections",
    "Self",
    "ToManyField",
    "ToOneField",
    "ValidatorFunc",
]

# Misc.

TypedDictType: TypeAlias = _TypedDictMeta
ParametrizedType: TypeAlias = _GenericAlias
JsonObject: TypeAlias = dict[str, Any] | list["JsonObject"]
PrefetchHackCacheType: TypeAlias = defaultdict[str, defaultdict[str, set[str]]]
LiteralArg: TypeAlias = str | int | bytes | bool | Enum | None

# TypeVars

From = TypeVar("From")
To = TypeVar("To")
TModel = TypeVar("TModel", bound=Model)
TGraphQLType = TypeVar("TGraphQLType", GraphQLInputType, GraphQLOutputType)
TTypedDict = TypeVar("TTypedDict", bound=TypedDictType)

# Literals

MutationKind: TypeAlias = Literal["create", "update", "delete", "custom"]
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"]
DispatchCategory: TypeAlias = Literal["types", "instances", "literals", "protocols"]

# NewTypes

Lambda = NewType("Lambda", Callable)
"""
Type used to regiser a different implementations for lambda functions
as opposed to a regular function in the FunctionDispatcher.
"""

empty = object()


# Protocols


@runtime_checkable
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


class ExpressionLike(Protocol):
    def resolve_expression(
        self,
        query: Query,
        allow_joins: bool,
        reuse: set[str] | None,
        summarize: bool,
        for_save: bool,
    ) -> ExpressionLike: ...


class DispatchProtocol(Protocol[From, To]):
    def __call__(self, key: From, **kwargs: Any) -> To: ...


DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]


class DjangoRequestProtocol(Protocol):
    @property
    def user(self) -> User | AnonymousUser: ...

    @property
    def session(self) -> SessionBase | MutableMapping[str, Any]: ...


class GQLInfoProtocol(Protocol):
    @property
    def context(self) -> DjangoRequestProtocol: ...


class ModelManager(Protocol[TModel]):  # noqa: PLR0904
    """Represents a manager for a model."""

    def get_queryset(self) -> QuerySet[TModel]: ...

    def iterator(self, chunk_size: int | None = None) -> Iterator[TModel]: ...

    def aggregate(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def count(self) -> int: ...

    def get(self, *args: Any, **kwargs: Any) -> TModel: ...

    def create(self, **kwargs: Any) -> TModel: ...

    def bulk_create(
        self,
        objs: Iterable[TModel],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
        update_conflicts: bool = False,
        update_fields: Collection[str] | None = None,
        unique_fields: Collection[str] | None = None,
    ) -> list[TModel]: ...

    def bulk_update(
        self,
        objs: Iterable[TModel],
        fields: Collection[str],
        batch_size: int | None = None,
    ) -> int: ...

    def get_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[TModel, bool]: ...

    def update_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        create_defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[TModel, bool]: ...

    def first(self) -> TModel | None: ...

    def last(self) -> TModel | None: ...

    def delete(self) -> int: ...

    def update(self, **kwargs: Any) -> int: ...

    def exists(self) -> bool: ...

    def contains(self, obj: TModel) -> bool: ...

    def values(self, *fields: str, **expressions: Any) -> QuerySet[TModel]: ...

    def values_list(self, *fields: str, flat: bool = False, named: bool = False) -> QuerySet[TModel]: ...

    def none(self) -> QuerySet[TModel]: ...

    def all(self) -> QuerySet[TModel]: ...

    def filter(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def exclude(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def union(self, *other_qs: QuerySet[TModel], all: bool = False) -> QuerySet[TModel]: ...  # noqa: A002

    def intersection(self, *other_qs: QuerySet[TModel]) -> QuerySet[TModel]: ...

    def difference(self, *other_qs: QuerySet[TModel]) -> QuerySet[TModel]: ...

    def select_related(self, *fields: Any) -> QuerySet[TModel]: ...

    def prefetch_related(self, *lookups: Any) -> QuerySet[TModel]: ...

    def annotate(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def alias(self, *args: Any, **kwargs: Any) -> QuerySet[TModel]: ...

    def order_by(self, *field_names: Any) -> QuerySet[TModel]: ...

    def distinct(self, *field_names: Any) -> QuerySet[TModel]: ...

    def reverse(self) -> QuerySet[TModel]: ...

    def defer(self, *fields: Any) -> QuerySet[TModel]: ...

    def only(self, *fields: Any) -> QuerySet[TModel]: ...

    def using(self, alias: str | None) -> QuerySet[TModel]: ...


class RelatedManager(ModelManager[TModel]):
    """Represents a manager for one-to-many and many-to-many relations."""

    def add(self, *objs: TModel, bulk: bool = True) -> int: ...

    def set(
        self,
        objs: Iterable[TModel],
        *,
        clear: bool = False,
        through_defaults: Any = None,
    ) -> QuerySet[TModel]: ...

    def clear(self) -> None: ...

    def remove(self, obj: Iterable[TModel], bulk: bool = True) -> TModel: ...

    def create(self, through_defaults: Any = None, **kwargs: Any) -> TModel: ...


# Model

ToOneField: TypeAlias = OneToOneField | OneToOneRel | ForeignKey
ToManyField: TypeAlias = ManyToManyField | ManyToManyRel | ManyToOneRel
RelatedField: TypeAlias = ToOneField | ToManyField
GenericField: TypeAlias = Union["GenericForeignKey", "GenericRelation", "GenericRel"]
ModelField: TypeAlias = Field | ForeignObjectRel
CombinableExpression: TypeAlias = Expression | Subquery
QueryResult: TypeAlias = Model | list[Model] | None
MutationResult: TypeAlias = Model | list[Model] | None
DjangoRequest: TypeAlias = WSGIRequest | DjangoRequestProtocol

# GraphQL

Root: TypeAlias = Any
GQLInfo: TypeAlias = GQLInfoProtocol | GraphQLResolveInfo
GraphQLInputOutputType: TypeAlias = GraphQLOutputType | GraphQLInputType
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]
GraphQLIOType: TypeAlias = GraphQLInputType | GraphQLOutputType


class NodeDict(Generic[TModel], TypedDict):
    cursor: str
    node: TModel


class PageInfoDict(TypedDict):
    hasNextPage: bool
    hasPreviousPage: bool
    startCursor: str | None
    endCursor: str | None


class ConnectionDict(Generic[TModel], TypedDict):
    totalCount: int
    pageInfo: PageInfoDict
    edges: list[NodeDict[TModel]]


# Resolvers

ValidatorFunc: TypeAlias = Callable[["Input", GQLInfo, Any], None]
OptimizerFunc: TypeAlias = Callable[["UndineField", "OptimizationData"], None]
FieldPermFunc: TypeAlias = Callable[["UndineField", GQLInfo, Model], None]
InputPermFunc: TypeAlias = Callable[["Input", GQLInfo, Any], None]

GraphQLFilterResolver: TypeAlias = Callable[..., Q]
"""(self: Model, info: GQLInfo, **kwargs: Any) -> Q"""

CalculationResolver: TypeAlias = Callable[..., QuerySet]
"""(self: Field, queryset: QuerySet, info: GQLInfo, **kwargs: Any) -> QuerySet"""

# Callbacks

QuerySetCallback: TypeAlias = Callable[[GQLInfo], QuerySet]
FilterCallback: TypeAlias = Callable[[QuerySet, GQLInfo], QuerySet]

# Refs

EntrypointRef: TypeAlias = Union[
    type["QueryType"],
    type["MutationType"],
    "Node",
    "Connection",
    Callable[..., Any],
]
FieldRef: TypeAlias = Union[
    Field,
    ForeignObjectRel,
    type["QueryType"],
    "LazyQueryType",
    "LazyQueryTypeUnion",
    "LazyLambdaQueryType",
    Expression,
    Subquery,
    GraphQLType,
    "TypeRef",
    "Connection",
    "Calculated",
    Callable[..., Any],
]
FilterRef: TypeAlias = Union[
    Field,
    ForeignObjectRel,
    Q,
    Expression,
    Subquery,
    Callable[..., Any],
]
OrderRef: TypeAlias = Union[
    F,
    Expression,
    Subquery,
]
InputRef: TypeAlias = Union[
    Field,
    type["MutationType"],
    "TypeRef",
    Callable[..., Any],
]


def eval_type(type_: Any, *, globals_: dict[str, Any] | None = None, locals_: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a type, possibly using the given globals and locals.

    This is a proxy of the 'typing._eval_type' function.
    """
    return _eval_type(type_, globals_ or {}, locals_ or {})  # pragma: no cover
