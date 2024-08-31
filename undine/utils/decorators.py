from __future__ import annotations

from typing import Any, Callable, TypeVar

from undine.typing import empty

__all__ = [
    "cached_class_property",
]


R = TypeVar("R")


class cached_class_property:  # noqa: N801
    """
    Decorator that can be used like `functools.cached_property`, but on the class level.

    >>> class A:
    ...     @cached_class_property
    ...     def foo(cls):
    ...         print("Called!")
    ...         return 42
    ...
    >>> A.foo
    Called!
    42
    >>> A.foo
    42
    """

    def __init__(self, func: Callable[[Any], R]) -> None:
        self.func = func
        self._result = empty

    def __get__(self, instance: Any, owner: type[Any]) -> R:
        if self._result is not empty:
            return self._result

        self._result = self.func(owner)
        return self._result
