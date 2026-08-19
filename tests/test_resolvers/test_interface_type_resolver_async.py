from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Value
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, FilterSet, GQLInfo, InterfaceField, InterfaceType, OrderSet, QueryType, RootType
from undine.dataclasses import FilterResults, OrderResults
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import InterfaceTypeResolver
from undine.typing import QuerySetMap

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__interface_type_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver.run_sync_async(root=None, info=mock_gql_info())

    assert any(r.name == "Test Task" for r in result)


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


async def test_resolvers__interface_type_resolver__check_permissions_async__sync_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    Query.named.permissions_func = permissions_func

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    await resolver.check_permissions_async(info=mock_gql_info(), root=None, query_type=TaskType, instances=[task])

    assert called_with == [task]


async def test_resolvers__interface_type_resolver__check_permissions_async__sync_func_2(undine_settings) -> None:
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


async def test_resolvers__interface_type_resolver__check_permissions_async__async_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    Query.named.permissions_func = permissions_func

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


async def test_resolvers__interface_type_resolver__check_permissions_async__async_func_2(undine_settings) -> None:
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


async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


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

    queryset_map: QuerySetMap = {TaskType: task_qs, ProjectType: project_qs}

    results = await resolver.fetch_instances_async(
        info=mock_gql_info(),
        root=None,
        queryset_map=queryset_map,
    )

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert task.pk in pks
    assert project.pk in pks


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


async def test_resolvers__interface_type_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver(root=None, info=mock_gql_info())

    assert len(result) == 1
    assert result[0].pk == task.pk


async def test_resolvers__interface_type_resolver__async__fetch_instances__filter_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class NamedFilterSet(FilterSet[Task, Project], auto=False): ...

    class Named(InterfaceType, filterset=NamedFilterSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedFilterSet, "__build__", return_value=none_result),
    ):
        result = await resolver.fetch_instances_async(info=mock_gql_info(), root=None, queryset_map=queryset_map)

    assert result == []


async def test_resolvers__interface_type_resolver__async__fetch_instances__filter_not_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class NamedFilterSet(FilterSet[Task, Project], auto=False): ...

    class Named(InterfaceType, filterset=NamedFilterSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedFilterSet, "__build__", return_value=not_none_result),
    ):
        result = await resolver.fetch_instances_async(info=mock_gql_info(), root=None, queryset_map=queryset_map)

    assert len(result) == 1
    assert result[0].pk == task.pk


async def test_resolvers__interface_type_resolver__async__fetch_instances__order(undine_settings) -> None:
    undine_settings.ASYNC = True

    class NamedOrderSet(OrderSet[Task, Project], auto=False): ...

    class Named(InterfaceType, orderset=NamedOrderSet):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class ProjectType(QueryType[Project], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(NamedOrderSet, "__build__", return_value=order_result),
    ):
        result = await resolver.fetch_instances_async(info=mock_gql_info(), root=None, queryset_map=queryset_map)

    assert len(result) == 1


async def test_resolvers__interface_type_resolver__fetch_instances_async__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=1)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver.run_sync_async(root=None, info=mock_gql_info())

    assert len(result) == 1
