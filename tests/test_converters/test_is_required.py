from __future__ import annotations

from example_project.app.models import Comment, Project, Task
from undine import Input, MutationType
from undine.converters import is_input_required
from undine.typing import TypeRef


def test_is_required__model_field__create_mutation():
    class TaskCreateMutation(MutationType, model=Task):
        name = Input()

    field = Task._meta.get_field("name")
    assert is_input_required(field, caller=TaskCreateMutation.name) is True


def test_is_required__model_field__update_mutation():
    class TaskUpdateMutation(MutationType, model=Task):
        name = Input()

    field = Task._meta.get_field("name")
    assert is_input_required(field, caller=TaskUpdateMutation.name) is False


def test_is_required__model_field__reverse_foreign_key():
    class TaskCreateMutation(MutationType, model=Task):
        steps = Input()

    field = Task._meta.get_field("steps")
    assert is_input_required(field, caller=TaskCreateMutation.steps) is False


def test_is_required__model_field__many_to_many():
    class TaskCreateMutation(MutationType, model=Task):
        assignees = Input()

    field = Task._meta.get_field("assignees")
    assert is_input_required(field, caller=TaskCreateMutation.assignees) is False


def test_is_required__model_field__nullable_field():
    class TaskCreateMutation(MutationType, model=Task):
        request = Input()

    field = Task._meta.get_field("request")
    assert is_input_required(field, caller=TaskCreateMutation.request) is False


def test_is_required__model_field__primary_key():
    class TaskUpdateMutation(MutationType, model=Task):
        pk = Input()

    field = Task._meta.get_field("id")
    assert is_input_required(field, caller=TaskUpdateMutation.pk) is True


def test_is_required__type_ref():
    class TaskUpdateMutation(MutationType, model=Task):
        field = Input(int)

    assert is_input_required(TypeRef(int), caller=TaskUpdateMutation.field) is False


def test_is_required__mutation_type():
    class ProjectMutation(MutationType, model=Project): ...

    class TaskUpdateMutation(MutationType, model=Task):
        project = Input(ProjectMutation)

    assert is_input_required(ProjectMutation, caller=TaskUpdateMutation.project) is False


def test_is_required__generic_foreign_key__create_mutation():
    class CommentCreateMutation(MutationType, model=Comment):
        target = Input()

    field = Comment._meta.get_field("target")
    assert is_input_required(field, caller=CommentCreateMutation.target) is True


def test_is_required__generic_foreign_key__update_mutation():
    class CommentUpdateMutation(MutationType, model=Comment):
        target = Input()

    field = Comment._meta.get_field("target")
    assert is_input_required(field, caller=CommentUpdateMutation.target) is False


def test_is_required__generic_relation():
    class TaskMutation(MutationType, model=Task):
        comments = Input()

    field = Task._meta.get_field("comments")
    assert is_input_required(field, caller=TaskMutation.comments) is False
