"""GraphQL middleware."""

from __future__ import annotations

import traceback
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Any, Generator, Iterable, Iterator, Self

from undine.errors.exceptions import GraphQLBadInputDataError
from undine.settings import undine_settings
from undine.typing import MutationMiddlewareParams
from undine.utils.logging import undine_logger
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from django.db import models
    from graphql import GraphQLFieldResolver

    from undine import MutationType
    from undine.typing import GQLInfo, MutationMiddlewareType

__all__ = [
    "MutationMiddlewareContext",
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


@dataclass
class ListItem:
    place: int
    data: dict[str, Any]


class InputDataValidationMiddleware:
    """
    Calls registered validators for each input field reachable from the mutation type.
    Also removes any input-only fields from the input data and adds them back after the mutation is done.
    """

    def __init__(self, params: MutationMiddlewareParams) -> None:
        self.params = params

    def __iter__(self) -> Generator:
        original_input_data = deepcopy(self.params.input_data)
        self.pre_mutation(self.params.mutation_type, self.params.input_data)
        yield
        self.params.input_data = original_input_data

    def pre_mutation(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> None:
        """
        Run all MutationType and Input validators for the fields in the given input data.
        Remove any input-only fields after validation.
        """
        from undine import MutationType  # noqa: PLC0415

        mutation_type.__validate__(info=self.params.info, input_data=input_data)

        for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
            input_ = mutation_type.__input_map__.get(field_name)
            if input_ is None:
                raise GraphQLBadInputDataError(mutation_type=mutation_type, field_name=field_name)

            value = input_data.pop(field_name)

            for validator in input_.validators:
                validator(value)

            if isinstance(value, dict) and is_subclass(input_.ref, MutationType):
                self.pre_mutation(mutation_type=input_.ref, input_data=value)

            elif isinstance(value, list) and is_subclass(input_.ref, MutationType):
                for item in value:
                    self.pre_mutation(mutation_type=input_.ref, input_data=item)

            if not input_.input_only:
                # Use field 'snake_case' name.
                input_data[input_.name] = value


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

    default_middleware: list[MutationMiddlewareType] = [
        InputDataValidationMiddleware,
        *undine_settings.MUTATION_MIDDLEWARE,
    ]

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

        for middleware in chain(self.default_middleware, mutation_type.__middleware__()):
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
