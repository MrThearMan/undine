from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.fastparse import parse_type_string
from mypy.nodes import AssignmentStmt, CallExpr, ListExpr, NameExpr, OpExpr, TypeInfo
from mypy.types import AnyType, Instance, NoneType, TypeOfAny, UnionType, get_proper_type

from mypy_undine.fullnames import QUERY_TYPE_META
from mypy_undine.utils.expression_utils import expression_to_string
from mypy_undine.utils.types_utils import query_type_model_from_class

if TYPE_CHECKING:
    from mypy.nodes import ClassDef, Expression
    from mypy.plugin import ClassDefContext
    from mypy.types import Type as MypyType


def find_field_call(cls: ClassDef, name: str, factory_fullname: str) -> CallExpr | None:
    """Find `<name> = <factory>(...)` in the class body (e.g. unwrapping `@ Directive()` OpExprs)."""
    for statement in cls.defs.body:
        if not isinstance(statement, AssignmentStmt):
            continue

        lvalue = statement.lvalues[0]
        if not isinstance(lvalue, NameExpr) or lvalue.name != name:
            continue

        call = _unwrap_factory_call(statement.rvalue, factory_fullname)
        if call is not None:
            return call
    return None


def _unwrap_factory_call(rvalue: Expression, factory_fullname: str) -> CallExpr | None:
    current: Expression = rvalue
    while isinstance(current, OpExpr) and current.op == "@":
        current = current.left

    if not isinstance(current, CallExpr):
        return None

    callee = current.callee
    if not isinstance(callee, NameExpr):
        return None

    if callee.fullname != factory_fullname:
        return None

    return current


def resolve_field_call_ref_type(ctx: ClassDefContext, call: CallExpr) -> MypyType:
    """
    Compute the ref type for a field factory call, honouring `many=True` / `nullable=True`.

    Returns `AnyType` for refs we cannot statically resolve (string field names, plain
    `Field()` with no ref, etc.) — callers should treat this as "skip the check".
    """
    if not call.args:
        return AnyType(TypeOfAny.special_form)

    ref_arg = call.args[0]
    inner = _resolve_ref_expression(ctx, ref_arg)
    if _kwarg_is_true(call, "many"):
        inner = _wrap_list(ctx, inner)
    if _kwarg_is_true(call, "nullable"):
        inner = _wrap_optional(inner)
    return inner


def has_external_directive(call: CallExpr, external_directive_fullname: str) -> bool:
    """True if `@ExternalDirective()` is applied via `@` operator or `directives=[...]` kwarg."""
    for arg_name, arg in zip(call.arg_names, call.args, strict=False):
        if arg_name != "directives":
            continue
        if not isinstance(arg, ListExpr):
            continue
        if any(_is_directive_call(item, external_directive_fullname) for item in arg.items):
            return True
    return False


def has_external_directive_matmul(rvalue: Expression, external_directive_fullname: str) -> bool:
    current: Expression = rvalue
    while isinstance(current, OpExpr) and current.op == "@":
        if _is_directive_call(current.right, external_directive_fullname):
            return True
        current = current.left
    return False


def _is_directive_call(expr: Expression, fullname: str) -> bool:
    if not isinstance(expr, CallExpr):
        return False
    callee = expr.callee
    if not isinstance(callee, NameExpr):
        return False
    node = callee.node
    if isinstance(node, TypeInfo):
        return node.fullname == fullname
    return callee.fullname == fullname


def _kwarg_is_true(call: CallExpr, kwarg: str) -> bool:
    for arg_name, arg in zip(call.arg_names, call.args, strict=False):
        if arg_name != kwarg:
            continue
        if isinstance(arg, NameExpr) and arg.fullname == "builtins.True":
            return True
    return False


def _resolve_ref_expression(ctx: ClassDefContext, ref_arg: Expression) -> MypyType:
    query_model = _query_type_model(ref_arg)
    if query_model is not None:
        return query_model

    try:
        ref_str = expression_to_string(ref_arg)
    except Exception:  # noqa: BLE001
        return AnyType(TypeOfAny.special_form)
    return _parse_type(ctx, ref_str)


def _query_type_model(ref_arg: Expression) -> MypyType | None:
    if not isinstance(ref_arg, NameExpr):
        return None
    node = ref_arg.node
    if not isinstance(node, TypeInfo):
        return None
    metaclass = node.metaclass_type
    if metaclass is None or metaclass.type.fullname != QUERY_TYPE_META:
        return None
    return query_type_model_from_class(node)


def _wrap_list(ctx: ClassDefContext, inner: MypyType) -> MypyType:
    named = ctx.api.named_type_or_none("builtins.list", [inner])
    if named is not None:
        return named
    return AnyType(TypeOfAny.special_form)


def _wrap_optional(current: MypyType) -> MypyType:
    proper = get_proper_type(current)
    if isinstance(proper, AnyType):
        return current
    if isinstance(proper, NoneType):
        return current
    if isinstance(proper, UnionType):
        if any(isinstance(get_proper_type(item), NoneType) for item in proper.items):
            return current
        return UnionType([*proper.items, NoneType()])
    return UnionType([current, NoneType()])


def wrap_optional(current: MypyType) -> MypyType:
    """Public alias so callers can force `T | None` (e.g. federation's @external carve-out)."""
    return _wrap_optional(current)


def _parse_type(ctx: ClassDefContext, type_str: str) -> MypyType:
    try:
        proper_type = parse_type_string(type_str, "typing.Any", ctx.cls.line, ctx.cls.column)
        analyzed = ctx.api.anal_type(proper_type)
    except Exception:  # noqa: BLE001
        return AnyType(TypeOfAny.special_form)

    if analyzed is None:
        return AnyType(TypeOfAny.special_form)
    return analyzed


def resolvable(typ: MypyType) -> bool:
    """True if the resolved type is concrete enough to make a return-type check meaningful."""
    proper = get_proper_type(typ)
    if isinstance(proper, AnyType):
        return False
    return not (isinstance(proper, Instance) and proper.type.fullname == "builtins.object")
