"""GraphQL middleware."""

from __future__ import annotations

import traceback
from itertools import chain
from typing import TYPE_CHECKING, Any, Generator, Iterable, Iterator, Self

from undine.errors.exceptions import GraphQLBadInputDataError
from undine.settings import undine_settings
from undine.utils.logging import undine_logger
from undine.utils.reflection import is_subclass

if TYPE_CHECKING:
    from graphql import GraphQLFieldResolver

    from undine import MutationType
    from undine.typing import GQLInfo, JsonType, MutationMiddlewareType

__all__ = [
    "MutationMiddlewareContext",
    "error_logging_middleware",
]

# -- Field resolver middleware ------------------------------------------------------------------------------------


def error_logging_middleware(resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
    try:
        return resolver(root, info, **kwargs)
    except Exception as err:  # noqa: BLE001
        undine_logger.error(traceback.format_exc())
        return err


# --- Mutation middleware -----------------------------------------------------------------------------------------


class RemoveInputOnlyFieldsMiddleware:
    """
    Removes any input-only fields from the input data before mutation
    and adds them back after the mutation is done.
    """

    def __init__(self, mutation_type: type[MutationType], info: GQLInfo, input_data: dict[str, Any]) -> None:
        self.mutation_type = mutation_type
        self.info = info
        self.input_data = input_data

    def __iter__(self) -> Generator:
        input_only_data = self.extract_input_only_data(mutation_type=self.mutation_type, input_data=self.input_data)
        yield
        self.extend(target=self.input_data, to_merge=input_only_data)

    def extract_input_only_data(self, mutation_type: type[MutationType], input_data: dict[str, Any]) -> JsonType:
        """
        Extracts all input-only field data from the given 'input_data'
        based on the undine.Inputs in the given MutationType.
        """
        from undine import MutationType

        input_only_data: JsonType = {}

        for field_name in list(input_data):  # Copy keys so that we can .pop() in the loop
            input_type = mutation_type.__input_map__.get(field_name)
            if input_type is None:
                raise GraphQLBadInputDataError(field_name=field_name)

            if input_type.input_only:
                input_only_data[field_name] = input_data.pop(field_name)
                continue

            value = input_data[field_name]

            if isinstance(value, dict) and is_subclass(input_type.ref, MutationType):
                data = self.extract_input_only_data(mutation_type=input_type.ref, input_data=value)
                if data:
                    input_only_data[field_name] = data

            elif isinstance(value, list) and is_subclass(input_type.ref, MutationType):
                nested_data: list[JsonType] = []
                for item in value:
                    data = self.extract_input_only_data(mutation_type=input_type.ref, input_data=item)
                    if data:
                        nested_data.append(data)

                if nested_data:
                    input_only_data[field_name] = nested_data

        return input_only_data

    def extend(self, *, target: JsonType, to_merge: JsonType) -> JsonType:
        """
        Recursively extend 'other' JSON object into 'target' JSON object.
        If there is a conflict, the 'other' dictionary's value is used.
        """
        for key, value in to_merge.items():
            if key not in target:
                target[key] = value
            elif isinstance(target[key], dict) and isinstance(value, dict):
                self.extend(target=target[key], to_merge=value)
            elif isinstance(target[key], list) and isinstance(value, list):
                value.extend(value)
            else:
                target[key] = value

        return target


class MutationMiddlewareContext:
    """
    Executes defined middlewares for a mutation.

    Middlewares should be either iterables or iterators that iterate twice.
    The first iteration should modify the data before the mutation is executed.
    The second iteration should modify the data after the mutation is executed.

    >>> # Function middleware
    >>> def my_middleware(mutation_type: type[MutationType], info: GQLInfo, input_data: dict[str, Any]) -> Generator:
    ...     # Do stuff before mutation is executed.
    ...     yield
    ...     # Do stuff after mutation is executed.
    ...
    >>> # Class middleware
    >>> class RemoveInputOnlyFieldsMiddleware:
    ...     def __init__(self, mutation_type: type[MutationType], info: GQLInfo, input_data: dict[str, Any]) -> None:
    ...         ...
    ...
    ...     def __iter__(self) -> Generator:
    ...         # Do stuff before mutation is executed.
    ...         yield
    ...         # Do stuff after mutation is executed.
    """

    default_middleware: list[MutationMiddlewareType] = [
        RemoveInputOnlyFieldsMiddleware,
        *undine_settings.MUTATION_MIDDLEWARE,
    ]

    def __init__(self, mutation_type: type[MutationType], info: GQLInfo, input_data: dict[str, Any]) -> None:
        self.middleware: list[Iterator] = []

        for middleware in chain(self.default_middleware, mutation_type.__middleware__()):
            result = middleware(mutation_type=mutation_type, info=info, input_data=input_data)
            if isinstance(result, Iterator):
                self.middleware.append(result)
            if isinstance(result, Iterable):
                self.middleware.append(iter(result))

    def __enter__(self) -> Self:
        for middleware in self.middleware:
            next(middleware)
        return self

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        for middleware in self.middleware:
            for _ in middleware:
                ...
