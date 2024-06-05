import datetime
import decimal
import uuid
from enum import Enum

import pytest
from django.db.models import F, TextChoices

from example_project.app.models import Comment, Project, Task
from undine import Input, MutationType
from undine.converters import convert_to_input_ref
from undine.dataclasses import TypeRef


def test_convert_to_input_ref__str():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input("name")

    field = Task._meta.get_field("name")
    assert convert_to_input_ref("name", caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__self():
    class TaskCreateMutation(MutationType, model=Task):
        related_tasks = Input("self")

    assert convert_to_input_ref("self", caller=TaskCreateMutation.related_tasks) == TaskCreateMutation


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
def test_convert_to_input_ref__type(ref):
    class TaskCreateMutation(MutationType, model=Task):
        custom = Input(ref)

    assert convert_to_input_ref(ref, caller=TaskCreateMutation.custom) == TypeRef(ref)


def test_convert_to_input_ref__f_expression():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input(F("name"))

    field = Task._meta.get_field("name")
    assert convert_to_input_ref(F("name"), caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__model_field():
    field = Task._meta.get_field("name")

    class TaskCreateMutation(MutationType, model=Task):
        name = Input(field)

    assert convert_to_input_ref(field, caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__deferred_attribute():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_input_ref(Task.name, caller=TaskCreateMutation.name) == field


def test_convert_to_input_ref__forward_many_to_one_descriptor():
    class TaskCreateMutation(MutationType, model=Task):
        project = Input(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_input_ref(Task.project, caller=TaskCreateMutation.project) == field


def test_convert_to_input_ref__reverse_many_to_one_descriptor():
    class TaskCreateMutation(MutationType, model=Task):
        steps = Input(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_input_ref(Task.steps, caller=TaskCreateMutation.steps) == field


def test_convert_to_input_ref__reverse_one_to_one_descriptor():
    class TaskCreateMutation(MutationType, model=Task):
        result = Input(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_input_ref(Task.result, caller=TaskCreateMutation.result) == field


def test_convert_to_input_ref__many_to_many_descriptor__forward():
    class TaskCreateMutation(MutationType, model=Task):
        assignees = Input(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_input_ref(Task.assignees, caller=TaskCreateMutation.assignees) == field


def test_convert_to_input_ref__many_to_many_descriptor__reverse():
    class TaskCreateMutation(MutationType, model=Task):
        reports = Input(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_input_ref(Task.reports, caller=TaskCreateMutation.reports) == field


def test_convert_to_input_ref__mutation_type():
    class ProjectMutation(MutationType, model=Project): ...

    class TaskCreateMutation(MutationType, model=Task):
        project = Input(ProjectMutation)

    assert convert_to_input_ref(ProjectMutation, caller=TaskCreateMutation.project) == ProjectMutation


def test_convert_to_input_ref__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskCreateMutation(MutationType, model=Task):
        comments = Input(field)

    assert convert_to_input_ref(field, caller=TaskCreateMutation.comments) == field


def test_convert_to_input_ref__generic_rel():
    class TaskCreateMutation(MutationType, model=Task):
        comments = Input(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_input_ref(Task.comments, caller=TaskCreateMutation.comments) == field


def test_convert_to_input_ref__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentCreateMutation(MutationType, model=Comment):
        target = Input(field)

    assert convert_to_input_ref(field, caller=CommentCreateMutation.target) == field
