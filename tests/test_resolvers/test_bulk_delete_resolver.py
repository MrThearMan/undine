from __future__ import annotations

from itertools import count
from types import SimpleNamespace
from typing import Any

import pytest
from django.db.models import Model

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import GQLInfo, MutationType
from undine.resolvers import BulkDeleteResolver


@pytest.mark.django_db
def test_bulk_delete_resolver() -> None:
    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    assert Task.objects.count() == 2

    class TaskDeleteMutation(MutationType[Task]): ...

    resolver: BulkDeleteResolver[Task] = BulkDeleteResolver(mutation_type=TaskDeleteMutation)

    data = [{"pk": task_1.pk}, {"pk": task_2.pk}]

    results = resolver(root=None, info=mock_gql_info(), input=data)

    assert results == [SimpleNamespace(pk=task_1.pk), SimpleNamespace(pk=task_2.pk)]

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_bulk_delete_resolver__mutation_hooks() -> None:
    task = TaskFactory.create()

    counter = count()

    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskDeleteMutation(MutationType[Task]):
        @classmethod
        def __validate__(cls, instance: Model, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

        @classmethod
        def __permissions__(cls, instance: Model, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal permission_called
            permission_called = next(counter)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

    resolver: BulkDeleteResolver[Task] = BulkDeleteResolver(mutation_type=TaskDeleteMutation)

    resolver(root=None, info=mock_gql_info(), input=[{"pk": task.pk}])

    assert permission_called == 0
    assert validate_called == 1
    assert after_called == 2
