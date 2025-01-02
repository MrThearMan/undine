from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, Generic

from django.db.models import Manager, Model, QuerySet
from graphql import GraphQLID, GraphQLObjectType

from undine.errors.exceptions import (
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
)
from undine.middleware.query import QueryMiddlewareHandler
from undine.optimizer.ast import get_underlying_type
from undine.optimizer.optimizer import QueryOptimizer
from undine.optimizer.prefetch_hack import evaluate_with_prefetch_hack
from undine.relay import Connection, Node, from_global_id, offset_to_cursor, to_global_id
from undine.settings import undine_settings
from undine.typing import ConnectionDict, GQLInfo, NodeDict, PageInfoDict, RelatedManager, TModel
from undine.utils.reflection import get_root_and_info_params

if TYPE_CHECKING:
    from types import FunctionType

    from undine import Field, QueryType

__all__ = [
    "ConnectionResolver",
    "FunctionResolver",
    "FunctionResolver",
    "GlobalIDResolver",
    "ModelFieldResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
    "NestedConnectionResolver",
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "NodeResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionResolver:
    """
    Resolves a GraphQL field using the given function.
    If `field` is provided, its permissions checks will be run before the function during resolver execution.
    """

    func: FunctionType | Callable[..., Any]
    field: Field | None = dataclasses.field(default=None, kw_only=True)
    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if self.field is not None and self.field.permissions_func is not None:
            self.field.permissions_func(self.field, info, root)

        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info
        return self.func(**kwargs)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelFieldResolver:
    """Resolves a model field to a value by attribute access."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        if self.field.permissions_func is not None:
            self.field.permissions_func(self.field, info, root)

        return getattr(root, self.field.model_field_name, None)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleRelatedFieldResolver:
    """Resolves single-related model field to its value."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> Model | None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(self.field, info, root)

        return getattr(root, self.field.model_field_name, None)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyRelatedFieldResolver:
    """Resolves a many-related model field to its queryset."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> QuerySet:
        if self.field.permissions_func is not None:
            self.field.permissions_func(self.field, info, root)

        manager: RelatedManager = getattr(root, self.field.model_field_name)
        return manager.get_queryset()


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeSingleResolver(Generic[TModel]):
    """Top-level resolver for fetching a single model object via a QueryType."""

    query_type: type[QueryType]
    max_complexity: int | None = None

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        middlewares = QueryMiddlewareHandler(root, info, self.query_type)

        @middlewares.wrap
        def getter() -> TModel | None:
            queryset = self.query_type.__get_queryset__(info).filter(**kwargs)
            model = self.query_type.__model__
            optimizer = QueryOptimizer(model=model, info=info, max_complexity=self.max_complexity)
            optimized_queryset = optimizer.optimize(queryset)
            instances = evaluate_with_prefetch_hack(optimized_queryset)
            return next(iter(instances), None)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeManyResolver(Generic[TModel]):
    """Top-level resolver for fetching a set of model objects via a QueryType."""

    query_type: type[QueryType]
    max_complexity: int | None = None

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, self.query_type, many=True)

        @middlewares.wrap
        def getter() -> list[TModel]:
            queryset = self.query_type.__get_queryset__(info)
            model = self.query_type.__model__
            optimizer = QueryOptimizer(model=model, info=info, max_complexity=self.max_complexity)
            optimized_queryset = optimizer.optimize(queryset)
            return evaluate_with_prefetch_hack(optimized_queryset)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeSingleResolver(Generic[TModel]):
    """Resolves a single-related field pointing to another QueryType."""

    query_type: type[QueryType]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> TModel | None:
        middlewares = QueryMiddlewareHandler(root, info, self.query_type, field=self.field)

        @middlewares.wrap
        def getter() -> TModel | None:
            return getattr(root, self.field.model_field_name, None)

        return getter()


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeManyResolver(Generic[TModel]):
    """Resolves a many-related field pointing to another QueryType."""

    query_type: type[QueryType]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, self.query_type, field=self.field, many=True)

        @middlewares.wrap
        def getter() -> list[TModel]:
            field_name = getattr(info.field_nodes[0].alias, "value", self.field.model_field_name)
            result: RelatedManager | list[Model] = getattr(root, field_name)
            if isinstance(result, Manager):
                return list(result.get_queryset())
            return result

        return getter()


# Relay


@dataclasses.dataclass(frozen=True, slots=True)
class GlobalIDResolver:
    """Resolves a model primary key as a Global ID."""

    typename: str

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> str:
        return to_global_id(self.typename, root.pk)


@dataclasses.dataclass(frozen=True, slots=True)
class NodeResolver:
    """Resolves a model instance though a Global ID."""

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        try:
            typename, object_id = from_global_id(kwargs["id"])
        except Exception as error:
            raise GraphQLNodeInvalidGlobalIDError(value=kwargs["id"]) from error

        object_type: GraphQLObjectType | None = info.schema.get_type(typename)
        if object_type is None:
            raise GraphQLNodeObjectTypeMissingError(typename=typename)

        if Node not in object_type.interfaces:
            raise GraphQLNodeInterfaceMissingError(typename=typename)

        query_type: type[QueryType] | None = object_type.extensions.get(undine_settings.QUERY_TYPE_EXTENSIONS_KEY)
        if query_type is None:
            raise GraphQLNodeQueryTypeMissingError(typename=typename)

        field: Field | None = query_type.__field_map__.get("id")
        if field is None:
            raise GraphQLNodeMissingIDFieldError(typename=typename)

        field_type = get_underlying_type(field.get_field_type())
        if field_type is not GraphQLID:
            raise GraphQLNodeIDFieldTypeError(typename=typename)

        resolver = QueryTypeSingleResolver(query_type=query_type)
        return resolver(root, info, pk=object_id)


@dataclasses.dataclass(frozen=True, slots=True)
class ConnectionResolver(Generic[TModel]):
    """Resolves a connection of items."""

    connection: Connection
    max_complexity: int | None = None

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, self.connection.query_type, many=True)

        total_count: int | None = 0
        start: int = 0
        stop: int | None = None

        @middlewares.wrap
        def getter() -> list[TModel]:
            nonlocal total_count, start, stop

            queryset = self.connection.query_type.__get_queryset__(info)
            model = self.connection.query_type.__model__
            optimizer = QueryOptimizer(model=model, info=info, max_complexity=self.max_complexity)
            optimized_queryset = optimizer.optimize(queryset)

            total_count = optimized_queryset._hints.get(undine_settings.CONNECTION_TOTAL_COUNT_KEY, None)
            start = optimized_queryset._hints.get(undine_settings.CONNECTION_START_INDEX_KEY, 0)
            stop = optimized_queryset._hints.get(undine_settings.CONNECTION_STOP_INDEX_KEY, None)

            return evaluate_with_prefetch_hack(optimized_queryset)

        instances = getter()
        typename = self.connection.query_type.__typename__

        edges = [
            NodeDict(
                cursor=offset_to_cursor(typename, start + index),
                node=instance,
            )
            for index, instance in enumerate(instances)
        ]
        return ConnectionDict(
            totalCount=total_count or 0,
            pageInfo=PageInfoDict(
                hasNextPage=(False if stop is None else True if total_count is None else stop < total_count),
                hasPreviousPage=start > 0,
                startCursor=None if not edges else edges[0]["cursor"],
                endCursor=None if not edges else edges[-1]["cursor"],
            ),
            edges=edges,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class NestedConnectionResolver(Generic[TModel]):
    """Resolves a nested connection from the given field."""

    connection: Connection
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        middlewares = QueryMiddlewareHandler(root, info, self.connection.query_type, field=self.field, many=True)

        total_count: int | None = None
        start: int = 0
        stop: int | None = None

        @middlewares.wrap
        def getter() -> list[TModel]:
            field_name = getattr(info.field_nodes[0].alias, "value", self.field.model_field_name)
            result: RelatedManager[TModel] | list[TModel] = getattr(root, field_name)

            if isinstance(result, Manager):
                result = list(result.get_queryset())

            if result:
                nonlocal total_count, start, stop

                total_count = getattr(result[0], undine_settings.CONNECTION_TOTAL_COUNT_KEY, None)
                start = getattr(result[0], undine_settings.CONNECTION_START_INDEX_KEY, 0)
                stop = getattr(result[0], undine_settings.CONNECTION_STOP_INDEX_KEY, None)

            return result

        instances = getter()
        typename = self.connection.query_type.__typename__

        edges = [
            NodeDict(
                cursor=offset_to_cursor(typename, start + index),
                node=instance,
            )
            for index, instance in enumerate(instances)
        ]
        return ConnectionDict(
            totalCount=total_count or 0,
            pageInfo=PageInfoDict(
                hasNextPage=(False if stop is None else True if total_count is None else stop < total_count),
                hasPreviousPage=start > 0,
                startCursor=None if not edges else edges[0]["cursor"],
                endCursor=None if not edges else edges[-1]["cursor"],
            ),
            edges=edges,
        )
