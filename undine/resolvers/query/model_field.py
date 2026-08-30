from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any, Generic

from undine.exceptions import GraphQLFieldNotNullableError
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import get_queried_field_name

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.manager import BaseManager
    from graphql.pyutils import AwaitableOrValue

    from undine import Field
    from undine.typing import GQLInfo

__all__ = [
    "ModelAttributeResolver",
    "ModelGenericForeignKeyResolver",
    "ModelManyRelatedFieldResolver",
    "ModelSingleRelatedFieldResolver",
]


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
