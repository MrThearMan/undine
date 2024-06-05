from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import MutationType
from undine.resolvers import CustomResolver
from undine.typing import GQLInfo, Root


@pytest.mark.django_db
def test_custom_resolver():
    task = TaskFactory.create(name="Test task")

    mutator_called = False

    class TaskMutation(MutationType, model=Task):
        @classmethod
        def __mutate__(cls, root: Root, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            nonlocal mutator_called
            mutator_called = True
            return "foo"

    resolver = CustomResolver(mutation_type=TaskMutation)

    data = {
        "pk": task.pk,
    }

    result = resolver(root=None, info=MockGQLInfo(), input=data)

    assert result == "foo"
    assert mutator_called is True
