from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from django.db.models import CharField, Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Person, Project, Task
from tests.helpers import parametrize_helper
from undine import MutationType, QueryType
from undine.converters import is_many
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef


class Params(NamedTuple):
    value: Any
    expected: bool


def func_1() -> list: ...
def func_2() -> list[str]: ...
def func_3() -> str: ...


class Arguments(TypedDict):
    value: int


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "list": Params(
                value=func_1,
                expected=True,
            ),
            "list generic": Params(
                value=func_2,
                expected=True,
            ),
            "non-list": Params(
                value=func_3,
                expected=False,
            ),
            "model field": Params(
                value=CharField(max_length=255),
                expected=False,
            ),
            "foreign key": Params(
                value=Task._meta.get_field("project"),
                expected=False,
            ),
            "many to many field": Params(
                value=Task._meta.get_field("assignees"),
                expected=True,
            ),
            "reverse foreign key": Params(
                value=Task._meta.get_field("steps"),
                expected=True,
            ),
            "reverse many to many field": Params(
                value=Task._meta.get_field("reports"),
                expected=True,
            ),
            "generic relation": Params(
                value=Task._meta.get_field("comments"),
                expected=True,
            ),
            "generic foreign key": Params(
                value=Comment._meta.get_field("target"),
                expected=False,
            ),
            "expression": Params(
                value=Now(),
                expected=False,
            ),
            "subquery": Params(
                value=Subquery(Task.objects.values("id")),
                expected=False,
            ),
            "lazy_union": Params(
                value=LazyQueryTypeUnion(field=Comment._meta.get_field("target")),
                expected=False,
            ),
            "type ref": Params(
                value=TypeRef(int),
                expected=False,
            ),
            "type ref list": Params(
                value=TypeRef(list),
                expected=True,
            ),
            "type ref list generic": Params(
                value=TypeRef(list[int]),
                expected=True,
            ),
            "calculated single": Params(
                value=Calculated(Arguments, returns=int),
                expected=False,
            ),
            "calculated many": Params(
                value=Calculated(Arguments, returns=list[int]),
                expected=True,
            ),
        },
    ),
)
def test_is_many(value, expected):
    assert is_many(value) is expected


def test_is_many__lazy_query_type__foreign_key():
    class ProjectType(QueryType, model=Project): ...

    field = Task._meta.get_field("project")
    lazy = LazyQueryType(field=field)

    assert is_many(lazy) is False


def test_is_many__lazy_query_type__many_to_many():
    class AssigneeType(QueryType, model=Person): ...

    field = Task._meta.get_field("assignees")
    lazy = LazyQueryType(field=field)

    assert is_many(lazy) is True


def test_is_many__lazy_lambda_query_type():
    class TaskType(QueryType, model=Task): ...

    lazy = LazyLambdaQueryType(callback=lambda: TaskType)

    assert is_many(lazy) is False


def test_is_many__lazy_query_type_uniony():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task): ...

    class CommentType(QueryType, model=Comment): ...

    field = Comment._meta.get_field("target")
    lazy = LazyQueryTypeUnion(field=field)

    assert is_many(lazy) is False


def test_is_many__query_type__foreign_key():
    class ProjectType(QueryType, model=Project): ...

    assert is_many(ProjectType, model=Task, name="project") is False


def test_is_many__query_type__many_to_many():
    class AssigneeType(QueryType, model=Person): ...

    assert is_many(AssigneeType, model=Task, name="assignees") is True


def test_is_many__mutation_type__foreign_key():
    class ProjectMutation(MutationType, model=Project): ...

    assert is_many(ProjectMutation, model=Task, name="project") is False


def test_is_many__mutation_type__many_to_many():
    class AssigneeMutation(MutationType, model=Person): ...

    assert is_many(AssigneeMutation, model=Task, name="assignees") is True
