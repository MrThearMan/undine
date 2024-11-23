# ruff: noqa: FBT001, FBT002
"""Custom type definitions for the project."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    MutableMapping,
    NewType,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

# Sort separately due to being a private import
from typing import _eval_type  # isort: skip  # noqa: PLC2701


from undine.dataclasses import TypeRef

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from graphql import FieldNode, GraphQLInputType, GraphQLOutputType, GraphQLResolveInfo, SelectionNode

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.sessions.backends.base import SessionBase
    from django.db.models.sql import Query

    from undine import Field, Input, MutationType, QueryType
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.utils.lazy import LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion

__all__ = [
    "CombinableExpression",
    "CombinableExpression",
    "DispatchProtocol",
    "DjangoRequestProtocol",
    "DocstringParserProtocol",
    "EntrypointRef",
    "ExpressionLike",
    "FieldRef",
    "FilterRef",
    "FilterRef",
    "GQLInfo",
    "GraphQLFilterResolver",
    "HttpMethod",
    "InputRef",
    "JsonObject",
    "Lambda",
    "ManagerProtocol",
    "ModelField",
    "MutationKind",
    "OptimizerFunc",
    "OrderRef",
    "QuerySetResolver",
    "RelatedField",
    "RelatedManagerProtocol",
    "Root",
    "Selections",
    "Self",
    "ToManyField",
    "ToOneField",
    "ValidatorFunc",
]


From = TypeVar("From")
To = TypeVar("To")
TModel = TypeVar("TModel", bound=models.Model)
TGraphQLType = TypeVar("TGraphQLType", GraphQLInputType, GraphQLOutputType)

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


class DjangoRequestProtocol(Protocol):
    @property
    def user(self) -> User | AnonymousUser: ...

    @property
    def session(self) -> SessionBase | MutableMapping[str, Any]: ...


class GQLInfoProtocol(Protocol):
    @property
    def context(self) -> DjangoRequestProtocol: ...


class ManagerProtocol(Protocol):  # noqa: PLR0904
    """Represents a manager for a model."""

    def get_queryset(self) -> models.QuerySet: ...

    def iterator(self, chunk_size: int | None = None) -> Iterator[models.Model]: ...

    def aggregate(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    def count(self) -> int: ...

    def get(self, *args: Any, **kwargs: Any) -> models.Model: ...

    def create(self, **kwargs: Any) -> models.Model: ...

    def bulk_create(
        self,
        objs: Iterable[models.Model],
        batch_size: int | None = None,
        ignore_conflicts: bool = False,
        update_conflicts: bool = False,
        update_fields: Collection[str] | None = None,
        unique_fields: Collection[str] | None = None,
    ) -> list[models.Model]: ...

    def bulk_update(
        self,
        objs: Iterable[models.Model],
        fields: Collection[str],
        batch_size: int | None = None,
    ) -> int: ...

    def get_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[models.Model, bool]: ...

    def update_or_create(
        self,
        defaults: Mapping[str, Any] | None = None,
        create_defaults: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple[models.Model, bool]: ...

    def first(self) -> models.Model | None: ...

    def last(self) -> models.Model | None: ...

    def delete(self) -> int: ...

    def update(self, **kwargs: Any) -> int: ...

    def exists(self) -> bool: ...

    def contains(self, obj: models.Model) -> bool: ...

    def values(self, *fields: str, **expressions: Any) -> models.QuerySet: ...

    def values_list(self, *fields: str, flat: bool = False, named: bool = False) -> models.QuerySet: ...

    def none(self) -> models.QuerySet: ...

    def all(self) -> models.QuerySet: ...

    def filter(self, *args: Any, **kwargs: Any) -> models.QuerySet: ...

    def exclude(self, *args: Any, **kwargs: Any) -> models.QuerySet: ...

    def union(self, *other_qs: models.QuerySet, all: bool = False) -> models.QuerySet: ...  # noqa: A002

    def intersection(self, *other_qs: models.QuerySet) -> models.QuerySet: ...

    def difference(self, *other_qs: models.QuerySet) -> models.QuerySet: ...

    def select_related(self, *fields: Any) -> models.QuerySet: ...

    def prefetch_related(self, *lookups: Any) -> models.QuerySet: ...

    def annotate(self, *args: Any, **kwargs: Any) -> models.QuerySet: ...

    def alias(self, *args: Any, **kwargs: Any) -> models.QuerySet: ...

    def order_by(self, *field_names: Any) -> models.QuerySet: ...

    def distinct(self, *field_names: Any) -> models.QuerySet: ...

    def reverse(self) -> models.QuerySet: ...

    def defer(self, *fields: Any) -> models.QuerySet: ...

    def only(self, *fields: Any) -> models.QuerySet: ...

    def using(self, alias: str | None) -> models.QuerySet: ...


class RelatedManagerProtocol(ManagerProtocol):
    """Represents a manager for one-to-many and many-to-many relations."""

    def add(self, *objs: Any, bulk: bool = True) -> int: ...

    def set(
        self,
        objs: Iterable[models.Model],
        *,
        clear: bool = False,
        through_defaults: Any = None,
    ) -> models.QuerySet: ...

    def clear(self) -> None: ...

    def remove(self, obj: Iterable[models.Model], bulk: bool = True) -> models.Model: ...

    def create(self, through_defaults: Any = None, **kwargs: Any) -> models.Model: ...


# Model

ToOneField: TypeAlias = models.OneToOneField | models.OneToOneRel | models.ForeignKey
ToManyField: TypeAlias = models.ManyToManyField | models.ManyToManyRel | models.ManyToOneRel
RelatedField: TypeAlias = ToOneField | ToManyField
ModelField: TypeAlias = models.Field | models.ForeignObjectRel
CombinableExpression: TypeAlias = models.Expression | models.Subquery

# GraphQL

Root: TypeAlias = Any
GQLInfo: TypeAlias = GQLInfoProtocol | GraphQLResolveInfo
GraphQLType: TypeAlias = GraphQLOutputType | GraphQLInputType
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]

# Misc.

TypedDictType: TypeAlias = type(TypedDict(""))
DjangoRequest: TypeAlias = WSGIRequest | DjangoRequestProtocol
MutationKind: TypeAlias = Literal["create", "update", "delete", "custom"]
HttpMethod: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "HEAD"]
JsonObject: TypeAlias = dict[str, Any] | list["JsonObject"]
ValidatorFunc: TypeAlias = Callable[["Input", Any], None]
OptimizerFunc: TypeAlias = Callable[["Field", "QueryOptimizer"], None]
QuerySetResolver: TypeAlias = Callable[..., models.QuerySet | models.Manager | None]
GraphQLFilterResolver: TypeAlias = Callable[..., models.Q]

# Refs

EntrypointRef: TypeAlias = Union[
    type["QueryType"],
    type["MutationType"],
    Callable[..., Any],
]
FieldRef: TypeAlias = Union[
    models.Field,
    models.ForeignObjectRel,
    type["QueryType"],
    "LazyQueryType",
    "LazyQueryTypeUnion",
    "LazyLambdaQueryType",
    models.Expression,
    models.Subquery,
    Callable[..., Any],
]
FilterRef: TypeAlias = Union[
    models.Field,
    models.ForeignObjectRel,
    models.Q,
    models.Expression,
    models.Subquery,
    Callable[..., Any],
]
OrderRef: TypeAlias = Union[
    models.F,
    models.Expression,
    models.Subquery,
]
InputRef: TypeAlias = Union[
    models.Field,
    type["MutationType"],
    TypeRef,
    Callable[..., Any],
]


def eval_type(type_: Any, *, globals_: dict[str, Any] | None = None, locals_: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a type, possibly using the given globals and locals.

    This is a proxy of the 'typing._eval_type' function.
    """
    return _eval_type(type_, globals_ or {}, locals_ or {})  # pragma: no cover
