from __future__ import annotations

from typing import TYPE_CHECKING

from mypy.nodes import (
    BytesExpr,
    CallExpr,
    ComplexExpr,
    DictExpr,
    EllipsisExpr,
    FloatExpr,
    IndexExpr,
    IntExpr,
    ListExpr,
    MemberExpr,
    MypyFile,
    NameExpr,
    OpExpr,
    StrExpr,
    TupleExpr,
    TypeInfo,
    Var,
)

from mypy_undine.fullnames import DIRECTIVE_META, FILTER_SET_META, INTERFACE_TYPE_META, ORDER_SET_META

if TYPE_CHECKING:
    from mypy.nodes import Expression, SymbolNode


def is_string(typ: Expression) -> bool:
    return isinstance(typ, StrExpr)


def is_integer_or_none(typ: Expression) -> bool:
    return isinstance(typ, IntExpr) or (isinstance(typ, NameExpr) and typ.fullname == "builtins.None")


def is_boolean(typ: Expression) -> bool:
    return isinstance(typ, NameExpr) and typ.fullname in {"builtins.True", "builtins.False"}


def is_kind(typ: Expression) -> bool:
    return isinstance(typ, StrExpr) and typ.value in {"create", "update", "delete", "related", "custom"}


def is_related_action(typ: Expression) -> bool:
    return isinstance(typ, StrExpr) and typ.value in {"null", "delete", "ignore"}


def is_directive(typ: Expression) -> bool:
    return (
        isinstance(typ, CallExpr)
        and isinstance(typ.callee, NameExpr)
        and isinstance(typ.callee.node, TypeInfo)
        and typ.callee.node.metaclass_type is not None
        and typ.callee.node.metaclass_type.type.fullname == DIRECTIVE_META
    )


def is_directive_list(typ: Expression) -> bool:
    return isinstance(typ, ListExpr) and all(is_directive(d) for d in typ.items)


def is_interface(typ: Expression) -> bool:
    return (
        isinstance(typ, NameExpr)
        and isinstance(typ.node, TypeInfo)
        and typ.node.metaclass_type is not None
        and typ.node.metaclass_type.type.fullname == INTERFACE_TYPE_META
    )


def is_interface_list(typ: Expression) -> bool:
    return isinstance(typ, ListExpr) and all(is_interface(d) for d in typ.items)


def is_filterset(typ: Expression) -> bool:
    return (
        isinstance(typ, NameExpr)
        and isinstance(typ.node, TypeInfo)
        and typ.node.metaclass_type is not None
        and typ.node.metaclass_type.type.fullname == FILTER_SET_META
    )


def is_orderset(typ: Expression) -> bool:
    return (
        isinstance(typ, NameExpr)
        and isinstance(typ.node, TypeInfo)
        and typ.node.metaclass_type is not None
        and typ.node.metaclass_type.type.fullname == ORDER_SET_META
    )


def is_location(typ: Expression) -> bool:
    return (
        isinstance(typ, MemberExpr)
        and isinstance(typ.expr, NameExpr)
        and typ.expr.fullname == "graphql.language.directive_locations.DirectiveLocation"
    ) or (
        isinstance(typ, StrExpr)
        and typ.value
        in {
            "argument definition",
            "ARGUMENT_DEFINITION",
            "enum value",
            "enum",
            "ENUM",
            "ENUM_VALUE",
            "field definition",
            "field",
            "FIELD",
            "FIELD_DEFINITION",
            "fragment definition",
            "fragment spread",
            "FRAGMENT_DEFINITION",
            "FRAGMENT_SPREAD",
            "inline fragment",
            "INLINE_FRAGMENT",
            "input field definition",
            "input object",
            "INPUT_FIELD_DEFINITION",
            "INPUT_OBJECT",
            "interface",
            "INTERFACE",
            "mutation",
            "MUTATION",
            "object",
            "OBJECT",
            "query",
            "QUERY",
            "scalar",
            "SCALAR",
            "schema",
            "SCHEMA",
            "subscription",
            "SUBSCRIPTION",
            "union",
            "UNION",
            "variable definition",
            "VARIABLE_DEFINITION",
        }
    )


def is_locations_list(typ: Expression) -> bool:
    return isinstance(typ, ListExpr) and all(is_location(d) for d in typ.items)


def is_exclude_list(typ: Expression) -> bool:
    return isinstance(typ, ListExpr) and all(is_string(d) for d in typ.items)


def is_extensions(typ: Expression) -> bool:
    return isinstance(typ, DictExpr) and all(is_string(k) for k, v in typ.items if k is not None)


def expression_to_string(expr: Expression) -> str:  # noqa: PLR0911,C901
    if isinstance(expr, NameExpr):
        if expr.node is None:
            return expr.name
        return node_to_string(expr.node)

    if isinstance(expr, MemberExpr):
        if expr.node is None:
            return f"{expression_to_string(expr.expr)}.{expr.name}"
        return f"{expression_to_string(expr.expr)}.{node_to_string(expr.node)}"

    if isinstance(expr, OpExpr):
        return expression_to_string(expr.left) + f" {expr.op} " + expression_to_string(expr.right)

    if isinstance(expr, IndexExpr):
        return expression_to_string(expr.base) + f"[{expression_to_string(expr.index)}]"

    if isinstance(expr, TupleExpr):
        return f"{', '.join(expression_to_string(arg) for arg in expr.items)}"

    if isinstance(expr, (StrExpr | IntExpr | FloatExpr | BytesExpr | ComplexExpr)):
        return repr(expr.value)

    if isinstance(expr, EllipsisExpr):
        return "..."

    if isinstance(expr, CallExpr) and isinstance(expr.callee, NameExpr):
        if expr.callee.fullname == "graphql.type.definition.GraphQLNonNull":
            arg = expression_to_string(expr.args[0])
            return arg.removesuffix(" | None")

        if expr.callee.fullname == "graphql.type.definition.GraphQLList":
            arg = expression_to_string(expr.args[0])
            return f"list[{arg}]"

    msg = f"Cannot convert expression {expr} to type string"
    raise RuntimeError(msg)


def node_to_string(node: SymbolNode) -> str:
    if isinstance(node, TypeInfo):
        return node.name
    if isinstance(node, Var):
        scalar_equivalent = GRAPHQL_SCALARS.get(node.fullname)
        if scalar_equivalent is not None:
            return f"{scalar_equivalent} | None"
        return node.name
    if isinstance(node, MypyFile):
        return node.name

    msg = f"Cannot convert node {node} to type string"
    raise RuntimeError(msg)


def convert_var(var: Var) -> None:
    return


GRAPHQL_SCALARS: dict[str, str] = {
    "graphql.type.scalars.GraphQLString": "str",
    "graphql.type.scalars.GraphQLInt": "int",
    "graphql.type.scalars.GraphQLFloat": "float",
    "graphql.type.scalars.GraphQLBoolean": "bool",
    "graphql.type.scalars.GraphQLID": "str",
    "undine.scalars.base16.GraphQLBase16": "str",
    "undine.scalars.base32.GraphQLBase32": "str",
    "undine.scalars.base64.GraphQLBase64": "str",
    "undine.scalars.date.GraphQLDate": "datetime.date",
    "undine.scalars.datetime.GraphQLDateTime": "datetime.datetime",
    "undine.scalars.decimal.GraphQLDecimal": "decimal.Decimal",
    "undine.scalars.duration.GraphQLDuration": "datetime.timedelta",
    "undine.scalars.email.GraphQLEmail": "str",
    "undine.scalars.file.GraphQLFile": "str",
    "undine.scalars.image.GraphQLImage": "str",
    "undine.scalars.ip.GraphQLIP": "str",
    "undine.scalars.ipv4.GraphQLIPv4": "str",
    "undine.scalars.ipv6.GraphQLIPv6": "str",
    "undine.scalars.json.GraphQLJSON": "str",
    "undine.scalars.null.GraphQLNull": "None",
    "undine.scalars.time.GraphQLTime": "datetime.time",
    "undine.scalars.url.GraphQLURL": "str",
    "undine.scalars.uuid.GraphQLUUID": "uuid.UUID",
}
