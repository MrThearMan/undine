from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import DirectiveLocation
from mypy.errorcodes import ARG_TYPE
from mypy.nodes import (
    MDEF,
    ArgKind,
    AssignmentStmt,
    CallExpr,
    Decorator,
    FuncDef,
    MemberExpr,
    NameExpr,
    OpExpr,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.types import CallableType, Instance, NoneType, UnboundType

from mypy_undine.fullnames import (
    DIRECTIVE,
    DIRECTIVE_ARGUMENT,
    DIRECTIVE_META,
    ENTRYPOINT,
    FIELD,
    FILTER,
    FILTER_SET,
    FILTER_SET_META,
    GQL_INFO,
    INPUT,
    INTERFACE_FIELD,
    INTERFACE_TYPE,
    INTERFACE_TYPE_META,
    MUTATION_TYPE,
    MUTATION_TYPE_META,
    ORDER,
    ORDER_SET,
    ORDER_SET_META,
    QUERY_TYPE,
    QUERY_TYPE_META,
    ROOT_TYPE,
    ROOT_TYPE_META,
)
from mypy_undine.utils.types_utils import (
    directive_locations_from_class,
    mutation_type_model_from_class,
    query_type_model_from_class,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from mypy.nodes import Argument, Expression, FuncDef
    from mypy.plugin import ClassDefContext


def fix_class_body(ctx: ClassDefContext) -> None:
    for statement in ctx.cls.defs.body:
        if isinstance(statement, Decorator):
            fix_decorated_methods(ctx, statement)
            continue

        if isinstance(statement, AssignmentStmt):
            value = statement.rvalue
            if isinstance(value, OpExpr) and value.op == "@":
                check_rmatmul_directives(ctx, value)
            continue


def fix_decorated_methods(ctx: ClassDefContext, value: Decorator) -> None:  # noqa: C901,PLR0912
    base_class_name = get_undine_class_based_on_metaclass(ctx.cls.info)
    if base_class_name is None:
        return

    descriptor_class = DESCRIPTOR_REVERSE_MAPPING[base_class_name]
    location = LOCATION_MAP[descriptor_class]
    descriptor_found: bool = False

    for decorator in reversed(value.decorators):
        if (
            isinstance(decorator, MemberExpr)
            and isinstance(decorator.expr, NameExpr)
            and decorator.expr.name in ctx.cls.info.names
        ):
            handler = DECORATOR_METHODS.get((base_class_name, decorator.name))
            if handler is not None:
                handler(ctx, value.func, decorator.expr.name)

            continue

        decorator_info = get_decorator_info(decorator)
        if decorator_info is None:
            return

        undine_class = get_undine_class_based_on_metaclass(decorator_info)

        if not descriptor_found:
            if undine_class == DIRECTIVE:
                msg = (
                    f'Directive "{decorator_info.name}" decorator must be applied '
                    f'on top of the "{descriptor_class}" decorator'
                )
                ctx.api.fail(msg, decorator)
                continue

            for base in decorator_info.mro:
                descriptor_target = DESCRIPTOR_MAPPING.get(base.fullname)
                if descriptor_target is None:
                    continue

                if descriptor_target != base_class_name:
                    msg = f'"{decorator_info.name}" does not work inside a "{base_class_name}" class'
                    ctx.api.fail(msg, decorator)
                    break

                descriptor_found = True
                handler = DECORATOR_METHODS.get((base_class_name, descriptor_class))
                if handler is not None:
                    handler(ctx, value.func, value.func.name)

                break

            continue

        if undine_class == DIRECTIVE:
            accepted_locations = directive_locations_from_class(decorator_info)

            if location not in accepted_locations:
                msg = f'Directive "{decorator_info.name}" does not support location "{location.name}"'
                ctx.api.fail(msg, decorator)

            continue


def check_rmatmul_directives(ctx: ClassDefContext, value: OpExpr) -> TypeInfo | None:
    left_value = value.left

    if isinstance(left_value, OpExpr):
        if left_value.op != "@":
            return None

        left_symbol_node = check_rmatmul_directives(ctx, left_value)
        if left_symbol_node is None:
            return None

    else:
        left_symbol_node = get_type_info(left_value)
        if left_symbol_node is None:
            return None

    right_value = value.right

    right_symbol_node = get_type_info(right_value)
    if right_symbol_node is None:
        return left_symbol_node

    metaclass_type = right_symbol_node.metaclass_type
    if metaclass_type is None:
        return left_symbol_node

    if metaclass_type.type.fullname != DIRECTIVE_META:
        return left_symbol_node

    accepted_locations = directive_locations_from_class(right_symbol_node)

    location = LOCATION_MAP.get(left_symbol_node.fullname)
    if location is None:
        return left_symbol_node

    if location not in accepted_locations:
        msg = f'Directive "{right_symbol_node.name}" does not support location "{location.name}"'
        ctx.api.fail(msg, right_value)

    return left_symbol_node


def get_type_info(expr: Expression) -> TypeInfo | None:
    if not isinstance(expr, CallExpr):
        return None

    callee = expr.callee
    if not isinstance(callee, NameExpr):
        return None

    symbol_node = callee.node
    if not isinstance(symbol_node, TypeInfo):
        return None

    return symbol_node


def check_arg_type(ctx: ClassDefContext, arg: Argument, *, expected: str) -> None:
    if arg.type_annotation is None:
        msg = f'Argument "{arg.variable.name}" is not type annotated; expected {expected!r}'
        ctx.api.fail(msg, arg, code=ARG_TYPE)
        return

    if not isinstance(arg.type_annotation, UnboundType):
        return

    node = ctx.api.lookup_qualified(arg.type_annotation.name, ctx.cls)
    if node is None:
        return

    if node.fullname != expected:
        name = getattr(node.node, "name", node.fullname)
        msg = f'Argument "{arg.variable.name}" has incompatible type "{name}"; expected {expected!r}'
        ctx.api.fail(msg, arg, code=ARG_TYPE)


def check_return_type(ctx: ClassDefContext, func: FuncDef, *, expected: str) -> None:
    if not isinstance(func.type, CallableType):
        return

    ret_type = func.type.ret_type
    if not isinstance(ret_type, UnboundType):
        return

    node = ctx.api.lookup_qualified(ret_type.name, ctx.cls)
    if node is None:
        return

    if node.fullname != expected:
        name = getattr(node.node, "name", node.fullname)
        msg = f'Return type of {func.name} has incompatible type "{name}"; expected {expected!r}'
        ctx.api.fail(msg, ret_type)


def set_arg_type(ctx: ClassDefContext, func: FuncDef, arg: Argument, lookup: str) -> None:
    field_typeinfo = ctx.api.lookup_fully_qualified_or_none(lookup)
    if field_typeinfo is not None and isinstance(field_typeinfo.node, TypeInfo):
        instance_type = Instance(field_typeinfo.node, [])
        arg.variable.type = instance_type
        arg.type_annotation = instance_type
        if isinstance(func.type, CallableType):
            func.type.arg_types[0] = instance_type


def to_staticmethod(ctx: ClassDefContext, func: FuncDef) -> None:
    func.is_decorated = True
    func.is_static = True

    var = Var(func.name, func.type)
    var.info = ctx.cls.info
    var._fullname = func._fullname  # noqa: SLF001
    var.is_staticmethod = True

    dec = Decorator(func, [], var)
    dec.line = func.line
    sym = SymbolTableNode(MDEF, dec)
    sym.plugin_generated = True
    ctx.cls.info.names[func.name] = sym


def get_decorator_info(decorator: Expression) -> TypeInfo | None:
    if isinstance(decorator, CallExpr):
        callee = decorator.callee
        if not isinstance(callee, NameExpr):
            return None

        info = callee.node

    elif isinstance(decorator, NameExpr):
        info = decorator.node

    else:
        return None

    if not isinstance(info, TypeInfo):
        return None

    return info


def get_undine_class_based_on_metaclass(info: TypeInfo) -> str | None:
    metaclass = info.metaclass_type
    if metaclass is None:
        return None

    return METACLASS_MAPPING.get(metaclass.type.fullname)


def check_entrypoint_resolve_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    # Resolvers can have some info and self missing so dont check positions
    for index, arg in enumerate(func.arguments):
        if index == 0 and arg.variable.name in {"self", "cls", "root"}:
            to_staticmethod(ctx, func)
            arg.variable.type = NoneType()
            arg.type_annotation = NoneType()
            if isinstance(func.type, CallableType):
                func.type.arg_types[index] = NoneType()
            continue

        if arg.variable.name == "info":
            check_arg_type(ctx, arg, expected=GQL_INFO)
            break


def check_field_resolve_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    # Resolvers can have some info and self missing so dont check positions
    for index, arg in enumerate(func.arguments):
        if index == 0 and arg.variable.name in {"self", "cls", "root"}:
            to_staticmethod(ctx, func)
            model_type = query_type_model_from_class(ctx.cls.info)
            if model_type is None:
                continue

            arg.variable.type = model_type
            arg.type_annotation = model_type
            if isinstance(func.type, CallableType):
                func.type.arg_types[index] = model_type
            continue

        if arg.variable.name == "info":
            check_arg_type(ctx, arg, expected=GQL_INFO)
            break


def check_input_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) not in {2, 3}:
        msg = (
            "The @Input decorator must be applied to a method with "
            "signature 'def (self, info: GQLInfo) -> Any' or 'def (self, info: GQLInfo, value: Any) -> Any'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]

    if arg_1.variable.name in {"self", "cls", "root"}:
        model_type = mutation_type_model_from_class(ctx.cls.info)
        if model_type is not None:
            arg_1.variable.type = model_type
            arg_1.type_annotation = model_type
            if isinstance(func.type, CallableType):
                func.type.arg_types[0] = model_type

    if arg_2.variable.name == "info":
        check_arg_type(ctx, arg_2, expected=GQL_INFO)
    else:
        msg = f'The second argument to "{func.name}" must be named "info"'
        ctx.api.fail(msg, arg_2)


def check_filter_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            "The @Filter decorator must be applied to a method with "
            "signature 'def (self, info: GQLInfo, *, value: Any) -> models.Q'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]
    arg_3 = func.arguments[2]

    set_arg_type(ctx, func, arg_1, FILTER)

    if arg_2.variable.name == "info":
        check_arg_type(ctx, arg_2, expected=GQL_INFO)
    else:
        msg = f'The second argument to "{name}" must be named "info"'
        ctx.api.fail(msg, arg_2)

    if arg_3.variable.name == "value":
        if arg_3.kind != ArgKind.ARG_NAMED:
            msg = 'Argument "value" to must be a keyword-only argument'
            ctx.api.fail(msg, arg_3)
    else:
        msg = f'The third argument to "{name}" must be named "value"'
        ctx.api.fail(msg, arg_3)

    check_return_type(ctx, func, expected="django.db.models.query_utils.Q")


def check_optimize_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            f"The @{name}.optimize decorator must be applied to a method with "
            f"signature 'def (self, info: GQLInfo) -> None'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]
    arg_3 = func.arguments[2]

    set_arg_type(ctx, func, arg_1, FIELD)

    check_arg_type(ctx, arg_2, expected="undine.optimizer.optimizer.OptimizationData")
    check_arg_type(ctx, arg_3, expected=GQL_INFO)

    check_return_type(ctx, func, expected="builtins.None")


def check_permissions_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            f"The @{name}.permission decorator must be applied to a method with "
            f"signature 'def (self, info: GQLInfo, value: Any) -> None'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]

    metaclass = ctx.cls.info.metaclass_type
    if metaclass is not None:
        metaclass_name = metaclass.type.fullname

        if metaclass_name == QUERY_TYPE_META:
            model_type = query_type_model_from_class(ctx.cls.info)
        elif metaclass_name == MUTATION_TYPE_META:
            model_type = mutation_type_model_from_class(ctx.cls.info)
        else:
            model_type = None

        if model_type is not None:
            arg_1.variable.type = model_type
            arg_1.type_annotation = model_type
            if isinstance(func.type, CallableType):
                func.type.arg_types[0] = model_type

    check_arg_type(ctx, arg_2, expected=GQL_INFO)


def check_visible_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arg_names) != 2:  # noqa: PLR2004
        msg = (
            f"The @{name}.visible decorator must be applied to a method with "
            f"signature 'def (self, request: DjangoRequestProtocol) -> bool'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]

    metaclass = ctx.cls.info.metaclass_type
    if metaclass is not None:
        metaclass_name = metaclass.type.fullname
        base_class_name = METACLASS_MAPPING.get(metaclass_name)
        if base_class_name is not None:
            descriptor = DESCRIPTOR_REVERSE_MAPPING.get(base_class_name)
            if descriptor is not None:
                set_arg_type(ctx, func, arg_1, descriptor)

    check_return_type(ctx, func, expected="builtins.bool")


def check_validate_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            f"The @{name}.validate decorator must be applied to a method with "
            f"signature 'def (self, info: GQLInfo, value: Any) -> None'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]

    metaclass = ctx.cls.info.metaclass_type
    if metaclass is not None:
        metaclass_name = metaclass.type.fullname

        if metaclass_name == QUERY_TYPE_META:
            model_type = query_type_model_from_class(ctx.cls.info)
        elif metaclass_name == MUTATION_TYPE_META:
            model_type = mutation_type_model_from_class(ctx.cls.info)
        else:
            model_type = None

        if model_type is not None:
            arg_1.variable.type = model_type
            arg_1.type_annotation = model_type
            if isinstance(func.type, CallableType):
                func.type.arg_types[0] = model_type

    check_arg_type(ctx, arg_2, expected=GQL_INFO)

    check_return_type(ctx, func, expected="builtins.None")


def check_convert_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arg_names) != 2:  # noqa: PLR2004
        msg = (
            f"The @{name}.convert decorator must be applied to a method with signature 'def (self, value: Any) -> Any'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]

    set_arg_type(ctx, func, arg_1, INPUT)


def check_filter_aliases_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            f"The @{name}.aliases decorator must be applied to a method with "
            f"signature 'def (self, info: GQLInfo, *, value: Any) -> dict[str, DjangoExpression]'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]
    arg_3 = func.arguments[2]

    set_arg_type(ctx, func, arg_1, FILTER)

    if arg_2.variable.name == "info":
        check_arg_type(ctx, arg_2, expected=GQL_INFO)
    else:
        msg = f'The second argument to "{func.name}" must be named "info"'
        ctx.api.fail(msg, arg_2)

    if arg_3.variable.name == "value":
        if arg_3.kind != ArgKind.ARG_NAMED:
            msg = f'Argument "{arg_3.variable.name}" to must be a keyword-only argument'
            ctx.api.fail(msg, arg_3)
    else:
        msg = f'The third argument to "{func.name}" must be named "value"'
        ctx.api.fail(msg, arg_3)

    check_return_type(ctx, func, expected="builtins.dict")


def check_order_aliases_func(ctx: ClassDefContext, func: FuncDef, name: str) -> None:
    if len(func.arguments) != 3:  # noqa: PLR2004
        msg = (
            f"The @{name}.aliases decorator must be applied to a method with "
            f"signature 'def (self, info: GQLInfo, *, descending: bool) -> dict[str, DjangoExpression]'"
        )
        ctx.api.fail(msg, func)
        return

    to_staticmethod(ctx, func)
    arg_1 = func.arguments[0]
    arg_2 = func.arguments[1]
    arg_3 = func.arguments[2]

    set_arg_type(ctx, func, arg_1, ORDER)

    if arg_2.variable.name == "info":
        check_arg_type(ctx, arg_2, expected=GQL_INFO)
    else:
        msg = f'The second argument to "{func.name}" must be named "info"'
        ctx.api.fail(msg, arg_2)

    if arg_3.variable.name == "descending":
        check_arg_type(ctx, arg_3, expected="builtins.bool")
        if arg_3.kind != ArgKind.ARG_NAMED:
            msg = f'Argument "{arg_3.variable.name}" to must be a keyword-only argument'
            ctx.api.fail(msg, arg_3)
    else:
        msg = f'The third argument to "{func.name}" must be named "descending"'
        ctx.api.fail(msg, arg_3)

    check_return_type(ctx, func, expected="builtins.dict")


DESCRIPTOR_MAPPING: dict[str, str] = {
    ENTRYPOINT: ROOT_TYPE,
    FIELD: QUERY_TYPE,
    INPUT: MUTATION_TYPE,
    FILTER: FILTER_SET,
    ORDER: ORDER_SET,
    INTERFACE_FIELD: INTERFACE_TYPE,
    DIRECTIVE_ARGUMENT: DIRECTIVE,
}
DESCRIPTOR_REVERSE_MAPPING = {v: k for k, v in DESCRIPTOR_MAPPING.items()}


METACLASS_MAPPING: dict[str, str] = {
    ROOT_TYPE_META: ROOT_TYPE,
    QUERY_TYPE_META: QUERY_TYPE,
    MUTATION_TYPE_META: MUTATION_TYPE,
    FILTER_SET_META: FILTER_SET,
    ORDER_SET_META: ORDER_SET,
    INTERFACE_TYPE_META: INTERFACE_TYPE,
    DIRECTIVE_META: DIRECTIVE,
}


DECORATOR_METHODS: dict[tuple[str, str], Callable[[ClassDefContext, FuncDef, str], None]] = {
    (ROOT_TYPE, ENTRYPOINT): check_entrypoint_resolve_func,
    (ROOT_TYPE, "resolve"): check_entrypoint_resolve_func,
    (ROOT_TYPE, "permissions"): check_permissions_func,
    (ROOT_TYPE, "visible"): check_visible_func,
    (QUERY_TYPE, FIELD): check_field_resolve_func,
    (QUERY_TYPE, "resolve"): check_field_resolve_func,
    (QUERY_TYPE, "optimize"): check_optimize_func,
    (QUERY_TYPE, "permissions"): check_permissions_func,
    (QUERY_TYPE, "visible"): check_visible_func,
    (MUTATION_TYPE, INPUT): check_input_func,
    (MUTATION_TYPE, "validate"): check_validate_func,
    (MUTATION_TYPE, "permissions"): check_permissions_func,
    (MUTATION_TYPE, "convert"): check_convert_func,
    (MUTATION_TYPE, "visible"): check_visible_func,
    (FILTER_SET, FILTER): check_filter_func,
    (FILTER_SET, "aliases"): check_filter_aliases_func,
    (FILTER_SET, "visible"): check_visible_func,
    (ORDER_SET, "aliases"): check_order_aliases_func,
    (ORDER_SET, "visible"): check_visible_func,
    (INTERFACE_TYPE, INTERFACE_FIELD): check_field_resolve_func,
    (INTERFACE_TYPE, "visible"): check_visible_func,
    (DIRECTIVE, "visible"): check_visible_func,
}


LOCATION_MAP: dict[str, DirectiveLocation] = {
    DIRECTIVE_ARGUMENT: DirectiveLocation.ARGUMENT_DEFINITION,
    ENTRYPOINT: DirectiveLocation.FIELD_DEFINITION,
    FIELD: DirectiveLocation.FIELD_DEFINITION,
    FILTER: DirectiveLocation.INPUT_FIELD_DEFINITION,
    INPUT: DirectiveLocation.INPUT_FIELD_DEFINITION,
    INTERFACE_FIELD: DirectiveLocation.FIELD_DEFINITION,
    ORDER: DirectiveLocation.ENUM_VALUE,
}
