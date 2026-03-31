from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.nodes import TypeInfo
from mypy.plugin import Plugin

from mypy_undine.base_class_hooks import get_base_class_hook
from mypy_undine.class_decorator_hooks import get_class_decorator_hook

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.plugin import ClassDefContext


__all__ = [
    "UndinePlugin",
    "plugin",
]


# TODO: Fix line and columns for errors!
class UndinePlugin(Plugin):
    """Mypy plugin for Undine."""

    def get_base_class_hook(self, fullname: str) -> Callable[[ClassDefContext], None] | None:
        type_info = self.get_type_info(fullname=fullname)
        if type_info is None:
            return None

        return get_base_class_hook(type_info)

    def get_class_decorator_hook_2(self, fullname: str) -> Callable[[ClassDefContext], bool] | None:
        type_info = self.get_type_info(fullname=fullname)
        if type_info is None:
            return None

        return get_class_decorator_hook(type_info)

    # Helpers

    def get_type_info(self, *, fullname: str) -> TypeInfo | None:
        symbol_table_node = self.lookup_fully_qualified(fullname)
        if symbol_table_node is None:
            return None

        symbol_node = symbol_table_node.node
        if not isinstance(symbol_node, TypeInfo):
            return None

        return symbol_node


def plugin(_version: str) -> type[Plugin]:
    return UndinePlugin
