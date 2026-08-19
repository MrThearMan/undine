from __future__ import annotations

from unittest.mock import patch

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, GQLInfo, QueryType, RootType
from undine.exceptions import GraphQLModelNotFoundError, GraphQLPermissionError
from undine.resolvers import QueryTypeSingleResolver

pytestmark = pytest.mark.django_db


def test_resolvers__query_type_single_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver.run_sync(root=task, info=mock_gql_info(), pk=task.pk) == task


def test_resolvers__query_type_single_resolver__permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], model=Task):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__query_type_single_resolver__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    with patch("undine.resolvers.query.optimize_sync", return_value=None):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert result is None


def test_resolvers__query_type_single_resolver__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    with patch("undine.resolvers.query.optimize_sync", return_value=None), pytest.raises(GraphQLModelNotFoundError):
        resolver.run_sync(root=None, info=mock_gql_info())
