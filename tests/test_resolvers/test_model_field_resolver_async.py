from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLFieldNotNullableError, GraphQLPermissionError
from undine.resolvers import ModelAttributeResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__model_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field()

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == "Async Task"


async def test_resolvers__model_field_resolver__async__not_nullable_null_value(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field(nullable=False)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Test")
    task.name = None  # type: ignore[assignment]

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__model_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == "Async Task"
    assert called_with == ["Async Task"]


async def test_resolvers__model_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        async def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__model_field_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field(nullable=True)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Test")
    task.name = None  # type: ignore[assignment]

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None
