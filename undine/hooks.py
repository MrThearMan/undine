from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, Self

from django.core.cache import caches
from django.db import transaction  # noqa: ICN003
from django.utils.connection import ConnectionProxy
from graphql import ExecutionResult, GraphQLError, OperationType

from undine.exceptions import GraphQLAPQHashInvalidError, GraphQLAsyncAtomicMutationNotSupportedError
from undine.parsers import GraphQLRequestParamsParser
from undine.settings import undine_settings
from undine.typing import CacheKeyData, ParseCacheKey, ResultCacheData, ValidationCacheKey, VisibilityCacheData
from undine.utils.graphql.caching import RequestCacheCalculator
from undine.utils.graphql.utils import (
    get_error_execution_result,
    get_fragment_definitions,
    get_operation_definition,
    is_atomic_mutation,
)
from undine.utils.graphql.validation_rules import get_validation_rules
from undine.utils.graphql.validation_rules.visibility_rule import VisibilityRule
from undine.utils.lru_cache import ParseCache, ValidationCache
from undine.utils.reflection import delegate_to_subgenerator

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable, Generator

    from django.contrib.auth.models import AbstractUser, AnonymousUser
    from django.core.cache import BaseCache
    from graphql import ASTValidationRule, DocumentNode, GraphQLFieldResolver
    from graphql.pyutils import AwaitableOrValue

    from undine.dataclasses import CacheControlResults, GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, GQLInfo, GraphQLResult, GraphQLStream, T

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

    validation_errors: list[GraphQLError] | None = None
    """Errors found when validating the GraphQL document. Available after validation is complete."""

    variables: dict[str, Any]
    """Variables passed to the GraphQL operation."""

    operation_name: str | None
    """Name of the GraphQL operation."""

    extensions: dict[str, Any]
    """GraphQL operation extensions received from the client."""

    request: DjangoRequestProtocol
    """Django request during which the GraphQL request is being executed."""

    result: AwaitableOrValue[GraphQLResult | GraphQLStream] | None
    """Execution result of the GraphQL operation. Adding a result here will cause an early exit."""

    lifecycle_hooks: list[LifecycleHook] = dataclasses.field(init=False)
    """Lifecycle hooks for this operation."""

    def __post_init__(self) -> None:
        self.lifecycle_hooks = [hook(context=self) for hook in undine_settings.LIFECYCLE_HOOKS]

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
        operation_definition = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
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
        operation_definition = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        self.is_atomic_mutation = is_atomic_mutation(operation_definition)

        if not self.is_atomic_mutation:
            yield
            return

        # `transaction.atomic` is not supported in async contexts.
        raise GraphQLAsyncAtomicMutationNotSupportedError

    def resolve(self, func: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:  # type: ignore[override]
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
        operation = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        if operation.operation != OperationType.QUERY:
            yield
            return

        fragments = get_fragment_definitions(self.context.document)  # type: ignore[arg-type]
        cache_results = RequestCacheCalculator(operation, fragments).run()

        if cache_results.cache_time <= 0:
            yield
            return

        user = self.context.request.user
        key = self.get_cache_key(user, cache_per_user=cache_results.cache_per_user)

        if undine_settings.REQUEST_CACHE_READ_PREDICATE(self.context):
            data: ResultCacheData | None = self.cache.get(key)

            if data is not None:
                self.context.result = data["result"]
                self.set_cache_read_headers(cache_results, data)
                yield
                return

        yield

        if not isinstance(self.context.result, ExecutionResult):
            return

        # Never cache errors since they can result from something transient (e.g. a connection error)
        if self.context.result.errors:
            return

        if undine_settings.REQUEST_CACHE_WRITE_PREDICATE(self.context):
            data = ResultCacheData(result=self.context.result, created_at=int(time.time()))
            self.cache.set(key, data, cache_results.cache_time)
            self.set_cache_write_headers(cache_results)

    async def on_execution_async(self) -> AsyncGenerator[None, None]:
        # We need a separate async version for caching and fetching the request user.
        # Unfortunately, there is a lot of repetition here.
        operation = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        if operation.operation != OperationType.QUERY:
            yield
            return

        fragments = get_fragment_definitions(self.context.document)  # type: ignore[arg-type]
        cache_results = RequestCacheCalculator(operation, fragments).run()

        if cache_results.cache_time <= 0:
            yield
            return

        user = await self.context.request.auser()
        key = self.get_cache_key(user, cache_per_user=cache_results.cache_per_user)

        if undine_settings.REQUEST_CACHE_READ_PREDICATE(self.context):
            data: ResultCacheData | None = await self.cache.aget(key)

            if data is not None:
                self.context.result = data["result"]
                self.set_cache_read_headers(cache_results, data)
                yield
                return

        yield

        if not isinstance(self.context.result, ExecutionResult):
            return

        # Never cache errors since they can result from something transient (e.g. a connection error)
        if self.context.result.errors:
            return

        if undine_settings.REQUEST_CACHE_WRITE_PREDICATE(self.context):
            data = ResultCacheData(result=self.context.result, created_at=int(time.time()))
            await self.cache.aset(key, data, cache_results.cache_time)
            self.set_cache_write_headers(cache_results)

    def set_cache_read_headers(self, cache_results: CacheControlResults, data: ResultCacheData) -> None:
        self.context.request.response_headers["Cache-Control"] = cache_results.to_cache_control_header()
        self.context.request.response_headers["Age"] = str(int(time.time()) - data["created_at"])

    def set_cache_write_headers(self, cache_results: CacheControlResults) -> None:
        self.context.request.response_headers["Cache-Control"] = cache_results.to_cache_control_header()
        self.context.request.response_headers["Age"] = "0"

    def get_cache_key(self, user: AbstractUser | AnonymousUser, *, cache_per_user: bool) -> str:
        key_data = CacheKeyData(
            source=self.context.source,
            variables=json.dumps(self.context.variables, separators=(",", ":"), sort_keys=True),
            operation_name=self.context.operation_name,
            extensions=json.dumps(self.context.extensions, separators=(",", ":"), sort_keys=True),
            is_authenticated=user.is_authenticated,
        )

        if cache_per_user:
            key_data["user_pk"] = user.pk

        extra_context = undine_settings.REQUEST_CACHE_EXTRA_CONTEXT(self.context)
        if extra_context:
            key_data["extra"] = json.dumps(extra_context, separators=(",", ":"), sort_keys=True)

        key = hashlib.sha256(json.dumps(key_data, separators=(",", ":")).encode()).hexdigest()
        return f"{undine_settings.REQUEST_CACHE_PREFIX}:{key}"


class VisibilityCacheHook(LifecycleHook):
    """Hook for caching the filtered introspection payload per user context."""

    @property
    def cache(self) -> BaseCache:
        return ConnectionProxy(caches, undine_settings.VISIBILITY_CACHE_ALIAS)  # type: ignore[return-value]

    def on_execution(self) -> Generator[None, None, None]:
        if not self.should_cache():
            yield
            return

        user = self.context.request.user
        key = self.get_cache_key(user)

        cached: ExecutionResult | None = self.cache.get(key)
        if cached is not None:
            self.context.result = cached
            yield
            return

        yield

        result = self.context.result
        if not isinstance(result, ExecutionResult) or result.errors:
            return

        self.cache.set(key, result, undine_settings.VISIBILITY_CACHE_TIMEOUT)

    async def on_execution_async(self) -> AsyncGenerator[None, None]:
        # We need a separate async version for caching and fetching the request user.
        # Unfortunately, there is a lot of repetition here.
        if not self.should_cache():
            yield
            return

        user = await self.context.request.auser()
        key = self.get_cache_key(user)

        cached: ExecutionResult | None = await self.cache.aget(key)
        if cached is not None:
            self.context.result = cached
            yield
            return

        yield

        result = self.context.result
        if not isinstance(result, ExecutionResult) or result.errors:
            return

        await self.cache.aset(key, result, undine_settings.VISIBILITY_CACHE_TIMEOUT)

    def should_cache(self) -> bool:
        if undine_settings.VISIBILITY_CACHE_TIMEOUT <= 0:
            return False

        schema = undine_settings.SCHEMA
        if not schema.extensions.get(undine_settings.VISIBILITY_ACTIVE_EXTENSIONS_KEY, False):
            return False

        operation = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        if operation.operation != OperationType.QUERY:
            return False

        return self.context.operation_name == "IntrospectionQuery"

    def get_cache_key(self, user: AbstractUser | AnonymousUser) -> str:
        key_data = VisibilityCacheData(user_pk=user.pk if user.is_authenticated else None)

        extra_context = undine_settings.VISIBILITY_CACHE_EXTRA_CONTEXT(self.context.request)
        if extra_context is not None:
            key_data["extra"] = extra_context

        key = hashlib.sha256(json.dumps(key_data, separators=(",", ":")).encode()).hexdigest()
        return f"{undine_settings.VISIBILITY_CACHE_PREFIX}:{key}"


class AutomaticPersistedQueriesHook(LifecycleHook):
    """Hook for saving automatic persisted queries."""

    def on_execution(self) -> Generator[None, None, None]:
        if "persistedQuery" not in self.context.extensions or "persistedQueryUsed" in self.context.extensions:
            yield
            return

        operation = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        if operation.operation != OperationType.QUERY:
            yield
            return

        try:
            apq_id = GraphQLRequestParamsParser.get_apq_document_id(self.context.extensions)
        except GraphQLError as error:
            self.context.result = get_error_execution_result(error)
            yield
            return

        from undine.persisted_documents.models import PersistedDocument  # noqa: PLC0415
        from undine.persisted_documents.utils import to_document_id  # noqa: PLC0415

        document_id = to_document_id(self.context.source)
        if document_id != apq_id:
            self.context.result = get_error_execution_result(GraphQLAPQHashInvalidError())
            yield
            return

        PersistedDocument.objects.update_or_create(
            document_id=document_id,
            defaults={"document": self.context.source},
        )

        yield

    async def on_execution_async(self) -> AsyncGenerator[None, None]:
        if "persistedQuery" not in self.context.extensions or "persistedQueryUsed" in self.context.extensions:
            yield
            return

        operation = get_operation_definition(self.context.document, self.context.operation_name)  # type: ignore[arg-type]
        if operation.operation != OperationType.QUERY:
            yield
            return

        try:
            apq_id = GraphQLRequestParamsParser.get_apq_document_id(self.context.extensions)
        except GraphQLError as error:
            self.context.result = get_error_execution_result(error)
            yield
            return

        from undine.persisted_documents.models import PersistedDocument  # noqa: PLC0415
        from undine.persisted_documents.utils import to_document_id  # noqa: PLC0415

        document_id = to_document_id(self.context.source)
        if document_id != apq_id:
            self.context.result = get_error_execution_result(GraphQLAPQHashInvalidError())
            yield
            return

        await PersistedDocument.objects.aupdate_or_create(
            document_id=document_id,
            defaults={"document": self.context.source},
        )

        yield


class ParseCacheHook(LifecycleHook):
    """Hook for caching parsed GraphQL documents in the memory of the process."""

    cache: ClassVar[ParseCache] = ParseCache()

    def on_parse(self) -> Generator[None, None, None]:
        max_size: int = self.cache.max_size

        if max_size <= 0 or self.context.result is not None or self.context.document is not None:
            yield
            return

        key = self.get_cache_key()

        document = self.cache.get(key)
        if document is not None:
            self.context.document = document
            yield
            return

        yield

        if self.context.document is not None:
            self.cache.set(key, self.context.document)

    def get_cache_key(self) -> ParseCacheKey:
        return ParseCacheKey(
            source=self.context.source,
            no_location=undine_settings.NO_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )


class ValidationCacheHook(LifecycleHook):
    """Hook for caching the validation outcome of GraphQL documents in the memory of the process."""

    cache: ClassVar[ValidationCache] = ValidationCache()

    def on_validation(self) -> Generator[None, None, None]:
        max_size: int = self.cache.max_size

        if max_size <= 0 or self.context.result is not None or self.context.validation_errors is not None:
            yield
            return

        rules = get_validation_rules(inside_request=True)

        # Visibility is resolved against the user making the request and the values of the variables
        # they sent, so the outcome is not a function of the document and the schema alone.
        if VisibilityRule in rules:
            yield
            return

        key = self.get_cache_key(rules)

        cached_errors = self.cache.get(key)
        if cached_errors is not None:
            self.context.validation_errors = list(cached_errors)
            yield
            return

        yield

        # Errors are modified when they are added to a response, so they cannot be shared
        # between requests. Only documents that validate without errors are cached.
        validation_errors = self.context.validation_errors
        if validation_errors is not None and not validation_errors:
            self.cache.set(key, validation_errors)

    def get_cache_key(self, rules: tuple[type[ASTValidationRule], ...]) -> ValidationCacheKey:
        # Every setting that can change whether a document is valid must be part of the key.
        return ValidationCacheKey(
            schema=undine_settings.SCHEMA,
            source=self.context.source,
            rules=rules,
            max_allowed_aliases=undine_settings.MAX_ALLOWED_ALIASES,
            max_allowed_directives=undine_settings.MAX_ALLOWED_DIRECTIVES,
            max_query_complexity=undine_settings.MAX_QUERY_COMPLEXITY,
            max_list_nesting_depth=undine_settings.MAX_LIST_NESTING_DEPTH,
        )


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

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:  # type: ignore[override]
        if hook.__class__.on_operation == LifecycleHook.on_operation:
            return None
        return hook.on_operation

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:  # type: ignore[override]
        if (
            hook.__class__.on_operation == LifecycleHook.on_operation
            and hook.__class__.on_operation_async == LifecycleHook.on_operation_async
        ):
            return None
        return hook.on_operation_async


class ParseLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the parse step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:  # type: ignore[override]
        if hook.__class__.on_parse == LifecycleHook.on_parse:
            return None
        return hook.on_parse

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:  # type: ignore[override]
        if (
            hook.__class__.on_parse == LifecycleHook.on_parse
            and hook.__class__.on_parse_async == LifecycleHook.on_parse_async
        ):
            return None
        return hook.on_parse_async


class ValidationLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the validation step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:  # type: ignore[override]
        if hook.__class__.on_validation == LifecycleHook.on_validation:
            return None
        return hook.on_validation

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:  # type: ignore[override]
        if (
            hook.__class__.on_validation == LifecycleHook.on_validation
            and hook.__class__.on_validation_async == LifecycleHook.on_validation_async
        ):
            return None
        return hook.on_validation_async


class ExecutionLifecycleHookManager(BaseLifecycleHookManager):
    """Manager for lifecycle hooks in the execution step."""

    def enter_sync(self, hook: LifecycleHook) -> Callable[[], Generator[None, None, None]] | None:  # type: ignore[override]
        if hook.__class__.on_execution == LifecycleHook.on_execution:
            return None
        return hook.on_execution

    def enter_async(self, hook: LifecycleHook) -> Callable[[], AsyncGenerator[None, None]] | None:  # type: ignore[override]
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


# Hook defaults


def should_read_from_cache(context: LifecycleHookContext) -> bool:
    """Check if the result should be read from cache."""
    return True


def should_write_to_cache(context: LifecycleHookContext) -> bool:
    """Check if the result should be written to cache."""
    return True


def default_extra_context(context: LifecycleHookContext) -> dict[str, Any]:
    """Default extra context for the cache key."""
    return {}
