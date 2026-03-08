from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import re
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, Self

from django.core.cache import caches
from django.db import transaction  # noqa: ICN003
from django.utils.connection import ConnectionProxy
from graphql import ExecutionResult, OperationType

from undine.exceptions import GraphQLAsyncAtomicMutationNotSupportedError
from undine.settings import undine_settings
from undine.utils.graphql.caching import RequestCacheCalculator
from undine.utils.graphql.utils import get_fragment_definitions, get_operation_definition, is_atomic_mutation
from undine.utils.reflection import delegate_to_subgenerator

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Generator

    from django.core.cache import BaseCache
    from graphql import DocumentNode, GraphQLFieldResolver

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, GQLInfo, T

__all__ = [
    "ExecutionLifecycleHookManager",
    "LifecycleHook",
    "LifecycleHookContext",
    "OperationLifecycleHookManager",
    "ParseLifecycleHookManager",
    "ValidationLifecycleHookManager",
]


@dataclasses.dataclass(kw_only=True)
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

    lifecycle_hooks: list[LifecycleHook] = dataclasses.field(init=False)
    """Lifecycle hooks for this operation."""

    def __post_init__(self) -> None:
        hooks = itertools.chain(
            undine_settings.LIFECYCLE_HOOKS,
            [RequestCacheHook, AtomicMutationHook],
        )
        self.lifecycle_hooks = [hook(context=self) for hook in hooks]

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


class LifecycleHook:
    """
    Base class for lifecycle hooks.

    Override methods to hook into the lifecycle of the GraphQL execution.
    Only overridden methods will be used.
    """

    def __init__(self, context: LifecycleHookContext) -> None:
        """
        Initialize a hook to use for an operation.

        :param context: The context for the hook.
        """
        self.context = context
        """Information on the GraphQL operation is being executed."""

    # Sync hooks.
    # Anything before the yield statement will be executed before the hooking point.
    # Anything after the yield statement will be executed after the hooking point.

    def on_operation(self) -> Generator[None, None, None]:
        """Hooking point that encompasses the entire GraphQL operation (parsing, validation, and execution)."""
        yield

    def on_parse(self) -> Generator[None, None, None]:
        """Hooking point that encompasses the parsing of the GraphQL document into an AST."""
        yield

    def on_validation(self) -> Generator[None, None, None]:
        """Hooking point that encompasses the GraphQL AST validation."""
        yield

    def on_execution(self) -> Generator[None, None, None]:
        """Hooking point that encompasses the execution of the GraphQL AST against the GraphQL schema."""
        yield

    # Resolver hook must be named 'resolve' to be compatible with 'MiddlewareManager'.
    # Should always call the resolver with the arguments as shown below.
    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        """Hooking point that encompasses the resolution of each GraphQL field."""
        return resolver(root, info, **kwargs)

    # Async versions delegate to the sync versions by default

    async def on_operation_async(self) -> AsyncGenerator[None, None]:
        """Same as `on_operation`, but async. Use sync version by default."""
        with delegate_to_subgenerator(self.on_operation()) as gen:
            for _ in gen:
                yield

    async def on_parse_async(self) -> AsyncGenerator[None, None]:
        """Same as `on_parse`, but async. Use sync version by default."""
        with delegate_to_subgenerator(self.on_parse()) as gen:
            for _ in gen:
                yield

    async def on_validation_async(self) -> AsyncGenerator[None, None]:
        """Same as `on_validation`, but async. Use sync version by default."""
        with delegate_to_subgenerator(self.on_validation()) as gen:
            for _ in gen:
                yield

    async def on_execution_async(self) -> AsyncGenerator[None, None]:
        """Same as `on_execution`, but async. Use sync version by default."""
        with delegate_to_subgenerator(self.on_execution()) as gen:
            for _ in gen:
                yield


# Builtin hooks


class AtomicMutationHook(LifecycleHook):
    """
    Hook for executing multiple GraphQL mutations atomically
    if the `@atomic` directive is used on a mutation.
    """

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.is_atomic_mutation: bool = False
        self.error: BaseException | None = None

    def on_execution(self) -> Generator[None, None, None]:
        operation_definition = get_operation_definition(self.context.document, self.context.operation_name)
        self.is_atomic_mutation = is_atomic_mutation(operation_definition)

        if not self.is_atomic_mutation:
            yield
            return

        atomic = transaction.atomic()
        atomic.__enter__()  # noqa: PLC2801
        try:
            yield

        except BaseException as error:
            atomic.__exit__(error.__class__, error, error.__traceback__)
            raise

        else:
            if self.error is not None:
                atomic.__exit__(self.error.__class__, self.error, self.error.__traceback__)
            else:
                atomic.__exit__(None, None, None)

        finally:
            self.error = None

    async def on_execution_async(self) -> AsyncGenerator[None, None]:
        operation_definition = get_operation_definition(self.context.document, self.context.operation_name)
        self.is_atomic_mutation = is_atomic_mutation(operation_definition)

        if not self.is_atomic_mutation:
            yield
            return

        # `transaction.atomic` is not supported in async contexts.
        raise GraphQLAsyncAtomicMutationNotSupportedError

    def resolve(self, func: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
        try:
            return func(root, info, **kwargs)

        except BaseException as error:
            # If an exception is thrown in a top-level resolver, it's likely that the mutation did not complete
            # correctly (e.g. a permission or a validation error) and we should rollback the transaction.
            if self.is_atomic_mutation and len(info.path.as_list()) == 1:
                self.error = error
            raise


class RequestCacheHook(LifecycleHook):
    """Hook for caching requests based on schema `@cacheRules` directives."""

    @property
    def cache(self) -> BaseCache:
        return ConnectionProxy(caches, undine_settings.REQUEST_CACHE_ALIAS)  # type: ignore[return-value]

    def on_execution(self) -> Generator[None, None, None]:
        operation = get_operation_definition(self.context.document, self.context.operation_name)
        if operation.operation != OperationType.QUERY:
            yield
            return

        fragments = get_fragment_definitions(self.context.document)
        cache_results = RequestCacheCalculator(operation, fragments).run()

        if cache_results.cache_time <= 0:
            yield
            return

        key = self.get_cache_key(cache_per_user=cache_results.cache_per_user)

        value: str | None = self.cache.get(key)
        was_cached = value is not None
        if was_cached:
            result: dict[str, Any] = json.loads(value)
            self.context.result = ExecutionResult(data=result["data"], extensions=result.get("extensions"))

        yield

        if was_cached or self.context.result.errors:
            return

        data = json.dumps(self.context.result.formatted, separators=(",", ":"))
        self.cache.set(key, data, cache_results.cache_time)

    def get_cache_key(self, *, cache_per_user: bool) -> str:
        source = re.sub(r"\s+", "", self.context.source, flags=re.UNICODE)
        variables = json.dumps(self.context.variables, separators=(",", ":"))
        key = f"{source}|{variables}"
        if cache_per_user:
            key = f"{key}|{self.context.request.user.pk}"
        return f"{undine_settings.REQUEST_CACHE_PREFIX}:" + hashlib.sha256(key.encode()).hexdigest()


# Hook managers


class BaseLifecycleHookManager(ExitStack, AsyncExitStack, ABC):
    """Allows executing multiple lifecycle hooks at once."""

    def __init__(self, *, hooks: list[LifecycleHook]) -> None:
        self.hooks = hooks
        super().__init__()

    @abstractmethod
    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]]: ...

    @abstractmethod
    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]]: ...

    def __enter__(self) -> Self:
        for hook in self.hooks:
            method = self.enter_sync(hook)
            if method is not None:
                self.enter_context(contextmanager(method)())
        return super().__enter__()

    async def __aenter__(self) -> Self:
        for hook in self.hooks:
            method = self.enter_async(hook)
            if method is not None:
                await self.enter_async_context(asynccontextmanager(method)())
        return await super().__aenter__()


class OperationLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks for the whole operation."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:
        if hook.__class__.on_operation == LifecycleHook.on_operation:
            return None
        return hook.on_operation

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:
        if (
            hook.__class__.on_operation == LifecycleHook.on_operation
            and hook.__class__.on_operation_async == LifecycleHook.on_operation_async
        ):
            return None
        return hook.on_operation_async


class ParseLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the parse step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:
        if hook.__class__.on_parse == LifecycleHook.on_parse:
            return None
        return hook.on_parse

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:
        if (
            hook.__class__.on_parse == LifecycleHook.on_parse
            and hook.__class__.on_parse_async == LifecycleHook.on_parse_async
        ):
            return None
        return hook.on_parse_async


class ValidationLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the validation step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:
        if hook.__class__.on_validation == LifecycleHook.on_validation:
            return None
        return hook.on_validation

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:
        if (
            hook.__class__.on_validation == LifecycleHook.on_validation
            and hook.__class__.on_validation_async == LifecycleHook.on_validation_async
        ):
            return None
        return hook.on_validation_async


class ExecutionLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the execution step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:
        if hook.__class__.on_execution == LifecycleHook.on_execution:
            return None
        return hook.on_execution

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:
        if (
            hook.__class__.on_execution == LifecycleHook.on_execution
            and hook.__class__.on_execution_async == LifecycleHook.on_execution_async
        ):
            return None
        return hook.on_execution_async


# Decorators


def with_lifecycle_hooks_manager(
    manager: type[BaseLifecycleHookManager],
) -> Callable[[Callable[[LifecycleHookContext], T]], Callable[[LifecycleHookContext], T]]:
    def decorator(func: Callable[[LifecycleHookContext], T]) -> Callable[[LifecycleHookContext], T]:
        @wraps(func)
        def wrapper(context: LifecycleHookContext) -> T:
            with manager(hooks=context.lifecycle_hooks):
                return func(context)

        return wrapper

    return decorator


with_operation_lifecycle_hooks_manager = with_lifecycle_hooks_manager(OperationLifecycleHookManager)
with_parse_lifecycle_hooks_manager = with_lifecycle_hooks_manager(ParseLifecycleHookManager)
with_validation_lifecycle_hooks_manager = with_lifecycle_hooks_manager(ValidationLifecycleHookManager)
with_execution_lifecycle_hooks_manager = with_lifecycle_hooks_manager(ExecutionLifecycleHookManager)


def with_lifecycle_hooks_manager_async(
    manager: type[BaseLifecycleHookManager],
) -> Callable[[Callable[[LifecycleHookContext], Awaitable[T]]], Callable[[LifecycleHookContext], Awaitable[T]]]:
    def decorator(
        func: Callable[[LifecycleHookContext], Awaitable[T]],
    ) -> Callable[[LifecycleHookContext], Awaitable[T]]:
        @wraps(func)
        async def wrapper(context: LifecycleHookContext) -> T:
            async with manager(hooks=context.lifecycle_hooks):
                return await func(context)

        return wrapper

    return decorator


with_operation_lifecycle_hooks_manager_async = with_lifecycle_hooks_manager_async(OperationLifecycleHookManager)
with_parse_lifecycle_hooks_manager_async = with_lifecycle_hooks_manager_async(ParseLifecycleHookManager)
with_validation_lifecycle_hooks_manager_async = with_lifecycle_hooks_manager_async(ValidationLifecycleHookManager)
with_execution_lifecycle_hooks_manager_async = with_lifecycle_hooks_manager_async(ExecutionLifecycleHookManager)
