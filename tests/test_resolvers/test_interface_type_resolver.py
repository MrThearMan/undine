from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.db.models import Value
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, FilterSet, GQLInfo, InterfaceField, InterfaceType, OrderSet, QueryType, RootType
from undine.dataclasses import FilterResults, OrderResults
from undine.resolvers import InterfaceTypeResolver

pytestmark = pytest.mark.django_db


def test_resolvers__interface_type_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = TaskFactory.create(name="Test Task")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert any(r.name == "Test Task" for r in result)


def test_resolvers__interface_type_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task = TaskFactory.create(name="Test Task")

    resolver.check_permissions(info=mock_gql_info(), root=None, query_type=TaskType, instances=[task])

    assert called_with == [task]


def test_resolvers__interface_type_resolver__fetch_instances__filter_none(undine_settings) -> None:
    undine_settings.ASYNC = False

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
        result = resolver.fetch_instances(info=mock_gql_info(), root=None, queryset_map=queryset_map)

    assert result == []


def test_resolvers__interface_type_resolver__filter_interface__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    with patch.object(NamedFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_interface(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


def test_resolvers__interface_type_resolver__filter_interface__aliases_distinct_no_filters(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    filter_result = FilterResults(
        filters=[],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(NamedFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_interface(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


def test_resolvers__interface_type_resolver__order_interface__aliases_no_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(NamedOrderSet, "__build__", return_value=order_result):
        result = resolver.order_interface(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []


def test_resolvers__interface_type_resolver__fetch_instances__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=1)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert len(result) == 1
