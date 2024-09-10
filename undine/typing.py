"""Custom type definitions used by Undine."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from types import FunctionType, SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Literal,
    Protocol,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
    runtime_checkable,
)

# Sort separately due to being a private import
from typing import _eval_type  # isort: skip


try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.db.models.fields.related_descriptors import (
    create_forward_many_to_many_manager,
    create_reverse_many_to_one_manager,
)
from graphql import FieldNode, GraphQLInputType, GraphQLOutputType, GraphQLResolveInfo, SelectionNode, Undefined

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser, User
    from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
    from django.contrib.sessions.backends.base import SessionBase
    from django.db.models.sql import Query

    from undine import ModelGQLMutation, ModelGQLType
    from undine.utils.lazy import LazyModelGQLType, LazyModelGQLTypeUnion

__all__ = [
    "CombinableExpression",
    "CombinableExpression",
    "DispatchProtocol",
    "DispatchWrapper",
    "DjangoRequest",
    "DocstringParserProtocol",
    "EntrypointRef",
    "Expr",
    "ExpressionKind",
    "FieldRef",
    "FilterRef",
    "FilterRef",
    "FilterResolverFunc",
    "FilterResults",
    "GQLInfo",
    "GraphQLFilterInfo",
    "GraphQLParams",
    "InputRef",
    "JsonType",
    "ManyToManyManager",
    "ModelField",
    "MutationInputType",
    "MutationKind",
    "OneToManyManager",
    "OrderingRef",
    "OrderingResults",
    "Parameter",
    "PostSaveHandler",
    "QuerySetResolver",
    "RelatedField",
    "RelatedManager",
    "Root",
    "Selections",
    "Self",
    "T",
    "ToManyField",
    "ToOneField",
]


T = TypeVar("T")
From = TypeVar("From")
To = TypeVar("To")
TModel = TypeVar("TModel", bound=models.Model)
TGraphQLType = TypeVar("TGraphQLType", GraphQLInputType, GraphQLOutputType)

empty = object()

_rel_mock = SimpleNamespace(field=SimpleNamespace(null=True))


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


# Classes purely for type-hinting.


class DjangoRequest(WSGIRequest):
    user: User | AnonymousUser
    session: SessionBase


DjangoRequest: TypeAlias = Union[WSGIRequest, DjangoRequest]


class GQLInfo(GraphQLResolveInfo):
    context: DjangoRequest


GQLInfo: TypeAlias = Union[GQLInfo, GraphQLResolveInfo]


# Dataclasses


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    annotation: type
    default_value: Any = Undefined


@dataclass(slots=True)
class GraphQLFilterInfo:
    model_type: type[ModelGQLType]
    filters: models.Q | None = None
    distinct: bool = False
    aliases: dict[str, CombinableExpression] = dataclasses.field(default_factory=dict)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    children: dict[str, GraphQLFilterInfo] = dataclasses.field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FilterResults:
    q: models.Q
    distinct: bool
    aliases: dict[str, CombinableExpression]


@dataclass(frozen=True, slots=True)
class OrderingResults:
    order_by: list[models.OrderBy]


@dataclass(frozen=True, slots=True)
class GraphQLParams:
    query: str
    variables: dict[str, Any] | None
    operation_name: str | None
    extensions: dict[str, Any] | None


@dataclass(slots=True)
class PostSaveData:
    post_save_handlers: list[Callable[[models.Model], Any]] = dataclasses.field(default_factory=list)
    input_only_data: dict[str, Any] = dataclasses.field(default_factory=dict)


class PaginationArgs(TypedDict):
    after: int | None
    before: int | None
    first: int | None
    last: int | None
    size: int | None


# Model typing

ToOneField: TypeAlias = models.OneToOneField | models.OneToOneRel | models.ForeignKey
ToManyField: TypeAlias = models.ManyToManyField | models.ManyToManyRel | models.ManyToOneRel
RelatedField: TypeAlias = Union[ToOneField, ToManyField, "GenericRelation", "GenericForeignKey"]
ModelField: TypeAlias = Union[models.Field, models.ForeignObjectRel, "GenericForeignKey"]
OneToManyManager: TypeAlias = create_reverse_many_to_one_manager(models.Manager, _rel_mock)
ManyToManyManager: TypeAlias = create_forward_many_to_many_manager(models.Manager, _rel_mock, True)  # noqa: FBT003
RelatedManager: TypeAlias = OneToManyManager | ManyToManyManager
CombinableExpression: TypeAlias = models.Expression | models.Subquery
Expr: TypeAlias = CombinableExpression | models.F | models.Q

# Misc.

Root: TypeAlias = Any
FilterResolverFunc: TypeAlias = Callable[..., models.Q]
QuerySetResolver: TypeAlias = Callable[..., models.QuerySet | models.Manager | None]
Selections: TypeAlias = Iterable[SelectionNode | FieldNode]
MutationKind: TypeAlias = Literal["create", "update", "delete", "custom"]
JsonType: TypeAlias = dict[str, Any] | list[dict[str, Any]]
DispatchWrapper: TypeAlias = Callable[[DispatchProtocol[From, To]], DispatchProtocol[From, To]]
MutationInputType: TypeAlias = JsonType | models.Model | list[models.Model] | None
PostSaveHandler: TypeAlias = Callable[[models.Model], Any]
TypedDictType: TypeAlias = type(TypedDict(""))

# Refs

EntrypointRef: TypeAlias = Union[
    type["ModelGQLType"],
    type["ModelGQLMutation"],
    FunctionType,
]
FieldRef: TypeAlias = Union[
    models.Field,
    models.ForeignObjectRel,
    type["ModelGQLType"],
    "LazyModelGQLType",
    "LazyModelGQLTypeUnion",
    models.Expression,
    models.Subquery,
    FunctionType,
]
FilterRef: TypeAlias = Union[
    models.Field,
    models.ForeignObjectRel,
    models.Q,
    models.Expression,
    models.Subquery,
    FunctionType,
]
OrderingRef: TypeAlias = Union[
    models.F,
    models.Expression,
    models.Subquery,
]
InputRef: TypeAlias = Union[
    models.Field,
    type["ModelGQLMutation"],
]


def eval_type(type_: Any, *, globals_: dict[str, Any] | None = None, locals_: dict[str, Any] | None = None) -> Any:
    """
    Evaluate a type, possibly using the given globals and locals.

    This is a proxy of the 'typing._eval_type' function.
    """
    return _eval_type(type_, globals_ or {}, locals_ or {})
