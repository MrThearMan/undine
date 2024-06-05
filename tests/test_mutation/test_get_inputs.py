from __future__ import annotations

from example_project.app.models import Comment, Task
from undine.mutation import get_inputs_for_model


def test_get_inputs_for_model() -> None:
    fields = get_inputs_for_model(Task)
    assert sorted(fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "name",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]


def test_get_inputs_for_model__exclude() -> None:
    fields = get_inputs_for_model(Task, exclude=["name"])
    assert sorted(fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]


def test_get_inputs_for_model__generic_foreign_key() -> None:
    fields = get_inputs_for_model(Comment)
    # 'object_id' and 'content_type' are not added due to how generic foreign keys are handled
    assert sorted(fields) == [
        "commenter",
        "contents",
        "pk",
        "target",
    ]
