from functools import partial, wraps

from undine.utils.reflection import get_wrapped_func, swappable_by_subclassing


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
