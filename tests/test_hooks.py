from __future__ import annotations

import contextlib
import hashlib
from typing import Any, AsyncGenerator, AsyncIterator, Generator
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.test import override_settings
from graphql import ExecutionResult, GraphQLError, GraphQLFieldResolver, parse

from example_project.app.models import Project, Task
from tests.conftest import skip_if_async
from tests.factories import TaskFactory
from tests.helpers import CountingValidationRule, DocumentRecordingHook, MockRequest, mock_gql_info
from undine import Entrypoint, Field, Filter, FilterSet, GQLInfo, MutationType, QueryType, RootType, create_schema
from undine.dataclasses import GraphQLHttpParams
from undine.exceptions import GraphQLAsyncAtomicMutationNotSupportedError
from undine.execution import _get_middleware_manager, execute_graphql_with_subscription  # noqa: PLC2701
from undine.hooks import (
    AtomicMutationHook,
    AutomaticPersistedQueriesHook,
    ExecutionLifecycleHookManager,
    HookPriority,
    LifecycleHook,
    LifecycleHookContext,
    OperationLifecycleHookManager,
    ParseCacheHook,
    ParseLifecycleHookManager,
    RequestCacheHook,
    ValidationCacheHook,
    ValidationLifecycleHookManager,
    VisibilityCacheHook,
)
from undine.persisted_documents.models import PersistedDocument
from undine.persisted_documents.utils import to_document_id
from undine.typing import DjangoRequestProtocol
from undine.utils.graphql.caching import RequestCacheCalculator
from undine.utils.visibility import apply_visibility


def make_hook_context(*, source: str = "query { hello }", extensions: dict | None = None) -> LifecycleHookContext:
    return LifecycleHookContext(
        source=source,
        document=parse(source),
        variables={},
        operation_name=None,
        extensions=extensions or {},
        request=MockRequest(),  # type: ignore[arg-type]
        result=None,
    )


def test_lifecycle_hook__base_default_sync_generators() -> None:
    context = make_hook_context()
    hook = LifecycleHook(context=context)

    list(hook.on_operation())
    list(hook.on_parse())
    list(hook.on_validation())
    list(hook.on_execution())


def test_lifecycle_hook__base_default_resolve() -> None:
    context = make_hook_context()
    hook = LifecycleHook(context=context)

    result = hook.resolve(lambda _r, _i: "value", None, mock_gql_info())
    assert result == "value"


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

    context = make_hook_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with OperationLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__operation_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context)]
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

    context = make_hook_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with ParseLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__parse_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context)]
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

    context = make_hook_context()

    hooks = [MyHook(context=context), YourHook(context=context)]

    with ValidationLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__validation_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context)]
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

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context), YourHook(context=context)]

    with ExecutionLifecycleHookManager(hooks=hooks):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__execution_manager__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context)]
    manager = ExecutionLifecycleHookManager(hooks=hooks)

    assert manager.enter_sync(hooks[0]) is None
    assert manager.enter_async(hooks[0]) is None


def test_lifecycle_hook__resolver() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("my before")
            result = resolver(root, info, **kwargs)
            call_stack.append("my after")
            return result

    class YourHook(LifecycleHook):
        def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:
            call_stack.append("your before")
            result = resolver(root, info, **kwargs)
            call_stack.append("your after")
            return result

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context), YourHook(context=context)]

    manager = _get_middleware_manager(hooks)

    def resolver_func(root, info, **kwargs):
        call_stack.append("inside")

    field_resolver = manager.get_field_resolver(field_resolver=resolver_func)

    field_resolver(root=None, info=mock_gql_info())

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_lifecycle_hook__field_resolver__hook_not_used() -> None:
    class MyHook(LifecycleHook): ...

    context = make_hook_context()

    hooks: list[LifecycleHook] = [MyHook(context=context)]
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

    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [MyHook]

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

    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [MyHook]

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

    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [MyHook]

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


# Hook registration


@pytest.mark.django_db
def test_lifecycle_hooks__registered_in_priority_order(undine_settings) -> None:
    undine_settings.PARSE_CACHE_MAX_SIZE = 10
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    class TracingHook(LifecycleHook):
        priority = HookPriority.TRACING

    class CustomHook(LifecycleHook): ...

    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [CustomHook, TracingHook]

    context = make_hook_context()

    # The order of the setting doesn't matter, and hooks for unused features are left out.
    assert [type(hook) for hook in context.lifecycle_hooks] == [TracingHook, ParseCacheHook, CustomHook]


@pytest.mark.django_db
def test_lifecycle_hooks__built_in_hooks_registered_for_the_features_in_use(undine_settings) -> None:
    undine_settings.PARSE_CACHE_MAX_SIZE = 10
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class TaskCreateMutation(MutationType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True, cache_time=10)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    context = make_hook_context()

    assert [type(hook) for hook in context.lifecycle_hooks] == [
        ParseCacheHook,
        ValidationCacheHook,
        RequestCacheHook,
        VisibilityCacheHook,
        AtomicMutationHook,
        AutomaticPersistedQueriesHook,
    ]


def test_lifecycle_hooks__registered_hooks_updated_when_django_settings_change(undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = []
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    context = make_hook_context()

    assert [type(hook) for hook in context.lifecycle_hooks] == [AutomaticPersistedQueriesHook]

    with override_settings(UNDINE={"AUTOMATIC_PERSISTED_QUERIES": False}):
        context = make_hook_context()

        assert [type(hook) for hook in context.lifecycle_hooks] == []


# AtomicMutationHook


async def test_lifecycle_hook__subscription__execution_hooks_close_before_each_result(undine_settings) -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None]:
            call_stack.append("before execution")
            yield
            call_stack.append("after execution")

    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [MyHook]

    class Query(RootType):
        @Entrypoint
        def example(self) -> str:
            return "Hello World"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for value in range(2, 0, -1):
                yield value

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    params = GraphQLHttpParams(
        document="subscription { countdown }",
        variables={},
        operation_name=None,
        extensions={},
    )
    stream = await execute_graphql_with_subscription(params, MockRequest(method="WEBSOCKET"))
    assert isinstance(stream, AsyncIterator), f"{stream=}"

    results: list[dict[str, Any] | None] = []

    async for result in stream:
        call_stack.append(f"delivered {result.data}")
        results.append(result.data)

    assert results == [{"countdown": 2}, {"countdown": 1}]

    # Delivering a result to the client is not part of the execution step.
    assert call_stack == [
        "before execution",
        "after execution",
        "delivered {'countdown': 2}",
        "before execution",
        "after execution",
        "delivered {'countdown': 1}",
        "before execution",
        "after execution",
    ]


@pytest.mark.django_db
def test_atomic_mutation_hook__no_error(undine_settings) -> None:

    context = make_hook_context(source="mutation @atomic { dummy }")
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    # hook.error is None — should call atomic.__exit__(None, None, None)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert hook.error is None


@pytest.mark.django_db
def test_atomic_mutation_hook__exception_during_execution(undine_settings) -> None:

    context = make_hook_context(source="mutation @atomic { dummy }")
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    with pytest.raises(ValueError, match="boom"):
        gen.throw(ValueError("boom"))  # triggers except BaseException → atomic.__exit__ → re-raise


@pytest.mark.django_db
def test_atomic_mutation_hook__resolver_error_captured(undine_settings) -> None:

    context = make_hook_context(source="mutation @atomic { dummy }")
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution()
    next(gen)  # enters atomic transaction, yields

    hook.error = ValueError("captured in resolver")  # simulate AtomicMutationHook.resolve capturing an error

    with contextlib.suppress(StopIteration):
        next(gen)  # completes normally → else branch → self.error is not None → atomic.__exit__ with error

    assert hook.error is None  # finally block clears it


@pytest.mark.django_db(transaction=True)
async def test_atomic_mutation_hook__async_raises(undine_settings) -> None:

    context = make_hook_context(source="mutation @atomic { dummy }")
    hook = AtomicMutationHook(context=context)

    gen = hook.on_execution_async()
    with pytest.raises(GraphQLAsyncAtomicMutationNotSupportedError):
        await anext(gen)


# RequestCacheHook


@pytest.mark.django_db
def test_request_cache_hook__result_not_execution_result(undine_settings) -> None:

    context = make_hook_context(source="query { field }")
    hook = RequestCacheHook(context=context)
    gen = hook.on_execution()

    # Patch RequestCacheCalculator.run so we get cache_time > 0
    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        next(gen)  # enters, gets past cache_time > 0 check, cache miss, reaches main yield

    context.result = "not_an_execution_result"  # will hit the `not isinstance` branch

    with contextlib.suppress(StopIteration):
        next(gen)  # runs: if not isinstance → return


@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_non_query(undine_settings) -> None:

    context = make_hook_context(source="mutation { dummy }")
    hook = RequestCacheHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # yields at non-query early return

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


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


@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_read_predicate_false(undine_settings) -> None:
    undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False
    undine_settings.REQUEST_CACHE_WRITE_PREDICATE = lambda _: False

    context = make_hook_context(source="query { field }")
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        gen = hook.on_execution_async()
        await anext(gen)  # predicate=False → skips cache read → yields at 302

        context.result = ExecutionResult(data={"field": "value"})

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_result_not_execution_result(undine_settings) -> None:
    undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False

    context = make_hook_context(source="query { field }")
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = "not_an_execution_result"

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_result_has_errors(undine_settings) -> None:
    undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False

    context = make_hook_context(source="query { field }")
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = ExecutionResult(data=None, errors=[GraphQLError("error")])

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_request_cache_hook__async_write_predicate_false(undine_settings) -> None:
    undine_settings.REQUEST_CACHE_READ_PREDICATE = lambda _: False
    undine_settings.REQUEST_CACHE_WRITE_PREDICATE = lambda _: False

    context = make_hook_context(source="query { field }")
    hook = RequestCacheHook(context=context)

    mock_results = type("R", (), {"cache_time": 10, "cache_per_user": False})()
    with patch.object(RequestCacheCalculator, "run", return_value=mock_results):
        gen = hook.on_execution_async()
        await anext(gen)  # yields at 302

        context.result = ExecutionResult(data={"field": "value"}, errors=None)

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


# AutomaticPersistedQueriesHook


@pytest.mark.django_db
def test_apq_hook__non_query_operation(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    source = "mutation { dummy }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = make_hook_context(source=source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution()
    next(gen)  # should hit: operation != QUERY → yield; return

    with contextlib.suppress(StopIteration):
        next(gen)


@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_no_persisted_query(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    context = make_hook_context(source="query { field }")  # no persistedQuery in extensions
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # no persistedQuery → yield; return immediately

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_non_query_operation(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    source = "mutation { dummy }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = make_hook_context(source=source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # non-query → yield; return

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_saves_document(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    source = "query { field }"
    sha_hash = hashlib.sha256(source.encode()).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}

    context = make_hook_context(source=source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # saves PersistedDocument, then yields

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    document_id = to_document_id(source)
    assert await PersistedDocument.objects.filter(document_id=document_id).aexists()


@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_hash_mismatch(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    source = "query { field }"
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": "wrong_hash"}}

    context = make_hook_context(source=source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # hash mismatch → sets context.result, yields

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    assert isinstance(context.result, ExecutionResult)
    assert context.result.errors


@pytest.mark.django_db(transaction=True)
async def test_apq_hook__async_invalid_persisted_query_format(undine_settings) -> None:
    undine_settings.AUTOMATIC_PERSISTED_QUERIES = True

    source = "query { field }"
    # Missing "version" key → GraphQLAPQVersionMissingError (a GraphQLError subclass)
    extensions: dict[str, Any] = {"persistedQuery": {}}

    context = make_hook_context(source=source, extensions=extensions)
    hook = AutomaticPersistedQueriesHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # APQ version missing → except GraphQLError → set result, yield

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)

    assert isinstance(context.result, ExecutionResult)
    assert context.result.errors


# VisibilityCacheHook


@pytest.mark.django_db
def test_visibility_cache_hook__is_enabled__disabled_by_timeout(undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 0

    assert VisibilityCacheHook.is_enabled() is False


@pytest.mark.django_db
def test_visibility_cache_hook__is_enabled__disabled_when_schema_visibility_inactive(undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert VisibilityCacheHook.is_enabled() is False


@pytest.mark.django_db
def test_visibility_cache_hook__is_enabled__schema_uses_visibility(undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert VisibilityCacheHook.is_enabled() is True


@pytest.mark.django_db
def test_visibility_cache_hook__should_cache__disabled_for_non_query_operation(undine_settings) -> None:
    undine_settings.VISIBILITY_CACHE_TIMEOUT = 60

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @classmethod
        def __is_visible__(cls, request: DjangoRequestProtocol) -> bool:
            return True

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)
    apply_visibility(undine_settings.SCHEMA)

    context = make_hook_context(source="mutation IntrospectionQuery { dummy }")
    context.operation_name = "IntrospectionQuery"
    hook = VisibilityCacheHook(context=context)

    assert hook.should_cache() is False


@pytest.mark.django_db
def test_visibility_cache_hook__sync_no_cache__early_yield(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)
    gen = hook.on_execution()

    next(gen)  # should_cache=False → yield and return

    with contextlib.suppress(StopIteration):
        next(gen)


@pytest.mark.django_db
def test_visibility_cache_hook__sync_result_not_execution_result(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    with patch.object(VisibilityCacheHook, "should_cache", return_value=True):
        gen = hook.on_execution()
        next(gen)  # cache miss → yields at line 365

        context.result = "not_an_execution_result"  # will hit `not isinstance` branch (line 368-369)

        with contextlib.suppress(StopIteration):
            next(gen)


@pytest.mark.django_db
def test_visibility_cache_hook__sync_result_has_errors(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    with patch.object(VisibilityCacheHook, "should_cache", return_value=True):
        gen = hook.on_execution()
        next(gen)  # cache miss → yields

        context.result = ExecutionResult(data=None, errors=[GraphQLError("boom")])

        with contextlib.suppress(StopIteration):
            next(gen)


@pytest.mark.django_db(transaction=True)
async def test_visibility_cache_hook__async_no_cache__early_yield(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    gen = hook.on_execution_async()
    await anext(gen)  # should_cache=False → yields and returns

    with contextlib.suppress(StopAsyncIteration):
        await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_visibility_cache_hook__async_cache_miss_writes_result(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    with patch.object(VisibilityCacheHook, "should_cache", return_value=True):
        # Ensure cache is empty
        hook.cache.clear()

        gen = hook.on_execution_async()
        await anext(gen)  # cache miss → yields

        context.result = ExecutionResult(data={"field": "value"}, errors=None)

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_visibility_cache_hook__async_cache_hit_returns_cached(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    cached = ExecutionResult(data={"field": "cached_value"}, errors=None)

    with (
        patch.object(VisibilityCacheHook, "should_cache", return_value=True),
        patch("django.core.cache.backends.locmem.LocMemCache.aget", return_value=cached),
    ):
        gen = hook.on_execution_async()
        await anext(gen)  # cache hit → sets context.result and yields

        assert context.result is cached

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_visibility_cache_hook__async_result_not_execution_result(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    with patch.object(VisibilityCacheHook, "should_cache", return_value=True):
        hook.cache.clear()

        gen = hook.on_execution_async()
        await anext(gen)  # cache miss → yields

        context.result = "not_an_execution_result"

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


@pytest.mark.django_db(transaction=True)
async def test_visibility_cache_hook__async_result_has_errors(undine_settings) -> None:
    context = make_hook_context(source="query { field }")
    hook = VisibilityCacheHook(context=context)

    with patch.object(VisibilityCacheHook, "should_cache", return_value=True):
        hook.cache.clear()

        gen = hook.on_execution_async()
        await anext(gen)  # cache miss → yields

        context.result = ExecutionResult(data=None, errors=[GraphQLError("boom")])

        with contextlib.suppress(StopAsyncIteration):
            await anext(gen)


# ParseCacheHook


@pytest.mark.django_db
def test_parse_cache_hook__same_document_is_parsed_once(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DocumentRecordingHook]
    undine_settings.PARSE_CACHE_MAX_SIZE = 10

    DocumentRecordingHook.documents.clear()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    assert graphql(query).has_errors is False
    assert graphql(query).has_errors is False

    assert len(DocumentRecordingHook.documents) == 2
    assert DocumentRecordingHook.documents[0] is DocumentRecordingHook.documents[1]


@pytest.mark.django_db
def test_parse_cache_hook__disabled_by_max_size(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DocumentRecordingHook]
    undine_settings.PARSE_CACHE_MAX_SIZE = 0

    DocumentRecordingHook.documents.clear()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    assert graphql(query).has_errors is False
    assert graphql(query).has_errors is False

    assert len(DocumentRecordingHook.documents) == 2
    assert DocumentRecordingHook.documents[0] is not DocumentRecordingHook.documents[1]


@pytest.mark.django_db
def test_parse_cache_hook__least_recently_used_document_is_discarded(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DocumentRecordingHook]
    undine_settings.PARSE_CACHE_MAX_SIZE = 1

    DocumentRecordingHook.documents.clear()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert graphql("query { tasks { name } }").has_errors is False
    assert graphql("query { tasks { done } }").has_errors is False
    assert graphql("query { tasks { name } }").has_errors is False

    assert len(DocumentRecordingHook.documents) == 3
    assert DocumentRecordingHook.documents[0] is not DocumentRecordingHook.documents[2]


@pytest.mark.django_db
def test_parse_cache_hook__max_tokens_is_part_of_the_cache_key(graphql, undine_settings) -> None:
    undine_settings.PARSE_CACHE_MAX_SIZE = 10

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    assert graphql(query).has_errors is False

    undine_settings.MAX_TOKENS = 2

    assert graphql(query).errors == [
        {
            "message": "Syntax Error: Document contains more than 2 tokens. Parsing aborted.",
            "locations": [{"line": 1, "column": 9}],
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_parse_cache_hook__document_that_cannot_be_parsed_is_not_cached(graphql, undine_settings) -> None:
    undine_settings.PARSE_CACHE_MAX_SIZE = 10

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    source = "query { tasks {"

    assert graphql(source).has_errors is True

    context = make_hook_context(source="query { hello }")
    context.source = source
    hook = ParseCacheHook(context=context)

    assert ParseCacheHook.cache.get(hook.get_cache_key()) is None


def test_parse_cache_hook__document_from_another_hook_is_kept(undine_settings) -> None:
    undine_settings.PARSE_CACHE_MAX_SIZE = 10

    context = make_hook_context()
    document = context.document
    hook = ParseCacheHook(context=context)

    gen = hook.on_parse()
    next(gen)

    assert context.document is document

    with contextlib.suppress(StopIteration):
        next(gen)

    assert ParseCacheHook.cache.get(hook.get_cache_key()) is None


# ValidationCacheHook


@pytest.mark.django_db
def test_validation_cache_hook__same_document_is_validated_once(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_VALIDATION_RULES = [CountingValidationRule]
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10
    CountingValidationRule.runs = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    assert graphql(query).has_errors is False
    assert graphql(query).has_errors is False

    assert CountingValidationRule.runs == 1


@pytest.mark.django_db(transaction=True)
async def test_validation_cache_hook__async_same_document_is_validated_once(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.ADDITIONAL_VALIDATION_RULES = [CountingValidationRule]
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    CountingValidationRule.runs = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    result = await graphql_async(query)
    assert result.has_errors is False

    result = await graphql_async(query)
    assert result.has_errors is False

    assert CountingValidationRule.runs == 1


@pytest.mark.django_db
def test_validation_cache_hook__disabled_by_max_size(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_VALIDATION_RULES = [CountingValidationRule]
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 0

    CountingValidationRule.runs = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { name } }"

    assert graphql(query).has_errors is False
    assert graphql(query).has_errors is False

    assert CountingValidationRule.runs == 2


@pytest.mark.django_db
def test_validation_cache_hook__document_with_errors_is_not_cached(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_VALIDATION_RULES = [CountingValidationRule]
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    CountingValidationRule.runs = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { missing } }"

    errors = [
        {
            "message": "Cannot query field 'missing' on type 'TaskType'.",
            "extensions": {"status_code": 400},
        }
    ]

    assert graphql(query).errors == errors
    assert graphql(query).errors == errors

    assert CountingValidationRule.runs == 2


@pytest.mark.django_db
def test_validation_cache_hook__least_recently_used_document_is_discarded(graphql, undine_settings) -> None:
    undine_settings.ADDITIONAL_VALIDATION_RULES = [CountingValidationRule]
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 1

    CountingValidationRule.runs = 0

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assert graphql("query { tasks { name } }").has_errors is False
    assert graphql("query { tasks { done } }").has_errors is False
    assert graphql("query { tasks { name } }").has_errors is False

    assert CountingValidationRule.runs == 3


@pytest.mark.django_db
def test_validation_cache_hook__result_for_another_schema_is_not_used(graphql, undine_settings) -> None:
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class QueryWithTasks(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class QueryWithProjects(RootType):
        projects = Entrypoint(ProjectType, many=True)

    query = "query { tasks { name } }"

    undine_settings.SCHEMA = create_schema(query=QueryWithTasks)

    assert graphql(query).has_errors is False

    undine_settings.SCHEMA = create_schema(query=QueryWithProjects)

    assert graphql(query).errors == [
        {
            "message": "Cannot query field 'tasks' on type 'QueryWithProjects'.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
@skip_if_async
def test_validation_cache_hook__visibility__result_is_not_shared_between_users(graphql, undine_settings) -> None:
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        secret = Field("name")

        @secret.visible
        def secret_visible(self, request: DjangoRequestProtocol) -> bool:
            return request.user.is_superuser

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query { tasks { secret } }"

    graphql.login_with_superuser()

    assert graphql(query).has_errors is False

    graphql.logout()

    assert graphql(query).errors == [
        {
            "message": "Cannot query field 'secret' on type 'TaskType'.",
            "extensions": {"status_code": 400},
        }
    ]


@pytest.mark.django_db
def test_validation_cache_hook__visibility__result_is_not_shared_between_variables(graphql, undine_settings) -> None:
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    class TaskFilterSet(FilterSet[Task], auto=False):
        name = Filter()
        filler = Filter("pk")

        @name.visible
        def name_visible(self, request: DjangoRequestProtocol) -> bool:
            return False

    @TaskFilterSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = "query($filter: TaskFilterSet!) { tasks(filter: $filter) { name } }"

    assert graphql(query, variables={"filter": {"filler": 1}}).has_errors is False

    assert graphql(query, variables={"filter": {"name": "foo"}}).errors == [
        {
            "message": "Field 'name' is not defined by type 'TaskFilterSet'.",
            "extensions": {"status_code": 400},
        }
    ]


def test_validation_cache_hook__errors_from_another_hook_are_kept(undine_settings) -> None:
    undine_settings.VALIDATION_CACHE_MAX_SIZE = 10

    error = GraphQLError("Cannot query field 'hello' on type 'Query'.")

    context = make_hook_context()
    context.validation_errors = [error]
    hook = ValidationCacheHook(context=context)

    gen = hook.on_validation()
    next(gen)

    assert context.validation_errors == [error]

    with contextlib.suppress(StopIteration):
        next(gen)
