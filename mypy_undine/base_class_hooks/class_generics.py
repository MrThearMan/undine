from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.types import Instance

from mypy_undine.fullnames import (
    FILTER_SET_META,
    MODEL,
    MUTATION_TYPE_META,
    ORDER_SET_META,
    QUERY_TYPE,
    QUERY_TYPE_META,
    UNION_TYPE_META,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.plugin import ClassDefContext


def check_query_type_generic(ctx: ClassDefContext) -> None:
    target = ctx.cls.info
    for base in target.bases:
        if base.type.metaclass_type is None:
            continue

        if base.type.metaclass_type.type.fullname != QUERY_TYPE_META:
            continue

        msg = "QueryType must be parameterized with a single Django Model"

        if len(base.args) != 1:
            ctx.api.fail(msg, base)
            return

        arg = base.args[0]
        if not isinstance(arg, Instance):
            ctx.api.fail(msg, base)
            return

        for arg_base in arg.type.mro:
            if arg_base.fullname == MODEL:
                return

        ctx.api.fail(msg, base)
        return


def check_mutation_type_generic(ctx: ClassDefContext) -> None:
    target = ctx.cls.info
    for base in target.bases:
        if base.type.metaclass_type is None:
            continue

        if base.type.metaclass_type.type.fullname != MUTATION_TYPE_META:
            continue

        msg = "MutationType must be parameterized with a single Django Model"

        if len(base.args) != 1:
            ctx.api.fail(msg, base)
            return

        arg = base.args[0]
        if not isinstance(arg, Instance):
            ctx.api.fail(msg, base)
            return

        for arg_base in arg.type.mro:
            if arg_base.fullname == MODEL:
                return

        ctx.api.fail(msg, base)
        return


def check_filterset_generic(ctx: ClassDefContext) -> None:
    target = ctx.cls.info
    for base in target.bases:
        if base.type.metaclass_type is None:
            continue

        if base.type.metaclass_type.type.fullname != FILTER_SET_META:
            continue

        msg = "FilterSet must be parameterized with one or more Django Models"

        for arg in base.args:
            if not isinstance(arg, Instance):
                ctx.api.fail(msg, base)
                return

            for arg_base in arg.type.mro:
                if arg_base.fullname == MODEL:
                    break
            else:
                ctx.api.fail(msg, base)
                return
        break


def check_orderset_generic(ctx: ClassDefContext) -> None:
    target = ctx.cls.info
    for base in target.bases:
        if base.type.metaclass_type is None:
            continue

        if base.type.metaclass_type.type.fullname != ORDER_SET_META:
            continue

        msg = "OrderSet must be parameterized with one or more Django Models"

        for arg in base.args:
            if not isinstance(arg, Instance):
                ctx.api.fail(msg, base)
                return

            for arg_base in arg.type.mro:
                if arg_base.fullname == MODEL:
                    break
            else:
                ctx.api.fail(msg, base)
                return
        break


def check_union_type_generic(ctx: ClassDefContext) -> None:
    target = ctx.cls.info
    for base in target.bases:
        if base.type.metaclass_type is None:
            continue

        if base.type.metaclass_type.type.fullname != UNION_TYPE_META:
            continue

        msg = "UnionType must be parameterized with at least two QueryTypes"
        count: int = 0

        for arg in base.args:
            if not isinstance(arg, Instance):
                ctx.api.fail(msg, base)
                return

            for arg_base in arg.type.mro:
                if arg_base.fullname == QUERY_TYPE:
                    count += 1
                    break
            else:
                ctx.api.fail(msg, base)
                return

        if count < 2:  # noqa: PLR2004
            ctx.api.fail(msg, base)
            return
        break


GENERIC_CHECKS: dict[str, Callable[[ClassDefContext], None]] = {
    QUERY_TYPE_META: check_query_type_generic,
    MUTATION_TYPE_META: check_mutation_type_generic,
    FILTER_SET_META: check_filterset_generic,
    ORDER_SET_META: check_orderset_generic,
    UNION_TYPE_META: check_union_type_generic,
}
