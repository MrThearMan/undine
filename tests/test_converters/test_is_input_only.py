from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db.models import CharField

from example_project.app.models import Comment, Project, Task
from tests.helpers import parametrize_helper
from undine import Input, MutationType
from undine.converters import is_input_only
from undine.dataclasses import TypeRef


class Params(NamedTuple):
    value: Any
    expected: bool


@pytest.mark.parametrize(
    **parametrize_helper({
        "model field": Params(
            value=CharField(max_length=255),
            expected=False,
        ),
        "foreign key": Params(
            value=Task._meta.get_field("project"),
            expected=False,
        ),
        "reverse foreign key": Params(
            value=Task._meta.get_field("steps"),
            expected=False,
        ),
        "generic relation": Params(
            value=Task._meta.get_field("comments"),
            expected=False,
        ),
        "generic foreign key": Params(
            value=Comment._meta.get_field("target"),
            expected=False,
        ),
    }),
)
def test_is_input_only(value, expected) -> None:
    assert is_input_only(value) is expected


def test_is_input_only__mutation_type() -> None:
    class TaskMutation(MutationType[Task]): ...

    assert is_input_only(TaskMutation) is False


def test_is_input_only__type_ref() -> None:
    class TaskCreateMutation(MutationType[Task]):
        foo = Input(int)

    assert is_input_only(TypeRef(int), caller=TaskCreateMutation.foo) is True


def test_is_input_only__type_ref__custom_mutation() -> None:
    class TaskMutation(MutationType[Task]):
        foo = Input(int)

    assert is_input_only(TypeRef(int), caller=TaskMutation.foo) is False


def test_is_input_only__type_ref__model_field() -> None:
    class TaskMutation(MutationType[Task]):
        name = Input(str)

    assert is_input_only(TypeRef(str), caller=TaskMutation.name) is False


def test_is_input_only__model() -> None:
    class TaskMutation(MutationType[Task]):
        project = Input(Project)

    assert is_input_only(Task, caller=TaskMutation.project) is False


def test_is_input_only__function() -> None:
    def func(root: Any, info: Any, value: Any) -> str:
        return value

    class TaskCreateMutation(MutationType[Task]):
        foo = Input(func)

    assert is_input_only(func, caller=TaskCreateMutation.foo) is True


def test_is_input_only__function__custom_mutation() -> None:
    def func(root: Any, info: Any, value: Any) -> str:
        return value

    class TaskMutation(MutationType[Task]):
        foo = Input(func)

    assert is_input_only(func, caller=TaskMutation.foo) is False


def test_is_input_only__function__model_field() -> None:
    def func(root: Any, info: Any, value: Any) -> str:
        return value

    class TaskMutation(MutationType[Task]):
        name = Input(func)

    assert is_input_only(func, caller=TaskMutation.name) is False
