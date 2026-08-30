from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any, Generic

from asgiref.sync import sync_to_async
from django.db.models.manager import BaseManager
from graphql import GraphQLID, GraphQLObjectType

from undine.exceptions import (
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLNodeTypeNotObjectTypeError,
)
from undine.optimizer.prefetch_hack import evaluate_with_prefetch_hack_async, evaluate_with_prefetch_hack_sync
from undine.relay import Node, from_global_id, to_global_id
from undine.settings import undine_settings
from undine.typing import ConnectionDict, NodeDict, PageInfoDict, TModel
from undine.utils.graphql.undine_extensions import get_undine_query_type
from undine.utils.graphql.utils import (
    get_field_path_identifier,
    get_queried_field_name,
    get_underlying_type,
    pre_evaluate_request_user,
)

from .query_type import QueryTypeSingleResolver

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, Field, QueryType
    from undine.optimizer.optimizer import QueryOptimizer
    from undine.relay import Connection, CursorPaginationHandler
    from undine.typing import GQLInfo


__all__ = [
    "ConnectionResolver",
    "GlobalIDResolver",
    "NestedConnectionResolver",
    "NodeResolver",
]


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
        if field is None:  # pragma: no cover
            raise GraphQLNodeMissingIDFieldError(typename=typename)

        field_type = get_underlying_type(field.get_field_type())  # type: ignore[type-var]
        if field_type is not GraphQLID:  # pragma: no cover
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
        queryset = self.run_optimizer(info)
        instances = evaluate_with_prefetch_hack_sync(queryset)
        self.check_permissions(root, info, instances)

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]
        return self.to_connection(instances, pagination=pagination)

    async def run_async(self, root: Any, info: GQLInfo) -> ConnectionDict[TModel]:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = await self.run_optimizer_async(info)
        instances = await evaluate_with_prefetch_hack_async(queryset)
        await self.check_permissions_async(root, info, instances)

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]
        return self.to_connection(instances, pagination=pagination)

    def get_queryset(self, info: GQLInfo) -> QuerySet[TModel]:
        return self.query_type.__get_queryset__(info)

    def run_optimizer(self, info: GQLInfo) -> QuerySet[TModel]:
        queryset = self.get_queryset(info)
        optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=queryset.model, info=info)
        optimizations = optimizer.compile()
        return optimizations.apply(queryset, info)

    async def run_optimizer_async(self, info: GQLInfo) -> QuerySet[TModel]:
        queryset = self.get_queryset(info)
        optimizer: QueryOptimizer = undine_settings.OPTIMIZER_CLASS(model=queryset.model, info=info)
        optimizations = optimizer.compile()
        # Applying may call 'queryset.count()'.
        return await sync_to_async(optimizations.apply)(queryset, info)

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

    def to_connection(self, instances: list[TModel], pagination: CursorPaginationHandler) -> ConnectionDict[TModel]:
        page = pagination.get_page(instances)
        edges = [
            NodeDict(cursor=cursor, node=instance)
            for cursor, instance in zip(page.cursors, page.instances, strict=True)
        ]
        return ConnectionDict(
            totalCount=page.total_count,
            pageInfo=PageInfoDict(
                hasNextPage=page.has_next_page,
                hasPreviousPage=page.has_previous_page,
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

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]
        return self.to_connection(instances, pagination)

    async def run_async(self, root: Model, info: GQLInfo, **kwargs: Any) -> ConnectionDict[TModel]:
        field_name = get_queried_field_name(self.field.field_name, info)
        instances = self.get_instances(root, field_name)
        await self.check_permissions_async(root, info, instances)

        key = get_field_path_identifier(info.path)
        pagination = info.context.undine_internal.connection_handler_storage[key]
        return self.to_connection(instances, pagination)

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

    def to_connection(self, instances: list[TModel], pagination: CursorPaginationHandler) -> ConnectionDict[TModel]:
        page = pagination.get_prefetch_page(instances)
        edges = [
            NodeDict(cursor=cursor, node=instance)
            for cursor, instance in zip(page.cursors, page.instances, strict=True)
        ]
        return ConnectionDict(
            totalCount=page.total_count,
            pageInfo=PageInfoDict(
                hasNextPage=page.has_next_page,
                hasPreviousPage=page.has_previous_page,
                startCursor=None if not edges else edges[0]["cursor"],
                endCursor=None if not edges else edges[-1]["cursor"],
            ),
            edges=edges,
        )
