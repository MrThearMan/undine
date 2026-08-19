from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLFieldNotNullableError, GraphQLPermissionError
from undine.resolvers import NestedQueryTypeSingleResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__nested_query_type_single_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == task.project


async def test_resolvers__nested_query_type_single_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None


async def test_resolvers__nested_query_type_single_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType, nullable=False)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == task.project
    assert called_with == [task.project]


async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        async def project_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        async def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_single_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver(root=task, info=mock_gql_info())
    assert result == task.project


async def test_resolvers__nested_query_type_single_resolver__call__async__null_not_nullable(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType, nullable=False)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver(root=task, info=mock_gql_info())
