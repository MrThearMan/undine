from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import MutationType
from undine.resolvers import BulkDeleteResolver


@pytest.mark.django_db
def test_bulk_delete_resolver():
    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    assert Task.objects.count() == 2

    class TaskDeleteMutation(MutationType, model=Task): ...

    resolver = BulkDeleteResolver(mutation_type=TaskDeleteMutation)

    data = [task_1.pk, task_2.pk]

    results = resolver(root=None, info=MockGQLInfo(), input=data)

    assert results == {"success": True}

    assert Task.objects.count() == 0
