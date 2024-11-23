from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory, TaskResultFactory
from tests.helpers import MockGQLInfo
from undine import Input, MutationType
from undine.errors.exceptions import (
    GraphQLMissingLookupFieldError,
    GraphQLModelConstaintViolationError,
    GraphQLModelNotFoundError,
)
from undine.resolvers import DeleteResolver

if TYPE_CHECKING:
    from undine.typing import GQLInfo


@pytest.mark.django_db
def test_delete_resolver():
    task = TaskFactory.create(name="Test task")

    class TaskDeleteMutation(MutationType, model=Task): ...

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    data = {
        "pk": task.pk,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == {"success": True}

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_delete_resolver__instance_not_found():
    class TaskDeleteMutation(MutationType, model=Task): ...

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    data = {
        "pk": 1,
    }

    with pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_delete_resolver__lookup_field_not_found():
    class TaskDeleteMutation(MutationType, model=Task): ...

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    data = {}

    with pytest.raises(GraphQLMissingLookupFieldError):
        resolver(root=None, info=MockGQLInfo(), input=data)


@pytest.mark.django_db
def test_delete_resolver__input_only_fields():
    task = TaskFactory.create(name="Test task")

    validator_called = False

    class TaskDeleteMutation(MutationType, model=Task):
        foo = Input(bool, input_only=True)

        @classmethod
        def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validator_called
            validator_called = True

            if input_data["foo"] is not True:
                msg = "Foo must not be True"
                raise ValueError(msg)

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    data = {
        "pk": task.pk,
        "foo": True,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == {"success": True}

    assert Task.objects.count() == 0

    assert validator_called is True


@pytest.mark.django_db
def test_delete_resolver__handle_integrity_errors():
    task = TaskFactory.create(name="Test task")
    TaskResultFactory.create(task=task)

    class TaskDeleteMutation(MutationType, model=Task): ...

    resolver = DeleteResolver(mutation_type=TaskDeleteMutation)

    data = {
        "pk": task.pk,
    }

    with pytest.raises(GraphQLModelConstaintViolationError):
        resolver(root=None, info=MockGQLInfo(), input=data)

    assert Task.objects.count() == 1
