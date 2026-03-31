from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from mypy.fastparse import parse_type_string
from mypy.nodes import ArgKind, Argument, AssignmentStmt, CallExpr, NameExpr, Var
from mypy.plugins.common import add_method_to_class
from mypy.types import AnyType, NoneType, TypeOfAny

from mypy_undine.fullnames import DIRECTIVE_ARGUMENT
from mypy_undine.utils.expression_utils import expression_to_string
from mypy_undine.utils.types_utils import has_init

if TYPE_CHECKING:
    from mypy.nodes import Expression
    from mypy.plugin import ClassDefContext


def create_directive_init(ctx: ClassDefContext) -> None:
    if has_init(ctx.cls):
        return

    arguments: list[Argument] = []
    for statement in ctx.cls.defs.body:
        if not isinstance(statement, AssignmentStmt):
            continue

        value = statement.rvalue
        if not isinstance(value, CallExpr):
            continue

        callee = value.callee
        if not isinstance(callee, NameExpr):
            continue

        if callee.fullname != DIRECTIVE_ARGUMENT:
            continue

        default_value: Expression | None = None
        with suppress(ValueError, IndexError):
            index = value.arg_names.index("default_value")
            default_value = value.args[index]

        arg = value.args[0]

        try:
            ann_str = expression_to_string(arg)
            proper_type = parse_type_string(ann_str, "typing.Any", ctx.cls.line, ctx.cls.column)
            analyzed_type = ctx.api.anal_type(proper_type)
        except Exception:  # noqa: BLE001
            analyzed_type = AnyType(TypeOfAny.special_form)

        name_expr = statement.lvalues[0]
        if not isinstance(name_expr, NameExpr):
            continue

        name = name_expr.name

        arguments.append(
            Argument(
                variable=Var(name, analyzed_type),
                type_annotation=analyzed_type,
                initializer=default_value,
                kind=ArgKind.ARG_NAMED if default_value is None else ArgKind.ARG_NAMED_OPT,
            ),
        )

    add_method_to_class(
        api=ctx.api,
        cls=ctx.cls,
        name="__init__",
        args=arguments,
        return_type=NoneType(),
    )
    return
