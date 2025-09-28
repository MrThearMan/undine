from __future__ import annotations

import uuid

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
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            #
            # Source details
            field_name="acceptancecriteria_set",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="task",
            related_model_pk_type=int,
            related_model=AcceptanceCriteria,
            related_nullable=True,
        ),
        "assignees": RelInfo(
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            #
            # Source details
            field_name="assignees",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="tasks",
            related_model_pk_type=int,
            related_model=Person,
            related_nullable=True,
        ),
        "comments": RelInfo(
            relation_type=RelationType.GENERIC_ONE_TO_MANY,
            #
            # Source details
            field_name="comments",
            model=Task,
            model_pk_type=str,
            nullable=True,
            #
            # Target details
            related_name="target",
            related_model_pk_type=int,
            related_model=Comment,
            related_nullable=True,
        ),
        "objective": RelInfo(
            relation_type=RelationType.REVERSE_ONE_TO_ONE,
            #
            # Source details
            field_name="objective",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="task",
            related_model_pk_type=int,
            related_model=TaskObjective,
            related_nullable=True,
        ),
        "project": RelInfo(
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            #
            # Source details
            field_name="project",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="tasks",
            related_model_pk_type=int,
            related_model=Project,
            related_nullable=True,
        ),
        "related_tasks": RelInfo(
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            #
            # Source details
            field_name="related_tasks",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="related_tasks",
            related_model_pk_type=int,
            related_model=Task,
            related_nullable=True,
        ),
        "reports": RelInfo(
            relation_type=RelationType.REVERSE_MANY_TO_MANY,
            #
            # Source details
            field_name="reports",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="tasks",
            related_model_pk_type=uuid.UUID,
            related_model=Report,
            related_nullable=True,
        ),
        "request": RelInfo(
            relation_type=RelationType.FORWARD_ONE_TO_ONE,
            #
            # Source details
            field_name="request",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="task",
            related_model_pk_type=int,
            related_model=ServiceRequest,
            related_nullable=True,
        ),
        "result": RelInfo(
            relation_type=RelationType.REVERSE_ONE_TO_ONE,
            #
            # Source details
            field_name="result",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="task",
            related_model=TaskResult,
            related_model_pk_type=int,
            related_nullable=False,
        ),
        "steps": RelInfo(
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            #
            # Source details
            field_name="steps",
            model=Task,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="task",
            related_model=TaskStep,
            related_model_pk_type=int,
            related_nullable=False,
        ),
    }


def test_parse_relation_info__comment() -> None:
    info = parse_model_relation_info(model=Comment)
    assert info == {
        "commenter": RelInfo(
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            #
            # Source details
            field_name="commenter",
            model=Comment,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="comments",
            related_model=Person,
            related_model_pk_type=int,
            related_nullable=True,
        ),
        "content_type": RelInfo(
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            #
            # Source details
            field_name="content_type",
            model=Comment,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name="comment_set",
            related_model=ContentType,
            related_model_pk_type=int,
            related_nullable=True,
        ),
        "target": RelInfo(
            relation_type=RelationType.GENERIC_MANY_TO_ONE,
            #
            # Source details
            field_name="target",
            model=Comment,
            model_pk_type=int,
            nullable=True,
            #
            # Target details
            related_name=None,
            related_model=None,
            related_model_pk_type=str,
            related_nullable=True,
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
