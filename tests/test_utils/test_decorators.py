from functools import partial

from undine.utils.decorators import cached_classmethod, cached_classproperty


def test_cached_classproperty():
    value = 1

    class A:
        x = 1

        @cached_classproperty
        def foo(self):
            nonlocal value
            value += 1
            return self.x

    class B(A):
        x = 2

    class C(A):
        x = 3

        @cached_classproperty
        def foo(self):
            nonlocal value
            value += 1
            return super().foo + 1

    # 'cached_class_property' is evaluated only once.
    assert value == 1

    assert A.foo == 1
    assert value == 2

    assert A.foo == 1
    assert value == 2

    # 'cached_class_property' is per class, so subclasses evaluate the again.
    assert B.foo == 2
    assert value == 3

    # super() calls evaluate the parent again due to descriptor semantics (therefore 'value' is +2)
    assert C.foo == 4
    assert value == 5

    # Previous values haven't changed.
    assert A.foo == 1
    assert B.foo == 2
    assert value == 5

    assert isinstance(A.foo, int)


def test_cached_classmethod():
    value = 1

    class A:
        x = 1

        @cached_classmethod
        def foo(self):
            nonlocal value
            value += 1
            return self.x

    class B(A):
        x = 2

    class C(A):
        x = 3

        @cached_classmethod
        def foo(self):
            nonlocal value
            value += 1
            return super().foo() + 1

    # 'cached_class_method' is evaluated only once.
    assert value == 1

    assert A.foo() == 1
    assert value == 2

    assert A.foo() == 1
    assert value == 2

    # 'cached_class_method' is per class, so subclasses evaluate the again.
    assert B.foo() == 2
    assert value == 3

    # super() calls evaluate the parent again due to descriptor semantics (therefore 'value' is +2)
    assert C.foo() == 4
    assert value == 5

    # Previous values haven't changed.
    assert A.foo() == 1
    assert B.foo() == 2
    assert value == 5

    # Clear cache.
    A.foo.clear()  # type: ignore[attr-defined]
    assert A.foo() == 1
    assert value == 6

    # Only that class is cleared.
    assert B.foo() == 2
    assert value == 6

    assert isinstance(A.foo, partial)
