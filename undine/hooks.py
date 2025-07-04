from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Self, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import TracebackType

    from graphql import DocumentNode, ExecutionResult

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol

__all__ = [
    "LifecycleHook",
    "LifecycleHookContext",
    "LifecycleHookManager",
    "delegate_to_subgenerator",
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
        async with delegate_to_subgenerator(gen):
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
        with delegate_to_subgenerator(self.run()) as gen:
            for _ in gen:
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


class delegate_to_subgenerator:  # noqa: N801
    """
    Allows delegating how a generator exists to a subgenerator.

    >>> def subgenerator():
    ...     for _ in range(2):
    ...         yield
    >>>
    >>> def generator():
    >>>     with delegate_to_subgenerator(subgenerator()) as sub:
    ...         for _ in sub:
    ...             yield
    >>>
    >>> for item in generator():
    ...     pass

    If the generator exists normally, the subgenerator will be closed.
    If the generator exists with an exception, the error is propagated to the subgenerator
    so that it may handle the error.
    """

    def __init__(self, gen: Generator[None, None, None] | AsyncGenerator[None, None]) -> None:
        """
        Allows delegating how a generator exists to a subgenerator.

        :param gen: The generator to delegate to. If generator is an async generator,
                    must use `async with` syntax to delegate. For regular generators,
                    plain `with` syntax must be used.
        """
        self.gen = gen

    def __enter__(self) -> Generator[None, None, None]:
        if not isinstance(self.gen, Generator):
            msg = "Given object is not a Generator"
            raise TypeError(msg)

        return self.gen

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if not isinstance(self.gen, Generator):  # type: ignore[unreachable]
            msg = "Given object is not a Generator"
            raise TypeError(msg)

        # If no exception was raised, close the generator.
        if exc_type is None:
            self.gen.close()
            return False

        # Otherwise, allow the subgenerator to handle the exception.
        # This has mostly been copied from `contextlib._GeneratorContextManager.__exit__`.
        if exc_value is None:
            exc_value = exc_type()

        try:
            self.gen.throw(exc_value)

        except StopIteration as error:
            return error is not exc_value

        except RuntimeError as error:
            if error is exc_value:
                error.__traceback__ = traceback
                return False
            if isinstance(exc_value, StopIteration) and error.__cause__ is exc_value:
                exc_value.__traceback__ = traceback
                return False
            raise

        except BaseException as error:
            if error is not exc_value:
                raise
            error.__traceback__ = traceback
            return False

        try:
            msg = "generator didn't stop after throw()"
            raise RuntimeError(msg)
        finally:
            self.gen.close()

    async def __aenter__(self) -> AsyncGenerator[None, None]:
        if not isinstance(self.gen, AsyncGenerator):
            msg = "Given object is not an AsyncGenerator"
            raise TypeError(msg)

        return self.gen

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if not isinstance(self.gen, AsyncGenerator):
            msg = "Given object is not an AsyncGenerator"
            raise TypeError(msg)

        # If no exception was raised, close the generator.
        if exc_type is None:
            await self.gen.aclose()
            return False

        # Otherwise, allow the subgenerator to handle the exception.
        # This has mostly been copied from `contextlib._AsyncGeneratorContextManager.__aexit__`.
        if exc_value is None:
            exc_value = exc_type()

        try:
            await self.gen.athrow(exc_value)

        except StopAsyncIteration as error:
            return error is not exc_value

        except RuntimeError as error:
            if error is exc_value:
                error.__traceback__ = traceback
                return False
            if isinstance(exc_value, (StopIteration, StopAsyncIteration)) and error.__cause__ is exc_value:
                exc_value.__traceback__ = traceback
                return False
            raise

        except BaseException as error:
            if error is not exc_value:
                raise
            error.__traceback__ = traceback
            return False

        try:
            msg = "generator didn't stop after athrow()"
            raise RuntimeError(msg)
        finally:
            await self.gen.aclose()
