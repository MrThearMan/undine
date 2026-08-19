from __future__ import annotations

from inspect import isawaitable
from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Value
from graphql import GraphQLNonNull, GraphQLString
from graphql.pyutils import Path

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import MockRequest, mock_gql_info
from undine import Entrypoint, Field, FilterSet, InterfaceField, InterfaceType, OrderSet, QueryType, RootType
from undine.dataclasses import FilterResults, OrderResults
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler
from undine.resolvers import InterfaceTypeConnectionResolver
from undine.typing import GQLContext, GQLInfo, QuerySetMap, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db(transaction=True)


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

    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map = {TaskType: task_qs}

    path = Path(prev=None, key="foo", typename="")
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

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=queryset_map):
        connection_dict = await resolver.run_async(root=None, info=info)

    assert len(connection_dict["edges"]) == 1
    assert connection_dict["edges"][0]["node"].pk == task.pk


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

    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs, ProjectType: project_qs}

    instances = await resolver.fetch_instances_async(
        root=None,
        info=mock_gql_info(),
        queryset_map=queryset_map,
        pagination=pagination,
    )

    assert len(instances) == 2
    pks = {i.pk for i in instances}
    assert task.pk in pks
    assert project.pk in pks


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

    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map = {TaskType: task_qs}

    path = Path(prev=None, key="foo", typename="")
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

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=queryset_map):
        coroutine = resolver(root=None, info=info)
        assert isawaitable(coroutine)
        connection_dict = await coroutine

    assert len(connection_dict["edges"]) == 1


async def test_resolvers__interface_type_connection_resolver__run_async__empty_connection(
    undine_settings,
) -> None:
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

    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    path = Path(None, "named", Named.__schema_name__)
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

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value={}):
        result = await resolver.run_async(root=None, info=info)

    assert result["totalCount"] == 0
    assert result["edges"] == []


async def test_resolvers__interface_type_connection_resolver__async__fetch_instances__filter_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class NamedFilterSet(FilterSet[Task, Project], auto=False): ...

    class Named(InterfaceType, filterset=NamedFilterSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedFilterSet, "__build__", return_value=none_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None, info=mock_gql_info(), queryset_map=queryset_map, pagination=pagination
        )

    assert instances == []


async def test_resolvers__interface_type_connection_resolver__async__fetch_instances__order(undine_settings) -> None:
    undine_settings.ASYNC = True

    class NamedOrderSet(OrderSet[Task, Project], auto=False): ...

    class Named(InterfaceType, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
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
    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedOrderSet, "__build__", return_value=order_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=mock_gql_info(),
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert len(instances) == 1


async def test_resolvers__interface_type_connection_resolver__async__fetch_instances__filter_and_order(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class NamedFilterSet(FilterSet[Task, Project], auto=False): ...

    class NamedOrderSet(OrderSet[Task, Project], auto=False): ...

    class Named(InterfaceType, filterset=NamedFilterSet, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
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
    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)
    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedFilterSet, "__build__", return_value=not_none_result),
        patch.object(NamedOrderSet, "__build__", return_value=order_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=mock_gql_info(),
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert len(instances) == 1


async def test_resolvers__interface_type_connection_resolver__async__fetch_instances__filter_only_not_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class NamedFilterSet(FilterSet[Task, Project], auto=False): ...

    class Named(InterfaceType, filterset=NamedFilterSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
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
    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedFilterSet, "__build__", return_value=not_none_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None, info=mock_gql_info(), queryset_map=queryset_map, pagination=pagination
        )

    assert len(instances) == 1
