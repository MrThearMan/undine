from __future__ import annotations

from functools import wraps
from types import FunctionType
from typing import Any, Callable, Literal, NotRequired, Protocol, Required, runtime_checkable

import pytest
from graphql import Undefined

from tests.helpers import exact
from undine.exceptions import FunctionDispatcherError, FunctionDispatcherImplementationNotFoundError
from undine.typing import Lambda
from undine.utils.function_dispatcher import FunctionDispatcher


def test_function_dispatcher__name() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()
    assert dispatcher.__name__ == "dispatcher"


def test_function_dispatcher__no_registered_implementation() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()
    with pytest.raises(FunctionDispatcherImplementationNotFoundError):
        dispatcher("test")


def test_function_dispatcher__use_implementation() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(key: str) -> str:
        return key

    assert dispatcher("test") == "test"


def test_function_dispatcher__use_implementation__none() -> None:
    dispatcher: FunctionDispatcher[None] = FunctionDispatcher()

    @dispatcher.register
    def _(key: None) -> None:
        return key

    assert dispatcher(None) is None


def test_function_dispatcher__use_implementation__type() -> None:
    dispatcher: FunctionDispatcher[type] = FunctionDispatcher()

    @dispatcher.register
    def _(key: type) -> type:
        return key

    assert dispatcher(type) is type


def test_function_dispatcher__wrong_implementation() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(key: str) -> str:  # pragma: no cover
        return key

    with pytest.raises(FunctionDispatcherImplementationNotFoundError):
        dispatcher(1)


def test_function_dispatcher__any_implementation() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(key: Any) -> Any:
        return key

    assert dispatcher("test") == "test"
    assert dispatcher(1) == 1
    assert dispatcher(Undefined) is Undefined


def test_function_dispatcher__different_implementations() -> None:
    dispatcher: FunctionDispatcher[int | str] = FunctionDispatcher()

    @dispatcher.register
    def _(key: int) -> int:  # noqa: FURB118
        return -key

    @dispatcher.register
    def _(key: str) -> str:
        return f"{key}-"

    assert dispatcher("test") == "test-"
    assert dispatcher(1) == -1


def test_function_dispatcher__use_parent_implementation() -> None:
    dispatcher: FunctionDispatcher[int] = FunctionDispatcher()

    class Parent:
        foo = 1

    class Child(Parent):
        bar = 2

    @dispatcher.register
    def _(key: Parent) -> int:
        return key.foo

    assert dispatcher(Child()) == 1


def test_function_dispatcher__class_should_not_use_instance_implementation() -> None:
    dispatcher: FunctionDispatcher[int] = FunctionDispatcher()

    class Parent:
        foo = 1

    class Child(Parent):
        bar = 2

    @dispatcher.register
    def _(key: Parent) -> int:
        return key.foo  # pragma: no cover

    with pytest.raises(FunctionDispatcherError):
        dispatcher(Child)


def test_function_dispatcher__nullable() -> None:
    dispatcher: FunctionDispatcher[type[int]] = FunctionDispatcher()

    @dispatcher.register
    def _(key: type[int]) -> type[int]:
        return key

    assert dispatcher(int | None) == int


def test_function_dispatcher__wrapper() -> None:
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


def test_function_dispatcher__undefined() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(key: Undefined) -> str:
        return key

    assert dispatcher(Undefined) is Undefined


def test_function_dispatcher__literal() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(_: Literal["foo"]) -> str:
        return "1"

    @dispatcher.register
    def _(_: Literal["bar"]) -> str:
        return "2"

    assert dispatcher("foo") == "1"
    assert dispatcher("bar") == "2"


def test_function_dispatcher__literal__union() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(_: Literal["foo", "bar"]) -> str:
        return "1"

    assert dispatcher("foo") == "1"
    assert dispatcher("bar") == "1"


def test_function_dispatcher__must_register_a_function() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    msg = "Can only register functions with 'dispatcher'. Got None."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher.register(None)


def test_function_dispatcher__no_arguments() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    msg = "Function 'my_impl' must have at least one argument so that it can be registered for 'dispatcher'."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl() -> str: ...


def test_function_dispatcher__first_argument_missing_type() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    msg = (
        "Function 'my_impl' must have a type hint for its first argument so that it can be registered for 'dispatcher'."
    )
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):

        @dispatcher.register
        def my_impl(key) -> str: ...


def test_function_dispatcher__register_union_generic() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(key: type[str | int]) -> Any:
        return key

    assert dispatcher(int) == int
    assert dispatcher(str) == str


def test_function_dispatcher__multiple_union_types() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(key: str) -> str:
        return ""

    msg = "Union type must have a single non-null type argument, got (<class 'str'>, <class 'int'>)."
    with pytest.raises(FunctionDispatcherError, match=exact(msg)):
        dispatcher(str | int | None)


def test_function_dispatcher__function() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: FunctionType) -> str:
        return ref()

    def func() -> str:
        return "foo"

    value = dispatcher(func)

    assert value == "foo"


def test_function_dispatcher__lambda() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: Lambda) -> str:
        return ref()

    value = dispatcher(lambda: "foo")

    assert value == "foo"


def test_function_dispatcher__lambda__not_confused_with_function() -> None:
    dispatcher: FunctionDispatcher[str] = FunctionDispatcher()

    @dispatcher.register
    def _(ref: Lambda) -> str:
        return ref()

    @dispatcher.register
    def _(ref: FunctionType) -> str:
        return "bar"

    value = dispatcher(lambda: "foo")

    assert value == "foo"


def test_function_dispatcher__not_required() -> None:
    dispatcher: FunctionDispatcher[type[int]] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: type[int], **kwargs: Any) -> type[int]:
        return ref

    assert dispatcher(NotRequired[int]) == int


def test_function_dispatcher__required() -> None:
    dispatcher: FunctionDispatcher[type[int]] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: type[int], **kwargs: Any) -> type[int]:
        return ref

    assert dispatcher(Required[int]) == int


def test_function_dispatcher__protocols() -> None:
    @runtime_checkable
    class MyProtocol(Protocol):
        def foo(self, a: int) -> int: ...

    dispatcher: FunctionDispatcher[int] = FunctionDispatcher()

    @dispatcher.register
    def my_impl(ref: MyProtocol, **kwargs: Any) -> int:
        return 1

    class Foo:
        def foo(self, a: int) -> int: ...

    assert dispatcher(Foo) == 1


def test_function_dispatcher__literals() -> None:
    dispatcher: FunctionDispatcher[int] = FunctionDispatcher()

    @dispatcher.register
    def my_impl_1(ref: Literal[1], **kwargs: Any) -> int:
        return 11

    @dispatcher.register
    def my_impl_2(ref: Literal[2], **kwargs: Any) -> int:
        return 22

    assert dispatcher(1) == 11

    assert dispatcher(2) == 22
