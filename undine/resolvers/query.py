from __future__ import annotations

import dataclasses
import inspect
import uuid
from asyncio import iscoroutinefunction
from collections import defaultdict
from itertools import count
from typing import TYPE_CHECKING, Any, Generic, Optional

from asgiref.sync import sync_to_async
from django.db.models import Q, Value
from django.db.models.manager import BaseManager
from graphql import GraphQLID, GraphQLObjectType

from undine import QueryType
from undine.dataclasses import OptimizationWithPagination, QuerySetMapWithPagination
from undine.exceptions import (
    GraphQLFieldNotNullableError,
    GraphQLModelNotFoundError,
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
from undine.utils.graphql.utils import (
    get_arguments,
    get_queried_field_name,
    get_underlying_type,
    pre_evaluate_request_user,
)
from undine.utils.model_utils import create_union_queryset
from undine.utils.reflection import get_root_and_info_params, is_subclass

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable
    from types import FunctionType

    from django.db.models import Model, QuerySet
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, Field, InterfaceType, UnionType
    from undine.dataclasses import FilterResults, OrderResults
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.relay import Connection, PaginationHandler
    from undine.typing import GQLInfo, QuerySetMap

__all__ = [
    "ConnectionResolver",
    "EntrypointFunctionResolver",
    "FieldFunctionResolver",
    "GlobalIDResolver",
    "InterfaceResolver",
    "ModelAttributeResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
    "NamedTupleFieldResolver",
    "NestedConnectionResolver",
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "NodeResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
    "TypedDictFieldResolver",
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
        await self.check_permissions_async(root, info, result)
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

        elif is_subclass(self.entrypoint.ref, QueryType):
            self.entrypoint.ref.__permissions__(result, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.entrypoint.permissions_func is not None:
            if self.entrypoint.many:
                for item in result:
                    if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                        await self.entrypoint.permissions_func(root, info, item)
                    else:
                        self.entrypoint.permissions_func(root, info, item)

            elif inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, result)

            else:
                self.entrypoint.permissions_func(root, info, result)

        elif is_subclass(self.entrypoint.ref, QueryType):
            if inspect.iscoroutinefunction(self.entrypoint.ref.__permissions__):
                await self.entrypoint.ref.__permissions__(result, info)
            else:
                self.entrypoint.ref.__permissions__(result, info)


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
        await self.check_permissions_async(root, info, result)
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

        elif is_subclass(self.field.ref, QueryType):
            self.field.ref.__permissions__(result, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.field.permissions_func is not None:
            if self.field.many:
                for item in result:
                    if inspect.iscoroutinefunction(self.field.permissions_func):
                        await self.field.permissions_func(root, info, item)
                    else:
                        self.field.permissions_func(root, info, item)

            elif inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, result)

            else:
                self.field.permissions_func(root, info, result)

        elif is_subclass(self.field.ref, QueryType):
            if inspect.iscoroutinefunction(self.field.ref.__permissions__):
                await self.field.ref.__permissions__(result, info)
            else:
                self.field.ref.__permissions__(result, info)


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

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[Any]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> Any:
        value = self.get_value(root, info)

        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        self.check_permissions(root, info, value)
        return value

    async def run_async(self, root: Model, info: GQLInfo) -> Any:
        value = self.get_value(root, info)

        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        await self.check_permissions_async(root, info, value)
        return value

    def get_value(self, root: Model, info: GQLInfo) -> Any:
        field_name = self.field.field_name
        if not self.static:
            field_name = get_queried_field_name(field_name, info)
        return getattr(root, field_name, None)

    def check_permissions(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

    async def check_permissions_async(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, value)
            else:
                self.field.permissions_func(root, info, value)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSingleRelatedFieldResolver(Generic[TModel]):
    """Resolves single-related model field to its primary key."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> Any:
        value: TModel | None = getattr(root, self.field.field_name, None)
        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        self.check_permissions(root, info, value)
        return value.pk

    async def run_async(self, root: Model, info: GQLInfo) -> Any:
        value: TModel | None = getattr(root, self.field.field_name, None)
        if value is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.field.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        await self.check_permissions_async(root, info, value)
        return value.pk

    def check_permissions(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

    async def check_permissions_async(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, value)
            else:
                self.field.permissions_func(root, info, value)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelManyRelatedFieldResolver(Generic[TModel]):
    """Resolves a many-related model field to a list of their primary keys."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[Any]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> list[Any]:
        instances = self.get_instances(root, info)
        self.check_permissions(root, info, instances)
        return [instance.pk for instance in instances]

    async def run_async(self, root: Model, info: GQLInfo) -> list[Any]:
        instances = self.get_instances(root, info)
        await self.check_permissions_async(root, info, instances)
        return [instance.pk for instance in instances]

    def get_instances(self, root: Model, info: GQLInfo) -> list[TModel]:
        field_name = get_queried_field_name(self.field.field_name, info)
        manager: BaseManager[TModel] = getattr(root, field_name)
        return list(manager.get_queryset())

    def check_permissions(self, root: Model, info: GQLInfo, instances: list[TModel]) -> None:
        if self.field.permissions_func is not None:
            for instance in instances:
                self.field.permissions_func(root, info, instance)

    async def check_permissions_async(self, root: Model, info: GQLInfo, instances: list[TModel]) -> None:
        if self.field.permissions_func is not None:
            for instance in instances:
                if inspect.iscoroutinefunction(self.field.permissions_func):
                    await self.field.permissions_func(root, info, instance)
                else:
                    self.field.permissions_func(root, info, instance)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelGenericForeignKeyResolver(Generic[TModel]):
    """Resolves generic foreign key field to its related model instance."""

    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> TModel | None:
        value: TModel | None = getattr(root, self.field.field_name, None)
        if value is None:
            return None

        self.check_permissions(root, info, value)
        return value

    async def run_async(self, root: Model, info: GQLInfo) -> TModel | None:
        value: TModel | None = getattr(root, self.field.field_name, None)
        if value is None:
            return None

        await self.check_permissions_async(root, info, value)
        return value

    def check_permissions(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, value)

    async def check_permissions_async(self, root: Model, info: GQLInfo, value: Any) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, value)
            else:
                self.field.permissions_func(root, info, value)


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

        if instance is None:
            if not self.entrypoint.nullable:
                raise GraphQLModelNotFoundError(model=self.query_type, pk=kwargs.get("pk"))
            return None

        self.check_permissions(root, info, instance)
        return instance

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = self.query_type.__get_queryset__(info)
        instance = await optimize_async(queryset, info, **kwargs)

        if instance is None:
            if not self.entrypoint.nullable:
                raise GraphQLModelNotFoundError(model=self.query_type, pk=kwargs.get("pk"))
            return None

        await self.check_permissions_async(root, info, instance)
        return instance

    def check_permissions(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.entrypoint.permissions_func is not None:
            self.entrypoint.permissions_func(root, info, instance)
        else:
            self.query_type.__permissions__(instance, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.entrypoint.permissions_func is not None:
            if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, instance)
            else:
                self.entrypoint.permissions_func(root, info, instance)

        elif inspect.iscoroutinefunction(self.query_type.__permissions__):
            await self.query_type.__permissions__(instance, info)

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
        instances = optimize_sync(queryset, info, limit=self.entrypoint.limit)
        self.check_permissions(root, info, instances)
        return instances

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = self.get_queryset(info)
        instances = await optimize_async(queryset, info, limit=self.entrypoint.limit)
        await self.check_permissions_async(root, info, instances)
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

    async def check_permissions_async(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(self.query_type.__permissions__):
                await self.query_type.__permissions__(instance, info)

            else:
                self.query_type.__permissions__(instance, info)


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeSingleResolver(Generic[TModel]):
    """Resolves a single-related field pointing to another QueryType."""

    query_type: type[QueryType[TModel]]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> TModel | None:
        instance: TModel | None = getattr(root, self.field.field_name, None)

        if instance is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        self.check_permissions(root, info, instance)
        return instance

    async def run_async(self, root: Model, info: GQLInfo) -> TModel | None:
        instance: TModel | None = getattr(root, self.field.field_name, None)

        if instance is None:
            if not self.field.nullable:
                raise GraphQLFieldNotNullableError(
                    typename=self.query_type.__schema_name__,
                    field_name=self.field.schema_name,
                )
            return None

        await self.check_permissions_async(root, info, instance)
        return instance

    def check_permissions(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.field.permissions_func is not None:
            self.field.permissions_func(root, info, instance)
        else:
            self.query_type.__permissions__(instance, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.field.permissions_func is not None:
            if inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, instance)
            else:
                self.field.permissions_func(root, info, instance)

        elif inspect.iscoroutinefunction(self.query_type.__permissions__):
            await self.query_type.__permissions__(instance, info)

        else:
            self.query_type.__permissions__(instance, info)


@dataclasses.dataclass(frozen=True, slots=True)
class NestedQueryTypeManyResolver(Generic[TModel]):
    """Resolves a many-related field pointing to another QueryType."""

    query_type: type[QueryType[TModel]]
    field: Field

    def __call__(self, root: Model, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo) -> list[TModel]:
        instances = self.get_instances(root, info)
        self.check_permissions(root, info, instances)
        return instances

    async def run_async(self, root: Model, info: GQLInfo) -> list[TModel]:
        instances = self.get_instances(root, info)
        await self.check_permissions_async(root, info, instances)
        return instances

    def get_instances(self, root: Model, info: GQLInfo) -> list[TModel]:
        field_name = get_queried_field_name(self.field.field_name, info)

        instances: list[TModel] = getattr(root, field_name)
        if isinstance(instances, BaseManager):
            instances = list(instances.get_queryset())
        return instances

    def check_permissions(self, root: Model, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.field.permissions_func is not None:
                self.field.permissions_func(root, info, instance)
            else:
                self.query_type.__permissions__(instance, info)

    async def check_permissions_async(self, root: Model, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.field.permissions_func is not None:
                if inspect.iscoroutinefunction(self.field.permissions_func):
                    await self.field.permissions_func(root, info, instance)
                else:
                    self.field.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(self.query_type.__permissions__):
                await self.query_type.__permissions__(instance, info)

            else:
                self.query_type.__permissions__(instance, info)


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

    @property
    def query_type(self) -> type[QueryType]:
        return self.connection.query_type  # type: ignore[return-value]

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
        await self.check_permissions_async(root, info, instances)
        return self.to_connection(instances, pagination=results.pagination)

    def get_queryset(self, info: GQLInfo) -> QuerySet[TModel]:
        return self.query_type.__get_queryset__(info)

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
                self.query_type.__permissions__(instance, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(self.query_type.__permissions__):
                await self.query_type.__permissions__(instance, info)

            else:
                self.query_type.__permissions__(instance, info)

    def to_connection(self, instances: list[TModel], pagination: PaginationHandler) -> ConnectionDict[TModel]:
        typename = self.query_type.__schema_name__
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

    @property
    def query_type(self) -> type[QueryType]:
        return self.connection.query_type  # type: ignore[return-value]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[ConnectionDict[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info)
        return self.run_sync(root, info)

    def run_sync(self, root: Model, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        field_name = get_queried_field_name(self.field.field_name, info)
        instances = self.get_instances(root, field_name)
        self.check_permissions(root, info, instances)
        return self.to_connection(instances)

    async def run_async(self, root: Model, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        field_name = get_queried_field_name(self.field.field_name, info)
        instances = self.get_instances(root, field_name)
        await self.check_permissions_async(root, info, instances)
        return self.to_connection(instances)

    def get_instances(self, root: Model, field_name: str) -> list[TModel]:
        instances: list[TModel] = getattr(root, field_name)
        if isinstance(instances, BaseManager):
            instances = list(instances.get_queryset())
        return instances

    def check_permissions(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.field.permissions_func is not None:
                self.field.permissions_func(root, info, instance)
            else:
                self.query_type.__permissions__(instance, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, instances: list[TModel]) -> None:
        for instance in instances:
            if self.field.permissions_func is not None:
                if inspect.iscoroutinefunction(self.field.permissions_func):
                    await self.field.permissions_func(root, info, instance)
                else:
                    self.field.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(self.query_type.__permissions__):
                await self.query_type.__permissions__(instance, info)

            else:
                self.query_type.__permissions__(instance, info)

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

        typename = self.query_type.__schema_name__
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
        return self.fetch_instances(root, info, queryset_map)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        return await self.fetch_instances_async(root, info, queryset_map)

    def fetch_instances(self, root: Any, info: GQLInfo, queryset_map: QuerySetMap) -> list[TModel]:
        """
        Fetch all instances from the querysets.

        Use a union query to filter and order the results together before fetching them.
        Then fetch the instances per-model and sort them in the same order as in the union query.
        """
        arg_values = get_arguments(info)

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        if self.union_type.__filterset__:
            filter_results = self.filter_union(arg_values, info, queryset_map)
            if filter_results.none:
                return []

        if self.union_type.__orderset__:
            order_results = self.order_union(arg_values, info, queryset_map)
            union_qs = union_qs.order_by(*order_results.order_by)

        union_qs = union_qs.values("__typename", "pk")

        if self.entrypoint.limit is not None:
            union_qs = union_qs[: self.entrypoint.limit]

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[str, int]] = defaultdict(dict)
        for index, item in enumerate(union_qs):
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = index

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

    async def fetch_instances_async(self, root: Any, info: GQLInfo, queryset_map: QuerySetMap) -> list[TModel]:
        arg_values = get_arguments(info)

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        if self.union_type.__filterset__:
            filter_results = self.filter_union(arg_values, info, queryset_map)
            if filter_results.none:
                return []

        if self.union_type.__orderset__:
            order_results = self.order_union(arg_values, info, queryset_map)
            union_qs = union_qs.order_by(*order_results.order_by)

        union_qs = union_qs.values("__typename", "pk")

        if self.entrypoint.limit is not None:
            union_qs = union_qs[: self.entrypoint.limit]

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[str, Any]] = defaultdict(dict)
        counter = count()
        async for item in union_qs:
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = next(counter)

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = await evaluate_with_prefetch_hack_async(queryset)
            await self.check_permissions_async(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

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

    async def check_permissions_async(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)

            else:
                query_type.__permissions__(instance, info)

    def filter_union(
        self,
        arg_values: dict[str, Any],
        info: GQLInfo,
        queryset_map: dict[type[QueryType], QuerySet[Any, Any]],
    ) -> FilterResults:
        filter_data = arg_values.get(undine_settings.QUERY_TYPE_FILTER_INPUT_KEY, {})
        filter_results = self.union_type.__filterset__.__build__(filter_data, info)
        if filter_results.none:
            return filter_results

        for query_type, queryset in queryset_map.items():
            if filter_results.aliases:
                queryset = queryset.alias(**filter_results.aliases)  # noqa: PLW2901
            if filter_results.distinct:
                queryset = queryset.distinct()  # noqa: PLW2901
            if filter_results.filters:
                queryset = queryset.filter(Q(*filter_results.filters))  # noqa: PLW2901

            queryset_map[query_type] = queryset

        return filter_results

    def order_union(
        self,
        arg_values: dict[str, Any],
        info: GQLInfo,
        queryset_map: dict[type[QueryType], QuerySet[Any, Any]],
    ) -> OrderResults:
        order_data = arg_values.get(undine_settings.QUERY_TYPE_ORDER_INPUT_KEY, [])
        order_results = self.union_type.__orderset__.__build__(order_data, info)

        for query_type, queryset in queryset_map.items():
            if order_results.aliases:
                queryset = queryset.alias(**order_results.aliases)  # noqa: PLW2901
            if order_results.order_by:
                queryset = queryset.order_by(*order_results.order_by, *queryset.query.order_by)  # noqa: PLW2901

            queryset_map[query_type] = queryset

        return order_results

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMap:
        queryset_map: QuerySetMap = {}

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

            optimizations.annotations["__typename"] = Value(query_type.__schema_name__)

            queryset = query_type.__get_queryset__(info)
            queryset_map[query_type] = optimizations.apply(queryset, info)

        return queryset_map

    def coalesce_pk(self, item: Any) -> Any:
        # Converting UUIDs to hex avoids an issue with union querysets with mixed int and UUID pks.
        return item.hex if isinstance(item, uuid.UUID) else item


@dataclasses.dataclass(frozen=True, slots=True)
class UnionTypeConnectionResolver(Generic[TModel]):
    """Resolves a connection of union type items."""

    connection: Connection
    entrypoint: Entrypoint

    @property
    def union_type(self) -> type[UnionType]:
        return self.connection.union_type  # type: ignore[return-value]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[ConnectionDict[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        result = self.optimize(info, **kwargs)
        if not result.queryset_map:
            return self.empty_connection()

        all_instances = self.fetch_instances(root, info, result)
        return self.to_connection(all_instances, pagination=result.pagination)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        result = self.optimize(info, **kwargs)
        if not result.queryset_map:
            return self.empty_connection()

        all_instances = await self.fetch_instances_async(root, info, result)
        return self.to_connection(all_instances, pagination=result.pagination)

    def fetch_instances(self, root: Any, info: GQLInfo, result: QuerySetMapWithPagination) -> list[TModel]:
        """
        Fetch paginated instances from the querysets.

        Use a union query to filter, order, and paginate the results together before fetching them.
        Then fetch the instances per-model and sort them in the same order as in the union query.
        """
        arg_values = get_arguments(info)
        queryset_map = result.queryset_map
        pagination = result.pagination

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        if self.union_type.__filterset__:
            filter_results = self.filter_union(arg_values, info, queryset_map)
            if filter_results.none:
                return []

        if self.union_type.__orderset__:
            order_results = self.order_union(arg_values, info, queryset_map)
            union_qs = union_qs.order_by(*order_results.order_by)

        union_qs = union_qs.values("__typename", "pk")
        union_qs = pagination.paginate_queryset(union_qs, info)

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
        for index, item in enumerate(union_qs):
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = index

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

    async def fetch_instances_async(self, root: Any, info: GQLInfo, result: QuerySetMapWithPagination) -> list[TModel]:
        """Async version of `fetch_instances`."""
        arg_values = get_arguments(info)

        queryset_map = result.queryset_map
        pagination = result.pagination

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")

        if self.union_type.__filterset__:
            filter_results = self.filter_union(arg_values, info, queryset_map)
            if filter_results.none:
                return []

        if self.union_type.__orderset__:
            order_results = self.order_union(arg_values, info, queryset_map)
            union_qs = union_qs.order_by(*order_results.order_by)

        union_qs = union_qs.values("__typename", "pk")
        # May call 'queryset.count()'.
        union_qs = await sync_to_async(pagination.paginate_queryset)(union_qs, info)

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
        counter = count()
        async for item in union_qs:
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = next(counter)

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = await evaluate_with_prefetch_hack_async(queryset)
            await self.check_permissions_async(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

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

    async def check_permissions_async(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)

            else:
                query_type.__permissions__(instance, info)

    def filter_union(
        self,
        arg_values: dict[str, Any],
        info: GQLInfo,
        queryset_map: dict[type[QueryType], QuerySet[Any, Any]],
    ) -> FilterResults:
        filter_data = arg_values.get(undine_settings.QUERY_TYPE_FILTER_INPUT_KEY, {})
        filter_results = self.union_type.__filterset__.__build__(filter_data, info)
        if filter_results.none:
            return filter_results

        for query_type, queryset in queryset_map.items():
            if filter_results.aliases:
                queryset = queryset.alias(**filter_results.aliases)  # noqa: PLW2901
            if filter_results.distinct:
                queryset = queryset.distinct()  # noqa: PLW2901
            if filter_results.filters:
                queryset = queryset.filter(Q(*filter_results.filters))  # noqa: PLW2901

            queryset_map[query_type] = queryset

        return filter_results

    def order_union(
        self,
        arg_values: dict[str, Any],
        info: GQLInfo,
        queryset_map: dict[type[QueryType], QuerySet[Any, Any]],
    ) -> OrderResults:
        order_data = arg_values.get(undine_settings.QUERY_TYPE_ORDER_INPUT_KEY, [])
        order_results = self.union_type.__orderset__.__build__(order_data, info)

        for query_type, queryset in queryset_map.items():
            if order_results.aliases:
                queryset = queryset.alias(**order_results.aliases)  # noqa: PLW2901
            if order_results.order_by:
                queryset = queryset.order_by(*order_results.order_by, *queryset.query.order_by)  # noqa: PLW2901

            queryset_map[query_type] = queryset

        return order_results

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMapWithPagination[TModel]:
        queryset_map: QuerySetMap = {}
        pagination: PaginationHandler | None = None

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

            optimizations.annotations["__typename"] = Value(query_type.__schema_name__)

            # Save pagination (should be the same for all query types)
            pagination = optimizations.pagination
            optimizations.pagination = None

            queryset = query_type.__get_queryset__(info)
            queryset_map[query_type] = optimizations.apply(queryset, info)

        return QuerySetMapWithPagination(queryset_map=queryset_map, pagination=pagination)

    def to_connection(self, instances: list[TModel], pagination: PaginationHandler) -> ConnectionDict[TModel]:
        typename = self.union_type.__schema_name__
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

    def empty_connection(self) -> ConnectionDict[TModel]:
        page_info = PageInfoDict(hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None)
        return ConnectionDict(totalCount=0, pageInfo=page_info, edges=[])

    def coalesce_pk(self, item: Any) -> Any:
        # Converting UUIDs to hex avoids an issue with union querysets with mixed int and UUID pks.
        return item.hex if isinstance(item, uuid.UUID) else item


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
        return self.fetch_instances(info, root, queryset_map)

    async def run_sync_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        queryset_map = self.optimize(info, **kwargs)
        return await self.fetch_instances_async(info, root, queryset_map)

    def fetch_instances(self, info: GQLInfo, root: Any, queryset_map: QuerySetMap) -> list[TModel]:
        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        # TODO: Filtering and ordering

        union_qs = union_qs.values("__typename", "pk")

        if self.entrypoint.limit is not None:
            union_qs = union_qs[: self.entrypoint.limit]

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
        for index, item in enumerate(union_qs):
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = index

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

    async def fetch_instances_async(self, info: GQLInfo, root: Any, queryset_map: QuerySetMap) -> list[TModel]:
        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        # TODO: Filtering and ordering

        union_qs = union_qs.values("__typename", "pk")

        if self.entrypoint.limit is not None:
            union_qs = union_qs[: self.entrypoint.limit]

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, Any]] = defaultdict(dict)
        counter = count()
        async for item in union_qs:
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = next(counter)

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = await evaluate_with_prefetch_hack_async(queryset)
            await self.check_permissions_async(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

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

    async def check_permissions_async(
        self,
        info: GQLInfo,
        root: Any,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)

            else:
                query_type.__permissions__(instance, info)

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMap:
        queryset_map: QuerySetMap = {}

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

            optimizations.annotations["__typename"] = Value(query_type.__schema_name__)

            queryset = query_type.__get_queryset__(info)
            queryset_map[query_type] = optimizations.apply(queryset, info)

        return queryset_map

    def coalesce_pk(self, item: Any) -> Any:
        # Converting UUIDs to hex avoids an issue with union querysets with mixed int and UUID pks.
        return item.hex if isinstance(item, uuid.UUID) else item


@dataclasses.dataclass(frozen=True, slots=True)
class InterfaceConnectionResolver(Generic[TModel]):
    """Resolves a connection of interface type items."""

    connection: Connection
    entrypoint: Entrypoint

    @property
    def interface_type(self) -> type[InterfaceType]:
        return self.connection.interface_type  # type: ignore[return-value]

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[ConnectionDict[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        result = self.optimize(info, **kwargs)
        if not result.queryset_map:
            return self.empty_connection()

        all_instances = self.fetch_instances(root, info, result)
        return self.to_connection(all_instances, pagination=result.pagination)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        result = self.optimize(info, **kwargs)
        if not result.queryset_map:
            return self.empty_connection()

        all_instances = await self.fetch_instances_async(root, info, result)
        return self.to_connection(all_instances, pagination=result.pagination)

    def fetch_instances(self, root: Any, info: GQLInfo, result: QuerySetMapWithPagination) -> list[TModel]:
        """
        Fetch paginated instances from the querysets.

        Use a union query to filter, order, and paginate the results together before fetching them.
        Then fetch the instances per-model and sort them in the same order as in the union query.
        """
        queryset_map = result.queryset_map
        pagination = result.pagination

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")  # Default ordering

        # TODO: Filtering and ordering

        union_qs = union_qs.values("__typename", "pk")
        union_qs = pagination.paginate_queryset(union_qs, info)

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
        for index, item in enumerate(union_qs):
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = index

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = evaluate_with_prefetch_hack_sync(queryset)
            self.check_permissions(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

    async def fetch_instances_async(self, root: Any, info: GQLInfo, result: QuerySetMapWithPagination) -> list[TModel]:
        """Async version of `fetch_instances`."""
        queryset_map = result.queryset_map
        pagination = result.pagination

        union_qs = create_union_queryset(queryset_map.values())
        union_qs = union_qs.order_by("pk")

        # TODO: Filtering and ordering

        union_qs = union_qs.values("__typename", "pk")
        # May call 'queryset.count()'.
        union_qs = await sync_to_async(pagination.paginate_queryset)(union_qs, info)

        # Store the order in which the union query returned the items
        # from each model, so that we can sort when the actual instances are fetched.
        pks_by_typename: dict[str, dict[Hashable, int]] = defaultdict(dict)
        counter = count()
        async for item in union_qs:
            pk = self.coalesce_pk(item["pk"])
            pks_by_typename[item["__typename"]][pk] = next(counter)

        all_instances: dict[int, TModel] = {}
        query_type_by_name = {query_type.__schema_name__: query_type for query_type in queryset_map}

        # Fetch all instances for each model, if some primary keys for it were returned in the union queryset.
        for typename, pk_to_index in pks_by_typename.items():
            query_type = query_type_by_name[typename]
            queryset = queryset_map[query_type]
            queryset = queryset.filter(pk__in=list(pk_to_index))
            instances = await evaluate_with_prefetch_hack_async(queryset)
            await self.check_permissions_async(root, info, query_type, instances)

            # Set the instances in the same order as the union query returned them.
            for instance in instances:
                pk = self.coalesce_pk(instance.pk)
                all_instances[pk_to_index[pk]] = instance

        return [instance for _, instance in sorted(all_instances.items())]

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

    async def check_permissions_async(
        self,
        root: Any,
        info: GQLInfo,
        query_type: type[QueryType[TModel]],
        instances: list[TModel],
    ) -> None:
        for instance in instances:
            if self.entrypoint.permissions_func is not None:
                if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                    await self.entrypoint.permissions_func(root, info, instance)
                else:
                    self.entrypoint.permissions_func(root, info, instance)

            elif inspect.iscoroutinefunction(query_type.__permissions__):
                await query_type.__permissions__(instance, info)

            else:
                query_type.__permissions__(instance, info)

    def optimize(self, info: GQLInfo, **kwargs: Any) -> QuerySetMapWithPagination:
        queryset_map: QuerySetMap = {}
        pagination: PaginationHandler | None = None

        for query_type in self.interface_type.__concrete_implementations__():
            model = query_type.__model__
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

            optimizations.annotations["__typename"] = Value(query_type.__schema_name__)

            # Save pagination (should be the same for all query types)
            pagination = optimizations.pagination
            optimizations.pagination = None

            queryset = query_type.__get_queryset__(info)
            queryset_map[query_type] = optimizations.apply(queryset, info)

        return QuerySetMapWithPagination(queryset_map=queryset_map, pagination=pagination)

    def to_connection(self, instances: list[TModel], pagination: PaginationHandler) -> ConnectionDict[TModel]:
        typename = self.interface_type.__schema_name__
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

    def empty_connection(self) -> ConnectionDict[TModel]:
        page_info = PageInfoDict(hasNextPage=False, hasPreviousPage=False, startCursor=None, endCursor=None)
        return ConnectionDict(totalCount=0, pageInfo=page_info, edges=[])

    def coalesce_pk(self, item: Any) -> Any:
        # Converting UUIDs to hex avoids an issue with union querysets with mixed int and UUID pks.
        return item.hex if isinstance(item, uuid.UUID) else item


# Miscellaneous


@dataclasses.dataclass(frozen=True, slots=True)
class TypedDictFieldResolver:
    """Resolves a typed dict field."""

    key: str
    """
    The actual key in the typed dict,
    which may have been converted to camel case for the GraphQL ObjectType.
    """

    def __call__(self, root: dict[str, Any], info: GQLInfo, **kwargs: Any) -> Any:
        return root.get(self.key)


@dataclasses.dataclass(frozen=True, slots=True)
class NamedTupleFieldResolver:
    """Resolves a named tuple field."""

    attr: str
    """
    The actual attribute in the named tuple,
    which may have been converted to camel case for the GraphQL ObjectType.
    """

    def __call__(self, root: object, info: GQLInfo, **kwargs: Any) -> Any:
        return getattr(root, self.attr, None)
