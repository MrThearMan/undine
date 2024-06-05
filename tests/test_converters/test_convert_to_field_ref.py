from __future__ import annotations

import datetime
import decimal
import uuid
from typing import NamedTuple

import pytest
from django.db.models import F, Q, Subquery, Value
from django.db.models.functions import Now

from example_project.app.models import Comment, Project, Task, TaskTypeChoices
from tests.helpers import mock_gql_info, parametrize_helper
from undine import Calculation, CalculationArgument, DjangoExpression, Field, GQLInfo, QueryType
from undine.converters import convert_to_field_ref
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.optimizer import OptimizationData


def test_convert_to_field_ref__str() -> None:
    class TaskType(QueryType[Task]):
        name = Field("name")

    field = Task._meta.get_field("name")
    assert convert_to_field_ref("name", caller=TaskType.name) == field


class Params(NamedTuple):
    value: type
    expected: TypeRef


@pytest.mark.parametrize(
    **parametrize_helper({
        "str": Params(
            value=str,
            expected=TypeRef(value=str),
        ),
        "bool": Params(
            value=bool,
            expected=TypeRef(value=bool),
        ),
        "int": Params(
            value=int,
            expected=TypeRef(value=int),
        ),
        "float": Params(
            value=float,
            expected=TypeRef(value=float),
        ),
        "decimal": Params(
            value=decimal.Decimal,
            expected=TypeRef(value=decimal.Decimal),
        ),
        "datetime": Params(
            value=datetime.datetime,
            expected=TypeRef(value=datetime.datetime),
        ),
        "date": Params(
            value=datetime.date,
            expected=TypeRef(value=datetime.date),
        ),
        "time": Params(
            value=datetime.time,
            expected=TypeRef(value=datetime.time),
        ),
        "timedelta": Params(
            value=datetime.timedelta,
            expected=TypeRef(value=datetime.timedelta),
        ),
        "uuid": Params(
            value=uuid.UUID,
            expected=TypeRef(value=uuid.UUID),
        ),
        "enum": Params(
            value=TaskTypeChoices,
            expected=TypeRef(value=TaskTypeChoices),
        ),
        "list": Params(
            value=list,
            expected=TypeRef(value=list),
        ),
        "dict": Params(
            value=dict,
            expected=TypeRef(value=dict),
        ),
    }),
)
def test_convert_to_field_ref__type(value, expected) -> None:
    class TaskType(QueryType[Task]):
        foo = Field(value)

    assert convert_to_field_ref(value, caller=TaskType.foo) == expected


def test_convert_to_field_ref__none() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    field = Task._meta.get_field("name")
    assert convert_to_field_ref(None, caller=TaskType.name) == field


def test_convert_to_field_ref__function() -> None:
    def func() -> str: ...

    class TaskType(QueryType[Task]):
        custom = Field(func)

    assert convert_to_field_ref(func, caller=TaskType.custom) == func


def test_convert_to_field_ref__lambda() -> None:
    class TaskType(QueryType[Task]):
        custom = Field(lambda: ProjectType)

    class ProjectType(QueryType[Project]): ...

    value = convert_to_field_ref(lambda: ProjectType, caller=TaskType.custom)

    assert isinstance(value, LazyLambda)
    assert value.callback() == ProjectType


def test_convert_to_field_ref__expression() -> None:
    expr = Now()

    class TaskType(QueryType[Task]):
        custom = Field(expr)

    assert convert_to_field_ref(expr, caller=TaskType.custom) == expr

    assert TaskType.custom.optimizer_func is not None

    info = mock_gql_info()
    data = OptimizationData(model=Task, info=info)

    TaskType.custom.optimizer_func(TaskType.custom, data, info)
    assert data.annotations["custom"] == expr


def test_convert_to_field_ref__subquery() -> None:
    sq = Subquery(Task.objects.values("id"))

    class TaskType(QueryType[Task]):
        custom = Field(sq)

    assert convert_to_field_ref(sq, caller=TaskType.custom) == sq

    assert TaskType.custom.optimizer_func is not None

    info = mock_gql_info()
    data = OptimizationData(model=Task, info=info)

    TaskType.custom.optimizer_func(TaskType.custom, data, info)
    assert data.annotations["custom"] == sq


def test_convert_to_field_ref__f_expression() -> None:
    f = F("name")

    class TaskType(QueryType[Task]):
        name = Field(f)

    field = Task._meta.get_field("name")
    assert convert_to_field_ref(f, caller=TaskType.name) == field


def test_convert_to_field_ref__q_expression() -> None:
    q = Q(name="foo")

    class TaskType(QueryType[Task]):
        name = Field(q)

    assert convert_to_field_ref(q, caller=TaskType.name) == q

    assert TaskType.name.optimizer_func is not None

    info = mock_gql_info()
    data = OptimizationData(model=Task, info=info)

    TaskType.name.optimizer_func(TaskType.name, data, info)
    assert data.annotations["name"] == q


def test_convert_to_field_ref__model_field() -> None:
    field = Task._meta.get_field("name")

    class TaskType(QueryType[Task]):
        name = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.name) == field


def test_convert_to_field_ref__related_field() -> None:
    field = Task._meta.get_field("project")

    class TaskType(QueryType[Task]):
        project = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.project) == LazyRelation(field=field)


def test_convert_to_field_ref__deferred_attribute() -> None:
    class TaskType(QueryType[Task]):
        name = Field(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_field_ref(Task.name, caller=TaskType.name) == field


def test_convert_to_field_ref__forward_many_to_one_descriptor() -> None:
    class TaskType(QueryType[Task]):
        project = Field(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_field_ref(Task.project, caller=TaskType.project) == LazyRelation(field=field)


def test_convert_to_field_ref__reverse_many_to_one_descriptor() -> None:
    class TaskType(QueryType[Task]):
        steps = Field(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_field_ref(Task.steps, caller=TaskType.steps) == LazyRelation(field=field)


def test_convert_to_field_ref__reverse_one_to_one_descriptor() -> None:
    class TaskType(QueryType[Task]):
        result = Field(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_field_ref(Task.result, caller=TaskType.result) == LazyRelation(field=field)


def test_convert_to_field_ref__many_to_many_descriptor__forward() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_field_ref(Task.assignees, caller=TaskType.assignees) == LazyRelation(field=field)


def test_convert_to_field_ref__many_to_many_descriptor__reverse() -> None:
    class TaskType(QueryType[Task]):
        reports = Field(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_field_ref(Task.reports, caller=TaskType.reports) == LazyRelation(field=field)


def test_convert_to_field_ref__query_type() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    assert convert_to_field_ref(ProjectType, caller=TaskType.project) == ProjectType


def test_convert_to_field_ref__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskType(QueryType[Task]):
        comments = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.comments) == LazyRelation(field)


def test_convert_to_field_ref__generic_rel() -> None:
    class TaskType(QueryType[Task]):
        comments = Field(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_field_ref(Task.comments, caller=TaskType.comments) == LazyRelation(field)


def test_convert_to_field_ref__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentType(QueryType[Comment]):
        target = Field(field)

    assert convert_to_field_ref(field, caller=CommentType.target) == LazyGenericForeignKey(field)


def test_convert_to_field_ref__generic_foreign_key__direct_ref() -> None:
    class CommentType(QueryType[Comment]):
        target = Field(Comment.target)

    field = Comment._meta.get_field("target")
    assert convert_to_field_ref(Comment.target, caller=CommentType.target) == LazyGenericForeignKey(field)


def test_convert_to_field_ref__calculation() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class TaskType(QueryType[Task]):
        name = Field(ExampleCalculation)

    assert convert_to_field_ref(ExampleCalculation, caller=TaskType.name) == ExampleCalculation
