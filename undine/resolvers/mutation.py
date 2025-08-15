from __future__ import annotations

import dataclasses
from types import FunctionType, SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic, Protocol

from asgiref.sync import sync_to_async
from django.db import transaction  # noqa: ICN003
from django.db.models import Q
from graphql import GraphQLError, Undefined

from undine import MutationType
from undine.exceptions import GraphQLErrorGroup, GraphQLMissingLookupFieldError
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import graphql_error_path, pre_evaluate_request_user
from undine.utils.model_utils import (
    convert_integrity_errors,
    get_bulk_create_kwargs,
    get_default_manager,
    get_instance_or_raise,
    get_instances_or_raise,
    get_pks_from_list_of_dicts,
    get_save_update_fields,
    set_forward_ids,
    use_save_signals,
)
from undine.utils.reflection import is_same_func

from .query import QueryTypeManyResolver, QueryTypeSingleResolver

if TYPE_CHECKING:
    from django.db.models import Model
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, GQLInfo, QueryType

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
        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            instance = self.mutate(instance=instance, info=info, input_data=input_data)

        self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        instance = self.model()
        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            instance = await self.mutate_async(instance=instance, info=info, input_data=input_data)

        self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return await resolver.run_async(root, info, pk=instance.pk)

    def mutate(self, instance: TModel, info: GQLInfo, input_data: Any) -> TModel:
        if not is_same_func(self.mutation_type.__mutate__, MutationType.__mutate__):
            return self.mutation_type.__mutate__(instance, info, input_data)

        for key, value in input_data.items():
            setattr(instance, key, value)

        if undine_settings.MUTATION_FULL_CLEAN:
            instance.full_clean()

        instance.save()
        return instance

    async def mutate_async(self, instance: TModel, info: GQLInfo, input_data: Any) -> TModel:
        if not is_same_func(self.mutation_type.__mutate__, MutationType.__mutate__):
            return await self.mutation_type.__mutate__(instance, info, input_data)

        for key, value in input_data.items():
            setattr(instance, key, value)

        if undine_settings.MUTATION_FULL_CLEAN:
            instance.full_clean()

        await instance.asave()
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

        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            instance = self.mutate(instance=instance, info=info, input_data=input_data)

        self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        input_data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in input_data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        instance = await sync_to_async(get_instance_or_raise)(model=self.model, pk=input_data["pk"])
        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            instance = await self.mutate_async(instance=instance, info=info, input_data=input_data)

        self.mutation_type.__after__(instance=instance, info=info, input_data=input_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return await resolver.run_async(root, info, pk=instance.pk)

    def mutate(self, instance: TModel, info: GQLInfo, input_data: Any) -> TModel:
        if not is_same_func(self.mutation_type.__mutate__, MutationType.__mutate__):
            return self.mutation_type.__mutate__(instance, info, input_data)

        for key, value in input_data.items():
            setattr(instance, key, value)

        if undine_settings.MUTATION_FULL_CLEAN:
            instance.full_clean()

        instance.save(update_fields=get_save_update_fields(instance, *input_data))
        return instance

    async def mutate_async(self, instance: TModel, info: GQLInfo, input_data: Any) -> TModel:
        if not is_same_func(self.mutation_type.__mutate__, MutationType.__mutate__):
            return await self.mutation_type.__mutate__(instance, info, input_data)

        for key, value in input_data.items():
            setattr(instance, key, value)

        if undine_settings.MUTATION_FULL_CLEAN:
            instance.full_clean()

        await instance.asave(update_fields=get_save_update_fields(instance, *input_data))
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

        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
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

        _pre_mutation_chain(
            mutation_type=self.mutation_type,
            instance=instance,
            info=info,
            input_data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            await instance.adelete()

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

        instances: list[TModel] = [self.model() for _ in input_data]

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            self.mutate(instances=instances, info=info, input_data=input_data)

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

        instances: list[TModel] = [self.model() for _ in input_data]

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            await self.mutate_async(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return await resolver.run_async(root, info)

    def mutate(self, instances: list[TModel], info: GQLInfo, input_data: Any) -> list[TModel]:
        if not is_same_func(self.mutation_type.__bulk_mutate__, MutationType.__bulk_mutate__):
            return self.mutation_type.__bulk_mutate__(instances, info, input_data)

        kwargs = get_bulk_create_kwargs(self.model, *input_data)

        for instance, data in zip(instances, input_data, strict=True):
            for key, value in data.items():
                setattr(instance, key, value)

            if undine_settings.MUTATION_FULL_CLEAN:
                set_forward_ids(instance)
                instance.full_clean()

        with use_save_signals(self.model, instances, kwargs.update_fields):
            return get_default_manager(self.model).bulk_create(objs=instances, **kwargs)

    async def mutate_async(self, instances: list[TModel], info: GQLInfo, input_data: Any) -> list[TModel]:
        if not is_same_func(self.mutation_type.__bulk_mutate__, MutationType.__bulk_mutate__):
            return await self.mutation_type.__bulk_mutate__(instances, info, input_data)

        kwargs = get_bulk_create_kwargs(self.model, *input_data)

        for instance, data in zip(instances, input_data, strict=True):
            for key, value in data.items():
                setattr(instance, key, value)

            if undine_settings.MUTATION_FULL_CLEAN:
                set_forward_ids(instance)
                instance.full_clean()

        with use_save_signals(self.model, instances, kwargs.update_fields):
            return await get_default_manager(self.model).abulk_create(objs=instances, **kwargs)


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

        pks = get_pks_from_list_of_dicts(input_data)
        instances = get_instances_or_raise(model=self.model, pks=pks)

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            self.mutate(instances=instances, info=info, input_data=input_data)

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

        pks = get_pks_from_list_of_dicts(input_data)
        instances = await sync_to_async(get_instances_or_raise)(model=self.model, pks=pks)

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            await self.mutate_async(instances=instances, info=info, input_data=input_data)

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        resolver = QueryTypeManyResolver(
            query_type=self.query_type,
            entrypoint=self.entrypoint,
            additional_filter=Q(pk__in=[instance.pk for instance in instances]),
        )
        return await resolver.run_async(root, info)

    def mutate(self, instances: list[TModel], info: GQLInfo, input_data: Any) -> list[TModel]:
        if not is_same_func(self.mutation_type.__bulk_mutate__, MutationType.__bulk_mutate__):
            return self.mutation_type.__bulk_mutate__(instances, info, input_data)

        kwargs = get_bulk_create_kwargs(self.model, *input_data)

        for instance, data in zip(instances, input_data, strict=True):
            for key, value in data.items():
                setattr(instance, key, value)

            if undine_settings.MUTATION_FULL_CLEAN:
                set_forward_ids(instance)
                instance.full_clean()

        with use_save_signals(self.model, instances, kwargs.update_fields):
            return get_default_manager(self.model).bulk_create(objs=instances, **kwargs)

    async def mutate_async(self, instances: list[TModel], info: GQLInfo, input_data: Any) -> list[TModel]:
        if not is_same_func(self.mutation_type.__bulk_mutate__, MutationType.__bulk_mutate__):
            return await self.mutation_type.__bulk_mutate__(instances, info, input_data)

        kwargs = get_bulk_create_kwargs(self.model, *input_data)

        for instance, data in zip(instances, input_data, strict=True):
            for key, value in data.items():
                setattr(instance, key, value)

            if undine_settings.MUTATION_FULL_CLEAN:
                set_forward_ids(instance)
                instance.full_clean()

        with use_save_signals(self.model, instances, kwargs.update_fields):
            return await get_default_manager(self.model).abulk_create(objs=instances, **kwargs)


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

        pks = get_pks_from_list_of_dicts(input_data)
        instances = get_instances_or_raise(model=self.model, pks=pks)

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
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

        _pre_mutation_chain_many(
            mutation_type=self.mutation_type,
            instances=instances,  # type: ignore[arg-type]
            info=info,
            data=input_data,
        )

        with transaction.atomic(), convert_integrity_errors():
            await get_default_manager(self.model).filter(pk__in=pks).adelete()

        for instance, data in zip(instances, input_data, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, input_data=data)

        return [SimpleNamespace(pk=pk) for pk in pks]


# Helpers


def _pre_mutation_chain(
    mutation_type: type[MutationType],
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
) -> None:
    _add_hidden_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    _run_function_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    _check_permissions(
        mutation_type=mutation_type,
        instance=instance,
        info=info,
        input_data=input_data,
    )
    _validate(
        mutation_type=mutation_type,
        instance=instance,
        info=info,
        input_data=input_data,
    )
    _remove_input_only_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )


def _pre_mutation_chain_many(
    mutation_type: type[MutationType],
    instances: list[Model],
    info: GQLInfo,
    data: list[dict[str, Any]],
) -> None:
    errors: list[GraphQLError] = []

    for i, (instance, sub_data) in enumerate(zip(instances, data, strict=True)):
        try:
            with graphql_error_path(info, key=i) as sub_info:
                _pre_mutation_chain(
                    instance=instance,
                    info=sub_info,
                    input_data=sub_data,
                    mutation_type=mutation_type,
                )
        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)


class MutationDataFunc(Protocol):
    def __call__(
        self,
        instance: Model,
        info: GQLInfo,
        input_data: dict[str, Any],
        mutation_type: type[MutationType],
    ) -> None: ...


def _add_hidden_inputs(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__hidden_inputs__.values():
        if isinstance(input_field.ref, FunctionType):
            input_data[input_field.name] = input_field.ref(instance, info)

        elif input_field.default_value is not Undefined:
            input_data[input_field.name] = input_field.default_value

    _run_for_related_mutation_types(
        func=_add_hidden_inputs,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


def _run_function_inputs(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__function_inputs__.values():
        field_data = input_data.get(input_field.name, Undefined)
        if field_data is Undefined:
            continue

        input_data[input_field.name] = input_field.ref(instance, info, input_data[input_field.name])

    _run_for_related_mutation_types(
        func=_run_function_inputs,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


def _check_permissions(
    mutation_type: type[MutationType],
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
) -> None:
    with graphql_error_path(info):
        mutation_type.__permissions__(instance, info, input_data)

    errors: list[GraphQLError] = []

    for key, value in input_data.items():
        input_field = mutation_type.__input_map__[key]
        if input_field.permissions_func is None:
            continue

        if value == input_field.default_value:
            continue

        try:
            with graphql_error_path(info, key=key) as sub_info:
                input_field.permissions_func(instance, sub_info, value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)


def _validate(
    mutation_type: type[MutationType],
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
) -> None:
    errors: list[GraphQLError] = []

    for key, value in input_data.items():
        input_field = mutation_type.__input_map__[key]
        if input_field.validator_func is None:
            continue

        if value == input_field.default_value:
            continue

        try:
            with graphql_error_path(info, key=key) as sub_info:
                input_field.validator_func(instance, sub_info, value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)

    with graphql_error_path(info):
        mutation_type.__validate__(instance, info, input_data)


def _remove_input_only_inputs(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__input_only_inputs__.values():
        input_data.pop(input_field.name, None)

    _run_for_related_mutation_types(
        func=_remove_input_only_inputs,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


def _run_for_related_mutation_types(
    func: MutationDataFunc,
    mutation_type: type[MutationType],
    info: GQLInfo,
    input_data: dict[str, Any],
) -> None:
    for input_field in mutation_type.__related_inputs__.values():
        field_data: dict[str, Any] | list[dict[str, Any]] | None = input_data.get(input_field.name)
        if not field_data:  # No value, null, empty list, etc.
            continue

        related_mutation_type: type[MutationType] = input_field.ref
        model = related_mutation_type.__model__

        if not input_field.many:
            dict_data: dict[str, Any] = field_data  # type: ignore[assignment]
            func(input_data=dict_data, instance=model(), mutation_type=related_mutation_type, info=info)
            continue

        list_data: list[dict[str, Any]] = field_data  # type: ignore[assignment]
        for item in list_data:
            func(input_data=item, instance=model(), mutation_type=related_mutation_type, info=info)
