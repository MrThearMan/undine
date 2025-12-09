from __future__ import annotations

import dataclasses
import inspect
from collections.abc import AsyncGenerator
from contextlib import aclosing, nullcontext
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Generic

from graphql import GraphQLError, located_error

from undine.exceptions import GraphQLErrorGroup
from undine.optimizer import optimize_async
from undine.typing import TModel
from undine.utils.graphql.utils import pre_evaluate_request_user
from undine.utils.reflection import get_root_and_info_params

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Callable, Coroutine

    from undine import Entrypoint, GQLInfo, QueryType
    from undine.subscriptions import QueryTypeSignalSubscription

__all__ = [
    "FunctionSubscriptionResolver",
    "SubscriptionValueResolver",
]


@dataclasses.dataclass(frozen=True, slots=True)
class SubscriptionValueResolver:
    """Resolves a value for a subscription."""

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        return root


@dataclasses.dataclass(frozen=True, slots=True)
class FunctionSubscriptionResolver:
    """Subscription resolver for a async generator function or async iterable coroutine."""

    func: Callable[..., AsyncGenerator[Any, None] | Coroutine[Any, Any, AsyncIterable[Any]]]
    entrypoint: Entrypoint

    root_param: str | None = dataclasses.field(default=None, init=False)
    info_param: str | None = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        params = get_root_and_info_params(self.func)
        object.__setattr__(self, "root_param", params.root_param)
        object.__setattr__(self, "info_param", params.info_param)

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[Any]:
        return self.subscribe(root, info, **kwargs)

    async def subscribe(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[Any]:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        if self.root_param is not None:
            kwargs[self.root_param] = root
        if self.info_param is not None:
            kwargs[self.info_param] = info

        value = self.func(**kwargs)
        iterable = await value if isawaitable(value) else value
        manager = aclosing(iterable) if isinstance(iterable, AsyncGenerator) else nullcontext(iterable)

        async with manager:
            try:
                async for result in iterable:
                    if isinstance(result, GraphQLErrorGroup):
                        yield result.located(path=info.path.as_list())
                        continue

                    if isinstance(result, GraphQLError):
                        yield located_error(result, nodes=info.field_nodes, path=info.path.as_list())
                        continue

                    await self.check_permissions_async(root, info, result)
                    yield result

            except GraphQLErrorGroup as error:
                raise error.located(path=info.path.as_list()) from error

            except Exception as error:
                raise located_error(error, nodes=info.field_nodes, path=info.path.as_list()) from error

    async def check_permissions_async(self, root: Any, info: GQLInfo, instance: dict[str, Any]) -> None:
        if self.entrypoint.permissions_func is not None:
            if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, instance)
            else:
                self.entrypoint.permissions_func(root, info, instance)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelSaveSubscriptionResolver(Generic[TModel]):
    """Subscription resolver for a model save signal."""

    subscription: QueryTypeSignalSubscription[TModel]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[TModel]:
        return self.subscribe(root, info, **kwargs)

    @property
    def query_type(self) -> type[QueryType]:
        return self.subscription.query_type

    async def subscribe(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[TModel]:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        query_type = self.subscription.query_type
        subscriber = self.subscription.create_subscriber()
        event_stream = subscriber.subscribe()

        async with aclosing(event_stream):
            try:
                async for event in event_stream:
                    queryset = query_type.__get_queryset__(info)
                    instance = await optimize_async(queryset, info, pk=event.pk)

                    # Instance was deleted before we got a chance to send it to the subscriber.
                    if instance is None:
                        continue

                    await self.check_permissions_async(root, info, instance)
                    yield instance

            except GraphQLErrorGroup as error:
                raise error.located(path=info.path.as_list()) from error

            except Exception as error:
                raise located_error(error, nodes=info.field_nodes, path=info.path.as_list()) from error

    async def check_permissions_async(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.entrypoint.permissions_func is not None:
            if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, instance)
            else:
                self.entrypoint.permissions_func(root, info, instance)

        elif inspect.iscoroutinefunction(self.query_type.__permissions__):
            await self.query_type.__permissions__(instance, info)

        else:
            self.query_type.__permissions__(instance, info)


@dataclasses.dataclass(frozen=True, slots=True)
class ModelDeleteSubscriptionResolver(Generic[TModel]):
    """Subscription resolver for a model delete signal."""

    subscription: QueryTypeSignalSubscription[TModel]
    entrypoint: Entrypoint

    def __call__(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[TModel]:
        return self.subscribe(root, info, **kwargs)

    async def subscribe(self, root: Any, info: GQLInfo, **kwargs: Any) -> AsyncIterable[TModel]:
        # Fetch user eagerly so that its available in synchronous parts of the code.
        await pre_evaluate_request_user(info)

        subscriber = self.subscription.create_subscriber()
        event_stream = subscriber.subscribe()

        async with aclosing(event_stream):
            try:
                async for event in event_stream:
                    await self.check_permissions_async(root, info, event)
                    yield event

            except GraphQLErrorGroup as error:
                raise error.located(path=info.path.as_list()) from error

            except Exception as error:
                raise located_error(error, nodes=info.field_nodes, path=info.path.as_list()) from error

    async def check_permissions_async(self, root: Any, info: GQLInfo, instance: TModel) -> None:
        if self.entrypoint.permissions_func is not None:
            if inspect.iscoroutinefunction(self.entrypoint.permissions_func):
                await self.entrypoint.permissions_func(root, info, instance)
            else:
                self.entrypoint.permissions_func(root, info, instance)
