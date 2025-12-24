from __future__ import annotations

from typing import Any, AsyncGenerator, Generator

import pytest
from graphql import GraphQLFieldResolver

from tests.helpers import mock_gql_info
from undine import Entrypoint, GQLInfo, RootType, create_schema
from undine.execution import _get_middleware_manager  # noqa: PLC2701
from undine.hooks import (
    ExecutionLifecycleHookManager,
    LifecycleHook,
    LifecycleHookContext,
    OperationLifecycleHookManager,
    ParseLifecycleHookManager,
    ValidationLifecycleHookManager,
)


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
