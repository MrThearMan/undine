from __future__ import annotations

import pytest

from example_project.app.models import Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.resolvers import BulkCreateResolver


@pytest.mark.django_db
def test_bulk_create_resolver():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(Task.request)
        project = Input(Task.project)

    resolver = BulkCreateResolver(mutation_type=TaskCreateMutation)

    data = [
        {
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
