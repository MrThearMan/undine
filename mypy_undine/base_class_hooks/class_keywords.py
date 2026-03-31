from __future__ import annotations

import dataclasses
from collections import Counter
from itertools import chain
from typing import TYPE_CHECKING

from graphql import DirectiveLocation
from mypy.errorcodes import ARG_TYPE, MISC
from mypy.nodes import CallExpr, ListExpr, NameExpr, TypeInfo

from mypy_undine.fullnames import (
    DIRECTIVE,
    DIRECTIVE_META,
    FILTER_SET,
    INTERFACE_TYPE,
    MUTATION_TYPE,
    ORDER_SET,
    QUERY_TYPE,
    ROOT_TYPE,
    UNION_TYPE,
)
from mypy_undine.utils.expression_utils import (
    is_boolean,
    is_directive_list,
    is_exclude_list,
    is_extensions,
    is_filterset,
    is_integer_or_none,
    is_interface_list,
    is_kind,
    is_locations_list,
    is_orderset,
    is_related_action,
    is_string,
)
from mypy_undine.utils.types_utils import directive_locations_from_class

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mypy.nodes import Expression
    from mypy.plugin import ClassDefContext


def validate_class_keywords(ctx: ClassDefContext, *, fullname: str) -> None:
    keyword_checks = KEYWORD_CHECKS.get(fullname)
    if keyword_checks is None:
        return

    label = fullname.rsplit(".", maxsplit=1)[-1]

    required_keywords: set[str] = {key for key, data in keyword_checks.items() if data.required}

    for key, expr in ctx.cls.keywords.items():
        if key == "metaclass":
            continue

        keyword_data = keyword_checks.get(key)
        if keyword_data is None:
            msg = f'Unexpected keyword argument "{key}" for "{label}" class definition'
            ctx.api.fail(msg, expr, code=MISC)
            continue

        required_keywords.discard(key)

        if not keyword_data.type_checker(expr):
            expected = keyword_data.expected_type
            msg = f'Argument "{key}" to "{ctx.cls.name}" has incompatible type; expected "{expected}"'
            ctx.api.fail(msg, expr, code=ARG_TYPE)
            continue

        for check in keyword_data.additional_checks:
            check(ctx, expr)

    for key in required_keywords:
        msg = f'Missing required class definition keyword argument "{key}" for "{ctx.cls.name}"'
        ctx.api.fail(msg, ctx.cls, code=MISC)


def check_directives(ctx: ClassDefContext, expr: Expression) -> None:  # noqa: C901,PLR0912
    if not isinstance(expr, ListExpr):
        return

    if not expr.items:
        return

    target = ctx.cls.info

    location: DirectiveLocation | None = None
    for base in target.mro[1:]:
        location = LOCATION_MAP.get(base.fullname)
        if location is not None:
            break

    if location is None:
        msg = f'Class "{target.name}" does not support directives'
        ctx.api.fail(msg, ctx.reason)
        return

    # Technically this counts other decorators as well
    decorator_counts = Counter(
        decorator.callee.fullname
        for decorator in chain(ctx.cls.decorators, expr.items)
        if isinstance(decorator, CallExpr) and isinstance(decorator.callee, NameExpr)
    )

    for directive in expr.items:
        if not isinstance(directive, CallExpr):
            continue

        callee = directive.callee
        if not isinstance(callee, NameExpr):
            continue

        type_info = callee.node
        if not isinstance(type_info, TypeInfo):
            continue

        if type_info.metaclass_type is None:
            continue

        if type_info.metaclass_type.type.fullname != DIRECTIVE_META:
            continue

        accepted_locations = directive_locations_from_class(type_info)
        if location not in accepted_locations:
            msg = f'Directive "{callee.name}" does not support location "{location.name}"'
            ctx.api.fail(msg, directive)
            continue

        count = decorator_counts[callee.fullname]
        if count > 1:
            msg = f'Directive "{callee.name}" is not repeatable'
            ctx.api.fail(msg, directive, code=MISC)
            continue


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class KeywordData:
    type_checker: Callable[[Expression], bool]
    expected_type: str
    required: bool = False
    additional_checks: list[Callable[[ClassDefContext, Expression], None]] = dataclasses.field(default_factory=list)


KEYWORD_CHECKS: Mapping[str, Mapping[str, KeywordData]] = {
    DIRECTIVE: {
        "locations": KeywordData(
            type_checker=is_locations_list,
            expected_type="list[DirectiveLocation]",
            required=True,
        ),
        "is_repeatable": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    FILTER_SET: {
        "auto": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "exclude": KeywordData(
            type_checker=is_exclude_list,
            expected_type="list[str]",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    INTERFACE_TYPE: {
        "interfaces": KeywordData(
            type_checker=is_interface_list,
            expected_type="list[type[InterfaceType]]",
        ),
        "cache_time": KeywordData(
            type_checker=is_integer_or_none,
            expected_type="int | None",
        ),
        "cache_per_user": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    MUTATION_TYPE: {
        "kind": KeywordData(
            type_checker=is_kind,
            expected_type="Literal['create', 'update', 'delete', 'related', 'custom']",
        ),
        "related_action": KeywordData(
            type_checker=is_related_action,
            expected_type="Literal['null', 'delete', 'ignore']",
        ),
        "auto": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "exclude": KeywordData(
            type_checker=is_exclude_list,
            expected_type="list[str]",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    ORDER_SET: {
        "auto": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "exclude": KeywordData(
            type_checker=is_exclude_list,
            expected_type="list[str]",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    QUERY_TYPE: {
        "filterset": KeywordData(
            type_checker=is_filterset,
            expected_type="type[FilterSet]",
        ),
        "orderset": KeywordData(
            type_checker=is_orderset,
            expected_type="type[OrderSet]",
        ),
        "auto": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "exclude": KeywordData(
            type_checker=is_exclude_list,
            expected_type="list[str]",
        ),
        "interfaces": KeywordData(
            type_checker=is_interface_list,
            expected_type="list[type[InterfaceType]]",
        ),
        "cache_time": KeywordData(
            type_checker=is_integer_or_none,
            expected_type="int | None",
        ),
        "cache_per_user": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "register": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    ROOT_TYPE: {
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
    UNION_TYPE: {
        "filterset": KeywordData(
            type_checker=is_filterset,
            expected_type="type[FilterSet]",
        ),
        "orderset": KeywordData(
            type_checker=is_orderset,
            expected_type="type[OrderSet]",
        ),
        "cache_time": KeywordData(
            type_checker=is_integer_or_none,
            expected_type="int | None",
        ),
        "cache_per_user": KeywordData(
            type_checker=is_boolean,
            expected_type="bool",
        ),
        "schema_name": KeywordData(
            type_checker=is_string,
            expected_type="str",
        ),
        "directives": KeywordData(
            type_checker=is_directive_list,
            expected_type="list[Directive]",
            additional_checks=[check_directives],
        ),
        "extensions": KeywordData(
            type_checker=is_extensions,
            expected_type="dict[str, Any]",
        ),
    },
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
