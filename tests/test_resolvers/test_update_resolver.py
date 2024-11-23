from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from django.core.exceptions import ValidationError

from example_project.app.models import ServiceRequest, Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.errors.exceptions import GraphQLMissingLookupFieldError, GraphQLModelNotFoundError
from undine.resolvers import UpdateResolver

if TYPE_CHECKING:
    from undine.typing import GQLInfo


@pytest.mark.django_db
def test_update_resolver():
    task = TaskFactory.create(name="Test task")

    class TaskUpdateMutation(MutationType, model=Task): ...

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    data = {
        "pk": task.pk,
        "name": "New task",
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "New task"


@pytest.mark.django_db
def test_update_resolver__instance_not_found():
    class TaskUpdateMutation(MutationType, model=Task): ...

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    data = {
        "pk": 1,
        "name": "New task",
    }

    with pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_update_resolver__lookup_field_not_found():
    class TaskUpdateMutation(MutationType, model=Task): ...

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    data = {
        "name": "New task",
    }

    with pytest.raises(GraphQLMissingLookupFieldError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_update_resolver__input_only_fields():
    task = TaskFactory.create(name="Test task")

    validator_called = False

    class TaskUpdateMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    data = {
        "pk": task.pk,
        "name": "New task",
        "foo": True,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert isinstance(result, Task)
    assert result.name == "New task"

    assert validator_called is True


@pytest.mark.django_db
def test_update_resolver__atomic():
    task = TaskFactory.create(name="Test task", request__details="Test request")
    request = task.request

    assert request.details == "Test request"

    class ServiceRequestType(MutationType, model=ServiceRequest): ...

    class TaskUpdateMutation(MutationType, model=Task):
        request = Input(ServiceRequestType)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation)

    data = {
        "pk": task.pk,
        "name": "1" * 300,
        "request": {
            "details": "New request",
            "submitted_at": "2024-01-01",
        },
    }

    with pytest.raises(ValidationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    task.refresh_from_db()

    assert task.request == request
    assert ServiceRequest.objects.count() == 1
