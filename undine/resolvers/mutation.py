from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.db.models import Q
from graphql import Undefined

from undine.exceptions import (
    GraphQLMissingInstancesToDeleteError,
    GraphQLMissingLookupFieldError,
    GraphQLModelConstraintViolationError,
)
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.model_utils import convert_integrity_errors, get_default_manager, get_instance_or_raise
from undine.utils.mutation_tree import mutate

from .query import QueryTypeManyResolver, QueryTypeSingleResolver

if TYPE_CHECKING:
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, MutationType, QueryType
    from undine.typing import GQLInfo

__all__ = [
    "BulkCreateResolver",
    "BulkDeleteResolver",
    "BulkUpdateResolver",
    "CreateResolver",
    "CustomResolver",
    "DeleteResolver",
    "UpdateResolver",
]


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
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance: TModel = mutate(data, model=self.model, info=info, mutation_type=self.mutation_type)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance: TModel = await sync_to_async(mutate)(
            data, model=self.model, info=info, mutation_type=self.mutation_type
        )

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return await resolver.run_async(root, info, pk=instance.pk)


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
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance: TModel = mutate(data, model=self.model, info=info, mutation_type=self.mutation_type)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance: TModel = await sync_to_async(mutate)(
            data, model=self.model, info=info, mutation_type=self.mutation_type
        )

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return await resolver.run_async(root, info, pk=instance.pk)


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
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk: Any = data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = get_instance_or_raise(model=self.model, pk=pk)

        self.mutation_type.__before__(instance=instance, info=info, input_data=data)

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            instance.delete()

        self.mutation_type.__after__(instance=instance, info=info, previous_data={})

        return SimpleNamespace(pk=pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> SimpleNamespace:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk: Any = data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = await sync_to_async(get_instance_or_raise)(model=self.model, pk=pk)

        self.mutation_type.__before__(instance=instance, info=info, input_data=data)

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            await instance.adelete()

        self.mutation_type.__after__(instance=instance, info=info, previous_data={})

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
        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances = mutate(data, model=self.model, info=info, mutation_type=self.mutation_type)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver.run_sync(root, info)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances: list[TModel] = await sync_to_async(mutate)(  # type: ignore[assignment]
            data,  # type: ignore[arg-type]
            model=self.model,
            info=info,
            mutation_type=self.mutation_type,
        )

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
        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances = mutate(data, model=self.model, info=info, mutation_type=self.mutation_type)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return resolver.run_sync(root, info)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[TModel]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instances: list[TModel] = await sync_to_async(mutate)(  # type: ignore[assignment]
            data,  # type: ignore[arg-type]
            model=self.model,
            info=info,
            mutation_type=self.mutation_type,
        )

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
        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pks = [input_data["pk"] for input_data in data if "pk" in input_data]
        queryset = get_default_manager(self.model).filter(pk__in=pks)
        instances = list(queryset)

        given = len(data)
        to_delete = len(instances)
        if to_delete != given:
            raise GraphQLMissingInstancesToDeleteError(given=given, to_delete=to_delete)

        for instance in instances:
            self.mutation_type.__before__(instance=instance, info=info, input_data={})

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            queryset.delete()

        for instance in instances:
            self.mutation_type.__after__(instance=instance, info=info, previous_data={})

        return [SimpleNamespace(pk=pk) for pk in pks]

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[SimpleNamespace]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pks = [input_data["pk"] for input_data in data if "pk" in input_data]
        queryset = get_default_manager(self.model).filter(pk__in=pks)
        instances = [instance async for instance in queryset]

        given = len(data)
        to_delete = len(instances)
        if to_delete != given:
            raise GraphQLMissingInstancesToDeleteError(given=given, to_delete=to_delete)

        for instance in instances:
            self.mutation_type.__before__(instance=instance, info=info, input_data={})

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            await queryset.adelete()

        for instance in instances:
            self.mutation_type.__after__(instance=instance, info=info, previous_data={})

        return [SimpleNamespace(pk=pk) for pk in pks]


# Custom


@dataclasses.dataclass(frozen=True, slots=True)
class CustomResolver:
    """Resolves a custom mutation a model instance."""

    mutation_type: type[MutationType]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and iscoroutinefunction(self.mutation_type.__mutate__):
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    @property
    def query_type(self) -> type[QueryType]:
        return self.mutation_type.__query_type__()

    @property
    def model(self) -> type[TModel]:
        return self.mutation_type.__model__  # type: ignore[return-value]

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        self.mutation_type.__before__(instance=root, info=info, input_data=input_data)

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            result = self.mutation_type.__mutate__(root, info, input_data)

        if isinstance(result, self.model):
            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return resolver.run_sync(root, info, pk=result.pk)

        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        self.mutation_type.__before__(instance=root, info=info, input_data=input_data)

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            result = await sync_to_async(self.mutation_type.__mutate__)(root, info, input_data)

        if isinstance(result, self.model):
            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return await resolver.run_async(root, info, pk=result.pk)

        return result
