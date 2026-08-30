from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any

from undine import QueryType
from undine.settings import undine_settings
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.reflection import get_root_and_info_params, is_subclass

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FunctionType

    from undine import Entrypoint, Field
    from undine.typing import GQLInfo

__all__ = [
    "EntrypointFunctionResolver",
    "FieldFunctionResolver",
    "NamedTupleFieldResolver",
    "TypedDictFieldResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class EntrypointFunctionResolver:
    """Resolves an `Entrypoint` using the given function."""

    func: FunctionType | Callable[..., Any]
    entrypoint: Entrypoint

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and inspect.iscoroutinefunction(self.func):
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        self.set_kwargs(kwargs, root, info)
        result = await self.func(**kwargs)
        await self.check_permissions_async(root, info, result)
        return result

    def set_kwargs(self, kwargs: dict[str, Any], root: Any, info: GQLInfo) -> None:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

    def check_permissions(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.entrypoint.permissions_func is not None:
            if self.entrypoint.many:
                for item in result:
                    self.entrypoint.permissions_func(root, info, item)
            else:
                self.entrypoint.permissions_func(root, info, result)

        elif is_subclass(self.entrypoint.ref, QueryType):
            self.entrypoint.ref.__permissions__(result, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.entrypoint.permissions_func is not None:
            if self.entrypoint.many:
                for item in result:
                    if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                        await self.entrypoint.permissions_func(root, info, item)
                    else:
                        self.entrypoint.permissions_func(root, info, item)

            elif inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, result)

            else:
                self.entrypoint.permissions_func(root, info, result)

        elif is_subclass(self.entrypoint.ref, QueryType):
            if inspect.iscoroutinefunction(self.entrypoint.ref.__permissions__):
                await self.entrypoint.ref.__permissions__(result, info)
            else:
                self.entrypoint.ref.__permissions__(result, info)


@dataclasses.dataclass(frozen=True, slots=True)
class FieldFunctionResolver:
    """Resolves a `Field` using the given function."""

    func: FunctionType | Callable[..., Any]
    field: Field

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        if undine_settings.ASYNC and inspect.iscoroutinefunction(self.func):
            return self.run_async(root, info, **kwargs)
        return self.run_sync(root, info, **kwargs)

    def run_sync(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = self.func(**kwargs)
        self.check_permissions(root, info, result)
        return result

    async def run_async(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        self.set_kwargs(kwargs, root, info)
        result = await self.func(**kwargs)
        await self.check_permissions_async(root, info, result)
        return result

    def set_kwargs(self, kwargs: dict[str, Any], root: Any, info: GQLInfo) -> None:
        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

    def check_permissions(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.field.permissions_func is not None:
            if self.field.many:
                for item in result:
                    self.field.permissions_func(root, info, item)
            else:
                self.field.permissions_func(root, info, result)

        elif is_subclass(self.field.ref, QueryType):
            self.field.ref.__permissions__(result, info)

    async def check_permissions_async(self, root: Any, info: GQLInfo, result: Any) -> None:
        if self.field.permissions_func is not None:
            if self.field.many:
                for item in result:
                    if inspect.iscoroutinefunction(self.field.permissions_func):
                        await self.field.permissions_func(root, info, item)
                    else:
                        self.field.permissions_func(root, info, item)

            elif inspect.iscoroutinefunction(self.field.permissions_func):
                await self.field.permissions_func(root, info, result)

            else:
                self.field.permissions_func(root, info, result)

        elif is_subclass(self.field.ref, QueryType):
            if inspect.iscoroutinefunction(self.field.ref.__permissions__):
                await self.field.ref.__permissions__(result, info)
            else:
                self.field.ref.__permissions__(result, info)


@dataclasses.dataclass(frozen=True, slots=True)
class TypedDictFieldResolver:
    """Resolves a typed dict field."""

    key: str
    """
    The actual key in the typed dict,
    which may have been converted to camel case for the GraphQL ObjectType.
    """

    def __call__(self, root: dict[str, Any], info: GQLInfo, **kwargs: Any) -> Any:
        return root.get(self.key)


@dataclasses.dataclass(frozen=True, slots=True)
class NamedTupleFieldResolver:
    """Resolves a named tuple field."""

    attr: str
    """
    The actual attribute in the named tuple,
    which may have been converted to camel case for the GraphQL ObjectType.
    """

    def __call__(self, root: object, info: GQLInfo, **kwargs: Any) -> Any:
        return getattr(root, self.attr, None)
