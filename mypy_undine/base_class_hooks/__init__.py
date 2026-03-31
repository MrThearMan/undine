from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from mypy_undine.fullnames import (
    DIRECTIVE_META,
    FILTER_SET_META,
    INTERFACE_TYPE_META,
    MUTATION_TYPE_META,
    ORDER_SET_META,
    QUERY_TYPE_META,
    ROOT_TYPE_META,
    UNION_TYPE_META,
)

from .class_body import fix_class_body
from .class_generics import GENERIC_CHECKS
from .class_keywords import KEYWORD_CHECKS, validate_class_keywords
from .directive_init import create_directive_init

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.nodes import TypeInfo
    from mypy.plugin import ClassDefContext


__all__ = [
    "get_base_class_hook",
]


def get_base_class_hook(info: TypeInfo) -> Callable[[ClassDefContext], None] | None:
    hooks: list[Callable[[ClassDefContext], None]] = []

    if info.fullname in KEYWORD_CHECKS:
        hooks.append(partial(validate_class_keywords, fullname=info.fullname))

    if info.metaclass_type is not None:
        metaclass_type = info.metaclass_type.type.fullname
        if metaclass_type == DIRECTIVE_META:
            hooks.append(create_directive_init)

        if metaclass_type in {
            ROOT_TYPE_META,
            QUERY_TYPE_META,
            MUTATION_TYPE_META,
            FILTER_SET_META,
            ORDER_SET_META,
            UNION_TYPE_META,
            INTERFACE_TYPE_META,
            DIRECTIVE_META,
        }:
            hooks.append(fix_class_body)

        generic_check = GENERIC_CHECKS.get(metaclass_type)
        if generic_check is not None:
            hooks.append(generic_check)

    if not hooks:
        return None

    def handle_base_classes(ctx: ClassDefContext) -> None:
        for hook in hooks:
            hook(ctx)

    return handle_base_classes
