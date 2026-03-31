from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from .decorators import DECORATOR_HOOKS

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.nodes import TypeInfo
    from mypy.plugin import ClassDefContext


__all__ = [
    "get_class_decorator_hook",
]


def get_class_decorator_hook(info: TypeInfo) -> Callable[[ClassDefContext], bool] | None:
    hooks: list[Callable[[ClassDefContext], None]] = []

    if info.metaclass_type is not None:
        metaclass = info.metaclass_type.type.fullname
        decorator_hook = DECORATOR_HOOKS.get(metaclass)
        if decorator_hook is not None:
            hooks.append(partial(decorator_hook, info=info))

    if not hooks:
        return None

    def handle_class_decorators(ctx: ClassDefContext) -> bool:
        for hook in hooks:
            hook(ctx)
        return True

    return handle_class_decorators
