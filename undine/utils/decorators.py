from __future__ import annotations

from functools import partial
from typing import Callable, Generic, TypeVar

from undine.typing import empty

__all__ = [
    "cached_class_method",
    "cached_class_property",
]


R = TypeVar("R")


class cached_class_property(Generic[R]):  # noqa: N801
    """A decorator that works like a @classmethod @property, but also caches the result."""

    def __init__(self, func: Callable[[type], R]) -> None:
        self.func = func
        self.value: R = empty

    def __get__(self, instance: object | None, owner: type) -> R:
        if self.value is empty:
            self.value = self.func(owner)
        return self.value


class cached_class_method(Generic[R]):  # noqa: N801
    """A decorator that works like a @classmethod, but also caches the result."""

    def __init__(self, func: Callable[[type], R]) -> None:
        self.func = func
        self.values_by_class: dict[type, R] = {}

    def __get__(self, instance: object | None, owner: type) -> Callable[[], R]:
        func = partial(self.__call__, cls=owner)
        func.clear = lambda: self.values_by_class.pop(owner, None)
        return func

    def __call__(self, cls: type) -> R:
        if cls in self.values_by_class:
            return self.values_by_class[cls]

        self.values_by_class[cls] = self.func(cls)
        return self.values_by_class[cls]
