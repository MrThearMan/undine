from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any, Generic, Optional

from django.db.models.manager import BaseManager

from undine.exceptions import GraphQLFieldNotNullableError, GraphQLModelNotFoundError
from undine.optimizer.optimizer import optimize_async, optimize_sync
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import get_queried_field_name, pre_evaluate_request_user

from .limits import entrypoint_limit

if TYPE_CHECKING:
    from django.db.models import Model, Q, QuerySet
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, Field, QueryType
    from undine.typing import GQLInfo

__all__ = [
    "NestedQueryTypeManyResolver",
    "NestedQueryTypeSingleResolver",
    "QueryTypeManyResolver",
    "QueryTypeSingleResolver",
]


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
        # Fetch user eagerly so that its available in synchronous parts of the code.
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
        limit = entrypoint_limit(self.entrypoint)
        instances = optimize_sync(queryset, info, limit=limit)
        self.check_permissions(root, info, instances)
        return instances

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        queryset = self.get_queryset(info)
        limit = entrypoint_limit(self.entrypoint)
        instances = await optimize_async(queryset, info, limit=limit)
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
                    typename=self.field.query_type.__schema_name__,
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
                    typename=self.field.query_type.__schema_name__,
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
