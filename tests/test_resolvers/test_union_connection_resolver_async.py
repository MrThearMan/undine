from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Value
from graphql.pyutils import Path

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import MockRequest, mock_gql_info
from undine import Entrypoint, Field, FilterSet, GQLInfo, OrderSet, QueryType, RootType, UnionType
from undine.dataclasses import FilterResults, OrderResults
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler
from undine.resolvers import UnionTypeConnectionResolver
from undine.typing import GQLContext, QuerySetMap, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db(transaction=True)


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

    pagination = CursorPaginationHandler(typename=Searchable.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs, ProjectType: project_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
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


async def test_resolvers__union_type_connection_resolver__call__async(undine_settings) -> None:
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

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Searchable.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

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

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(UnionTypeConnectionResolver, "optimize", return_value=queryset_map),
    ):
        result = await resolver(root=None, info=info)

    assert isinstance(result, dict)
    assert "edges" in result


async def test_resolvers__union_type_connection_resolver__fetch_instances_async__filter_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Searchable.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    path = Path(None, "searchable", Searchable.__schema_name__)
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

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=info,
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert instances == []


async def test_resolvers__union_type_connection_resolver__fetch_instances_async__order(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Searchable.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    path = Path(None, "searchable", Searchable.__schema_name__)
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

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableOrderSet, "__build__", return_value=order_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=info,
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert len(instances) == 1


async def test_resolvers__union_type_connection_resolver__run_async__empty_connection(undine_settings) -> None:
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

    pagination = CursorPaginationHandler(typename="Searchable", first=10)
    path = Path(None, "searchable", None)
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

    with patch.object(UnionTypeConnectionResolver, "optimize", return_value={}):
        result = await resolver.run_async(root=None, info=info)

    assert result["totalCount"] == 0
    assert result["edges"] == []


async def test_resolvers__union_type_connection_resolver__async__fetch_instances_filter_not_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Searchable.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=not_none_result),
    ):
        instances = await resolver.fetch_instances_async(
            root=None,
            info=mock_gql_info(),
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert len(instances) == 1
    assert instances[0].pk == task.pk
