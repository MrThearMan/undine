from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db.models import F, OrderBy, OuterRef, Q, Subquery
from django.db.models.expressions import ResolvedOuterRef
from django.db.models.functions import Now

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine.converters import extend_expression


class Params(NamedTuple):
    input_value: Any
    field_name: str
    output_value: Any


@pytest.mark.parametrize(
    **parametrize_helper({
        "F": Params(
            input_value=F("name"),
            field_name="report",
            output_value=F("report__name"),
        ),
        "Q value": Params(
            input_value=Q(name__exact="foo"),
            field_name="report",
            output_value=Q(report__name__exact="foo"),
        ),
        "Q expression": Params(
            input_value=Q(name__exact=Now()),
            field_name="report",
            output_value=Q(report__name__exact=Now()),
        ),
        "Q multiple": Params(
            input_value=Q(name__in=Now(), name__exact="foo"),
            field_name="report",
            output_value=Q(report__name__in=Now(), report__name__exact="foo"),
        ),
        "Q inner": Params(
            input_value=Q(Q(name__in=Now()) | Q(name__exact="foo")),
            field_name="report",
            output_value=Q(Q(report__name__in=Now()) | Q(report__name__exact="foo")),
        ),
        "expression": Params(
            input_value=OrderBy(F("name")),
            field_name="report",
            output_value=OrderBy(F("report__name")),
        ),
    }),
)
def test_converters__extend_expression(input_value, field_name, output_value) -> None:
    assert repr(extend_expression(input_value, field_name=field_name)) == repr(output_value)


def test_converters__extend_expression__subquery() -> None:
    input_value = Subquery(Task.objects.filter(pk=OuterRef("task")))
    field_name = "report"
    sq = extend_expression(input_value, field_name=field_name)

    condition = sq.query.where.children[0]
    assert isinstance(condition.rhs, ResolvedOuterRef)
    assert condition.rhs.name == "report__task"
