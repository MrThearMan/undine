from __future__ import annotations

import pytest
from django.db.models import Prefetch, Value
from graphql.pyutils import Path

from example_project.app.models import Person, Task
from tests.factories import TaskFactory
from tests.helpers import MockRequest, keyset_cursor, mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler, Node
from undine.resolvers import NestedConnectionResolver
from undine.typing import ConnectionDict, GQLContext, NodeDict, PageInfoDict, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db


def test_resolvers__nested_connection_resolver(undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    TaskFactory.create(assignees__name="Test assignee")

    task: Task = Task.objects.prefetch_related(  # type: ignore[assignment]
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
    ).first()

    assignee: Person = task.assignees.first()  # type: ignore[assignment]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection,
        field=TaskType.assignees,
    )

    pagination = CursorPaginationHandler(typename="PersonType", first=1)
    path = Path(None, "assignees", "")

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

    result = resolver.run_sync(root=task, info=info)

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


def test_resolvers__nested_connection_resolver__field_permissions(undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    TaskFactory.create(assignees__name="Test assignee")

    task: Task = Task.objects.prefetch_related(  # type: ignore[assignment]
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
    ).first()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_connection_resolver__query_type_permissions(undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    TaskFactory.create(assignees__name="Test assignee")

    task: Task = Task.objects.prefetch_related(  # type: ignore[assignment]
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
    ).first()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_connection_resolver__to_attr(undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    TaskFactory.create(assignees__name="Test assignee")

    task: Task = Task.objects.prefetch_related(  # type: ignore[assignment]
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.PAGINATION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.PAGINATION_START_INDEX_KEY: Value(0),
                    undine_settings.PAGINATION_STOP_INDEX_KEY: Value(1),
                },
            ),
            to_attr="original_assignees",
        ),
    ).first()

    assignee: Person = task.original_assignees[0]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    pagination = CursorPaginationHandler(typename="PersonType", first=1)
    path = Path(prev=None, key="original_assignees", typename="")

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

    result = resolver.run_sync(root=task, info=info)

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
