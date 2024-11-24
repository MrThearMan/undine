from __future__ import annotations

from functools import partial, wraps
from inspect import Parameter
from typing import TYPE_CHECKING

import pytest

from undine.errors.exceptions import FunctionSignatureParsingError
from undine.utils.reflection import FunctionEqualityWrapper, get_signature, get_wrapped_func, swappable_by_subclassing


def test_swappable_by_subclassing():
    @swappable_by_subclassing
    class A:
        def __init__(self, arg: int = 1) -> None:
            self.one = arg

    a = A()
    assert type(a) is A
    assert a.one == 1

    class B(A):
        def __init__(self, arg: int = 1) -> None:
            super().__init__(arg)
            self.two = arg * 2

    b = A(2)
    assert type(b) is B
    assert b.one == 2
    assert b.two == 4

    class C(A):
        def __init__(self, arg: int = 1, second_arg: int = 2) -> None:
            super().__init__(arg)
            self.three = second_arg * 3

    c = A(3, 4)
    assert type(c) is C
    assert c.one == 3
    assert not hasattr(c, "two")
    assert c.three == 12

    class D(B): ...

    d = A()
    assert type(d) is C  # Only direct subclasses are swapped.


def test_get_wrapped_func():
    def func(): ...

    assert get_wrapped_func(func) == func


def test_get_wrapped_func__method():
    class Foo:
        def func(self): ...

    assert get_wrapped_func(Foo.func) == Foo.func


def test_get_wrapped_func__property():
    class Foo:
        @property
        def func(self): ...

    assert get_wrapped_func(Foo.func) == Foo.func.fget


def test_get_wrapped_func__partial():
    def func(x: int): ...

    foo = partial(func, 1)

    assert get_wrapped_func(foo) == func


def test_get_wrapped_func__wrapped():
    def inner(): ...
    def func(): ...

    foo = wraps(func)(inner)

    assert get_wrapped_func(foo) == func


def test_function_equality_wrapper__called():
    def func() -> str:
        return "foo"

    wrapped = FunctionEqualityWrapper(func, context=1)
    assert wrapped() == "foo"


def test_function_equality_wrapper__same_context():
    def func() -> str:
        return "foo"

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    wrapped_2 = FunctionEqualityWrapper(func, context=1)

    assert wrapped_1 == wrapped_2


def test_function_equality_wrapper__different_context():
    def func() -> str:
        return "foo"

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    wrapped_2 = FunctionEqualityWrapper(func, context=2)

    assert wrapped_1 != wrapped_2


def test_function_equality_wrapper__different_object():
    def func() -> str:
        return "foo"

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert wrapped_1 != "foo"


def test_function_equality_wrapper__unwrapped_function():
    def func() -> str:
        return "foo"

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert wrapped_1 != func


def test_function_equality_wrapper__hash():
    def func() -> str:
        return "foo"

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert hash(wrapped_1) == hash(1)


def test_get_signature():
    def func(arg: str) -> int: ...

    sig = get_signature(func)

    assert dict(sig.parameters) == {
        "arg": Parameter(name="arg", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
    }

    assert sig.return_annotation == int


def test_get_signature__parsing_error():
    # MockRequest is not defined during runtime since its in a 'TYPE_CHECKING' block,
    # so function signature parsing should fail.
    if TYPE_CHECKING:
        from tests.helpers import MockRequest

    def func(arg: MockRequest) -> int: ...

    with pytest.raises(FunctionSignatureParsingError):
        get_signature(func)
