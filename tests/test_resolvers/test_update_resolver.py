from __future__ import annotations

from inspect import isawaitable
from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Input, MutationType, QueryType, RootType
from undine.exceptions import GraphQLMissingLookupFieldError, GraphQLModelNotFoundError
from undine.resolvers import UpdateResolver
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_update_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    task = TaskFactory.create(name="Test task")

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.update_task)

    with patch_optimizer():
        result = resolver(root=None, info=mock_gql_info(), input={"pk": task.pk, "name": "New task"})

    assert isinstance(result, Task)
    assert result.name == "New task"


@pytest.mark.django_db
def test_update_resolver__instance_not_found(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.update_task)

    with pytest.raises(GraphQLModelNotFoundError):
        resolver(root=None, info=mock_gql_info(), input={"pk": 1, "name": "New task"})


@pytest.mark.django_db
def test_update_resolver__lookup_field_not_found(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.update_task)

    with pytest.raises(GraphQLMissingLookupFieldError):
        resolver(root=None, info=mock_gql_info(), input={"name": "New task"})


@pytest.mark.django_db
def test_update_resolver__mutation_hooks(undine_settings) -> None:
    undine_settings.ASYNC = False

    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    task = TaskFactory.create(name="Test task")

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

        @name.validate
        def _(self, info: GQLInfo, value: str) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @name.permissions
        def _(self, info: GQLInfo, value: str) -> None:
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

    class Query(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.update_task)

    data = {
        "pk": task.pk,
        "name": "New task",
    }

    with patch_optimizer():
        resolver(root=None, info=mock_gql_info(), input=data)

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_update_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    task = await sync_to_async(TaskFactory.create)(name="Test task")

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    resolver = UpdateResolver(mutation_type=TaskUpdateMutation, entrypoint=Query.update_task)

    with patch_optimizer():
        result = resolver(root=None, info=mock_gql_info(), input={"pk": task.pk, "name": "New task"})

        assert isawaitable(result)
        result = await result

    assert isinstance(result, Task)
    assert result.name == "New task"
