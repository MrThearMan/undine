from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLModelNotFoundError, GraphQLPermissionError
from undine.resolvers import QueryTypeSingleResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__query_type_single_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=task, info=mock_gql_info(), pk=task.pk)

    assert result == task


async def test_resolvers__query_type_single_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    async def mock_optimize_async(*args: Any, **kwargs: Any) -> None:  # noqa: RUF029
        return None

    with patch("undine.resolvers.query.optimize_async", side_effect=mock_optimize_async):
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result is None


async def test_resolvers__query_type_single_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    async def mock_optimize_async(*args: Any, **kwargs: Any) -> None:  # noqa: RUF029
        return None

    with (
        patch("undine.resolvers.query.optimize_async", side_effect=mock_optimize_async),
        pytest.raises(GraphQLModelNotFoundError),
    ):
        await resolver.run_async(root=None, info=mock_gql_info())


async def test_resolvers__query_type_single_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)

    assert result == task
    assert called_with == [task]


async def test_resolvers__query_type_single_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)


async def test_resolvers__query_type_single_resolver__async__check_permissions_async__async_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)

    assert result == task
    assert called_with == [task]


async def test_resolvers__query_type_single_resolver__async__check_permissions_async__sync_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)
