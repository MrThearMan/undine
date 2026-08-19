from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import QueryTypeManyResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__query_type_many_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert result == [task]


async def test_resolvers__query_type_many_resolver__async__check_permissions_async__sync_func(
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

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result == [task]
    assert called_with == [task]


async def test_resolvers__query_type_many_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


async def test_resolvers__query_type_many_resolver__async__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


async def test_resolvers__query_type_many_resolver__async__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())
