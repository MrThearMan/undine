from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from django.db.models import CharField, DateTimeField
from django.db.models.functions import Cast, Now

from example_project.app.models import Comment, Person, Project, Task
from tests.helpers import parametrize_helper
from undine import Field, QueryType
from undine.converters import is_field_nullable
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion


class Params(NamedTuple):
    value: Any
    expected: bool


def func_1() -> int: ...
def func_2() -> int | None: ...
def func_3() -> int | str: ...


class Arguments(TypedDict):
    value: int


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "func": Params(
                value=func_1,
                expected=False,
            ),
            "func nullable": Params(
                value=func_2,
                expected=True,
            ),
            "model field": Params(
                value=CharField(max_length=255),
                expected=False,
            ),
            "model field nullable": Params(
                value=CharField(max_length=255, null=True),
                expected=True,
            ),
            "reverse one-to-one": Params(
                value=Task._meta.get_field("result"),
                expected=True,
            ),
            "reverse foreign key": Params(
                value=Task._meta.get_field("steps"),
                expected=False,
            ),
            "reverse many-to-many key": Params(
                value=Task._meta.get_field("reports"),
                expected=False,
            ),
            "expression": Params(
                value=Now(),
                expected=False,
            ),
            "expression nullable": Params(
                value=Cast(Now(), output_field=DateTimeField(null=True)),
                expected=True,
            ),
            "lazy query type": Params(
                value=LazyQueryType(field=Task._meta.get_field("project")),
                expected=True,
            ),
            "lazy query type union": Params(
                value=LazyQueryTypeUnion(field=Comment._meta.get_field("target")),
                expected=False,
            ),
            "generic relation": Params(
                value=Task._meta.get_field("comments"),
                expected=True,
            ),
            "generic foreign key": Params(
                value=Comment._meta.get_field("target"),
                expected=False,
            ),
            "calculated single": Params(
                value=Calculated(Arguments, return_annotation=int),
                expected=False,
            ),
            "calculated many": Params(
                value=Calculated(Arguments, return_annotation=int | None),
                expected=True,
            ),
        },
    ),
)
def test_is_field_nullable(value, expected):
    assert is_field_nullable(value) is expected


def test_is_field_nullable__query_type():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType)

    assert is_field_nullable(TaskType, caller=TaskType.assignees) is False


def test_is_field_nullable__query_type__nullable():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    assert is_field_nullable(TaskType, caller=TaskType.project) is True


def test_is_field_nullable__query_type__lambda():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(lambda: PersonType)

    lazy = LazyLambdaQueryType(callback=lambda: PersonType)
    assert is_field_nullable(lazy, caller=TaskType.assignees) is False
