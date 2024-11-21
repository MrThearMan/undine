from __future__ import annotations

import traceback
from contextlib import suppress
from copy import deepcopy
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterable, Iterator, Self

from graphql import Undefined

from undine.dataclasses import MutationMiddlewareParams
from undine.settings import undine_settings
from undine.testing.query_logging import capture_database_queries
from undine.utils.logging import undine_logger
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest
    from django.db import models
    from django.http import HttpResponse
    from graphql import GraphQLFieldResolver

    from undine import MutationType
    from undine.typing import GQLInfo, JsonObject, MutationMiddlewareType

__all__ = [
    "AlterInputDataMiddleware",
    "InputDataValidationMiddleware",
    "MutationMiddlewareContext",
    "RemoveInputOnlyFieldsMiddleware",
    "error_logging_middleware",
    "sql_log_middleware",
]

# --- Django middleware  ------------------------------------------------------------------------------------------


def sql_log_middleware(get_response: Callable[[WSGIRequest], HttpResponse]) -> Callable[[WSGIRequest], HttpResponse]:
    def middleware(request: WSGIRequest) -> HttpResponse:
        with capture_database_queries(log=True):
            return get_response(request)

    return middleware


# -- Field resolver middleware ------------------------------------------------------------------------------------


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception:
        undine_logger.error(traceback.format_exc())
        raise


# --- Mutation middleware -----------------------------------------------------------------------------------------


class AlterInputDataMiddleware:
    """
    Alters input data before validation:
    - Adds default values for hidden inputs
    - Calls callable inputs
    """

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    def __iter__(self) -> Generator:
        self.fill_input_data(self.params.mutation_type, self.params.input_data)
        yield
        # TODO: Post-mutation hooks?

    def fill_input_data(self, mutation_type: type[MutationType], input_data: JsonObject) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.fill_input_data(mutation_type=mutation_type, input_data=item)
            return

        for field_name, inpt in mutation_type.__input_map__.items():
            value: Any = input_data.get(field_name, Undefined)

            if inpt.hidden and inpt.default_value is not Undefined:
                input_data[field_name] = value = inpt.default_value

            if isinstance(inpt.ref, FunctionType):
                args = () if value is Undefined else (value,)
                input_data[field_name] = value = inpt.ref(inpt, self.params.info, *args)

            # TODO: Doesn't add default values from nested MutationTypes if no other data for it is provided.
            if value is Undefined:
                continue

            if is_subclass(inpt.ref, MutationType):
                self.fill_input_data(mutation_type=inpt.ref, input_data=value)


class InputDataValidationMiddleware:
    """Run validation for all fields in the given input data."""

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    def __iter__(self) -> Generator:
        self.validate_data(self.params.mutation_type, self.params.input_data)
        yield

    def validate_data(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        from undine import MutationType  # noqa: PLC0415

        # TODO: Should we run `__validate__` for the list once or all items separately?
        if isinstance(input_data, list):
            for item in input_data:
                self.validate_data(mutation_type=mutation_type, input_data=item)
            return

        # Validate all fields individually.
        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if inpt.validator_func is not None:
                inpt.validator_func(inpt, value)

            if is_subclass(inpt.ref, MutationType):
                self.validate_data(mutation_type=inpt.ref, input_data=value)

        # Validate all fields together.
        mutation_type.__validate__(info=self.params.info, input_data=input_data)


class RemoveInputOnlyFieldsMiddleware:
    """Remove any input-only fields from the given input data. Restores the original input data after mutation."""

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    def __iter__(self) -> Generator:
        original_input_data = deepcopy(self.params.input_data)
        self.remove_input_only_fields(self.params.mutation_type, self.params.input_data)
        yield
        self.params.input_data = original_input_data

    def remove_input_only_fields(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.remove_input_only_fields(mutation_type=mutation_type, input_data=item)
            return

        for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
            inpt = mutation_type.__input_map__[field_name]

            if is_subclass(inpt.ref, MutationType):
                self.remove_input_only_fields(mutation_type=inpt.ref, input_data=input_data[field_name])

            if inpt.input_only:
                input_data.pop(field_name, None)


class MutationMiddlewareContext:
    """
    Executes defined middlewares for a mutation.

    Middlewares should be either iterables or iterators that iterate twice.
    The first iteration should modify the data before the mutation is executed.
    The second iteration should modify the data after the mutation is executed.

    >>> # Function middleware
    >>> def my_middleware(params: MutationMiddlewareParams) -> Generator:
    ...     # Do stuff before mutation is executed.
    ...     yield
    ...     # Do stuff after mutation is executed.
    ...
    >>> # Class middleware
    >>> class MyMiddleware:
    ...     def __init__(self, params: MutationMiddlewareParams) -> None:
    ...         self.params = params
    ...
    ...     def __iter__(self) -> Generator:
    ...         # Do stuff before mutation is executed.
    ...         yield
    ...         # Do stuff after mutation is executed.
    """

    def __init__(
        self,
        mutation_type: type[MutationType],
        info: GQLInfo,
        input_data: dict[str, Any],
        instance: models.Model | None = None,
    ) -> None:
        self.middleware: list[Iterator] = []

        self.params = MutationMiddlewareParams(
            mutation_type=mutation_type,
            info=info,
            input_data=input_data,
            instance=instance,
        )

        default_middleware: list[MutationMiddlewareType] = [
            AlterInputDataMiddleware,
            InputDataValidationMiddleware,
            *undine_settings.MUTATION_MIDDLEWARE,
            *mutation_type.__middleware__(),
            RemoveInputOnlyFieldsMiddleware,
        ]

        for middleware in default_middleware:
            result = middleware(self.params)
            if isinstance(result, Iterator):
                self.middleware.append(result)
            elif isinstance(result, Iterable):
                self.middleware.append(iter(result))

    def __enter__(self) -> Self:
        for middleware in self.middleware:
            with suppress(StopIteration):
                next(middleware)
        return self

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        for middleware in reversed(self.middleware):
            with suppress(StopIteration):
                next(middleware)
