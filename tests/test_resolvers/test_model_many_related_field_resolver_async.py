from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import ModelManyRelatedFieldResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__model_many_related_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == assignee.pk


async def test_resolvers__model_many_related_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert len(result) == 1
    assert len(called_with) == 1


async def test_resolvers__model_many_related_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with (
        patch(
            "undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances",
            return_value=instances,
        ),
        pytest.raises(GraphQLPermissionError),
    ):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__model_many_related_field_resolver__async__call(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver(root=task, info=mock_gql_info())

    assert len(result) == 1
    assert result[0] == assignee.pk
