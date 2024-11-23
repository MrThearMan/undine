from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from contextlib import suppress
from copy import deepcopy
from types import FunctionType
from typing import TYPE_CHECKING, Any, Generator, Iterable, Iterator, Self

from django.utils.functional import classproperty
from graphql import Undefined

from undine.dataclasses import MutationMiddlewareParams
from undine.utils.logging import undine_logger
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.db import models
    from graphql import GraphQLFieldResolver

    from undine import MutationType
    from undine.typing import GQLInfo, JsonObject

__all__ = [
    "InputDataModificationMiddleware",
    "InputDataValidationMiddleware",
    "InputOnlyDataRemovalMiddleware",
    "MutationMiddleware",
    "MutationMiddlewareHandler",
    "error_logging_middleware",
]


# -- Field resolver middleware ------------------------------------------------------------------------------------


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception:
        undine_logger.error(traceback.format_exc())
        raise


# --- Mutation middleware -----------------------------------------------------------------------------------------


class MutationMiddleware(ABC):
    """Base class for mutation middleware."""

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    @abstractmethod
    def __iter__(self) -> Iterator:
        """
        Should be a generator that yields once.
        Block before yield happends before the mutation is executed.
        Block after yield happens after the mutation is executed.
        """

    @abstractmethod
    @classproperty
    def priority(self) -> int:
        """Middleware priority. Lower number means executed first."""


class InputDataModificationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for hidden input and callable inputs to work.
    Should be executed as the first middleware.

    Alters input data before validation:
    - Adds default values for hidden inputs
    - Calls callable inputs
    """

    priority: int = 0

    def __iter__(self) -> Generator:
        self.fill_input_data(self.params.mutation_type, self.params.input_data)
        yield

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

            # Don't add default values from nested MutationTypes if no other data for it is provided.
            if value is Undefined:
                continue

            if is_subclass(inpt.ref, MutationType):
                self.fill_input_data(mutation_type=inpt.ref, input_data=value)


class InputDataValidationMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input validation to work.

    Run validation for all fields in the given input data.
    """

    priority: int = 100

    def __iter__(self) -> Generator:
        self.validate_data(self.params.mutation_type, self.params.input_data)
        yield

    def validate_data(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        from undine import MutationType  # noqa: PLC0415

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


class PostMutationHandlingMiddleware(MutationMiddleware):
    """
    Mutation middleware required for post-mutation handling to work.

    Run all `__post_handle__` methods for all MutationTypes based on the mutation input data.
    """

    priority: int = 100

    def __iter__(self) -> Generator:
        yield
        self.post_handling(self.params.mutation_type, self.params.input_data)

    def post_handling(self, mutation_type: type[MutationType], input_data: JsonObject) -> None:
        from undine import MutationType  # noqa: PLC0415

        if isinstance(input_data, list):
            for item in input_data:
                self.post_handling(mutation_type=mutation_type, input_data=item)
            return

        for field_name, value in input_data.items():
            inpt = mutation_type.__input_map__[field_name]

            if is_subclass(inpt.ref, MutationType):
                self.post_handling(mutation_type=inpt.ref, input_data=value)

        mutation_type.__post_handle__(info=self.params.info, input_data=input_data)


class InputOnlyDataRemovalMiddleware(MutationMiddleware):
    """
    Mutation middleware required for input-only fields to work.

    Remove any input-only fields from the given input data.
    Add them back in after the mutation is executed.
    """

    priority: int = 200  # Should probably run as the last middleware.

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


class MutationMiddlewareHandler:
    """Executes defined middlewares for a MutationType."""

    def __init__(
        self,
        mutation_type: type[MutationType],
        info: GQLInfo,
        input_data: JsonObject,
        instance: models.Model | None = None,
    ) -> None:
        self.middleware: list[Iterator] = []

        self.params = MutationMiddlewareParams(
            mutation_type=mutation_type,
            info=info,
            input_data=input_data,
            instance=instance,
        )

        sorted_middleware = sorted(mutation_type.__middleware__(), key=lambda m: (m.priority, m.__name__))

        for middleware in sorted_middleware:
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
