from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async
from graphql.pyutils import Path

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import MockRequest, keyset_cursor, mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler, Node
from undine.resolvers import ConnectionResolver
from undine.typing import ConnectionDict, GQLContext, NodeDict, PageInfoDict, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__connection_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = await sync_to_async(TaskFactory.create)()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    path = Path(None, "tasks", typename=TaskType.__schema_name__)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination):
        result = await resolver.run_async(root=task, info=info)

    typename = TaskType.__schema_name__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=False,
                hasPreviousPage=False,
                startCursor=keyset_cursor(typename),
                endCursor=keyset_cursor(typename),
            ),
            edges=[
                NodeDict(
                    cursor=keyset_cursor(typename),
                    node=task,
                ),
            ],
        )
    )


async def test_resolvers__connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    await sync_to_async(TaskFactory.create)()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    path = Path(None, "tasks", typename=TaskType.__schema_name__)
    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination):
        result = await resolver(root=None, info=info)

    assert isinstance(result, dict)
    assert "edges" in result


async def test_resolvers__connection_resolver__check_permissions_async__sync_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    task = await sync_to_async(TaskFactory.create)()

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)
    path = Path(None, "tasks", typename=TaskType.__schema_name__)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination):
        result = await resolver.run_async(root=None, info=info)

    assert called_with == [task]
    assert len(result["edges"]) == 1


async def test_resolvers__connection_resolver__check_permissions_async__async_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)
    path = Path(None, "tasks", typename=Query.__schema_name__)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=info)


async def test_resolvers__connection_resolver__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)
    path = Path(None, "tasks", typename=Query.__schema_name__)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=info)


async def test_resolvers__connection_resolver__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)

    path = Path(None, "tasks", typename=Query.__schema_name__)
    info = mock_gql_info(
        path=path,
        context=GQLContext(
            request=MockRequest(),
            undine_internal=UndineInternalContext(
                connection_handler_storage={
                    get_field_path_identifier(path): pagination,
                },
            ),
        ),
    )

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=info)
