from __future__ import annotations

import dataclasses
import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic

from asgiref.sync import sync_to_async
from django.db.models import Model, Q
from graphql import Undefined

from undine.exceptions import GraphQLMissingLookupFieldError, GraphQLMutationInstanceLimitError
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.model_utils import (
    convert_integrity_errors,
    get_default_manager,
    get_instance_or_raise,
    get_instances_or_raise,
    get_pks_from_list_of_dicts,
)
from undine.utils.pre_mutation import pre_mutation, pre_mutation_async, pre_mutation_many, pre_mutation_many_async

from .query import QueryTypeManyResolver, QueryTypeSingleResolver

if TYPE_CHECKING:
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, GQLInfo, MutationType, QueryType

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "CreateResolver",
    "DeleteResolver",
    "UpdateResolver",
]


# Single


@dataclasses.dataclass(frozen=True, slots=True)
class CreateResolver(Generic[TModel]):
    """Resolves a mutation for creating a model instance using."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    @property
    def query_type(self) -> type[QueryType[TModel]]:
        return self.mutation_type.__query_type__()

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance = self.model()
        pre_mutation(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            instance = self.mutation_type.__mutate__(instance=instance, info=info, input_data=input_data)

        if isinstance(instance, Model):
            self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return resolver.run_sync(root, info, pk=instance.pk)

        return instance

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance = self.model()
        await pre_mutation_async(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        if inspect.iscoroutinefunction(self.mutation_type.__mutate__):
            func = self.mutation_type.__mutate__
        else:
            func = sync_to_async(self.mutation_type.__mutate__)

        with convert_integrity_errors():
            instance = await func(instance=instance, info=info, input_data=input_data)

        if isinstance(instance, Model):
            if inspect.iscoroutinefunction(self.mutation_type.__after__):
                await self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]
            else:
                self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return await resolver.run_async(root, info, pk=instance.pk)

        return instance


@dataclasses.dataclass(frozen=True, slots=True)
class UpdateResolver(Generic[TModel]):
    """Resolves a mutation for updating a model instance."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[TModel | None]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    @property
    def query_type(self) -> type[QueryType[TModel]]:
        return self.mutation_type.__query_type__()

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in input_data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = get_instance_or_raise(model=self.model, pk=input_data["pk"])

        pre_mutation(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            instance = self.mutation_type.__mutate__(instance=instance, info=info, input_data=input_data)

        if isinstance(instance, Model):
            self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return resolver.run_sync(root, info, pk=instance.pk)

        return instance

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in input_data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = await sync_to_async(get_instance_or_raise)(model=self.model, pk=input_data["pk"])
        await pre_mutation_async(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        if inspect.iscoroutinefunction(self.mutation_type.__mutate__):
            func = self.mutation_type.__mutate__
        else:
            func = sync_to_async(self.mutation_type.__mutate__)

        with convert_integrity_errors():
            instance = await func(instance=instance, info=info, input_data=input_data)

        if isinstance(instance, Model):
            if inspect.iscoroutinefunction(self.mutation_type.__after__):
                await self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]
            else:
                self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)  # type: ignore[arg-type]

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return await resolver.run_async(root, info, pk=instance.pk)

        return instance


@dataclasses.dataclass(frozen=True, slots=True)
class DeleteResolver(Generic[TModel]):
    """Resolves a mutation for deleting a model instance."""

    mutation_type: type[MutationType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[SimpleNamespace]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> SimpleNamespace:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk: Any = input_data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = get_instance_or_raise(model=self.model, pk=input_data["pk"])

        pre_mutation(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            instance.delete()

        self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        return SimpleNamespace(pk=pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> SimpleNamespace:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk: Any = input_data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = await sync_to_async(get_instance_or_raise)(model=self.model, pk=input_data["pk"])

        await pre_mutation_async(
            instance=instance,
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            await instance.adelete()

        if inspect.iscoroutinefunction(self.mutation_type.__after__):
            await self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)
        else:
            self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        return SimpleNamespace(pk=pk)


# Bulk


@dataclasses.dataclass(frozen=True, slots=True)
class BulkCreateResolver(Generic[TModel]):
    """Resolves a bulk create mutation for creating a list of model instances."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    @property
    def query_type(self) -> type[QueryType[TModel]]:
        return self.mutation_type.__query_type__()

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        count = len(input_data)
        if count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=count)

        instances: list[TModel] = [self.model() for _ in input_data]

        pre_mutation_many(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            instances = self.mutation_type.__bulk_mutate__(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver.run_sync(root, info)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        count = len(input_data)
        if count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=count)

        instances: list[TModel] = [self.model() for _ in input_data]

        await pre_mutation_many_async(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        if inspect.iscoroutinefunction(self.mutation_type.__bulk_mutate__):
            func = self.mutation_type.__bulk_mutate__
        else:
            func = sync_to_async(self.mutation_type.__bulk_mutate__)

        with convert_integrity_errors():
            instances = await func(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            if inspect.iscoroutinefunction(self.mutation_type.__after__):
                await self.mutation_type.__after__(instance=instance, info=info, input_data=data)
            else:
                self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return await resolver.run_async(root, info)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkUpdateResolver(Generic[TModel]):
    """Resolves a bulk update mutation for updating a list of model instances."""

    mutation_type: type[MutationType[TModel]]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[TModel]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    @property
    def query_type(self) -> type[QueryType[TModel]]:
        return self.mutation_type.__query_type__()

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        count = len(input_data)
        if count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=count)

        pks = get_pks_from_list_of_dicts(input_data)
        instances = get_instances_or_raise(model=self.model, pks=pks)

        pre_mutation_many(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            instances = self.mutation_type.__bulk_mutate__(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver.run_sync(root, info)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        count = len(input_data)
        if count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=count)

        pks = get_pks_from_list_of_dicts(input_data)
        instances = await sync_to_async(get_instances_or_raise)(model=self.model, pks=pks)

        await pre_mutation_many_async(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        if inspect.iscoroutinefunction(self.mutation_type.__bulk_mutate__):
            func = self.mutation_type.__bulk_mutate__
        else:
            func = sync_to_async(self.mutation_type.__bulk_mutate__)

        with convert_integrity_errors():
            instances = await func(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            if inspect.iscoroutinefunction(self.mutation_type.__after__):
                await self.mutation_type.__after__(instance=instance, info=info, input_data=data)
            else:
                self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return await resolver.run_async(root, info)


@dataclasses.dataclass(frozen=True, slots=True)
class BulkDeleteResolver(Generic[TModel]):
    """Resolves a bulk delete mutation for deleting a list of model instances."""

    mutation_type: type[MutationType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AwaitableOrValue[list[SimpleNamespace]]:
        if undine_settings.ASYNC:
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[SimpleNamespace]:
        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        count = len(input_data)
        if count > undine_settings.MUTATION_INSTANCE_LIMIT:
            raise GraphQLMutationInstanceLimitError(limit=undine_settings.MUTATION_INSTANCE_LIMIT, count=count)

        pks = get_pks_from_list_of_dicts(input_data)
        instances = get_instances_or_raise(model=self.model, pks=pks)

        pre_mutation_many(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            get_default_manager(self.model).filter(pk__in=pks).delete()

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        return [SimpleNamespace(pk=pk) for pk in pks]

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[SimpleNamespace]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pks = get_pks_from_list_of_dicts(input_data)
        instances = await sync_to_async(get_instances_or_raise)(model=self.model, pks=pks)

        await pre_mutation_many_async(
            instances=instances,  # type: ignore[arg-type]
            info=info,
            input_data=input_data,
            mutation_type=self.mutation_type,
        )

        with convert_integrity_errors():
            await get_default_manager(self.model).filter(pk__in=pks).adelete()

        for instance, data in zip(instances, input_data, strict=True):
            if inspect.iscoroutinefunction(self.mutation_type.__after__):
                await self.mutation_type.__after__(instance=instance, info=info, input_data=data)
            else:
                self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        return [SimpleNamespace(pk=pk) for pk in pks]
