from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable

from graphql import Undefined

if TYPE_CHECKING:
    from django.db import models

    from undine import MutationType, QueryType
    from undine.typing import CombinableExpression, GQLInfo, JsonObject

__all__ = [
    "FilterResults",
    "GraphQLFilterInfo",
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


@dataclasses.dataclass(slots=True)
class GraphQLFilterInfo:
    model_type: type[QueryType]
    filters: list[models.Q] = dataclasses.field(default_factory=list)
    distinct: bool = False
    aliases: dict[str, CombinableExpression] = dataclasses.field(default_factory=dict)
    order_by: list[models.OrderBy] = dataclasses.field(default_factory=list)
    children: dict[str, GraphQLFilterInfo] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True, slots=True)
class FilterResults:
    filters: list[models.Q]
    distinct: bool
    aliases: dict[str, CombinableExpression]


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
class MutationMiddlewareParams:
    mutation_type: type[MutationType]
    info: GQLInfo
    input_data: JsonObject
    instance: models.Model | None = None


@dataclasses.dataclass(slots=True)
class PaginationArgs:
    after: int | None
    before: int | None
    first: int | None
    last: int | None
    size: int | None
