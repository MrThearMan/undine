from __future__ import annotations

import inspect
from types import FunctionType
from typing import TYPE_CHECKING, Any

from asgiref.sync import sync_to_async
from graphql import GraphQLError, Undefined

from undine.exceptions import GraphQLErrorGroup
from undine.utils.graphql.utils import graphql_error_path
from undine.utils.model_utils import get_instance_or_raise, get_instances_or_raise

if TYPE_CHECKING:
    from django.db.models import Model

    from undine import GQLInfo, MutationType
    from undine.typing import MutationDataCoroutine, MutationDataFunc


__all__ = [
    "pre_mutation",
    "pre_mutation_async",
    "pre_mutation_many",
    "pre_mutation_many_async",
]


# Sync


def pre_mutation(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    """Run all pre-mutation handling for the given instance and input data."""
    _fetch_model_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
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
    _permissions(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    _validate(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    _remove_input_only_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )


def pre_mutation_many(
    instances: list[Model],
    info: GQLInfo,
    input_data: list[dict[str, Any]],
    mutation_type: type[MutationType],
) -> None:
    """Run all pre-mutation handling for the given instances and input data."""
    errors: list[GraphQLError] = []

    for i, (instance, sub_data) in enumerate(zip(instances, input_data, strict=True)):
        try:
            with graphql_error_path(info, key=i) as sub_info:
                pre_mutation(
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


def _fetch_model_inputs(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__model_inputs__.values():
        field_data = input_data.get(input_field.name)
        if field_data is None:
            continue

        with graphql_error_path(info, key=input_field.name):
            if input_field.many:
                input_data[input_field.name] = get_instances_or_raise(model=input_field.ref, pks=field_data)
            else:
                input_data[input_field.name] = get_instance_or_raise(model=input_field.ref, pk=field_data)

    _run_for_related_mutation_types(
        func=_fetch_model_inputs,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


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
        if input_field.hidden:  # Hidden function inputs have already been run
            continue

        field_data = input_data.get(input_field.name, Undefined)
        if field_data is Undefined:
            continue

        input_data[input_field.name] = input_field.ref(instance, info, field_data)

    _run_for_related_mutation_types(
        func=_run_function_inputs,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


def _permissions(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
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

    _run_for_related_mutation_types(
        func=_permissions,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


def _validate(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
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

    _run_for_related_mutation_types(
        func=_validate,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )

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
    errors: list[GraphQLError] = []

    for input_field in mutation_type.__related_inputs__.values():
        field_data: dict[str, Any] | list[dict[str, Any]] | None = input_data.get(input_field.name)
        if not field_data:  # No value, null, empty list, empty dict, etc.
            continue

        related_mutation_type: type[MutationType] = input_field.ref
        model = related_mutation_type.__model__

        with graphql_error_path(info, key=input_field.name) as sub_info:
            if not input_field.many:
                dict_data: dict[str, Any] = field_data  # type: ignore[assignment]

                try:
                    func(
                        instance=model(),
                        info=sub_info,
                        input_data=dict_data,
                        mutation_type=related_mutation_type,
                    )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())

                continue

            list_data: list[dict[str, Any]] = field_data  # type: ignore[assignment]
            for i, item in enumerate(list_data):
                try:
                    with graphql_error_path(sub_info, key=i) as list_info:
                        func(
                            instance=model(),
                            info=list_info,
                            input_data=item,
                            mutation_type=related_mutation_type,
                        )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())
    if errors:
        raise GraphQLErrorGroup(errors)


# Async


async def pre_mutation_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    """Run all pre-mutation handling for the given instance and input data."""
    await _fetch_model_inputs_async(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    await _add_hidden_inputs_async(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    await _run_function_inputs_async(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    await _permissions_async(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    await _validate_async(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )
    _remove_input_only_inputs(
        instance=instance,
        info=info,
        input_data=input_data,
        mutation_type=mutation_type,
    )


async def pre_mutation_many_async(
    instances: list[Model],
    info: GQLInfo,
    input_data: list[dict[str, Any]],
    mutation_type: type[MutationType],
) -> None:
    """Run all pre-mutation handling for the given instances and input data."""
    errors: list[GraphQLError] = []

    for i, (instance, sub_data) in enumerate(zip(instances, input_data, strict=True)):
        try:
            with graphql_error_path(info, key=i) as sub_info:
                await pre_mutation_async(
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


async def _fetch_model_inputs_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__model_inputs__.values():
        field_data = input_data.get(input_field.name)
        if field_data is None:
            continue

        with graphql_error_path(info, key=input_field.name):
            if input_field.many:
                input_data[input_field.name] = await sync_to_async(get_instances_or_raise)(
                    model=input_field.ref,
                    pks=field_data,
                )
            else:
                input_data[input_field.name] = await sync_to_async(get_instance_or_raise)(
                    model=input_field.ref,
                    pk=field_data,
                )

    await _run_for_related_mutation_types_async(
        coroutine=_fetch_model_inputs_async,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


async def _add_hidden_inputs_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__hidden_inputs__.values():
        if inspect.iscoroutinefunction(input_field.ref):
            input_data[input_field.name] = await input_field.ref(instance, info)

        elif isinstance(input_field.ref, FunctionType):
            input_data[input_field.name] = input_field.ref(instance, info)

        elif input_field.default_value is not Undefined:
            input_data[input_field.name] = input_field.default_value

    await _run_for_related_mutation_types_async(
        coroutine=_add_hidden_inputs_async,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


async def _run_function_inputs_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    for input_field in mutation_type.__function_inputs__.values():
        if input_field.hidden:  # Hidden function inputs have already been run
            continue

        field_data = input_data.get(input_field.name, Undefined)
        if field_data is Undefined:
            continue

        if inspect.iscoroutinefunction(input_field.ref):
            input_data[input_field.name] = await input_field.ref(instance, info, field_data)
            continue

        input_data[input_field.name] = input_field.ref(instance, info, field_data)

    await _run_for_related_mutation_types_async(
        coroutine=_run_function_inputs_async,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


async def _permissions_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
) -> None:
    with graphql_error_path(info):
        if inspect.iscoroutinefunction(mutation_type.__permissions__):
            await mutation_type.__permissions__(instance, info, input_data)
        else:
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
                if inspect.iscoroutinefunction(input_field.permissions_func):
                    await input_field.permissions_func(instance, sub_info, value)
                else:
                    input_field.permissions_func(instance, sub_info, value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)

    await _run_for_related_mutation_types_async(
        coroutine=_permissions_async,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )


async def _validate_async(
    instance: Model,
    info: GQLInfo,
    input_data: dict[str, Any],
    mutation_type: type[MutationType],
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
                if inspect.iscoroutinefunction(input_field.validator_func):
                    await input_field.validator_func(instance, sub_info, value)
                else:
                    input_field.validator_func(instance, sub_info, value)

        except GraphQLError as error:
            errors.append(error)

        except GraphQLErrorGroup as error_group:
            errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)

    await _run_for_related_mutation_types_async(
        coroutine=_validate_async,
        mutation_type=mutation_type,
        info=info,
        input_data=input_data,
    )

    with graphql_error_path(info):
        if inspect.iscoroutinefunction(mutation_type.__validate__):
            await mutation_type.__validate__(instance, info, input_data)
        else:
            mutation_type.__validate__(instance, info, input_data)


async def _run_for_related_mutation_types_async(
    coroutine: MutationDataCoroutine,
    mutation_type: type[MutationType],
    info: GQLInfo,
    input_data: dict[str, Any],
) -> None:
    errors: list[GraphQLError] = []

    for input_field in mutation_type.__related_inputs__.values():
        field_data: dict[str, Any] | list[dict[str, Any]] | None = input_data.get(input_field.name)
        if not field_data:  # No value, null, empty list, empty dict, etc.
            continue

        related_mutation_type: type[MutationType] = input_field.ref
        model = related_mutation_type.__model__

        with graphql_error_path(info, key=input_field.name) as sub_info:
            if not input_field.many:
                dict_data: dict[str, Any] = field_data  # type: ignore[assignment]

                try:
                    await coroutine(
                        instance=model(),
                        info=sub_info,
                        input_data=dict_data,
                        mutation_type=related_mutation_type,
                    )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())

                continue

            list_data: list[dict[str, Any]] = field_data  # type: ignore[assignment]
            for i, item in enumerate(list_data):
                try:
                    with graphql_error_path(sub_info, key=i) as list_info:
                        await coroutine(
                            instance=model(),
                            info=list_info,
                            input_data=item,
                            mutation_type=related_mutation_type,
                        )

                except GraphQLError as error:
                    errors.append(error)

                except GraphQLErrorGroup as error_group:
                    errors.extend(error_group.flatten())

    if errors:
        raise GraphQLErrorGroup(errors)
