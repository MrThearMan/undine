import datetime

import pytest

from example_project.app.models import Comment, Task, TaskType
from example_project.app.mutations import CommentCreateMutation, TaskCreateMutation
from tests.factories import TaskFactory
from undine.utils.mutation_handler import MutationHandler

pytestmark = [
    pytest.mark.django_db,
]


def test_mutation_handler__task():
    handler = MutationHandler[Task](mutation_class=TaskCreateMutation)

    data = {
        "name": "Test task",
        "type": TaskType.TASK.value,
        "request": {
            "details": "Test request",
        },
        "project": {
            "name": "Test project",
            "team": {
                "name": "Test team",
            },
        },
        "assignees": [
            {
                "name": "Test user",
                "email": "test@user.com",
            },
        ],
        "result": {
            "details": "Test result",
            "time_used": datetime.timedelta(seconds=1),
        },
        "steps": [
            {
                "name": "Test step",
            },
        ],
        "reports": [
            {
                "name": "Test report",
                "content": "Test report content",
            },
        ],
        "comments": [
            {
                "contents": "Test comment",
                "commenter": {
                    "name": "Test commenter",
                    "email": "test@commenter.com",
                },
            },
        ],
        "relatedTasks": [
            {
                "name": "Related task",
                "request": {
                    "details": "Related request",
                },
                "project": {
                    "name": "Related project",
                    "team": {
                        "name": "Related team",
                    },
                },
            },
        ],
    }

    instance = handler.create(data)

    assert instance.name == "Test task"
    assert instance.type == TaskType.TASK

    assert instance.request.details == "Test request"

    assert instance.project.name == "Test project"
    assert instance.project.team.name == "Test team"

    assert instance.assignees.count() == 1
    assert instance.assignees.first().name == "Test user"

    assert instance.result.details == "Test result"
    assert instance.result.time_used == datetime.timedelta(seconds=1)

    assert instance.steps.count() == 1
    assert instance.steps.first().name == "Test step"

    assert instance.reports.count() == 1
    assert instance.reports.first().name == "Test report"
    assert instance.reports.first().content == "Test report content"

    assert instance.comments.count() == 1
    assert instance.comments.first().contents == "Test comment"
    assert instance.comments.first().commenter.name == "Test commenter"

    assert instance.related_tasks.count() == 1
    assert instance.related_tasks.first().name == "Related task"
    assert instance.related_tasks.first().request.details == "Related request"
    assert instance.related_tasks.first().project.name == "Related project"
    assert instance.related_tasks.first().project.team.name == "Related team"


def test_mutation_handler__comment():
    handler = MutationHandler[Comment](mutation_class=CommentCreateMutation)

    task = TaskFactory.create(name="Test task")

    data = {
        "contents": "Test comment",
        "commenter": {
            "name": "Test commenter",
            "email": "test@commenter.com",
        },
        "target": {
            "typename": "Task",
            "pk": str(task.pk),
        },
    }

    instance = handler.create(data)

    assert instance.contents == "Test comment"
    assert instance.commenter.name == "Test commenter"
    assert instance.commenter.email == "test@commenter.com"

    assert isinstance(instance.target, Task)
    assert instance.target.name == "Test task"
