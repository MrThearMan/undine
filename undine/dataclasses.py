from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable

from graphql import Undefined

if TYPE_CHECKING:
    from django.db import models

    from undine import Field, MutationType, QueryType
    from undine.typing import ExpressionLike, GQLInfo, JsonObject

__all__ = [
    "FilterResults",
    "GraphQLParams",
    "LookupRef",
    "MutationMiddlewareParams",
    "OrderResults",
    "PaginationArgs",
    "Parameter",
    "PostSaveData",
    "TypeRef",
]


@dataclasses.dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    annotation: type
    default_value: Any = Undefined


@dataclasses.dataclass(frozen=True, slots=True)
class FilterResults:
    filters: list[models.Q]
    distinct: bool
    aliases: dict[str, ExpressionLike]


@dataclasses.dataclass(frozen=True, slots=True)
class OrderResults:
    order_by: list[models.OrderBy]


@dataclasses.dataclass(frozen=True, slots=True)
class GraphQLParams:
    query: str
    variables: dict[str, Any] | None = None
    operation_name: str | None = None
    extensions: dict[str, Any] | None = None


@dataclasses.dataclass(slots=True)
class PostSaveData:
    post_save_handlers: list[Callable[[models.Model], Any]] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True, slots=True)
class TypeRef:
    value: type


@dataclasses.dataclass(frozen=True, slots=True)
class LookupRef:
    ref: Any
    lookup: str


@dataclasses.dataclass(slots=True)
class QueryMiddlewareParams:
    query_type: type[QueryType]
    info: GQLInfo
    field: Field | None = None
    parent_instance: models.Model | None = None
    instance: models.Model | None = None
    instances: list[models.Model] | None = None


@dataclasses.dataclass(slots=True)
class MutationMiddlewareParams:
    mutation_type: type[MutationType]
    info: GQLInfo
    input_data: JsonObject
    instance: models.Model | None = None  # Single mutations.
    instances: list[models.Model] | None = None  # Bulk mutations.


@dataclasses.dataclass(slots=True)
class PaginationArgs:
    after: int | None
    """The index after which to start (exclusive)."""
    before: int | None
    """The index before which to stop (exclusive)."""
    first: int | None
    """The number of items to return from the start."""
    last: int | None
    """The number of items to return from the end (after evaluating first)."""
    size: int | None
    """The total number of items in the queryset."""
