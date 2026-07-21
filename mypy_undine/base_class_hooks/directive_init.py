from __future__ import annotations

import dataclasses
from contextlib import suppress
from typing import TYPE_CHECKING

from mypy.fastparse import parse_type_string
from mypy.nodes import ArgKind, Argument, AssignmentStmt, CallExpr, NameExpr, OpExpr, Var
from mypy.plugins.common import add_attribute_to_class, add_method_to_class
from mypy.types import AnyType, NoneType, TypeOfAny

from mypy_undine.fullnames import DIRECTIVE_ARGUMENT
from mypy_undine.utils.expression_utils import expression_to_string
from mypy_undine.utils.types_utils import has_init

if TYPE_CHECKING:
    from mypy.nodes import Expression
    from mypy.plugin import ClassDefContext
    from mypy.types import Type as MypyType


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _DirectiveArgumentSpec:
    name: str
    arg_type: MypyType
    default_value: Expression | None


def create_directive_init(ctx: ClassDefContext) -> None:
    specs = _collect_directive_arguments(ctx)

    for spec in specs:
        add_attribute_to_class(
            api=ctx.api,
            cls=ctx.cls,
            name=spec.name,
            typ=spec.arg_type,
            overwrite_existing=True,
        )

    if has_init(ctx.cls):
        return

    arguments = [
        Argument(
            variable=Var(spec.name, spec.arg_type),
            type_annotation=spec.arg_type,
            initializer=spec.default_value,
            kind=ArgKind.ARG_NAMED if spec.default_value is None else ArgKind.ARG_NAMED_OPT,
        )
        for spec in specs
    ]

    add_method_to_class(
        api=ctx.api,
        cls=ctx.cls,
        name="__init__",
        args=arguments,
        return_type=NoneType(),
    )


def _collect_directive_arguments(ctx: ClassDefContext) -> list[_DirectiveArgumentSpec]:
    specs: list[_DirectiveArgumentSpec] = []
    for statement in ctx.cls.defs.body:
        if not isinstance(statement, AssignmentStmt):
            continue

        call = _unwrap_directive_argument_call(statement.rvalue)
        if call is None:
            continue

        name_expr = statement.lvalues[0]
        if not isinstance(name_expr, NameExpr):
            continue

        default_value: Expression | None = None
        with suppress(ValueError, IndexError):
            index = call.arg_names.index("default_value")
            default_value = call.args[index]

        arg_type = _resolve_argument_type(ctx, call.args[0])

        specs.append(
            _DirectiveArgumentSpec(
                name=name_expr.name,
                arg_type=arg_type,
                default_value=default_value,
            )
        )
    return specs


def _unwrap_directive_argument_call(rvalue: Expression) -> CallExpr | None:
    current: Expression = rvalue
    while isinstance(current, OpExpr) and current.op == "@":
        current = current.left

    if not isinstance(current, CallExpr):
        return None

    callee = current.callee
    if not isinstance(callee, NameExpr):
        return None

    if callee.fullname != DIRECTIVE_ARGUMENT:
        return None

    if not current.args:
        return None

    return current


def _resolve_argument_type(ctx: ClassDefContext, ref_arg: Expression) -> MypyType:
    try:
        ann_str = expression_to_string(ref_arg)
        proper_type = parse_type_string(ann_str, "typing.Any", ctx.cls.line, ctx.cls.column)
        analyzed = ctx.api.anal_type(proper_type)
    except Exception:  # noqa: BLE001
        return AnyType(TypeOfAny.special_form)
    if analyzed is None:
        return AnyType(TypeOfAny.special_form)
    return analyzed
