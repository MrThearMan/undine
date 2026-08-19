from __future__ import annotations

from typing import Any

import pytest
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

pytestmark = pytest.mark.django_db


def test_resolvers__connection_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = TaskFactory.create()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    path = Path(prev=None, key="tasks", typename=TaskType.__schema_name__)

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
        result = resolver.run_sync(root=task, info=info)

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


def test_resolvers__connection_resolver__permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = TaskFactory.create()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__connection_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    task = TaskFactory.create()

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

    with patch_optimizer(pagination=pagination):
        result = resolver.run_sync(root=None, info=info)

    assert called_with == [task]
    assert len(result["edges"]) == 1
