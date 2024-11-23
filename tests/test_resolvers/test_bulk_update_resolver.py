from __future__ import annotations

import pytest

from example_project.app.models import Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory, TaskFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.resolvers import BulkUpdateResolver


@pytest.mark.django_db
def test_bulk_update_resolver():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")
    task = TaskFactory.create(name="Task", type=TaskTypeChoices.STORY.value)

    class TaskUpdateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)

    resolver = BulkUpdateResolver(mutation_type=TaskUpdateMutation)

    data = [
        {
            "pk": task.pk,
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": request.pk,
            "project": project.pk,
        },
    ]

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, list)
    assert len(result) == 1

    result = result[0]

    assert isinstance(result, Task)
    assert result.name == "Test task"
    assert result.type == TaskTypeChoices.STORY
    assert result.request == request
    assert result.project == project


# TODO: More tests
