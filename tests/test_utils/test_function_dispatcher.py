from __future__ import annotations

from functools import wraps
from types import FunctionType
from typing import Any, Callable, Literal, NotRequired, Required

import pytest
from graphql import Undefined

from tests.helpers import exact
from undine.errors.exceptions import FunctionDispatcherError
from undine.typing import Lambda
from undine.utils.function_dispatcher import FunctionDispatcher


def test_function_dispatcher__name() -> None:
    dispatcher = FunctionDispatcher()
    assert dispatcher.__name__ == "dispatcher"


def test_function_dispatcher__no_registered_implementation() -> None:
    dispatcher = FunctionDispatcher()
    msg = "'dispatcher' doesn't contain an implementation for '<class 'str'>' (test)."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher("test")


def test_function_dispatcher__use_implementation() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: str) -> str:
        return key

    assert dispatcher("test") == "test"


def test_function_dispatcher__wrong_implementation() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: str) -> str:
        return key

    msg = "'dispatcher' doesn't contain an implementation for '<class 'int'>' (1)."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher(1)


def test_function_dispatcher__any_implementation() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: Any) -> Any:
        return key

    assert dispatcher("test") == "test"
    assert dispatcher(1) == 1


def test_function_dispatcher__different_implementations() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: int) -> int:  # noqa: FURB118
        return -key

    @dispatcher.register
    def _(key: str) -> str:
        return f"{key}-"

    assert dispatcher("test") == "test-"
    assert dispatcher(1) == -1


def test_function_dispatcher__use_parent_implementation() -> None:
    dispatcher = FunctionDispatcher()

    class Parent:
        foo = 1

    class Child(Parent):
        bar = 2

    @dispatcher.register
    def _(key: Parent) -> int:
        return key.foo

    assert dispatcher(Child) == 1


def test_function_dispatcher__nullable():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: type[int]) -> type[int]:
        return key

    assert dispatcher(int | None) == int


def test_function_dispatcher__return_nullable():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: type[int]) -> type[int]:
        return key

    assert dispatcher(int | None, return_nullable=True) == (int, True)
    assert dispatcher(int, return_nullable=True) == (int, False)


def test_function_dispatcher__wrapper():
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        def inner(value, **kwargs) -> int:
            return 1

        return inner

    dispatcher = FunctionDispatcher(wrapper=wrapper)

    @dispatcher.register
    def _(key: int) -> int:
        return key

    assert dispatcher(2) == 1
    assert dispatcher(3) == 1


def test_function_dispatcher__union_default():
    dispatcher = FunctionDispatcher(union_default=type)

    @dispatcher.register
    def _(key: type[int]) -> type[int]:
        return key

    @dispatcher.register
    def _(key: type[str]) -> type[str]:
        return key

    @dispatcher.register
    def _(key: type) -> type:
        return Any

    assert dispatcher(int) == int
    assert dispatcher(str) == str
    assert dispatcher(str | int) == Any


def test_function_dispatcher__undefined() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(key: Any) -> Any:
        return key

    msg = "FunctionDispatcher key must be a type or value."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher(Undefined)


def test_function_dispatcher__literal() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(_: Literal["foo"]) -> str:
        return "1"

    @dispatcher.register
    def _(_: Literal["bar"]) -> str:
        return "2"

    assert dispatcher("foo") == "1"
    assert dispatcher("bar") == "2"


def test_function_dispatcher__literal__union() -> None:
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(_: Literal["foo", "bar"]) -> str:
        return "1"

    assert dispatcher("foo") == "1"
    assert dispatcher("bar") == "1"


def test_function_dispatcher__must_register_a_function():
    dispatcher = FunctionDispatcher()

    msg = "Can only register functions with 'dispatcher'. Got None."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher.register(None)  # type: ignore[arg-type]


def test_function_dispatcher__cannot_register_implementation_for_undefined():
    dispatcher = FunctionDispatcher()

    msg = "Cannot register function 'my_impl' for 'dispatcher': First argument type cannot be 'Undefined'."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl(key: Undefined) -> str:
            return key


def test_function_dispatcher__no_arguments():
    dispatcher = FunctionDispatcher()

    msg = "Function 'my_impl' must have at least one argument so that it can be registered for 'dispatcher'."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl() -> str:
            return ""


def test_function_dispatcher__first_argument_missing_type():
    dispatcher = FunctionDispatcher()

    msg = (
        "Function 'my_impl' must have a type hint for its first argument "
        "so that it can be registered for 'dispatcher'."
    )
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl(key) -> str:
            return ""


def test_function_dispatcher__cannot_register_union_generic():
    dispatcher = FunctionDispatcher()

    msg = "'dispatcher' cannot register an implementation for type 'type[str | int]'."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl(key: type[str | int]) -> str:
            return ""


def test_function_dispatcher__multiple_union_types():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def my_impl(key: str) -> str:
        return ""

    msg = "Union type must have a single non-null type argument, got (<class 'str'>, <class 'int'>)."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher(str | int | None)


def test_function_dispatcher__function():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: FunctionType) -> str:
        return ref()

    def func() -> str:
        return "foo"

    value = dispatcher(func)

    assert value == "foo"


def test_function_dispatcher__lambda():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: Lambda) -> str:
        return ref()

    value = dispatcher(lambda: "foo")

    assert value == "foo"


def test_function_dispatcher__lambda__not_confused_with_function():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def _(ref: Lambda) -> str:
        return ref()

    @dispatcher.register
    def _(ref: FunctionType) -> str:
        return "bar"

    value = dispatcher(lambda: "foo")

    assert value == "foo"


def test_function_dispatcher__not_required():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: int) -> int:
        return ref

    assert dispatcher(NotRequired[int]) == int
    assert dispatcher(NotRequired[int], return_nullable=True) == (int, True)


def test_function_dispatcher__required():
    dispatcher = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: int) -> int:
        return ref

    assert dispatcher(Required[int]) == int
    assert dispatcher(Required[int], return_nullable=True) == (int, False)
