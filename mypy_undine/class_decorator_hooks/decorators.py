from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Protocol

from graphql import DirectiveLocation
from mypy.nodes import CallExpr, ListExpr, NameExpr

from mypy_undine.fullnames import (
    DIRECTIVE_META,
    FILTER_SET,
    FILTER_SET_META,
    INTERFACE_TYPE,
    INTERFACE_TYPE_META,
    MUTATION_TYPE,
    ORDER_SET,
    ORDER_SET_META,
    QUERY_TYPE,
    ROOT_TYPE,
    UNION_TYPE,
)
from mypy_undine.utils.types_utils import (
    directive_locations_from_class,
    filterset_models_from_class,
    models_match,
    orderset_models_from_class,
    query_type_model_from_class,
    supports_interfaces,
    type_fingerprint,
    union_member_model_ids,
)

if TYPE_CHECKING:
    from mypy.nodes import TypeInfo
    from mypy.plugin import ClassDefContext


def filterset_hook(ctx: ClassDefContext, info: TypeInfo) -> None:
    target = ctx.cls.info
    filterset_models = filterset_models_from_class(info)
    if filterset_models is None:
        return

    query_model = query_type_model_from_class(target)
    if query_model is not None:
        if len(filterset_models) != 1:
            msg = f"FilterSet used as @{info.name} on QueryType must be parameterized with a single model"
            ctx.api.fail(msg, ctx.reason)
            return

        if not models_match(filterset_models[0], query_model):
            msg = "FilterSet model does not match QueryType model"
            ctx.api.fail(msg, ctx.reason)

        return

    union_ids = union_member_model_ids(target)
    if union_ids is not None:
        if len(filterset_models) < 2:  # noqa: PLR2004
            msg = "FilterSet used on UnionType must be parameterized with multiple models"
            ctx.api.fail(msg, ctx.reason)
            return

        deco_ids = frozenset(type_fingerprint(m) for m in filterset_models)
        if deco_ids != union_ids:
            msg = "FilterSet models do not match UnionType member models"
            ctx.api.fail(msg, ctx.reason)

        return

    msg = "FilterSet decorator must be applied to a QueryType or UnionType subclass"
    ctx.api.fail(msg, ctx.reason)
    return


def orderset_hook(ctx: ClassDefContext, info: TypeInfo) -> None:
    target = ctx.cls.info
    deco_models = orderset_models_from_class(info)
    if deco_models is None:
        return

    query_model = query_type_model_from_class(target)
    if query_model is not None:
        if len(deco_models) != 1:
            msg = f"OrderSet used as @{info.name} on QueryType must be parameterized with a single model"
            ctx.api.fail(msg, ctx.reason)
            return

        if not models_match(deco_models[0], query_model):
            msg = "OrderSet model does not match QueryType model"
            ctx.api.fail(msg, ctx.reason)

        return

    union_ids = union_member_model_ids(target)
    if union_ids is not None:
        if len(deco_models) < 2:  # noqa: PLR2004
            msg = "OrderSet used on UnionType must be parameterized with multiple models"
            ctx.api.fail(msg, ctx.reason)
            return

        deco_ids = frozenset(type_fingerprint(m) for m in deco_models)
        if deco_ids != union_ids:
            msg = "OrderSet models do not match UnionType member models"
            ctx.api.fail(msg, ctx.reason)

        return

    msg = "OrderSet decorator must be applied to a QueryType or UnionType subclass"
    ctx.api.fail(msg, ctx.reason)
    return


def interface_hook(ctx: ClassDefContext, info: TypeInfo) -> None:
    target = ctx.cls.info
    if not supports_interfaces(target):
        msg = "InterfaceTypes can only be applied to a QueryType or InterfaceType subclass"
        ctx.api.fail(msg, ctx.reason)
        return

    return


def directive_hook(ctx: ClassDefContext, info: TypeInfo) -> None:
    target = ctx.cls.info
    accepted_locations = directive_locations_from_class(info)

    for base in target.mro[1:]:
        location = LOCATION_MAP.get(base.fullname)
        if location is None:
            continue

        if location not in accepted_locations:
            msg = f'Directive "{info.name}" does not support location "{location.name}"'
            ctx.api.fail(msg, ctx.reason)

        break

    else:
        msg = f'Class "{target.name}" does not support directives'
        ctx.api.fail(msg, ctx.reason)
        return

    directive_count: int = 0

    directives = copy(ctx.cls.decorators)

    directives_list = ctx.cls.keywords.get("directives")
    if isinstance(directives_list, ListExpr):
        directives.extend(directives_list.items)

    for expr in directives:
        if not isinstance(expr, CallExpr):
            continue

        callee = expr.callee
        if not isinstance(callee, NameExpr):
            continue

        if callee.fullname != info.fullname:
            continue

        directive_count += 1
        if directive_count > 1:
            msg = f'Directive "{info.name}" is not repeatable'
            ctx.api.fail(msg, ctx.reason)
            break


class DecoratorHook(Protocol):
    def __call__(self, ctx: ClassDefContext, *, info: TypeInfo) -> None: ...


DECORATOR_HOOKS: dict[str, DecoratorHook] = {
    FILTER_SET_META: filterset_hook,
    ORDER_SET_META: orderset_hook,
    INTERFACE_TYPE_META: interface_hook,
    DIRECTIVE_META: directive_hook,
}


LOCATION_MAP: dict[str, DirectiveLocation] = {
    FILTER_SET: DirectiveLocation.INPUT_OBJECT,
    INTERFACE_TYPE: DirectiveLocation.INTERFACE,
    MUTATION_TYPE: DirectiveLocation.INPUT_OBJECT,
    ORDER_SET: DirectiveLocation.ENUM,
    QUERY_TYPE: DirectiveLocation.OBJECT,
    ROOT_TYPE: DirectiveLocation.OBJECT,
    UNION_TYPE: DirectiveLocation.UNION,
}
