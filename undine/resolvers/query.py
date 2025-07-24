from __future__ import annotations

import dataclasses
from asyncio import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeAlias

from asgiref.sync import sync_to_async
from django.db.models import Manager, QuerySet
from graphql import GraphQLID, GraphQLObjectType

from undine import QueryType
from undine.dataclasses import OptimizationWithPagination
from undine.exceptions import (
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLNodeTypeNotObjectTypeError,
)
from undine.optimizer.optimizer import optimize_async, optimize_sync
from undine.optimizer.prefetch_hack import evaluate_with_prefetch_hack_async, evaluate_with_prefetch_hack_sync
from undine.relay import Node, from_global_id, offset_to_cursor, to_global_id
from undine.settings import undine_settings
from undine.typing import ConnectionDict, NodeDict, PageInfoDict, TModel
from undine.utils.graphql.undine_extensions import get_undine_query_type
from undine.utils.graphql.utils import get_queried_field_name, get_underlying_type, pre_evaluate_request_user
from undine.utils.reflection import get_root_and_info_params

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from django.db.models import Model, Q
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, Field, InterfaceType, UnionType
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.relay import Connection, PaginationHandler
    from undine.typing import GQLInfo

__all__ = [
    "ConnectionResolver",
    "EntrypointFunctionResolver",
    "FieldFunctionResolver",
    "GlobalIDResolver",
    "InterfaceResolver",
    "ModelAttributeResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
    "NestedConnectionResolver",
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "NodeResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
    "UnionTypeResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class EntrypointFunctionResolver:
    """Resolves an `Entrypoint` using the given function."""

    func: FunctionType | Callable[..., Any]
    entrypoint: Entrypoint

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and iscoroutinefunction(self.func):
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        self.set_kwargs(kwargs, root, info)
        result = await self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    def set_kwargs(self, kwargs: dict[str, Any], root: Any, info: GQLInfo) -> None:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

    def check_permissions(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.entrypoint.permissions_func is not None:
            if self.entrypoint.many:
                for item in result:
                    self.entrypoint.permissions_func(root, info, item)
            else:
                self.entrypoint.permissions_func(root, info, result)


@dataclasses.dataclass(frozen=True, slots=True)
class FieldFunctionResolver:
    """Resolves a `Field` using the given function."""

    func: FunctionType | Callable[..., Any]
    field: Field

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and iscoroutinefunction(self.func):
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = await self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    def set_kwargs(self, kwargs: dict[str, Any], root: Any, info: GQLInfo) -> None:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

    def check_permissions(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.field.permissions_func is not None:
            if self.field.many:
                for item in result:
                    self.field.permissions_func(root, info, item)
            else:
                self.field.permissions_func(root, info, result)


# Model field resolvers


@dataclasses.dataclass(frozen=True, slots=True)
class ModelAttributeResolver:
    """Resolves a model field or annotation to a value by attribute access."""

    field: Field

    static: bool = True
    """
    If the attribute is queried multiple times in the same operation, should it return
    different values, for example, based on input arguments?
    """

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        field_name = self.field.name
        if not self.static:
            field_name = get_queried_field_name(field_name, info)

        value = getattr(root, field_name, None)

        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

        return value


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleRelatedFieldResolver(Generic[TModel]):
    """Resolves single-related model field to its primary key."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> int | None:
        value: TModel | None = getattr(root, self.field.name, None)

        if value is None:
            return None

        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

        return value.pk


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyRelatedFieldResolver(Generic[TModel]):
    """Resolves a many-related model field to a list of their primary keys."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        field_name = get_queried_field_name(self.field.name, info)
        manager: Manager[TModel] = getattr(root, field_name)
        instances = list(manager.get_queryset())

        if self.field.permissions_func is not None:
            for instance in instances:
                self.field.permissions_func(root, info, instance)

        return [instance.pk for instance in instances]


@dataclasses.dataclass(frozen=True, slots=True)
class ModelGenericForeignKeyResolver(Generic[TModel]):
    """Resolves generic foreign key field to its related model instance."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> TModel | None:
        value: TModel | None = getattr(root, self.field.name, None)

        if value is None:
            return None

        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

        return value


# Query type resolvers


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeSingleResolver(Generic[TModel]):
    """Top-level resolver for fetching a single model object via a QueryType."""

    query_type: type[QueryType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        queryset = self.query_type.__get_queryset__(info)
        instance = optimize_sync(queryset, info, **kwargs)

        if instance is not None:
            self.check_permissions(root, info, instance)
        return instance

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = self.query_type.__get_queryset__(info)
        instance = await optimize_async(queryset, info, **kwargs)

        if instance is not None:
            self.check_permissions(root, info, instance)
        return instance

    def check_permissions(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.entrypoint.permissions_func is not None:
            self.entrypoint.permissions_func(root, info, instance)
        else:
            self.query_type.__permissions__(instance, info)


@dataclasses.dataclass(frozen=True, slots=True)
class QueryTypeManyResolver(Generic[TModel]):
    """Top-level resolver for fetching a set of model objects via a QueryType."""

    query_type: type[QueryType[TModel]]
    entrypoint: Entrypoint

    additional_filter: Optional[Q] = None  # noqa: UP045

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset = self.get_queryset(info)
        instances = optimize_sync(queryset, info)
        self.check_permissions(root, info, instances)
        return instances

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = self.get_queryset(info)
        instances = await optimize_async(queryset, info)
        self.check_permissions(root, info, instances)
        return instances

    def get_queryset(self, info: GQLInfo) -> QuerySet[TModel]:
        queryset = self.query_type.__get_queryset__(info)
        if self.additional_filter is not None:
            queryset = queryset.filter(self.additional_filter)
        return queryset

    def check_permissions(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                self.entrypoint.permissions_func(root, info, instance)
            else:
                self.query_type.__permissions__(instance, info)


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeSingleResolver(Generic[TModel]):
    """Resolves a single-related field pointing to another QueryType."""

    query_type: type[QueryType[TModel]]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> TModel | None:
        instance: TModel | None = getattr(root, self.field.name, None)

        if instance is not None:
            if self.field.permissions_func is not None:
                self.field.permissions_func(root, info, instance)
            else:
                self.query_type.__permissions__(instance, info)

        return instance


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeManyResolver(Generic[TModel]):
    """Resolves a many-related field pointing to another QueryType."""

    query_type: type[QueryType[TModel]]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        field_name = get_queried_field_name(self.field.name, info)

        instances: list[TModel] = getattr(root, field_name)
        if isinstance(instances, Manager):
            instances = list(instances.get_queryset())

        for instance in instances:
            if self.field.permissions_func is not None:
                self.field.permissions_func(root, info, instance)
            else:
                self.query_type.__permissions__(instance, info)

        return instances


# Relay


@dataclasses.dataclass(frozen=True, slots=True)
class GlobalIDResolver:
    """Resolves a model primary key as a Global ID."""

    typename: str

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> str:
        return to_global_id(self.typename, root.pk)


@dataclasses.dataclass(frozen=True, slots=True)
class NodeResolver(Generic[TModel]):
    """Resolves a model instance through a Global ID."""

    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        try:
            typename, object_id = from_global_id(kwargs["id"])
        except Exception as error:
            raise GraphQLNodeInvalidGlobalIDError(value=kwargs["id"]) from error

        object_type = info.schema.get_type(typename)
        if object_type is None:
            raise GraphQLNodeObjectTypeMissingError(typename=typename)

        if not isinstance(object_type, GraphQLObjectType):
            raise GraphQLNodeTypeNotObjectTypeError(typename=typename)

        query_type = get_undine_query_type(object_type)
        if query_type is None:
            raise GraphQLNodeQueryTypeMissingError(typename=typename)

        if Node not in query_type.__interfaces__:
            raise GraphQLNodeInterfaceMissingError(typename=typename)

        field: Field | None = query_type.__field_map__.get("id")
        if field is None:
            raise GraphQLNodeMissingIDFieldError(typename=typename)

        field_type = get_underlying_type(field.get_field_type())  # type: ignore[type-var]
        if field_type is not GraphQLID:
            raise GraphQLNodeIDFieldTypeError(typename=typename)

        resolver = QueryTypeSingleResolver(query_type=query_type, entrypoint=self.entrypoint)
        return resolver(root, info, pk=object_id)


@dataclasses.dataclass(frozen=True, slots=True)
class ConnectionResolver(Generic[TModel]):
    """Resolves a connection of items."""

    connection: Connection
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[ConnectionDict[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Any, info: GQLInfo) -> ConnectionDict[TModel]:
        results = self.run_optimizer(info)
        instances = evaluate_with_prefetch_hack_sync(results.queryset)
        self.check_permissions(root, info, instances)
        return self.to_connection(instances, pagination=results.pagination)

    async def run_async(self, root: Any, info: GQLInfo) -> ConnectionDict[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        results = await self.run_optimizer_async(info)
        instances = await evaluate_with_prefetch_hack_async(results.queryset)
        self.check_permissions(root, info, instances)
        return self.to_connection(instances, pagination=results.pagination)

    def get_queryset(self, info: GQLInfo) -> QuerySet[TModel]:
        return self.connection.query_type.__get_queryset__(info)

    def run_optimizer(self, info: GQLInfo) -> OptimizationWithPagination[TModel]:
        queryset = self.get_queryset(info)
        optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=queryset.model, info=info)
        optimizations = optimizer.compile()
        optimized_queryset = optimizations.apply(queryset, info)
        return OptimizationWithPagination(
            queryset=optimized_queryset,
            pagination=optimizations.pagination,  # type: ignore[arg-type]
        )

    async def run_optimizer_async(self, info: GQLInfo) -> OptimizationWithPagination[TModel]:
        queryset = self.get_queryset(info)
        optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=queryset.model, info=info)
        optimizations = optimizer.compile()
        # Applying may call 'queryset.count()'.
        optimized_queryset = await sync_to_async(optimizations.apply)(queryset, info)
        return OptimizationWithPagination(
            queryset=optimized_queryset,
            pagination=optimizations.pagination,  # type: ignore[arg-type]
        )

    def check_permissions(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                self.entrypoint.permissions_func(root, info, instance)
            else:
                self.connection.query_type.__permissions__(instance, info)

    def to_connection(self, instances: list[TModel], pagination: PaginationHandler) -> ConnectionDict[TModel]:
        typename = self.connection.query_type.__schema_name__
        edges = [
            NodeDict(
                cursor=offset_to_cursor(typename, pagination.start + index),
                node=instance,
            )
            for index, instance in enumerate(instances)
        ]
        return ConnectionDict(
            totalCount=pagination.total_count or 0,
            pageInfo=PageInfoDict(
                hasNextPage=(
                    False
                    if pagination.stop is None
                    else True
                    if pagination.total_count is None
                    else pagination.stop < pagination.total_count
                ),
                hasPreviousPage=pagination.start > 0,
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
        field_name = get_queried_field_name(self.field.name, info)
        instances = self.get_instances(root, field_name)
        self.check_permissions(root, info, instances)
        return self.to_connection(instances)

    def get_instances(self, root: Model, field_name: str) -> list[TModel]:
        instances: list[TModel] = getattr(root, field_name)
        if isinstance(instances, Manager):
            instances = list(instances.get_queryset())
        return instances

    def check_permissions(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.field.permissions_func is not None:
                self.field.permissions_func(root, info, instance)
            else:
                self.connection.query_type.__permissions__(instance, info)

    def get_pagination_params(self, instances: list[TModel]) -> tuple[int, int | None, int | None]:
        total_count: int | None = None
        start: int = 0
        stop: int | None = None

        # Not optimal, as we don't know the actual pagination params if there are no results.
        if instances:
            total_count = getattr(instances[0], undine_settings.CONNECTION_TOTAL_COUNT_KEY, None)
            start = getattr(instances[0], undine_settings.CONNECTION_START_INDEX_KEY, 0)
            stop = getattr(instances[0], undine_settings.CONNECTION_STOP_INDEX_KEY, None)

        return start, stop, total_count

    def to_connection(self, instances: list[TModel]) -> ConnectionDict[TModel]:
        start, stop, total_count = self.get_pagination_params(instances)

        typename = self.connection.query_type.__schema_name__
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


# UnionType


QuerySetMap: TypeAlias = dict[type[QueryType[TModel]], QuerySet[TModel]]


@dataclasses.dataclass(frozen=True, slots=True)
class UnionTypeResolver(Generic[TModel]):
    """Top-level resolver for fetching a set of model objects from a `UnionType`."""

    union_type: type[UnionType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        all_instances = self.fetch_instances(root, info, queryset_map)
        return self.union_type.__process_results__(all_instances, info)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        all_instances = await self.fetch_instances_async(root, info, queryset_map)
        return self.union_type.__process_results__(all_instances, info)

    def fetch_instances(self, root: Any, info: GQLInfo, queryset_map: QuerySetMap[TModel]) -> list[TModel]:
        all_instances: list[TModel] = []

        for query_type, queryset in queryset_map.items():
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(root, info, query_type, instances)
            all_instances.extend(instances)

        return all_instances

    async def fetch_instances_async(self, root: Any, info: GQLInfo, queryset_map: QuerySetMap[TModel]) -> list[TModel]:
        all_instances: list[TModel] = []

        for query_type, queryset in queryset_map.items():
            instances = await evaluate_with_prefetch_hack_async(queryset)
            self.check_permissions(root, info, query_type, instances)
            all_instances.extend(instances)

        return all_instances

    def check_permissions(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                self.entrypoint.permissions_func(root, info, instance)
            else:
                query_type.__permissions__(instance, info)

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMap[TModel]:
        queryset_map: QuerySetMap[TModel] = {}

        for model, query_type in self.union_type.__query_types_by_model__.items():
            optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=model, info=info)
            optimizations = optimizer.compile()

            # If nothing is selected from this union type member, don't fetch anything from it
            if not optimizations:
                continue

            args: dict[str, Any] = {}
            filter_key = f"{undine_settings.QUERY_TYPE_FILTER_INPUT_KEY}{model.__name__}"
            order_by_key = f"{undine_settings.QUERY_TYPE_ORDER_INPUT_KEY}{model.__name__}"

            if filter_key in kwargs:
                args[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY] = kwargs[filter_key]
            if order_by_key in kwargs:
                args[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY] = kwargs[order_by_key]

            optimizer.handle_undine_query_type(query_type, args)

            queryset = query_type.__get_queryset__(info)
            optimized_queryset = optimizations.apply(queryset, info)

            queryset_map[query_type] = optimized_queryset[: self.entrypoint.limit]

        return queryset_map


@dataclasses.dataclass(frozen=True, slots=True)
class _UnionTypeConnectionResolver:  # TODO: Implement
    """Resolves a connection of union type items."""

    connection: Connection
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[Model]:
        msg = "Union connections are not implemented yet."
        raise NotImplementedError(msg)


# InterfaceType


@dataclasses.dataclass(frozen=True, slots=True)
class InterfaceResolver(Generic[TModel]):
    """Resolves an interface type to all of its implementations."""

    interface: type[InterfaceType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_sync_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        all_instances = self.fetch_instances(info, root, queryset_map)
        return self.interface.__process_results__(all_instances, info)

    async def run_sync_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        all_instances = await self.fetch_instances_async(info, root, queryset_map)
        return self.interface.__process_results__(all_instances, info)

    def fetch_instances(self, info: GQLInfo, root: Any, queryset_map: QuerySetMap[TModel]) -> list[TModel]:
        all_instances: list[TModel] = []

        for query_type, queryset in queryset_map.items():
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(info, root, query_type, instances)
            all_instances.extend(instances)

        return all_instances

    async def fetch_instances_async(self, info: GQLInfo, root: Any, queryset_map: QuerySetMap[TModel]) -> list[TModel]:
        all_instances: list[TModel] = []

        for query_type, queryset in queryset_map.items():
            instances = await evaluate_with_prefetch_hack_async(queryset)
            self.check_permissions(info, root, query_type, instances)
            all_instances.extend(instances)

        return all_instances

    def check_permissions(
        self,
        info: GQLInfo,
        root: Any,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                self.entrypoint.permissions_func(root, info, instance)
            else:
                query_type.__permissions__(instance, info)

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMap[TModel]:
        queryset_map: QuerySetMap[TModel] = {}

        for query_type in self.interface.__concrete_implementations__():
            model = query_type.__model__
            optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=model, info=info)
            optimizations = optimizer.compile()

            # If nothing is selected from this interface implementation, don't fetch anything from it
            if not optimizations:
                continue

            args: dict[str, Any] = {}
            filter_key = f"{undine_settings.QUERY_TYPE_FILTER_INPUT_KEY}{model.__name__}"
            order_by_key = f"{undine_settings.QUERY_TYPE_ORDER_INPUT_KEY}{model.__name__}"

            if filter_key in kwargs:
                args[undine_settings.QUERY_TYPE_FILTER_INPUT_KEY] = kwargs[filter_key]
            if order_by_key in kwargs:
                args[undine_settings.QUERY_TYPE_ORDER_INPUT_KEY] = kwargs[order_by_key]

            optimizer.handle_undine_query_type(query_type, args)

            queryset = query_type.__get_queryset__(info)
            optimized_queryset = optimizations.apply(queryset, info)

            queryset_map[query_type] = optimized_queryset[: self.entrypoint.limit]

        return queryset_map


@dataclasses.dataclass(frozen=True, slots=True)
class _InterfaceConnectionResolver:  # TODO: Implement
    """Resolves a connection of interface type items."""

    connection: Connection
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[Model]:
        msg = "Interface connections are not implemented yet."
        raise NotImplementedError(msg)
