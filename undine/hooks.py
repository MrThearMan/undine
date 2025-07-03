from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack, ExitStack, aclosing, asynccontextmanager, contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Self, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Generator

    from graphql import DocumentNode, ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "LifecycleHook",
    "LifecycleHookContext",
    "LifecycleHookManager",
    "use_lifecycle_hooks_async",
    "use_lifecycle_hooks_sync",
]


@dataclasses.dataclass(slots=True, kw_only=True)
class LifecycleHookContext:
    """Context passed to a lifecycle hook."""

    source: str
    """Source GraphQL document string."""

    document: DocumentNode | None
    """Parsed GraphQL document AST. Available after parsing is complete."""

    variables: dict[str, Any]
    """Variables passed to the GraphQL operation."""

    operation_name: str | None
    """Name of the GraphQL operation."""

    extensions: dict[str, Any]
    """GraphQL operation extensions received from the client."""

    request: DjangoRequestProtocol
    """Django request during which the GraphQL request is being executed."""

    result: ExecutionResult | Awaitable[ExecutionResult | AsyncIterator[ExecutionResult]] | None
    """Execution result of the GraphQL operation. Adding a result here will cause an early exit."""

    @classmethod
    def from_graphql_params(cls, params: GraphQLHttpParams, request: DjangoRequestProtocol) -> Self:
        return cls(
            source=params.document,
            document=None,
            variables=params.variables,
            operation_name=params.operation_name,
            extensions=params.extensions,
            request=request,
            result=None,
        )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LifecycleHook(ABC):
    """Base class for lifecycle hooks."""

    context: LifecycleHookContext

    @contextmanager
    def use_sync(self) -> Generator[None, None, None]:
        yield from self.run()

    @asynccontextmanager
    async def use_async(self) -> AsyncGenerator[None, None]:
        gen = self.run_async()
        async with aclosing(gen):
            async for _ in gen:
                yield

    @abstractmethod
    def run(self) -> Generator[None, None, None]:
        """
        Override this method to define how the hook should be executed.
        Anything before the yield statement will be executed before the hooking point.
        Anything after the yield statement will be executed after the hooking point.
        """
        yield

    async def run_async(self) -> AsyncGenerator[None, None]:
        """
        Override this method to define how the hook should be executed in an async context.
        Uses the `run` method by default.
        """
        for _ in self.run():
            yield


TLifecycleHook = TypeVar("TLifecycleHook", bound=LifecycleHook)


class LifecycleHookManager(ExitStack, AsyncExitStack):
    """Allows executing multiple lifecycle hooks at once."""

    def __init__(self, *, hooks: list[type[TLifecycleHook]], context: LifecycleHookContext) -> None:
        self.hooks: list[TLifecycleHook] = [hook(context=context) for hook in hooks]
        super().__init__()

    def __enter__(self) -> Self:
        for hook in self.hooks:
            self.enter_context(hook.use_sync())
        return super().__enter__()

    async def __aenter__(self) -> Self:
        for hook in self.hooks:
            await self.enter_async_context(hook.use_async())
        return await super().__aenter__()


R = TypeVar("R")
HookableSync = Callable[[LifecycleHookContext], R]
HookableAsync = Callable[[LifecycleHookContext], Awaitable[R]]


def use_lifecycle_hooks_sync(hooks: list[type[TLifecycleHook]]) -> Callable[[HookableSync[R]], HookableSync[R]]:
    """Run given function using the given lifecycle hooks."""

    def decorator(func: HookableSync[R]) -> HookableSync[R]:
        @wraps(func)
        def wrapper(context: LifecycleHookContext) -> R:
            with LifecycleHookManager(hooks=hooks, context=context):
                return func(context)

        return wrapper

    return decorator


def use_lifecycle_hooks_async(hooks: list[type[TLifecycleHook]]) -> Callable[[HookableAsync[R]], HookableAsync[R]]:
    """Run given function using the given lifecycle hooks."""

    def decorator(func: HookableAsync[R]) -> HookableAsync[R]:
        @wraps(func)
        async def wrapper(context: LifecycleHookContext) -> R:  # type: ignore[return]
            async with LifecycleHookManager(hooks=hooks, context=context):
                return await func(context)

        return wrapper

    return decorator
