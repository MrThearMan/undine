from __future__ import annotations

import os

import pytest

from example_project.app.models import Comment, Project, Task
from undine import Input, MutationType
from undine.converters import is_input_required
from undine.dataclasses import TypeRef


def test_is_required__model_field__create_mutation() -> None:
    class TaskCreateMutation(MutationType[Task]):
        name = Input()

    field = Task._meta.get_field("name")
    assert is_input_required(field, caller=TaskCreateMutation.name) is True


def test_is_required__model_field__update_mutation() -> None:
    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

    field = Task._meta.get_field("name")
    assert is_input_required(field, caller=TaskUpdateMutation.name) is False


def test_is_required__model_field__reverse_foreign_key() -> None:
    class TaskCreateMutation(MutationType[Task]):
        steps = Input()

    field = Task._meta.get_field("steps")
    assert is_input_required(field, caller=TaskCreateMutation.steps) is False


def test_is_required__model_field__many_to_many() -> None:
    class TaskCreateMutation(MutationType[Task]):
        assignees = Input()

    field = Task._meta.get_field("assignees")
    assert is_input_required(field, caller=TaskCreateMutation.assignees) is False


@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Does not work with async")  # TODO: Async
def test_is_required__model_field__model() -> None:
    class TaskCreateMutation(MutationType[Task]):
        project = Input(Project)

    assert is_input_required(Project, caller=TaskCreateMutation.project) is False


def test_is_required__model_field__nullable_field() -> None:
    class TaskCreateMutation(MutationType[Task]):
        request = Input()

    field = Task._meta.get_field("request")
    assert is_input_required(field, caller=TaskCreateMutation.request) is False


def test_is_required__model_field__primary_key() -> None:
    class TaskUpdateMutation(MutationType[Task]):
        pk = Input()

    field = Task._meta.get_field("id")
    assert is_input_required(field, caller=TaskUpdateMutation.pk) is True


def test_is_required__type_ref() -> None:
    class TaskUpdateMutation(MutationType[Task]):
        field = Input(int)

    assert is_input_required(TypeRef(int), caller=TaskUpdateMutation.field) is False


def test_is_required__mutation_type() -> None:
    class TaskProject(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(TaskProject)

    assert is_input_required(TaskProject, caller=TaskUpdateMutation.project) is False


def test_is_required__generic_foreign_key__create_mutation() -> None:
    class CommentCreateMutation(MutationType[Comment]):
        target = Input()

    field = Comment._meta.get_field("target")
    assert is_input_required(field, caller=CommentCreateMutation.target) is True


def test_is_required__generic_foreign_key__update_mutation() -> None:
    class CommentUpdateMutation(MutationType[Comment]):
        target = Input()

    field = Comment._meta.get_field("target")
    assert is_input_required(field, caller=CommentUpdateMutation.target) is False


def test_is_required__generic_relation() -> None:
    class TaskMutation(MutationType[Task]):
        comments = Input()

    field = Task._meta.get_field("comments")
    assert is_input_required(field, caller=TaskMutation.comments) is False
