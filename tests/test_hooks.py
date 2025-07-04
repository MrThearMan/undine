from __future__ import annotations

from typing import AsyncGenerator, Generator

import pytest
from graphql import ExecutionResult, GraphQLError

from undine.hooks import (
    LifecycleHook,
    LifecycleHookContext,
    LifecycleHookManager,
    use_lifecycle_hooks_async,
    use_lifecycle_hooks_sync,
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


def test_lifecycle_hook() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    hook = MyHook(context=get_default_context())

    with hook.use_sync():
        call_stack.append("inside")

    assert call_stack == ["before", "inside", "after"]


def test_lifecycle_hook__context() -> None:
    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            self.context.variables["hello"] = "world"
            yield
            self.context.variables["hello"] = "undine"

    context = get_default_context()
    context.variables["hello"] = "you"

    hook = MyHook(context=context)

    assert context.variables["hello"] == "you"

    with hook.use_sync():
        assert context.variables["hello"] == "world"

    assert context.variables["hello"] == "undine"


def test_lifecycle_hook_manager() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            nonlocal call_stack

            call_stack.append("my before")
            yield
            call_stack.append("my after")

    class YourHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("your before")
            yield
            call_stack.append("your after")

    context = get_default_context()

    with LifecycleHookManager(hooks=[MyHook, YourHook], context=context):
        call_stack.append("inside")

    assert call_stack == ["my before", "your before", "inside", "your after", "my after"]


def test_use_lifecycle_hooks_sync() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks_sync(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "inside", "after"]


def test_use_lifecycle_hooks_sync__error_raised() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks_sync(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    with pytest.raises(ValueError, match="Error"):
        func(ctx)

    assert call_stack == ["before", "inside"]

    assert ctx.result is None


def test_use_lifecycle_hooks_sync__error_raised__catch() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            try:
                yield
            except ValueError as error:
                call_stack.append("after")
                self.context.result = ExecutionResult(errors=[GraphQLError(str(error))])

    @use_lifecycle_hooks_sync(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "inside", "after"]

    assert isinstance(ctx.result, ExecutionResult)
    assert ctx.result.data is None
    assert ctx.result.errors == [GraphQLError("Error")]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")

    ctx = get_default_context()

    await func(ctx)

    assert call_stack == ["before", "inside", "after"]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async__error_raised() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    with pytest.raises(ValueError, match="Error"):
        await func(ctx)

    assert call_stack == ["before", "inside"]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async__error_raised__catch() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            try:
                yield
            except ValueError as error:
                call_stack.append("after")
                self.context.result = ExecutionResult(errors=[GraphQLError(str(error))])

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    await func(ctx)

    assert call_stack == ["before", "inside", "after"]

    assert isinstance(ctx.result, ExecutionResult)
    assert ctx.result.data is None
    assert ctx.result.errors == [GraphQLError("Error")]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async__run_async() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

        async def run_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before async")
            yield
            call_stack.append("after async")

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")

    ctx = get_default_context()

    await func(ctx)

    assert call_stack == ["before async", "inside", "after async"]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async__run_async__error_raised() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

        async def run_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before async")
            yield
            call_stack.append("after async")

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    with pytest.raises(ValueError, match="Error"):
        await func(ctx)

    assert call_stack == ["before async", "inside"]


@pytest.mark.asyncio
async def test_use_lifecycle_hooks_async__run_async__error_raised__catch() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            try:
                yield
            except ValueError as error:
                call_stack.append("after")
                self.context.result = ExecutionResult(errors=[GraphQLError(str(error))])

        async def run_async(self) -> AsyncGenerator[None, None]:
            call_stack.append("before async")
            try:
                yield
            except ValueError as error:
                call_stack.append("after async")
                self.context.result = ExecutionResult(errors=[GraphQLError(str(error))])

    @use_lifecycle_hooks_async(hooks=[MyHook])
    async def func(context: LifecycleHookContext) -> None:  # noqa: RUF029
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    await func(ctx)

    assert call_stack == ["before async", "inside", "after async"]

    assert isinstance(ctx.result, ExecutionResult)
    assert ctx.result.data is None
    assert ctx.result.errors == [GraphQLError("Error")]
