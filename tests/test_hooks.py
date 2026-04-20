from __future__ import annotations

import contextlib
import hashlib
from typing import Any, AsyncGenerator, Generator
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from graphql import ExecutionResult, GraphQLError, GraphQLFieldResolver, parse

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockRequest, mock_gql_info
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLAsyncAtomicMutationNotSupportedError
from undine.execution import _get_middleware_manager  # noqa: PLC2701
from undine.hooks import (
    AtomicMutationHook,
    AutomaticPersistedQueriesHook,
    ExecutionLifecycleHookManager,
    LifecycleHook,
    LifecycleHookContext,
    OperationLifecycleHookManager,
    ParseLifecycleHookManager,
    RequestCacheHook,
    ValidationLifecycleHookManager,
)
from undine.persisted_documents.models import PersistedDocument
from undine.persisted_documents.utils import to_document_id
from undine.utils.graphql.caching import RequestCacheCalculator


def get_default_context() -> LifecycleHookContext:
    return LifecycleHookContext(
        source="query { hello }",
        document=None,
        variables={},
        operation_name=None,
        extensions={},
        request=None,  # type: ignore[arg-type]
        result=None,
    )


def test_lifecycle_hook__operation_manager() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            call_stack.append("my before")
            yield
            call_stack.append("my after")

    class YourHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            call_stack.append("your before")
            yield
            call_stack.append("your after")

    context = get_default_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with OperationLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__operation_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = get_default_context()

    hooks = [MyHook(context=context)]
    manager = OperationLifecycleHookManager(hooks=hooks)

    assert manager.enter_sync(hooks[0]) is None
    assert manager.enter_async(hooks[0]) is None


def test_lifecycle_hook__parse_manager() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            call_stack.append("my before")
            yield
            call_stack.append("my after")

    class YourHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            call_stack.append("your before")
            yield
            call_stack.append("your after")

    context = get_default_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with ParseLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__parse_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = get_default_context()

    hooks = [MyHook(context=context)]
    manager = ParseLifecycleHookManager(hooks=hooks)

    assert manager.enter_sync(hooks[0]) is None
    assert manager.enter_async(hooks[0]) is None


def test_lifecycle_hook__validation_manager() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_validation(self) -> Generator[None, None, None]:
            call_stack.append("my before")
            yield
            call_stack.append("my after")

    class YourHook(LifecycleHook):
        def on_validation(self) -> Generator[None, None, None]:
            call_stack.append("your before")
            yield
            call_stack.append("your after")

    context = get_default_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with ValidationLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__validation_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = get_default_context()

    hooks = [MyHook(context=context)]
    manager = ValidationLifecycleHookManager(hooks=hooks)

    assert manager.enter_sync(hooks[0]) is None
    assert manager.enter_async(hooks[0]) is None


def test_lifecycle_hook__execution_manager() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            call_stack.append("my before")
            yield
            call_stack.append("my after")

    class YourHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            call_stack.append("your before")
            yield
            call_stack.append("your after")

    context = get_default_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with ExecutionLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__execution_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = get_default_context()

    hooks = [MyHook(context=context)]
    manager = ExecutionLifecycleHookManager(hooks=hooks)

    assert manager.enter_sync(hooks[0]) is None
    assert manager.enter_async(hooks[0]) is None


def test_lifecycle_hook__resolver() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def resolve(self, resolve: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("my before")
            result = resolve(root, info, **kwargs)
            call_stack.append("my after")
            return result

    class YourHook(LifecycleHook):
        def resolve(self, resolve: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("your before")
            result = resolve(root, info, **kwargs)
            call_stack.append("your after")
            return result

    context = get_default_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    manager = _get_middleware_manager(hooks)

    def resolver(root, info, **kwargs):
        call_stack.append("inside")

    field_resolver = manager.get_field_resolver(field_resolver=resolver)

    field_resolver(root=None, info=mock_gql_info())

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__field_resolver__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = get_default_context()

    hooks = [MyHook(context=context)]
    assert _get_middleware_manager(hooks) is None


def test_lifecycle_hook__request(graphql, undine_settings) -> None:
    undine_settings.GRAPHQL_PATH = "graphql/sync/"

    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            call_stack.append("before operation")
            yield
            call_stack.append("after operation")

        def on_parse(self) -> Generator[None, None, None]:
            call_stack.append("before parse")
            yield
            call_stack.append("after parse")

        def on_validation(self) -> Generator[None, None, None]:
            call_stack.append("before validation")
            yield
            call_stack.append("after validation")

        def on_execution(self) -> Generator[None, None, None]:
            call_stack.append("before execution")
            yield
            call_stack.append("after execution")

        def resolve(self, resolve: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("before resolver")
            result = resolve(root, info, **kwargs)
            call_stack.append("after resolver")
            return result

    undine_settings.LIFECYCLE_HOOKS = [MyHook]

    class Query(RootType):
        @Entrypoint
        def example(self, info: GQLInfo) -> str:
            call_stack.append("in entrypoint")
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    result = graphql("query { example }")

    assert result.has_errors is False, result.errors
    assert result.data == {"example": "Hello World"}

    assert call_stack == [
        "before operation",
        "before parse",
        "after parse",
        "before validation",
        "after validation",
        "before execution",
        "before resolver",
        "in entrypoint",
        "after resolver",
        "after execution",
        "after operation",
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_lifecycle_hook__request__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        async def on_operation_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before operation")
            yield
            call_stack.append("after operation")

        async def on_parse_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before parse")
            yield
            call_stack.append("after parse")

        async def on_validation_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before validation")
            yield
            call_stack.append("after validation")

        async def on_execution_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before execution")
            yield
            call_stack.append("after execution")

        def resolve(self, resolve: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("before resolver")
            result = resolve(root, info, **kwargs)
            call_stack.append("after resolver")
            return result

    undine_settings.LIFECYCLE_HOOKS = [MyHook]

    class Query(RootType):
        @Entrypoint
        def example(self, info: GQLInfo) -> str:
            call_stack.append("in entrypoint")
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    result = await graphql_async("query { example }")

    assert result.has_errors is False, result.errors
    assert result.data == {"example": "Hello World"}

    assert call_stack == [
        "before operation",
        "before parse",
        "after parse",
        "before validation",
        "after validation",
        "before execution",
        "before resolver",
        "in entrypoint",
        "after resolver",
        "after execution",
        "after operation",
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_lifecycle_hook__request__async__using_sync_methods(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None]:
            call_stack.append("before operation")
            yield
            call_stack.append("after operation")

        def on_parse(self) -> Generator[None, None]:
            call_stack.append("before parse")
            yield
            call_stack.append("after parse")

        def on_validation(self) -> Generator[None, None]:
            call_stack.append("before validation")
            yield
            call_stack.append("after validation")

        def on_execution(self) -> Generator[None, None]:
            call_stack.append("before execution")
            yield
            call_stack.append("after execution")

        def resolve(self, resolve: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("before resolver")
            result = resolve(root, info, **kwargs)
            call_stack.append("after resolver")
            return result

    undine_settings.LIFECYCLE_HOOKS = [MyHook]

    class Query(RootType):
        @Entrypoint
        def example(self, info: GQLInfo) -> str:
            call_stack.append("in entrypoint")
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    result = await graphql_async("query { example }")

    assert result.has_errors is False, result.errors
    assert result.data == {"example": "Hello World"}

    assert call_stack == [
        "before operation",
        "before parse",
        "after parse",
        "before validation",
        "after validation",
        "before execution",
        "before resolver",
        "in entrypoint",
        "after resolver",
        "after execution",
        "after operation",
    ]


def _make_context(source: str, *, extensions: dict | None = None, undine_settings=None) -> LifecycleHookContext:
    if undine_settings is not None:
        undine_settings.LIFECYCLE_HOOKS = []
    doc = parse(source)
    return LifecycleHookContext(
        source=source,
        document=doc,
        variables={},
        operation_name=None,
        extensions=extensions or {},
        request=MockRequest(),
        result=None,
    )


# LifecycleHook base default methods


def test_lifecycle_hook__base_default_sync_generators() -> None:
    context = get_default_context()
    hook = LifecycleHook(context=context)

    list(hook.on_operation())
    list(hook.on_parse())
    list(hook.on_validation())
    list(hook.on_execution())


def test_lifecycle_hook__base_default_resolve() -> None:
    context = get_default_context()
    hook = LifecycleHook(context=context)

    result = hook.resolve(lambda _r, _i: "value", None, mock_gql_info())
    assert result == "value"


# AtomicMutationHook


@pytest.mark.django_db
def test_atomic_mutation_hook__exception_during_execution(undine_settings) -> None:
    context = _make_context("mutation @atomic { dummy }", undine_settings=undine_settings)
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    with pytest.raises(ValueError, match="boom"):
        gen.throw(ValueError("boom"))  # triggers except BaseException → atomic.__exit__ → re-raise


@pytest.mark.django_db
def test_atomic_mutation_hook__resolver_error_captured(undine_settings) -> None:
    context = _make_context("mutation @atomic { dummy }", undine_settings=undine_settings)
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    hook.error = ValueError("captured in resolver")  # simulate AtomicMutationHook.resolve capturing an error

    with contextlib.suppress(StopIteration):
        next(gen)  # completes normally → else branch → self.error is not None → atomic.__exit__ with error

    assert hook.error is None  # finally block clears it


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_atomic_mutation_hook__async_raises(undine_settings) -> None:
    context = _make_context("mutation @atomic { dummy }", undine_settings=undine_settings)
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution_async()
    with pytest.raises(GraphQLAsyncAtomicMutationNotSupportedError):
        await anext(gen)


# RequestCacheHook


@pytest.mark.django_db
def test_request_cache_hook__result_not_execution_result(undine_settings) -> None:
    context = _make_context("query { field }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)
    gen = hook.on_execution()

    # Patch RequestCacheCalculator.run so we get cache_time > 0
    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        next(gen)  # enters, gets past cache_time > 0 check, cache miss, reaches main yield

    context.result = "not_an_execution_result"  # will hit the `not isinstance` branch

    with contextlib.suppress(StopIteration):
        next(gen)  # runs: if not isinstance → return


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_non_query(undine_settings) -> None:
    context = _make_context("mutation { dummy }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # yields at non-query early return

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_write_and_read_from_cache(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType, cache_time=10)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Cached Task")

    query = "query($pk: Int!) { task(pk: $pk) { name } }"
    variables = {"pk": task.pk}

    # First request: cache miss → writes to cache
    result1 = await graphql_async(query, variables=variables)
    assert result1.has_errors is False
    assert result1.response.headers.get("Cache-Control") is not None
    assert result1.response.headers["Age"] == "0"

    # Second request: cache hit → reads from cache, Age > 0 (or 0 if frozen time)
    result2 = await graphql_async(query, variables=variables)
    assert result2.has_errors is False
    assert result2.data == {"task": {"name": "Cached Task"}}


# AutomaticPersistedQueriesHook


@pytest.mark.django_db
def test_apq_hook__non_query_operation(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    source = "mutation { dummy }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = _make_context(source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution()
    next(gen)  # should hit: operation != QUERY → yield; return

    with contextlib.suppress(StopIteration):
        next(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_no_persisted_query(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    context = _make_context("query { field }")  # no persistedQuery in extensions
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # no persistedQuery → yield; return immediately

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_non_query_operation(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    source = "mutation { dummy }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = _make_context(source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # non-query → yield; return

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_saves_document(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    source = "query { field }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = _make_context(source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # saves PersistedDocument, then yields

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    document_id = to_document_id(source)
    assert await PersistedDocument.objects.filter(document_id=document_id).aexists()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_hash_mismatch(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    source = "query { field }"
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": "wrong_hash"}}

    context = _make_context(source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # hash mismatch → sets context.result, yields

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    assert isinstance(context.result, ExecutionResult)
    assert context.result.errors


@pytest.mark.django_db
def test_atomic_mutation_hook__no_error(undine_settings) -> None:
    context = _make_context("mutation @atomic { dummy }", undine_settings=undine_settings)
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    # hook.error is None — should call atomic.__exit__(None, None, None)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert hook.error is None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_read_predicate_false(undine_settings) -> None:
    context = _make_context("query { field }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False
        undine_settings.REQUEST_CACHE_WRITE_PREDICATE = lambda _: False

        gen = hook.on_execution_async()
        await anext(gen)  # predicate=False → skips cache read → yields at 302

        context.result = ExecutionResult(data={"field": "value"})

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_result_not_execution_result(undine_settings) -> None:
    context = _make_context("query { field }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False

        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = "not_an_execution_result"

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_result_has_errors(undine_settings) -> None:
    context = _make_context("query { field }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False

        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = ExecutionResult(data=None, errors=[GraphQLError("error")])

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_write_predicate_false(undine_settings) -> None:
    context = _make_context("query { field }", undine_settings=undine_settings)
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False
        undine_settings.REQUEST_CACHE_WRITE_PREDICATE = lambda _: False

        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = ExecutionResult(data={"field": "value"}, errors=None)

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_invalid_persisted_query_format(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [AutomaticPersistedQueriesHook]

    source = "query { field }"
    # Missing "version" key → GraphQLAPQVersionMissingError (a GraphQLError subclass)
    extensions = {"persistedQuery": {}}

    context = _make_context(source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # APQ version missing → except GraphQLError → set result, yield

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    assert isinstance(context.result, ExecutionResult)
    assert context.result.errors
