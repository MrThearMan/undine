from __future__ import annotations

import dataclasses
from types import FunctionType, SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.db.models import Q
from graphql import GraphQLError, Undefined

from undine import MutationType
from undine.exceptions import GraphQLErrorGroup, GraphQLMissingLookupFieldError, GraphQLModelConstraintViolationError
from undine.settings import undine_settings
from undine.typing import TModel
from undine.utils.graphql.utils import graphql_error_path, pre_evaluate_request_user
from undine.utils.model_utils import convert_integrity_errors, get_default_manager
from undine.utils.mutation_data import MutationData, get_mutation_data
from undine.utils.mutation_tree import bulk_mutate, mutate
from undine.utils.reflection import is_list_of, is_subclass

from .query import QueryTypeManyResolver, QueryTypeSingleResolver

if TYPE_CHECKING:
    from django.db.models import Model
    from graphql.pyutils import AwaitableOrValue

    from undine import Entrypoint, GQLInfo, Input, QueryType
    from undine.typing import EntrypointPermFunc, InputPermFunc, ValidatorFunc

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

        mutation_data = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data

        instance = mutate(mutation_data, model=self.model)

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        mutation_data: MutationData = await sync_to_async(get_mutation_data)(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data

        instance: TModel = await sync_to_async(mutate)(mutation_data, model=self.model)

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

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

        mutation_data = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data

        instance = mutate(mutation_data, model=self.model)

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

        resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
        return resolver.run_sync(root, info, pk=instance.pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> TModel | None:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        if "pk" not in data:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        mutation_data: MutationData = await sync_to_async(get_mutation_data)(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data

        instance: TModel = await sync_to_async(mutate)(mutation_data, model=self.model)

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

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

        mutation_data = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data
        instance = mutation_data.instance

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            instance.delete()

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

        return SimpleNamespace(pk=pk)

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> SimpleNamespace:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        pk: Any = data.get("pk", Undefined)
        if pk is Undefined:
            raise GraphQLMissingLookupFieldError(model=self.model, key="pk")

        mutation_data: MutationData = await sync_to_async(get_mutation_data)(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data
        instance = mutation_data.instance

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            await instance.adelete()

        self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

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

        mutation_datas = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        instances = bulk_mutate(mutation_datas, model=self.model)

        for instance, pre_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=pre_data)

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

        mutation_datas: list[MutationData] = await sync_to_async(get_mutation_data)(  # type: ignore[assignment]
            model=self.model,
            data=data,  # type: ignore[arg-type]
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        instances: list[TModel] = await sync_to_async(bulk_mutate)(mutation_datas, model=self.model)  # type: ignore[arg-type,assignment]

        for instance, pre_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=pre_data)

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

        mutation_datas = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        instances = bulk_mutate(mutation_datas, model=self.model)

        for instance, pre_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=pre_data)

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

        mutation_datas: list[MutationData] = await sync_to_async(get_mutation_data)(  # type: ignore[assignment]
            model=self.model,
            data=data,  # type: ignore[arg-type]
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        instances: list[TModel] = await sync_to_async(bulk_mutate)(mutation_datas, model=self.model)  # type: ignore[arg-type,assignment]

        for instance, previous_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

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

        mutation_datas = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        instances = [mutation_data.instance for mutation_data in mutation_datas]
        pks = [instance.pk for instance in instances]

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            get_default_manager(self.model).filter(pk__in=pks).delete()

        for instance, previous_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

        return [SimpleNamespace(pk=pk) for pk in pks]

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> list[SimpleNamespace]:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: list[dict[str, Any]] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        mutation_datas: list[MutationData] = await sync_to_async(get_mutation_data)(  # type: ignore[assignment]
            model=self.model,
            data=data,  # type: ignore[arg-type]
            mutation_type=self.mutation_type,
        )

        instances = [mut_data.instance for mut_data in mutation_datas]
        pks = [instance.pk for instance in instances]

        _pre_mutation_chain_many(
            root=root,
            info=info,
            mutation_datas=mutation_datas,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_datas = [mutation_data.previous_data for mutation_data in mutation_datas]

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            await get_default_manager(self.model).filter(pk__in=pks).adelete()

        for instance, previous_data in zip(instances, previous_datas, strict=True):
            self.mutation_type.__after__(instance=instance, info=info, previous_data=previous_data)

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
        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        mutation_data = get_mutation_data(
            model=self.model,
            data=data,
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data
        parent = mutation_data.instance

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            result = self.mutation_type.__mutate__(parent, info, data)

        if isinstance(result, self.model):
            self.mutation_type.__after__(instance=result, info=info, previous_data=previous_data)

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return resolver.run_sync(root, info, pk=result.pk)

        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        # Fetch user eagerly so that its available e.g. for permission checks in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        data: dict[str, Any] = kwargs[undine_settings.MUTATION_INPUT_DATA_KEY]

        mutation_data: MutationData = await sync_to_async(get_mutation_data)(  # type: ignore[assignment]
            model=self.model,
            data=data,  # type: ignore[arg-type]
            mutation_type=self.mutation_type,
        )

        _pre_mutation_chain(
            root=root,
            info=info,
            mutation_data=mutation_data,
            mutation_type=self.mutation_type,
            permissions_func=self.entrypoint.permissions_func,
        )

        previous_data = mutation_data.previous_data
        parent = mutation_data.instance

        with convert_integrity_errors(GraphQLModelConstraintViolationError):
            result = await self.mutation_type.__mutate__(parent, info, data)

        if isinstance(result, self.model):
            self.mutation_type.__after__(instance=result, info=info, previous_data=previous_data)

            resolver = QueryTypeSingleResolver(query_type=self.query_type, entrypoint=self.entrypoint)
            return await resolver.run_async(root, info, pk=result.pk)

        return result


def _pre_mutation_chain(
    root: Any,
    info: GQLInfo,
    mutation_data: MutationData,
    mutation_type: type[MutationType],
    permissions_func: InputPermFunc | EntrypointPermFunc | None = None,
) -> None:
    _add_hidden_inputs(
        mutation_data=mutation_data,
        mutation_type=mutation_type,
        info=info,
    )
    _check_permissions(
        parent=root,
        info=info,
        mutation_data=mutation_data,
        mutation_type=mutation_type,
        parent_permissions_func=permissions_func,
    )
    _validate(
        parent=root,
        info=info,
        mutation_data=mutation_data,
        mutation_type=mutation_type,
    )
    _remove_input_only_inputs(
        mutation_data=mutation_data,
        mutation_type=mutation_type,
        info=info,
    )


def _pre_mutation_chain_many(
    root: Any,
    info: GQLInfo,
    mutation_datas: list[MutationData],
    mutation_type: type[MutationType],
    permissions_func: InputPermFunc | EntrypointPermFunc | None = None,
) -> None:
    errors: list[GraphQLError] = []

    for i, mutation_data in enumerate(mutation_datas):
        try:
            with graphql_error_path(info, key=i) as sub_info:
                _pre_mutation_chain(
                    root=root,
                    info=sub_info,
                    mutation_data=mutation_data,
                    mutation_type=mutation_type,
                    permissions_func=permissions_func,
                )
        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)


def _add_hidden_inputs(
    mutation_data: MutationData,
    mutation_type: type[MutationType],
    info: GQLInfo,
) -> None:
    instance = mutation_data.instance

    for input_field in mutation_type.__input_map__.values():
        if input_field.hidden:
            if isinstance(input_field.ref, FunctionType):
                mutation_data.data[input_field.name] = input_field.ref(instance, info)

            elif input_field.default_value is not Undefined:
                mutation_data.data[input_field.name] = input_field.default_value

        if input_field.name not in mutation_data.data:
            return

        value = mutation_data.data[input_field.name]

        if not input_field.hidden and isinstance(input_field.ref, FunctionType):
            mutation_data.data[input_field.name] = input_field.ref(instance, info, value)

        if not is_subclass(input_field.ref, MutationType):
            return

        if is_list_of(value, MutationData):
            for item in value:
                _add_hidden_inputs(item, input_field.ref, info)
            return

        if isinstance(value, MutationData):
            _add_hidden_inputs(value, input_field.ref, info)


def _check_permissions(
    parent: Any,
    info: GQLInfo,
    mutation_data: MutationData,
    *,
    mutation_type: type[MutationType],
    parent_permissions_func: InputPermFunc | EntrypointPermFunc | None = None,
) -> None:
    input_data = mutation_data.plain_data

    with graphql_error_path(info):
        if parent_permissions_func is not None:
            parent_permissions_func(parent, info, input_data)
        else:
            mutation_type.__permissions__(mutation_data.instance, info, input_data)

    errors: list[GraphQLError] = []

    for key, value in input_data.items():
        input_field = mutation_type.__input_map__[key]
        original_value = mutation_data.data[key]

        if value == input_field.default_value:
            continue

        try:
            with graphql_error_path(info, key=input_field.schema_name) as sub_info:
                _check_permissions_input(mutation_data.instance, sub_info, value, input_field, original_value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)


def _check_permissions_input(
    parent: Model,
    info: GQLInfo,
    value: Any,
    input_field: Input,
    original_value: Any,
) -> None:
    if is_subclass(input_field.ref, MutationType):
        if isinstance(original_value, list):
            errors: list[GraphQLError] = []

            for index, item in enumerate(original_value):
                try:
                    with graphql_error_path(info, key=index) as list_info:
                        _check_permissions(
                            parent=parent,
                            info=list_info,
                            mutation_data=item,
                            mutation_type=input_field.ref,
                            parent_permissions_func=input_field.permissions_func,
                        )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())

            if errors:
                raise GraphQLErrorGroup(errors)

        else:
            _check_permissions(
                parent=parent,
                info=info,
                mutation_data=original_value,
                mutation_type=input_field.ref,
                parent_permissions_func=input_field.permissions_func,
            )

    elif input_field.permissions_func is not None:
        input_field.permissions_func(parent, info, value)


def _validate(
    parent: Any,
    info: GQLInfo,
    mutation_data: MutationData,
    *,
    mutation_type: type[MutationType],
    parent_validation_func: ValidatorFunc | None = None,
) -> None:
    errors: list[GraphQLError] = []

    input_data = mutation_data.plain_data

    for key, value in input_data.items():
        input_field = mutation_type.__input_map__[key]
        original_value = mutation_data.data[key]

        if value == input_field.default_value:
            continue

        try:
            with graphql_error_path(info, key=input_field.schema_name) as sub_info:
                _validate_input(mutation_data.instance, sub_info, value, input_field, original_value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    with graphql_error_path(info):
        if parent_validation_func is not None:
            parent_validation_func(parent, info, input_data)
        else:
            mutation_type.__validate__(mutation_data.instance, info, input_data)

    if errors:
        raise GraphQLErrorGroup(errors)


def _validate_input(
    parent: Model,
    info: GQLInfo,
    value: Any,
    input_field: Input,
    original_value: Any,
) -> None:
    if is_subclass(input_field.ref, MutationType):
        if isinstance(value, list):
            errors: list[GraphQLError] = []

            for index, item in enumerate(original_value):
                try:
                    with graphql_error_path(info, key=index) as list_info:
                        _validate(
                            parent=parent,
                            info=list_info,
                            mutation_data=item,
                            mutation_type=input_field.ref,
                            parent_validation_func=input_field.validator_func,
                        )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())

            if errors:
                raise GraphQLErrorGroup(errors)

        else:
            _validate(
                parent=parent,
                info=info,
                mutation_data=original_value,
                mutation_type=input_field.ref,
                parent_validation_func=input_field.validator_func,
            )

    elif input_field.validator_func is not None:
        input_field.validator_func(parent, info, value)


def _remove_input_only_inputs(
    mutation_data: MutationData,
    mutation_type: type[MutationType],
    info: GQLInfo,
) -> None:
    for input_field in mutation_type.__input_map__.values():
        if input_field.input_only:
            mutation_data.data.pop(input_field.name, None)

        if input_field.name not in mutation_data.data:
            return

        value = mutation_data.data[input_field.name]

        if not is_subclass(input_field.ref, MutationType):
            return

        if is_list_of(value, MutationData):
            for item in value:
                _remove_input_only_inputs(item, input_field.ref, info)
            return

        if isinstance(value, MutationData):
            _remove_input_only_inputs(value, input_field.ref, info)
