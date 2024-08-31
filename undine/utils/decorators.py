from __future__ import annotations

from typing import Any, Callable, TypeVar

from undine.typing import empty

__all__ = [
    "cached_class_property",
]


R = TypeVar("R")


class cached_class_property:  # noqa: N801
    def __init__(self, func: Callable[[Any], R]) -> None:
        self.func = func
        self._result = empty

    def __get__(self, instance: Any, owner: type[Any]) -> R:
        if self._result is not empty:
            return self._result

        self._result = self.func(owner)
        return self._result
