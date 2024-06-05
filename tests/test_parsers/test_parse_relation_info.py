from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.app.models import (
    AcceptanceCriteria,
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskObjective,
    TaskResult,
    TaskStep,
)
from tests.helpers import exact
from undine.parsers import parse_model_relation_info
from undine.parsers.parse_relation_info import RelInfo
from undine.typing import RelationType


def test_parse_relation_info__task() -> None:
    info = parse_model_relation_info(model=Task)
    assert info == {
        "acceptancecriteria_set": RelInfo(
            field_name="acceptancecriteria_set",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
            model=AcceptanceCriteria,
        ),
        "assignees": RelInfo(
            field_name="assignees",
            related_name="tasks",
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
            model=Person,
        ),
        "comments": RelInfo(
            field_name="comments",
            related_name="target",
            relation_type=RelationType.GENERIC_ONE_TO_MANY,
            nullable=True,
            related_model_pk_type=int,
            model=Comment,
        ),
        "objective": RelInfo(
            field_name="objective",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
            model=TaskObjective,
        ),
        "project": RelInfo(
            field_name="project",
            related_name="tasks",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
            model=Project,
        ),
        "related_tasks": RelInfo(
            field_name="related_tasks",
            related_name="related_tasks",
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
            model=Task,
        ),
        "reports": RelInfo(
            field_name="reports",
            related_name="tasks",
            relation_type=RelationType.REVERSE_MANY_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
            model=Report,
        ),
        "request": RelInfo(
            field_name="request",
            related_name="task",
            relation_type=RelationType.FORWARD_ONE_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
            model=ServiceRequest,
        ),
        "result": RelInfo(
            field_name="result",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_ONE,
            nullable=False,
            related_model_pk_type=int,
            model=TaskResult,
        ),
        "steps": RelInfo(
            field_name="steps",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
            model=TaskStep,
        ),
    }


def test_parse_relation_info__comment() -> None:
    info = parse_model_relation_info(model=Comment)
    assert info == {
        "commenter": RelInfo(
            field_name="commenter",
            related_name="comments",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
            model=Person,
        ),
        "content_type": RelInfo(
            field_name="content_type",
            related_name="comment_set",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
            model=ContentType,
        ),
        "target": RelInfo(
            field_name="target",
            related_name=None,
            relation_type=RelationType.GENERIC_MANY_TO_ONE,
            nullable=False,
            related_model_pk_type=str,  # 'object_id' type, not actual 'id' type of generic relations
            model=None,
        ),
    }


def test_relation_type__for_related_field() -> None:
    assert RelationType.for_related_field(Task._meta.get_field("project")) == RelationType.FORWARD_MANY_TO_ONE
    assert RelationType.for_related_field(Task._meta.get_field("assignees")) == RelationType.FORWARD_MANY_TO_MANY
    assert RelationType.for_related_field(Task._meta.get_field("comments")) == RelationType.GENERIC_ONE_TO_MANY
    assert RelationType.for_related_field(Task._meta.get_field("objective")) == RelationType.REVERSE_ONE_TO_ONE
    assert RelationType.for_related_field(Task._meta.get_field("related_tasks")) == RelationType.FORWARD_MANY_TO_MANY


def test_relation_type__for_related_field__not_a_related_field() -> None:
    msg = "Unknown related field: app.Task.name (of type <class 'django.db.models.fields.CharField'>)"
    with pytest.raises(ValueError, match=exact(msg)):
        RelationType.for_related_field(Task._meta.get_field("name"))
