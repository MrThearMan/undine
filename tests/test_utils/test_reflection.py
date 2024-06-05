from __future__ import annotations

from functools import partial, wraps
from inspect import Parameter
from typing import TYPE_CHECKING, NotRequired, Required

import pytest
from graphql import GraphQLResolveInfo

from undine.exceptions import FunctionSignatureParsingError
from undine.typing import GQLInfo
from undine.utils.reflection import (
    FunctionEqualityWrapper,
    get_instance_name,
    get_root_and_info_params,
    get_signature,
    get_wrapped_func,
    has_callable_attribute,
    is_lambda,
    is_not_required_type,
    is_required_type,
    is_subclass,
    reverse_enumerate,
)


def test_get_wrapped_func() -> None:
    def func() -> None: ...

    assert get_wrapped_func(func) == func


def test_get_wrapped_func__method() -> None:
    class Foo:
        def func(self): ...

    assert get_wrapped_func(Foo.func) == Foo.func


def test_get_wrapped_func__property() -> None:
    class Foo:
        @property
        def func(self): ...

    assert get_wrapped_func(Foo.func) == Foo.func.fget


def test_get_wrapped_func__classmethod() -> None:
    captured = None

    def capture(value):
        nonlocal captured
        captured = value
        return value

    class Foo:
        @capture
        @classmethod
        def func(cls): ...

    assert isinstance(captured, classmethod)

    assert get_wrapped_func(captured) == Foo.func.__func__


def test_get_wrapped_func__staticmethod() -> None:
    captured = None

    def capture(value):
        nonlocal captured
        captured = value
        return value

    class Foo:
        @capture
        @staticmethod
        def func() -> None: ...

    assert isinstance(captured, staticmethod)

    assert get_wrapped_func(captured) == Foo.func


def test_get_wrapped_func__partial() -> None:
    def func(x: int): ...

    foo = partial(func, 1)

    assert get_wrapped_func(foo) == func


def test_get_wrapped_func__wrapped() -> None:
    def inner() -> None: ...
    def func() -> None: ...

    foo = wraps(func)(inner)

    assert get_wrapped_func(foo) == func


def test_function_equality_wrapper__called() -> None:
    def func() -> str:
        return "foo"

    wrapped = FunctionEqualityWrapper(func, context=1)
    assert wrapped() == "foo"


def test_function_equality_wrapper__same_context() -> None:
    def func() -> str: ...

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    wrapped_2 = FunctionEqualityWrapper(func, context=1)

    assert wrapped_1 == wrapped_2


def test_function_equality_wrapper__different_context() -> None:
    def func() -> str: ...

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    wrapped_2 = FunctionEqualityWrapper(func, context=2)

    assert wrapped_1 != wrapped_2


def test_function_equality_wrapper__different_object() -> None:
    def func() -> str: ...

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert wrapped_1 != "foo"


def test_function_equality_wrapper__unwrapped_function() -> None:
    def func() -> str: ...

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert wrapped_1 != func


def test_function_equality_wrapper__hash() -> None:
    def func() -> str: ...

    wrapped_1 = FunctionEqualityWrapper(func, context=1)
    assert hash(wrapped_1) == hash(1)


def test_get_signature() -> None:
    def func(arg: str) -> int: ...

    sig = get_signature(func)

    assert dict(sig.parameters) == {
        "arg": Parameter(name="arg", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
    }

    assert sig.return_annotation == int


def test_get_signature__parsing_error() -> None:
    # MockRequest is not defined during runtime since it's in a 'TYPE_CHECKING' block,
    # so function signature parsing should fail.
    if TYPE_CHECKING:
        from tests.helpers import MockRequest  # noqa: PLC0415

    def func(arg: MockRequest) -> int: ...

    with pytest.raises(FunctionSignatureParsingError):
        get_signature(func)


def test_has_callable_attribute() -> None:
    class Foo:
        def bar(self) -> int: ...

    assert has_callable_attribute(Foo, "bar") is True
    assert has_callable_attribute(Foo, "baz") is False


def test_is_subclass() -> None:
    class Foo: ...

    class Bar(Foo): ...

    assert is_subclass(Foo, Bar) is False
    assert is_subclass(Bar, Foo) is True
    assert is_subclass(1, Foo) is False


def test_is_lambda() -> None:
    def foo() -> int: ...

    assert is_lambda(foo) is False
    assert is_lambda(lambda: 1) is True
    assert is_lambda(1) is False


def test_is_required_type() -> None:
    assert is_required_type(Required[int]) is True
    assert is_required_type(NotRequired[int]) is False
    assert is_required_type(int) is False
    assert is_required_type(1) is False


def test_is_not_required_type() -> None:
    assert is_not_required_type(Required[int]) is False
    assert is_not_required_type(NotRequired[int]) is True
    assert is_not_required_type(int) is False
    assert is_not_required_type(1) is False


def test_get_instance_name() -> None:
    class Foo:
        def __init__(self) -> None:
            self.__name__ = get_instance_name()

    foo = Foo()

    assert foo.__name__ == "foo"


def test_get_root_and_info_params() -> None:
    def foo(self, info: GraphQLResolveInfo) -> int: ...

    params = get_root_and_info_params(foo)
    assert params.root_param == "self"
    assert params.info_param == "info"


def test_get_root_and_info_params__no_root() -> None:
    def foo(info: GQLInfo) -> int: ...

    params = get_root_and_info_params(foo)
    assert params.root_param is None
    assert params.info_param == "info"


def test_get_root_and_info_params__no_info() -> None:
    def foo(self) -> int: ...

    params = get_root_and_info_params(foo)
    assert params.root_param == "self"
    assert params.info_param is None


def test_get_root_and_info_params__root_cls() -> None:
    def foo(cls) -> int: ...

    params = get_root_and_info_params(foo)
    assert params.root_param == "cls"
    assert params.info_param is None


def test_get_root_and_info_params__root_param_name(undine_settings) -> None:
    undine_settings.RESOLVER_ROOT_PARAM_NAME = "x"

    def foo(x) -> int: ...

    params = get_root_and_info_params(foo)
    assert params.root_param == "x"
    assert params.info_param is None


@pytest.mark.parametrize("inpt", [[1, 2, 3], [1], []])
def test_reverse_enumerate(inpt) -> None:
    for i, item in reverse_enumerate(inpt):
        assert item == inpt[-1]
        inpt.pop(i)

    assert inpt == []
