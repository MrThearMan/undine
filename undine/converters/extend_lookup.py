from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import ResolvedOuterRef

from undine.typing import ExpressionLike
from undine.utils.function_dispatcher import FunctionDispatcher

__all__ = [
    "extend_expression_to_joined_table",
]


# TODO: Testing
extend_expression_to_joined_table = FunctionDispatcher[ExpressionLike, ExpressionLike]()
"""
Rewrite an expression so that any containing lookups are referenced from the given table.

Positional arguments:
 - expression: The expression to extend.

Keyword arguments:
 - table_name: Name of the table to extend the lookup to.
"""


@extend_expression_to_joined_table.register
def _(expression: models.F, **kwargs: Any) -> models.F:
    table_name: str = kwargs["table_name"]
    expression = deepcopy(expression)
    expression.name = f"{table_name}{LOOKUP_SEP}{expression.name}"
    return expression


@extend_expression_to_joined_table.register
def _(expression: models.Q, **kwargs: Any) -> models.Q:
    table_name: str = kwargs["table_name"]
    expression = deepcopy(expression)

    children = expression.children
    expression.children = []
    for child in children:
        if isinstance(child, tuple):
            value = child[1]
            if isinstance(child[1], (models.F, models.Q, models.Expression, models.Subquery)):
                value = extend_expression_to_joined_table(child[1], table_name)

            expression.children.append((f"{table_name}{LOOKUP_SEP}{child[0]}", value))

        else:
            expression.children.append(extend_expression_to_joined_table(child, table_name))

    return expression


@extend_expression_to_joined_table.register
def _(expression: models.Expression, **kwargs: Any) -> models.Expression:
    table_name: str = kwargs["table_name"]
    expression = deepcopy(expression)

    expressions = [extend_expression_to_joined_table(expr, table_name) for expr in expression.get_source_expressions()]
    expression.set_source_expressions(expressions)
    return expression


@extend_expression_to_joined_table.register
def _(expression: models.Subquery, **kwargs: Any) -> models.Subquery:
    def extend_subquery_to_joined_table(expr: Any, table_name: str) -> Any:
        """For sub-queries, only OuterRefs are rewritten."""
        if isinstance(expr, (models.OuterRef, ResolvedOuterRef)):
            expr = deepcopy(expr)
            expr.name = f"{table_name}{LOOKUP_SEP}{expr.name}"
            return expr

        expr = deepcopy(expr)
        expressions = [extend_subquery_to_joined_table(expr, table_name) for expr in expr.get_source_expressions()]
        expr.set_source_expressions(expressions)
        return expr

    table_name: str = kwargs["table_name"]
    expression = deepcopy(expression)
    sub_expressions = expression.query.where.children
    expression.query.where.children = []
    for child in sub_expressions:
        expression.query.where.children.append(extend_subquery_to_joined_table(child, table_name))
    return expression
