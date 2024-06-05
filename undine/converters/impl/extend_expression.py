from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.db.models import Expression, F, OuterRef, Q, Subquery
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import ResolvedOuterRef

from undine.converters import extend_expression


@extend_expression.register
def _(expression: F, **kwargs: Any) -> F:
    field_name: str = kwargs["field_name"]
    expression = deepcopy(expression)
    expression.name = f"{field_name}{LOOKUP_SEP}{expression.name}"
    return expression


@extend_expression.register
def _(expression: Q, **kwargs: Any) -> Q:
    field_name: str = kwargs["field_name"]
    expression = deepcopy(expression)

    children = expression.children
    expression.children = []
    for child in children:
        if isinstance(child, tuple):
            key = f"{field_name}{LOOKUP_SEP}{child[0]}"
            value = child[1]

            if value in extend_expression:
                value = extend_expression(child[1], field_name=field_name)

            expression.children.append((key, value))
            continue

        new_expression = extend_expression(child, field_name=field_name)
        expression.children.append(new_expression)

    return expression


@extend_expression.register
def _(expression: Expression, **kwargs: Any) -> Expression:
    field_name: str = kwargs["field_name"]
    expression = deepcopy(expression)

    expressions = [extend_expression(expr, field_name=field_name) for expr in expression.get_source_expressions()]
    expression.set_source_expressions(expressions)
    return expression


@extend_expression.register
def _(expression: Subquery, **kwargs: Any) -> Subquery:
    def extend_subquery(expr: Any, *, field_name_: str) -> Any:
        """For sub-queries, only OuterRefs are rewritten."""
        if isinstance(expr, OuterRef | ResolvedOuterRef):
            expr = deepcopy(expr)
            expr.name = f"{field_name_}{LOOKUP_SEP}{expr.name}"
            return expr

        expr = deepcopy(expr)
        expressions = [extend_subquery(expr, field_name_=field_name_) for expr in expr.get_source_expressions()]
        expr.set_source_expressions(expressions)
        return expr

    field_name: str = kwargs["field_name"]
    expression = deepcopy(expression)
    sub_expressions = expression.query.where.children
    expression.query.where.children = []
    for child in sub_expressions:
        expression.query.where.children.append(extend_subquery(child, field_name_=field_name))
    return expression
