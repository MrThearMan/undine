from __future__ import annotations

from typing import Generator

import pytest
from graphql import ExecutionResult, GraphQLError

from undine.hooks import LifecycleHook, LifecycleHookContext, LifecycleHookManager, use_lifecycle_hooks


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

    with hook.use():
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

    with hook.use():
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


def test_use_lifecycle_hooks() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "inside", "after"]


def test_use_lifecycle_hooks__set_result_in_hook() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            self.context.result = ExecutionResult(data={"hello": "world"})
            yield
            call_stack.append("after")

    @use_lifecycle_hooks(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "after"]

    assert ctx.result is not None
    assert ctx.result.data == {"hello": "world"}
    assert ctx.result.errors is None


def test_use_lifecycle_hooks__graphql_error_raised() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")
        msg = "Error"
        raise GraphQLError(msg)

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "inside", "after"]

    assert ctx.result is not None
    assert ctx.result.data is None
    assert ctx.result.errors == [GraphQLError("Error")]


def test_use_lifecycle_hooks__non_graphql_error_raised() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")
            yield
            call_stack.append("after")

    @use_lifecycle_hooks(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    with pytest.raises(ValueError, match="Error"):
        func(ctx)

    assert call_stack == ["before", "inside"]

    assert ctx.result is None


def test_use_lifecycle_hooks__non_graphql_error_raised__catch() -> None:
    call_stack: list[str] = []

    class MyHook(LifecycleHook):
        def run(self) -> Generator[None, None, None]:
            call_stack.append("before")

            try:
                yield
            except ValueError as error:
                call_stack.append("after")
                self.context.result = ExecutionResult(errors=[GraphQLError(str(error))])

    @use_lifecycle_hooks(hooks=[MyHook])
    def func(context: LifecycleHookContext) -> None:
        call_stack.append("inside")
        msg = "Error"
        raise ValueError(msg)

    ctx = get_default_context()

    func(ctx)

    assert call_stack == ["before", "inside", "after"]

    assert ctx.result is not None
    assert ctx.result.data is None
    assert ctx.result.errors == [GraphQLError("Error")]
