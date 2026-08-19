from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Project, Task
from tests.factories import ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLFieldNotNullableError, GraphQLPermissionError
from undine.resolvers import ModelSingleRelatedFieldResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__model_single_related_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == project.pk


async def test_resolvers__model_single_related_field_resolver__async__call(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver(root=task, info=mock_gql_info())
    assert result == project.pk


async def test_resolvers__model_single_related_field_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None


async def test_resolvers__model_single_related_field_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field(nullable=False)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__model_single_related_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        project = Field()

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == project.pk
    assert called_with == [project]


async def test_resolvers__model_single_related_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

        @project.permissions
        async def project_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__model_single_related_field_resolver__async__not_nullable_null(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field(nullable=False)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver(root=task, info=mock_gql_info())
