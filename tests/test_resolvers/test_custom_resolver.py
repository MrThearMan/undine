from __future__ import annotations

from itertools import count
from typing import Any

import pytest

from example_project.app.models import Task
from tests.helpers import mock_gql_info
from undine import Entrypoint, Input, MutationType, RootType
from undine.resolvers import CustomResolver
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_custom_resolver() -> None:
    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    mutate_called: int = -1
    after_called: int = -1

    class TaskMutation(MutationType[Task]):
        name = Input()

        @name.validate
        def _(self: Task, info: GQLInfo, value: str) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @name.permissions
        def _(self: Task, info: GQLInfo, value: str) -> None:
            nonlocal input_permission_called
            input_permission_called = next(counter)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal permission_called
            permission_called = next(counter)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

        @classmethod
        def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> Any:
            nonlocal mutate_called
            mutate_called = next(counter)
            return input_data

    class Mutation(RootType):
        task_mutation = Entrypoint(Task)

    resolver = CustomResolver(mutation_type=TaskMutation, entrypoint=Mutation.task_mutation)

    data = {"name": "foo"}

    result = resolver(root=None, info=mock_gql_info(), input=data)

    assert result == data

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert mutate_called == 4
    assert after_called == -1  # No after mutation
