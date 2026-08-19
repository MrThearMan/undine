from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Prefetch, Value
from graphql.pyutils import Path

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import MockRequest, keyset_cursor, mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler, Node
from undine.resolvers import NestedConnectionResolver
from undine.typing import ConnectionDict, GQLContext, NodeDict, PageInfoDict, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__nested_connection_resolver__async(undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    await sync_to_async(TaskFactory.create)(assignees__name="Test assignee")

    task: Task = await Task.objects.prefetch_related(  # type: ignore[assignment]
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.PAGINATION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.PAGINATION_START_INDEX_KEY: Value(0),
                    undine_settings.PAGINATION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).afirst()

    assignee: Person = next(iter(task.assignees.all()))  # type: ignore[assignment]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection,
        field=TaskType.assignees,
    )

    pagination = CursorPaginationHandler(typename="PersonType", first=1)
    path = Path(None, "assignees", None)
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

    result = await resolver.run_async(root=task, info=info)

    typename = PersonType.__schema_name__
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
                    node=assignee,
                ),
            ],
        )
    )


async def test_resolvers__nested_connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    await sync_to_async(TaskFactory.create)(assignees__name="Test assignee")

    task: Task = await Task.objects.prefetch_related(  # type: ignore[assignment]
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.PAGINATION_TOTAL_COUNT_KEY: Value(10),
                    undine_settings.PAGINATION_START_INDEX_KEY: Value(0),
                    undine_settings.PAGINATION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).afirst()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection,
        field=TaskType.assignees,
    )

    pagination = CursorPaginationHandler(typename=TaskType.__schema_name__, first=10)

    path = Path(None, "assignees", typename=PersonType.__schema_name__)
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

    result = await resolver(root=task, info=info)

    assert isinstance(result, dict)
    assert "edges" in result
    assert len(result["edges"]) == 1


async def test_resolvers__nested_connection_resolver__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    called_with: list[Any] = []

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])

    assert called_with == [assignee]


async def test_resolvers__nested_connection_resolver__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])


async def test_resolvers__nested_connection_resolver__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]):
        @classmethod
        async def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])


async def test_resolvers__nested_connection_resolver__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])
