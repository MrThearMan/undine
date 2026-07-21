from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from mypy.nodes import ArgKind, Argument, AssignmentStmt, CallExpr, NameExpr, OpExpr, Var
from mypy.plugins.common import add_attribute_to_class, add_method_to_class
from mypy.types import NoneType

from mypy_undine.fullnames import EXTERNAL_DIRECTIVE, FEDERATION_FIELD
from mypy_undine.utils.field_types import (
    has_external_directive,
    has_external_directive_matmul,
    resolve_field_call_ref_type,
    wrap_optional,
)
from mypy_undine.utils.types_utils import has_init

if TYPE_CHECKING:
    from mypy.nodes import Expression
    from mypy.plugin import ClassDefContext
    from mypy.types import Type as MypyType


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _FederationFieldSpec:
    name: str
    field_type: MypyType
    is_optional: bool


def create_federation_type_init(ctx: ClassDefContext) -> None:
    fields = _collect_federation_fields(ctx)

    for field in fields:
        add_attribute_to_class(
            api=ctx.api,
            cls=ctx.cls,
            name=field.name,
            typ=field.field_type,
            overwrite_existing=True,
        )

    if has_init(ctx.cls):
        return

    arguments = [
        Argument(
            variable=Var(field.name, field.field_type),
            type_annotation=field.field_type,
            initializer=NameExpr("None") if field.is_optional else None,
            kind=ArgKind.ARG_NAMED_OPT if field.is_optional else ArgKind.ARG_NAMED,
        )
        for field in fields
    ]

    add_method_to_class(
        api=ctx.api,
        cls=ctx.cls,
        name="__init__",
        args=arguments,
        return_type=NoneType(),
    )


def _collect_federation_fields(ctx: ClassDefContext) -> list[_FederationFieldSpec]:
    fields: list[_FederationFieldSpec] = []
    for statement in ctx.cls.defs.body:
        if not isinstance(statement, AssignmentStmt):
            continue

        name_expr = statement.lvalues[0]
        if not isinstance(name_expr, NameExpr):
            continue

        call, is_external = _extract_federation_field_call(statement.rvalue)
        if call is None:
            continue

        field_type = resolve_field_call_ref_type(ctx, call)
        is_optional = is_external or _has_kwarg_true(call, "nullable")
        if is_external:
            field_type = wrap_optional(field_type)

        fields.append(
            _FederationFieldSpec(
                name=name_expr.name,
                field_type=field_type,
                is_optional=is_optional,
            )
        )
    return fields


def _extract_federation_field_call(rvalue: Expression) -> tuple[CallExpr | None, bool]:
    is_external = has_external_directive_matmul(rvalue, EXTERNAL_DIRECTIVE)

    current: Expression = rvalue
    while isinstance(current, OpExpr) and current.op == "@":
        current = current.left

    if not isinstance(current, CallExpr):
        return None, is_external

    callee = current.callee
    if not isinstance(callee, NameExpr):
        return None, is_external
    if callee.fullname != FEDERATION_FIELD:
        return None, is_external

    if not is_external:
        is_external = has_external_directive(current, EXTERNAL_DIRECTIVE)

    return current, is_external


def _has_kwarg_true(call: CallExpr, name: str) -> bool:
    for arg_name, arg in zip(call.arg_names, call.args, strict=False):
        if arg_name != name:
            continue
        if isinstance(arg, NameExpr) and arg.fullname == "builtins.True":
            return True
    return False
