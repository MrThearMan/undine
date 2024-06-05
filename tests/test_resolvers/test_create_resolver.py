from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import ValidationError

from example_project.app.models import ServiceRequest, Task, TaskTypeChoices
from tests.factories import ProjectFactory, ServiceRequestFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.resolvers import CreateResolver
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_create_resolver():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")

    class TaskCreateMutation(MutationType, model=Task): ...

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": request.pk,
        "project": project.pk,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "Test task"
    assert result.type == TaskTypeChoices.STORY
    assert result.request == request
    assert result.project == project


@pytest.mark.django_db
def test_create_resolver__input_only_fields():
    project = ProjectFactory.create(name="Test project")
    request = ServiceRequestFactory.create(details="Test request")

    validator_called = False

    class TaskCreateMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": request.pk,
        "project": project.pk,
        "foo": True,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "Test task"

    assert validator_called is True


@pytest.mark.django_db
def test_create_resolver__atomic():
    project = ProjectFactory.create(name="Test project")

    class ServiceRequestType(MutationType, model=ServiceRequest): ...

    class TaskCreateMutation(MutationType, model=Task):
        request = Input(ServiceRequestType)

    resolver = CreateResolver(mutation_type=TaskCreateMutation)

    data = {
        "name": "1" * 300,
        "type": TaskTypeChoices.STORY.value,
        "request": {
            "details": "Test request",
            "submitted_at": "2024-01-01",
        },
        "project": project.pk,
    }

    with pytest.raises(ValidationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    assert ServiceRequest.objects.count() == 0
    assert Task.objects.count() == 0
