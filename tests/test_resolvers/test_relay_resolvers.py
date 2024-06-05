from __future__ import annotations

import pytest
from django.db.models import Prefetch, Value
from graphql.pyutils import Path

from example_project.app.models import Person, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, QueryType, RootType, create_schema
from undine.exceptions import (
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLPermissionError,
)
from undine.relay import Connection, Node, PaginationHandler, offset_to_cursor, to_global_id
from undine.resolvers import ConnectionResolver, GlobalIDResolver, NestedConnectionResolver, NodeResolver
from undine.typing import ConnectionDict, GQLInfo, NodeDict, PageInfoDict


@pytest.mark.django_db
def test_resolvers__global_id_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    task = TaskFactory.create()

    resolver = GlobalIDResolver(typename=TaskType.__schema_name__)

    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    assert resolver(root=task, info=mock_gql_info()) == object_id


@pytest.mark.django_db
def test_resolvers__node_resolver(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer():
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__not_a_global_id(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)

    with patch_optimizer(), pytest.raises(GraphQLNodeInvalidGlobalIDError):
        assert resolver(root=task, info=info, id="foo") == task


@pytest.mark.django_db
def test_resolvers__node_resolver__object_type_not_in_schema(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename="ProjectType", object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeObjectTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__does_not_implement_node_interface(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeInterfaceMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_undine_query_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    TaskType.__extensions__ = {}  # Remove undine QueryType extension on purpose.

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeQueryTypeMissingError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__node_resolver__missing_id_field(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        name = Field()

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskType.__field_map__.pop("id")  # Remove `id` field on purpose

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer(), pytest.raises(GraphQLNodeMissingIDFieldError):
        assert resolver(root=task, info=info, id=object_id) == task


@pytest.mark.django_db
def test_resolvers__connection_resolver(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = TaskFactory.create()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination):
        result = resolver(root=task, info=mock_gql_info())

    typename = TaskType.__schema_name__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=task,
                ),
            ],
        )
    )


@pytest.mark.django_db
def test_resolvers__connection_resolver__permissions(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = TaskFactory.create()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).first()

    assignee: Person = task.assignees.first()  # type: ignore[assignment]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    result = resolver(root=task, info=mock_gql_info())

    typename = PersonType.__schema_name__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=assignee,
                ),
            ],
        )
    )


@pytest.mark.django_db
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
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).first()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    with pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).first()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    with pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
                    undine_settings.CONNECTION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.CONNECTION_START_INDEX_KEY: Value(0),
                    undine_settings.CONNECTION_STOP_INDEX_KEY: Value(1),
                },
            ),
            to_attr="original_assignees",
        ),
    ).first()

    assignee: Person = task.original_assignees[0]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    info = mock_gql_info(path=Path(prev=None, key="original_assignees", typename=""))

    result = resolver(root=task, info=info)

    typename = PersonType.__schema_name__
    assert result == (
        ConnectionDict(
            totalCount=100,
            pageInfo=PageInfoDict(
                hasNextPage=True,
                hasPreviousPage=False,
                startCursor=offset_to_cursor(typename, 0),
                endCursor=offset_to_cursor(typename, 0),
            ),
            edges=[
                NodeDict(
                    cursor=offset_to_cursor(typename, 0),
                    node=assignee,
                ),
            ],
        )
    )
