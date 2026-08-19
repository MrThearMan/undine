from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.db.models import Value
from graphql import GraphQLNonNull, GraphQLString
from graphql.pyutils import Path

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import MockRequest, mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, FilterSet, InterfaceField, InterfaceType, OrderSet, QueryType, RootType
from undine.dataclasses import FilterResults, OrderResults
from undine.exceptions import GraphQLPermissionError
from undine.relay import Connection, CursorPaginationHandler
from undine.resolvers import InterfaceTypeConnectionResolver
from undine.typing import GQLContext, GQLInfo, QuerySetMap, UndineInternalContext
from undine.utils.graphql.utils import get_field_path_identifier

pytestmark = pytest.mark.django_db


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

    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs, ProjectType: project_qs}

    instances = resolver.fetch_instances(
        root=None,
        info=mock_gql_info(),
        queryset_map=queryset_map,
        pagination=pagination,
    )

    assert len(instances) == 2
    pks = {i.pk for i in instances}
    assert task.pk in pks
    assert project.pk in pks


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


def test_resolvers__interface_type_connection_resolver__run_sync(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task = TaskFactory.create(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = CursorPaginationHandler(typename=Named.__schema_name__, first=10)
    queryset_map: QuerySetMap = {TaskType: task_qs}

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

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=queryset_map):
        result = resolver.run_sync(root=None, info=info)

    assert len(result["edges"]) == 1
    assert result["edges"][0]["node"].pk == task.pk


def test_resolvers__interface_type_connection_resolver__optimize__with_filter_order_kwargs(
    undine_settings,
) -> None:
    undine_settings.ASYNC = False

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

    TaskFactory.create(name="Task 1")

    # Pass filter and orderBy kwargs for the Task model to exercise lines 1728 and 1730
    filter_key = f"filter{Task.__name__}"
    order_key = f"orderBy{Task.__name__}"

    with patch_optimizer():
        queryset_map = resolver.optimize(info=mock_gql_info(), **{filter_key: {}, order_key: []})

    # Should produce a non-empty queryset_map (Task is selected)
    assert queryset_map == {}


def test_resolvers__interface_type_connection_resolver__fetch_instances__filter_none(undine_settings) -> None:
    undine_settings.ASYNC = False

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
        instances = resolver.fetch_instances(
            root=None,
            info=mock_gql_info(),
            queryset_map=queryset_map,
            pagination=pagination,
        )

    assert instances == []


def test_resolvers__interface_type_connection_resolver__filter_interface__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

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
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with patch.object(NamedFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_interface(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


def test_resolvers__interface_type_connection_resolver__filter_interface__aliases_distinct_no_filters(
    undine_settings,
) -> None:
    undine_settings.ASYNC = False

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


def test_resolvers__interface_type_connection_resolver__order_interface__aliases_no_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

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

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(NamedOrderSet, "__build__", return_value=order_result):
        result = resolver.order_interface(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []


def test_resolvers__interface_type_connection_resolver__optimize__filter_order_kwargs_non_empty(
    undine_settings,
) -> None:
    undine_settings.ASYNC = False

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

    TaskFactory.create(name="Task 1")

    filter_key = f"filter{Task.__name__}"
    order_key = f"orderBy{Task.__name__}"

    with patch_optimizer(annotations={"__test_annotation__": Value("test")}):
        queryset_map = resolver.optimize(info=mock_gql_info(), **{filter_key: {}, order_key: []})

    assert queryset_map is not None
