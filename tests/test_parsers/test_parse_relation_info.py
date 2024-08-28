from example_project.app.models import Comment, Task
from undine.parsers import parse_model_relation_info
from undine.parsers.parse_model_relation_info import RelatedFieldInfo, RelationType


def test_parse_relation_info__task():
    info = parse_model_relation_info(Task)
    assert info == {
        "acceptanceCriteria": RelatedFieldInfo(
            field_name="acceptance_criteria",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            nullable=True,
            related_model_pk_type=int,
        ),
        "assignees": RelatedFieldInfo(
            field_name="assignees",
            related_name="tasks",
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
        ),
        "comments": RelatedFieldInfo(
            field_name="comments",
            related_name="target",
            relation_type=RelationType.GENERIC_ONE_TO_MANY,
            nullable=True,
            related_model_pk_type=int,
        ),
        "project": RelatedFieldInfo(
            field_name="project",
            related_name="tasks",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=False,
            related_model_pk_type=int,
        ),
        "relatedTasks": RelatedFieldInfo(
            field_name="related_tasks",
            related_name="related_tasks",
            relation_type=RelationType.FORWARD_MANY_TO_MANY,
            nullable=False,
            related_model_pk_type=int,
        ),
        "reports": RelatedFieldInfo(
            field_name="reports",
            related_name="tasks",
            relation_type=RelationType.REVERSE_MANY_TO_MANY,
            nullable=True,
            related_model_pk_type=int,
        ),
        "request": RelatedFieldInfo(
            field_name="request",
            related_name="task",
            relation_type=RelationType.FORWARD_ONE_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
        ),
        "result": RelatedFieldInfo(
            field_name="result",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_ONE,
            nullable=True,
            related_model_pk_type=int,
        ),
        "steps": RelatedFieldInfo(
            field_name="steps",
            related_name="task",
            relation_type=RelationType.REVERSE_ONE_TO_MANY,
            nullable=True,
            related_model_pk_type=int,
        ),
    }


def test_parse_relation_info__comment():
    info = parse_model_relation_info(Comment)
    assert info == {
        "commenter": RelatedFieldInfo(
            field_name="commenter",
            related_name="comments",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=False,
            related_model_pk_type=int,
        ),
        "contentType": RelatedFieldInfo(
            field_name="content_type",
            related_name="comment_set",
            relation_type=RelationType.FORWARD_MANY_TO_ONE,
            nullable=False,
            related_model_pk_type=int,
        ),
        "target": RelatedFieldInfo(
            field_name="target",
            related_name=None,
            relation_type=RelationType.GENERIC_MANY_TO_ONE,
            nullable=False,
            related_model_pk_type=None,
        ),
    }
