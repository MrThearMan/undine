from __future__ import annotations

from typing import Any

import pytest
from django.db.models import Model, Q

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import QueryTypeManyResolver

pytestmark = pytest.mark.django_db


def test_resolvers__query_type_many_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver.run_sync(root=task, info=mock_gql_info()) == [task]


def test_resolvers__query_type_many_resolver__permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Model, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__query_type_many_resolver__additional_filtering(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    TaskFactory.create()
    task = TaskFactory.create()

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
        additional_filter=Q(pk=task.pk),
    )

    with patch_optimizer():
        assert resolver.run_sync(root=task, info=mock_gql_info()) == [task]


def test_resolvers__query_type_many_resolver__entrypoint_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert result == [task]
    assert called_with == [task]
