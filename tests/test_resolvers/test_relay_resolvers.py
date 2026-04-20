from __future__ import annotations

from inspect import isawaitable
from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Prefetch, Value
from graphql import GraphQLNonNull, GraphQLString
from graphql.pyutils import Path

from example_project.app.models import Person, Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, InterfaceField, InterfaceType, QueryType, RootType, UnionType, create_schema
from undine.dataclasses import QuerySetMapWithPagination
from undine.exceptions import (
    GraphQLNodeInterfaceMissingError,
    GraphQLNodeInvalidGlobalIDError,
    GraphQLNodeMissingIDFieldError,
    GraphQLNodeObjectTypeMissingError,
    GraphQLNodeQueryTypeMissingError,
    GraphQLPermissionError,
)
from undine.pagination import PaginationHandler
from undine.relay import Connection, Node, offset_to_cursor, to_global_id
from undine.resolvers import (
    ConnectionResolver,
    GlobalIDResolver,
    InterfaceTypeConnectionResolver,
    InterfaceTypeResolver,
    NestedConnectionResolver,
    NodeResolver,
    UnionTypeConnectionResolver,
)
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
    undine_settings.ASYNC = False

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__node_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    with patch_optimizer():
        coroutine = resolver(root=task, info=info, id=object_id)
        assert isawaitable(coroutine)

        result = await coroutine
        assert result == task


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
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = TaskFactory.create()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination):
        result = resolver.run_sync(root=task, info=mock_gql_info())

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    task = await sync_to_async(TaskFactory.create)()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination):
        result = await resolver.run_async(root=task, info=mock_gql_info())

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

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=1)
    pagination.total_count = 100

    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


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
                    undine_settings.PAGINATION_TOTAL_COUNT_KEY: Value(100),
                    undine_settings.PAGINATION_START_INDEX_KEY: Value(0),
                    undine_settings.PAGINATION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).first()

    assignee: Person = task.assignees.first()  # type: ignore[assignment]

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    result = resolver.run_sync(root=task, info=mock_gql_info())

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

    info = mock_gql_info(path=Path(prev=None, key="original_assignees", typename=""))

    result = resolver.run_sync(root=task, info=info)

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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
        connection=connection, field=TaskType.assignees
    )

    result = await resolver.run_async(root=task, info=mock_gql_info())

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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__fetch_instances_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    project = await sync_to_async(ProjectFactory.create)(name="Project 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs, ProjectType: project_qs},
        pagination=pagination,
    )

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=mock_gql_info(),
            result=result_with_pagination,
        )

    assert len(instances) == 2
    pks = {i.pk for i in instances}
    assert task.pk in pks
    assert project.pk in pks


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(connection)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    called_with: list[Any] = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(connection)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__check_permissions_async__query_type_async_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__check_permissions_async__query_type_sync_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__empty_connection(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    result = resolver.empty_connection()

    assert result == ConnectionDict(
        totalCount=0,
        pageInfo=PageInfoDict(
            hasNextPage=False,
            hasPreviousPage=False,
            startCursor=None,
            endCursor=None,
        ),
        edges=[],
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__fetch_instances_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")
    project = await sync_to_async(ProjectFactory.create)(name="My Project")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    queryset_map = {TaskType: task_qs, ProjectType: project_qs}

    results = await resolver.fetch_instances_async(
        info=mock_gql_info(),
        root=None,
        queryset_map=queryset_map,
    )

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert task.pk in pks
    assert project.pk in pks


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__sync_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    Query.named.permissions_func = permissions_func

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")

    await resolver.check_permissions_async(
        info=mock_gql_info(),
        root=None,
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__async_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    called_with: list[Any] = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    Query.named.permissions_func = permissions_func

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")

    await resolver.check_permissions_async(
        info=mock_gql_info(),
        root=None,
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_sync_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_async_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__run_sync_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver: InterfaceTypeResolver = InterfaceTypeResolver(
        interface=Named,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="My Task")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        results = await resolver.run_sync_async(root=None, info=mock_gql_info())

    assert len(results) == 1
    assert results[0].pk == task.pk


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__fetch_instances(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    pagination = PaginationHandler(typename=Named.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs, ProjectType: project_qs},
        pagination=pagination,
    )

    instances = resolver.fetch_instances(root=None, info=mock_gql_info(), result=result_with_pagination)

    assert len(instances) == 2
    pks = {i.pk for i in instances}
    assert task.pk in pks
    assert project.pk in pks


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__check_permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = TaskFactory.create(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__check_permissions__permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        named = Entrypoint(connection)

    Query.named.permissions_func = permissions_func

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = TaskFactory.create(name="Task 1")

    resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__run_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    pagination = PaginationHandler(typename=Named.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs},
        pagination=pagination,
    )

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=result_with_pagination):
        connection_dict = await resolver.run_async(root=None, info=mock_gql_info())

    assert len(connection_dict["edges"]) == 1
    assert connection_dict["edges"][0]["node"].pk == task.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__fetch_instances_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    project = await sync_to_async(ProjectFactory.create)(name="Project 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    pagination = PaginationHandler(typename=Named.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs, ProjectType: project_qs},
        pagination=pagination,
    )

    instances = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), result=result_with_pagination)

    assert len(instances) == 2
    pks = {i.pk for i in instances}
    assert task.pk in pks
    assert project.pk in pks


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        named = Entrypoint(connection)

    Query.named.permissions_func = permissions_func

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    called_with: list[Any] = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class Query(RootType):
        named = Entrypoint(connection)

    Query.named.permissions_func = permissions_func

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__check_permissions_async__query_type_sync_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__check_permissions_async__query_type_async_perms(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    pagination = PaginationHandler(typename=Named.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs},
        pagination=pagination,
    )

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=result_with_pagination):
        coroutine = resolver(root=None, info=mock_gql_info())
        assert isawaitable(coroutine)
        connection_dict = await coroutine

    assert len(connection_dict["edges"]) == 1
