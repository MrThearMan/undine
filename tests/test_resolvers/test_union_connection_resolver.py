from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.db.models import Q, Value
from graphql.pyutils import Path

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import MockRequest, mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, FilterSet, GQLInfo, OrderSet, QueryType, RootType, UnionType
from undine.dataclasses import FilterResults, OrderResults
from undine.relay import Connection, CursorPaginationHandler
from undine.resolvers import UnionTypeConnectionResolver
from undine.typing import ConnectionDict, GQLContext, PageInfoDict, QuerySetMap, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db


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


def test_resolvers__union_type_connection_resolver__filter_union__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

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
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with patch.object(SearchableFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


def test_resolvers__union_type_connection_resolver__filter_union__with_filters(undine_settings) -> None:

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
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[Q(pk__isnull=False)],
        aliases={},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False


def test_resolvers__union_type_connection_resolver__order_union__with_order_by(undine_settings) -> None:

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


def test_resolvers__union_type_connection_resolver__run_sync__empty_connection(undine_settings) -> None:
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
        result = resolver.run_sync(root=None, info=info)

    assert result["totalCount"] == 0
    assert result["edges"] == []


def test_resolvers__union_type_connection_resolver__fetch_instances__filter_none(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        instances = resolver.fetch_instances(
            root=None,
            info=mock_gql_info(),
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert instances == []


def test_resolvers__union_type_connection_resolver__fetch_instances__order(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task = TaskFactory.create(name="Task 1")

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
        instances = resolver.fetch_instances(root=None, info=info, queryset_map=queryset_map, pagination=pagination)

    assert len(instances) == 1


def test_resolvers__union_type_connection_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task = TaskFactory.create(name="Task 1")

    resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])

    assert called_with == [task]


def test_resolvers__union_type_connection_resolver__filter_union__with_aliases_distinct_filters(
    undine_settings,
) -> None:

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
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[Q(pk__isnull=False)],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


def test_resolvers__union_type_connection_resolver__order_union__with_aliases_and_order_by(
    undine_settings,
) -> None:

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


def test_resolvers__union_type_connection_resolver__filter_union__aliases_distinct_no_filters(
    undine_settings,
) -> None:
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


def test_resolvers__union_type_connection_resolver__order_union__aliases_no_order_by(
    undine_settings,
) -> None:
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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []


def test_resolvers__union_type_connection_resolver__optimize__empty_optimizations(undine_settings) -> None:
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

    with patch_optimizer():
        queryset_map = resolver.optimize(info=mock_gql_info())

    assert queryset_map == {}
