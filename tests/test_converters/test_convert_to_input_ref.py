from __future__ import annotations

import datetime
import decimal
import os
import uuid
from enum import Enum

import pytest
from django.db.models import F, TextChoices

from example_project.app.models import Comment, Project, Task
from undine import Input, MutationType
from undine.converters import convert_to_input_ref
from undine.dataclasses import LazyLambda, TypeRef
from undine.exceptions import InvalidInputMutationTypeError


def test_convert_to_input_ref__str() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input("name")

    field = Task._meta.get_field("name")
    assert convert_to_input_ref("name", caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__lambda() -> None:
    class TaskCreateMutation(MutationType[Task]):
        related_tasks = Input(lambda: TaskCreateMutation)

    value = convert_to_input_ref(lambda: TaskCreateMutation, caller=TaskCreateMutation.related_tasks)

    assert isinstance(value, LazyLambda)
    assert value.callback() == TaskCreateMutation


class ExampleEnum(Enum):
    FOO = "foo"
    BAR = "bar"


class ExampleTextChoices(TextChoices):
    FOO = "foo", "Foo"
    BAR = "bar", "Bar"


@pytest.mark.parametrize(
    "ref",
    [
        str,
        bool,
        int,
        float,
        decimal.Decimal,
        datetime.datetime,
        datetime.date,
        datetime.time,
        datetime.timedelta,
        uuid.UUID,
        ExampleEnum,
        ExampleTextChoices,
        list,
        dict,
    ],
)
def test_convert_to_input_ref__type(ref) -> None:
    class TaskCreateMutation(MutationType[Task]):
        custom = Input(ref)

    assert convert_to_input_ref(ref, caller=TaskCreateMutation.custom) == TypeRef(ref)


def test_convert_to_input_ref__f_expression() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input(F("name"))

    field = Task._meta.get_field("name")
    assert convert_to_input_ref(F("name"), caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__model_field() -> None:
    field = Task._meta.get_field("name")

    class TaskCreateMutation(MutationType[Task]):
        name = Input(field)

    assert convert_to_input_ref(field, caller=TaskCreateMutation.name) == field


@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Does not work with async")  # TODO: Async
def test_convert_to_input_ref__model() -> None:
    class TaskCreateMutation(MutationType[Task]):
        project = Input(Project)

    assert convert_to_input_ref(Project, caller=TaskCreateMutation.project) == Project


def test_convert_to_input_ref__deferred_attribute() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_input_ref(Task.name, caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__forward_many_to_one_descriptor() -> None:
    class TaskCreateMutation(MutationType[Task]):
        project = Input(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_input_ref(Task.project, caller=TaskCreateMutation.project) == field


def test_convert_to_input_ref__reverse_many_to_one_descriptor() -> None:
    class TaskCreateMutation(MutationType[Task]):
        steps = Input(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_input_ref(Task.steps, caller=TaskCreateMutation.steps) == field


def test_convert_to_input_ref__reverse_one_to_one_descriptor() -> None:
    class TaskCreateMutation(MutationType[Task]):
        result = Input(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_input_ref(Task.result, caller=TaskCreateMutation.result) == field


def test_convert_to_input_ref__many_to_many_descriptor__forward() -> None:
    class TaskCreateMutation(MutationType[Task]):
        assignees = Input(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_input_ref(Task.assignees, caller=TaskCreateMutation.assignees) == field


def test_convert_to_input_ref__many_to_many_descriptor__reverse() -> None:
    class TaskCreateMutation(MutationType[Task]):
        reports = Input(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_input_ref(Task.reports, caller=TaskCreateMutation.reports) == field


def test_convert_to_input_ref__mutation_type() -> None:
    class TaskProject(MutationType[Project], kind="related"): ...

    assert "tasks" in TaskProject.__input_map__

    class TaskCreateMutation(MutationType[Task]):
        project = Input(TaskProject)

    assert convert_to_input_ref(TaskProject, caller=TaskCreateMutation.project) == TaskProject

    # Since `TaskProject` is used as Related input for `TaskCreateMutation`,
    # the reverse relation is removed from its input map.
    assert "tasks" not in TaskProject.__input_map__


def test_convert_to_input_ref__mutation_type__not_related() -> None:
    class ProjectMutation(MutationType[Project]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    inpt = Input(ProjectMutation)

    with pytest.raises(InvalidInputMutationTypeError):
        convert_to_input_ref(TaskCreateMutation, caller=inpt)


def test_convert_to_input_ref__generic_relation() -> None:
    field = Task._meta.get_field("comments")

    class TaskCreateMutation(MutationType[Task]):
        comments = Input(field)

    assert convert_to_input_ref(field, caller=TaskCreateMutation.comments) == field


def test_convert_to_input_ref__generic_rel() -> None:
    class TaskCreateMutation(MutationType[Task]):
        comments = Input(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_input_ref(Task.comments, caller=TaskCreateMutation.comments) == field


def test_convert_to_input_ref__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    class CommentCreateMutation(MutationType[Comment]):
        target = Input(field)

    assert convert_to_input_ref(field, caller=CommentCreateMutation.target) == field
