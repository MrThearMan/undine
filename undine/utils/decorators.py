from __future__ import annotations

from functools import partial
from typing import Callable, Generic, TypeVar
from weakref import WeakKeyDictionary

__all__ = [
    "cached_classmethod",
    "cached_classproperty",
]


R = TypeVar("R")


class cached_classproperty(Generic[R]):  # noqa: N801
    """A decorator that works like a @classmethod @property, but also caches the result per class."""

    def __init__(self, func: Callable[[type], R]) -> None:
        self.func = func
        self.values_by_class: WeakKeyDictionary[type, R] = WeakKeyDictionary()

    def __get__(self, instance: object | None, owner: type) -> R:
        if owner not in self.values_by_class:
            self.values_by_class[owner] = self.func(owner)
        return self.values_by_class[owner]


class cached_classmethod(Generic[R]):  # noqa: N801
    """A decorator that works like a @classmethod, but also caches the result per class."""

    def __init__(self, func: Callable[[type], R]) -> None:
        self.func = func
        self.values_by_class: WeakKeyDictionary[type, R] = WeakKeyDictionary()

    def __get__(self, instance: object | None, owner: type) -> Callable[[], R]:
        func = partial(self.__call__, cls=owner)
        func.clear = lambda: self.values_by_class.pop(owner, None)
        return func

    def __call__(self, cls: type) -> R:
        if cls not in self.values_by_class:
            self.values_by_class[cls] = self.func(cls)
        return self.values_by_class[cls]
