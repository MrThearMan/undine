from __future__ import annotations

import asyncio
import contextlib
import inspect
import sys
from enum import Enum
from functools import partial, wraps
from inspect import Parameter
from typing import TYPE_CHECKING, Annotated, NamedTuple, NotRequired, Required

import django
import pytest
from graphql import GraphQLResolveInfo

from undine.exceptions import FunctionSignatureParsingError, UnionTypeMultipleTypesError
from undine.typing import GQLInfo
from undine.utils.reflection import (
    FunctionEqualityWrapper,
    as_coroutine_func_if_not,
    async_enumerate,
    cache_signature_if_function,
    can_be_literal_arg,
    cancel_awaitable,
    delegate_to_subgenerator,
    get_enum_from_string,
    get_instance_name,
    get_non_null_type,
    get_root_and_info_params,
    get_signature,
    get_traceback,
    get_wrapped_func,
    has_callable_attribute,
    is_annotated,
    is_generic_list,
    is_lambda,
    is_list_of,
    is_namedtuple,
    is_not_required_type,
    is_required_type,
    is_same_func,
    is_subclass,
    reverse_enumerate,
    sort_by_mro,
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


def test_get_wrapped_func__bound_method() -> None:
    class Foo:
        def bar(self): ...

    foo = Foo()
    bound = foo.bar
    result = get_wrapped_func(bound)
    assert result == Foo.bar


def test_get_enum_from_string__value() -> None:
    class Color(Enum):
        RED = "red"

    result = get_enum_from_string(Color, "red")
    assert result == Color.RED


def test_get_enum_from_string__name() -> None:
    class Color(Enum):
        RED = "red"

    result = get_enum_from_string(Color, "RED")
    assert result == Color.RED


def test_get_enum_from_string__invalid() -> None:
    class Color(Enum):
        RED = "red"

    with pytest.raises(ValueError):  # noqa: PT011
        get_enum_from_string(Color, "BLUE")


def test_get_non_null_type__simple() -> None:
    result = get_non_null_type(int | None)
    assert result is int


def test_get_non_null_type__required() -> None:
    result = get_non_null_type(Required[int])
    assert result is int


def test_get_non_null_type__not_required() -> None:
    result = get_non_null_type(NotRequired[str])
    assert result is str


def test_get_non_null_type__non_union() -> None:
    result = get_non_null_type(int)
    assert result is int


def test_cache_signature_if_function() -> None:
    def my_func(x: int) -> str:
        return str(x)

    result = cache_signature_if_function(my_func)
    assert result == my_func


def test_is_list_of__true() -> None:
    assert is_list_of([1, 2, 3], int) is True


def test_is_list_of__empty_disallowed() -> None:
    assert is_list_of([], int) is False


def test_is_list_of__empty_allowed() -> None:
    assert is_list_of([], int, allow_empty=True) is True


def test_is_list_of__mixed() -> None:
    assert is_list_of([1, "two"], int) is False


def test_is_generic_list__true() -> None:
    assert is_generic_list(list[str]) is True


def test_is_generic_list__false() -> None:
    assert is_generic_list(list) is False
    assert is_generic_list(str) is False


def test_is_namedtuple__true() -> None:
    class Foo(NamedTuple):
        x: int

    assert is_namedtuple(Foo) is True


def test_is_namedtuple__false() -> None:
    assert is_namedtuple(int) is False


def test_is_annotated__true() -> None:
    assert is_annotated(Annotated[int, "metadata"]) is True


def test_is_annotated__false() -> None:
    assert is_annotated(int) is False


def test_is_same_func() -> None:
    def func(): ...

    assert is_same_func(func, func) is True


def test_is_same_func__different() -> None:
    def func1(): ...
    def func2(): ...

    assert is_same_func(func1, func2) is False


def test_can_be_literal_arg__str() -> None:
    assert can_be_literal_arg("foo") is True


def test_can_be_literal_arg__float() -> None:
    assert can_be_literal_arg(1.5) is False


def test_get_root_and_info_params__info_first() -> None:
    def func(info: GQLInfo, other: int) -> None: ...

    result = get_root_and_info_params(func)
    assert result.root_param is None
    assert result.info_param == "info"


def test_sort_by_mro() -> None:
    class A: ...

    class B(A): ...

    class C(B): ...

    result = sort_by_mro([A, C, B])
    assert result.index(C) < result.index(B)
    assert result.index(B) < result.index(A)


def test_sort_by_mro__unrelated() -> None:
    class A: ...

    class B: ...

    result = sort_by_mro([A, B])
    assert len(result) == 2


def test_sort_by_mro__diamond() -> None:
    class A: ...

    class B(A): ...

    class C(A): ...

    class D(B, C): ...

    # D should come before B and C, which come before A
    result = sort_by_mro([A, B, C, D])
    assert result.index(D) < result.index(B)
    assert result.index(D) < result.index(C)


def test_get_traceback() -> None:
    try:
        msg = "test"
        raise ValueError(msg)  # noqa: TRY301
    except ValueError as e:
        result = get_traceback(e.__traceback__)
    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Python 3.12 required")
@pytest.mark.skipif(django.VERSION < (5, 2), reason="Django 5.2 required")
def test_as_coroutine_func_if_not__sync() -> None:
    def sync_func(): ...

    result = as_coroutine_func_if_not(sync_func)
    assert inspect.iscoroutinefunction(result)


def test_as_coroutine_func_if_not__async() -> None:
    async def async_func(): ...

    result = as_coroutine_func_if_not(async_func)
    assert result is async_func


def test_cancel_awaitable__coroutine() -> None:
    async def my_coro(): ...

    coro = my_coro()
    cancel_awaitable(coro)  # should close without error


@pytest.mark.asyncio
async def test_cancel_awaitable__future() -> None:  # noqa: RUF029
    future = asyncio.Future()
    cancel_awaitable(future)
    assert future.cancelled()


def test_cancel_awaitable__other() -> None:
    cancel_awaitable(None)  # should not error


@pytest.mark.asyncio
async def test_async_enumerate() -> None:
    async def gen():  # noqa: RUF029
        yield "a"
        yield "b"

    results = []
    async for i, item in async_enumerate(gen()):
        results.append((i, item))

    assert results == [(0, "a"), (1, "b")]


def test_delegate_to_subgenerator__normal() -> None:
    def sub():
        yield
        yield

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield

    list(gen())  # should not error


def test_delegate_to_subgenerator__wrong_type() -> None:
    async def async_gen():  # noqa: RUF029
        yield

    with pytest.raises(TypeError), delegate_to_subgenerator(async_gen()):
        pass


def test_delegate_to_subgenerator__exception_suppressed() -> None:
    def sub():
        with contextlib.suppress(StopIteration):
            yield

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                raise StopIteration

    # If StopIteration is thrown into subgen and subgen handles it
    with contextlib.suppress(Exception):
        list(gen())


def test_delegate_to_subgenerator__exception_propagated() -> None:
    def sub():
        with contextlib.suppress(ValueError):
            yield

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                msg = "test"
                raise ValueError(msg)

    list(gen())  # should not raise


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_normal() -> None:
    async def sub():  # noqa: RUF029
        yield
        yield

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield

    results = [x async for x in gen()]
    assert len(results) == 2  # yields None twice


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_wrong_type() -> None:
    def sync_gen():
        yield

    with pytest.raises(TypeError):
        async with delegate_to_subgenerator(sync_gen()):
            pass


def test_get_non_null_type__union_no_none() -> None:
    # Union without NoneType: args are left as-is, raises if multiple types
    with pytest.raises(UnionTypeMultipleTypesError):
        get_non_null_type(int | str)


def test_get_non_null_type__union_with_none_and_multiple() -> None:
    # Union with NoneType plus multiple other types raises an error
    with pytest.raises(UnionTypeMultipleTypesError):
        get_non_null_type(int | str | None)


def test_delegate_to_subgenerator__exit_wrong_type() -> None:
    # __exit__ with a non-Generator object raises TypeError
    ctx = delegate_to_subgenerator.__new__(delegate_to_subgenerator)
    ctx.gen = object()  # type: ignore[assignment]
    with pytest.raises(TypeError, match="not a Generator"):
        ctx.__exit__(None, None, None)


def test_delegate_to_subgenerator__exc_type_no_value() -> None:
    # exc_value is None: __exit__ constructs exc_value from exc_type
    def sub():
        with contextlib.suppress(ValueError):
            yield

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                raise ValueError  # raise without a message

    list(gen())  # should not raise


def test_delegate_to_subgenerator__exception_reraises() -> None:
    # Exception different from exc_value is re-raised
    class MyError(Exception): ...

    def sub():
        try:
            yield
        except ValueError:
            raise MyError from None

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                msg = "test"
                raise ValueError(msg)

    with pytest.raises(MyError):
        list(gen())


def test_delegate_to_subgenerator__runtime_error_same_as_exc() -> None:
    # When gen.throw raises a RuntimeError that is the same as exc_value
    def sub():
        try:
            yield
        except RuntimeError:
            raise

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                msg = "test"
                raise RuntimeError(msg)

    with pytest.raises(RuntimeError):
        list(gen())


def test_delegate_to_subgenerator__runtime_error_stop_iteration_cause() -> None:
    # RuntimeError whose cause is a StopIteration (StopIteration from generator turned into RuntimeError)
    stop = StopIteration()

    def sub():
        try:
            yield
        except StopIteration:
            raise RuntimeError from stop

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                raise stop

    with contextlib.suppress(Exception):
        list(gen())


def test_delegate_to_subgenerator__generator_no_stop_after_throw() -> None:
    # Generator doesn't stop after throw - raises RuntimeError
    def sub():
        try:
            yield
        except ValueError:
            yield  # subgenerator yields again instead of stopping

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                msg = "test"
                raise ValueError(msg)

    with pytest.raises(RuntimeError, match="generator didn't stop after throw"):
        list(gen())


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_exit_wrong_type() -> None:
    # __aexit__ called on sync generator raises TypeError
    def sync_gen():
        yield

    ctx = delegate_to_subgenerator(sync_gen())
    with pytest.raises(TypeError):
        await ctx.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_exc_type_no_value() -> None:
    # async exc_value is None: __aexit__ constructs exc_value from exc_type
    async def sub():  # noqa: RUF029
        with contextlib.suppress(ValueError):
            yield

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                raise ValueError  # raise without a message

    results = [x async for x in gen()]
    assert len(results) == 1


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_exception_reraises() -> None:
    # Async exception different from exc_value is re-raised
    class MyError(Exception): ...

    async def sub():  # noqa: RUF029
        try:
            yield
        except ValueError:
            raise MyError from None

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                msg = "test"
                raise ValueError(msg)

    with pytest.raises(MyError):
        _ = [x async for x in gen()]


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_runtime_error_same_as_exc() -> None:
    # When async gen athrow raises RuntimeError that is the same as exc_value
    async def sub():  # noqa: RUF029
        try:
            yield
        except RuntimeError:
            raise

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                msg = "test"
                raise RuntimeError(msg)

    with pytest.raises(RuntimeError):
        _ = [x async for x in gen()]


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_stop_async_iteration_suppressed() -> None:
    # StopAsyncIteration that is the exc_value is suppressed (returns True)
    async def sub():  # noqa: RUF029
        try:
            yield
        except StopAsyncIteration:
            raise StopAsyncIteration from None

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                raise StopAsyncIteration

    with contextlib.suppress(Exception):
        _ = [x async for x in gen()]


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_runtime_error_stop_async_iteration_cause() -> None:
    # RuntimeError whose cause is a StopAsyncIteration
    stop = StopAsyncIteration()

    async def sub():  # noqa: RUF029
        try:
            yield
        except StopAsyncIteration:
            raise RuntimeError from stop

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                raise stop

    with contextlib.suppress(Exception):
        _ = [x async for x in gen()]


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__async_generator_no_stop_after_throw() -> None:
    # Async generator doesn't stop after athrow - raises RuntimeError
    async def sub():  # noqa: RUF029
        try:
            yield
        except ValueError:
            yield  # subgenerator yields again instead of stopping

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                msg = "test"
                raise ValueError(msg)

    with pytest.raises(RuntimeError, match="generator didn't stop after athrow"):
        _ = [x async for x in gen()]


def test_delegate_to_subgenerator__exit_exc_value_none() -> None:
    def sub():
        with contextlib.suppress(ValueError):
            yield

    gen_obj = sub()
    ctx = delegate_to_subgenerator(gen_obj)
    ctx.__enter__()
    # Start the generator so it's at the yield point
    next(gen_obj)
    # Call __exit__ with exc_type set but exc_value=None (exc_value constructed from exc_type)
    result = ctx.__exit__(ValueError, None, None)
    # sub() suppresses the ValueError, StopIteration is raised, returns True
    assert result is True


def test_delegate_to_subgenerator__exit_different_runtime_error_reraises() -> None:
    different_error = RuntimeError("different")

    def sub():
        try:
            yield
        except ValueError:
            raise different_error from None

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                msg = "trigger"
                raise ValueError(msg)

    with pytest.raises(RuntimeError, match="different"):
        list(gen())


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__aexit_exc_value_none() -> None:
    async def sub():  # noqa: RUF029
        with contextlib.suppress(ValueError):
            yield

    gen_obj = sub()
    ctx = delegate_to_subgenerator(gen_obj)
    await ctx.__aenter__()
    # Start the async generator so it's at the yield point
    await anext(gen_obj)
    result = await ctx.__aexit__(ValueError, None, None)
    assert result is True


def test_delegate_to_subgenerator__exit_base_exception_same_object() -> None:
    exc = KeyboardInterrupt("test")

    def sub():
        try:
            yield
        except KeyboardInterrupt:
            raise  # re-raise exactly the same object

    def gen():
        with delegate_to_subgenerator(sub()) as s:
            for _ in s:
                yield
                raise exc

    with pytest.raises(KeyboardInterrupt):
        list(gen())


@pytest.mark.asyncio
async def test_delegate_to_subgenerator__aexit_base_exception_same_object() -> None:
    exc = KeyboardInterrupt("test")

    async def sub():
        try:
            yield
        except KeyboardInterrupt:
            raise  # re-raise exactly the same object

    async def gen():
        async with delegate_to_subgenerator(sub()) as s:
            async for _ in s:
                yield
                raise exc

    with pytest.raises(KeyboardInterrupt):
        _ = [x async for x in gen()]
