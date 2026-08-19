from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.db.models import Value

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Entrypoint, Field, FilterSet, GQLInfo, OrderSet, QueryType, RootType, UnionType
from undine.dataclasses import FilterResults, OrderResults
from undine.resolvers import UnionTypeResolver

pytestmark = pytest.mark.django_db


def test_resolvers__union_type_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = TaskFactory.create(name="Task 1")

    resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])

    assert called_with == [task]


def test_resolvers__union_type_resolver__filter_union__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with patch.object(SearchableFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


def test_resolvers__union_type_resolver__fetch_instances__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        result = resolver.fetch_instances(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


def test_resolvers__union_type_resolver__fetch_instances__filter_none_sync(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task = TaskFactory.create(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        result = resolver.fetch_instances(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert result == []


def test_resolvers__union_type_resolver__filter_union__aliases_distinct_no_filters(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


def test_resolvers__union_type_resolver__order_union__aliases_and_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


def test_resolvers__union_type_resolver__order_union__aliases_no_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []
