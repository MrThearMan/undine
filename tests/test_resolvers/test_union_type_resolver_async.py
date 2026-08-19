from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Value

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, FilterSet, GQLInfo, OrderSet, QueryType, RootType, UnionType
from undine.dataclasses import FilterResults, OrderResults
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import UnionTypeResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__union_type_resolver__fetch_instances_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    project = await sync_to_async(ProjectFactory.create)(name="Project 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    queryset_map = {TaskType: task_qs, ProjectType: project_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        results = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert task.pk in pks
    assert project.pk in pks


async def test_resolvers__union_type_resolver__check_permissions_async__sync_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
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


async def test_resolvers__union_type_resolver__check_permissions_async__async_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
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


async def test_resolvers__union_type_resolver__check_permissions_async__query_type_sync_permissions(
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

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
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


async def test_resolvers__union_type_resolver__check_permissions_async__query_type_async_permissions(
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

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
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


async def test_resolvers__union_type_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with (
        patch.object(UnionTypeResolver, "optimize", return_value={TaskType: task_qs}),
        patch("undine.resolvers.query.get_arguments", return_value={}),
    ):
        result = await resolver(root=None, info=mock_gql_info())

    assert len(result) == 1
    assert result[0].pk == task.pk


async def test_resolvers__union_type_resolver__async__fetch_instances_filter_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert result == []


async def test_resolvers__union_type_resolver__async__fetch_instances_order(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableOrderSet, "__build__", return_value=order_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


async def test_resolvers__union_type_resolver__async__fetch_instances_with_limit(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True, limit=1)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


async def test_resolvers__union_type_resolver__async__fetch_instances_filter_not_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=not_none_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1
    assert result[0].pk == task.pk
