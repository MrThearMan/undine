from __future__ import annotations

import re
from functools import wraps
from typing import Any, Callable, Literal

import pytest
from graphql import Undefined

from undine.errors.exceptions import FunctionDispatcherError
from undine.utils.function_dispatcher import FunctionDispatcher


def test_function_dispatcher__name() -> None:
    func = FunctionDispatcher()
    assert func.name == "func"


def test_function_dispatcher__no_registered_implementation() -> None:
    func = FunctionDispatcher()
    msg = "'func' doesn't contain an implementation for '<class 'str'>' (test)."
    with pytest.raises(FunctionDispatcherError, match=re.escape(msg)):
        func("test")


def test_function_dispatcher__use_implementation() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: str) -> str:
        return key

    assert func("test") == "test"


def test_function_dispatcher__wrong_implementation() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: str) -> str:
        return key

    msg = "'func' doesn't contain an implementation for '<class 'int'>' (1)."
    with pytest.raises(FunctionDispatcherError, match=re.escape(msg)):
        func(1)


def test_function_dispatcher__any_implementation() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: Any) -> Any:
        return key

    assert func("test") == "test"
    assert func(1) == 1


def test_function_dispatcher__different_implementations() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: int) -> int:
        return -key

    @func.register
    def _(key: str) -> str:
        return f"{key}-"

    assert func("test") == "test-"
    assert func(1) == -1


def test_function_dispatcher__use_parent_implementation() -> None:
    func = FunctionDispatcher()

    class Parent:
        foo = 1

    class Child(Parent):
        bar = 2

    @func.register
    def _(key: Parent) -> int:
        return key.foo

    assert func(Child) == 1


def test_function_dispatcher__nullable() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: type[int]) -> type[int]:
        return key

    assert func(int | None) == int


def test_function_dispatcher__return_nullable() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: type[int]) -> type[int]:
        return key

    assert func(int | None, return_nullable=True) == (int, True)
    assert func(int, return_nullable=True) == (int, False)


def test_function_dispatcher__wrapper() -> None:
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def inner(value, **kwargs) -> int:
            return 1

        return inner

    func = FunctionDispatcher(wrapper=wrapper)

    @func.register
    def _(key: int) -> int:
        return key

    assert func(2) == 1
    assert func(3) == 1


def test_function_dispatcher__union_default() -> None:
    func = FunctionDispatcher(union_default=type)

    @func.register
    def _(key: type[int]) -> type[int]:
        return key

    @func.register
    def _(key: type[str]) -> type[str]:
        return key

    @func.register
    def _(key: type) -> type:
        return Any

    assert func(int) == int
    assert func(str) == str
    assert func(str | int) == Any


def test_function_dispatcher__undefined() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(key: Any) -> Any:
        return key

    msg = "FunctionDispatcher key must be a type or value."
    with pytest.raises(FunctionDispatcherError, match=re.escape(msg)):
        func(Undefined)


def test_function_dispatcher__literal() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(_: Literal["foo"]) -> str:
        return "1"

    @func.register
    def _(_: Literal["bar"]) -> str:
        return "2"

    assert func("foo") == "1"
    assert func("bar") == "2"


def test_function_dispatcher__literal__union() -> None:
    func = FunctionDispatcher()

    @func.register
    def _(_: Literal["foo", "bar"]) -> str:
        return "1"

    assert func("foo") == "1"
    assert func("bar") == "1"
