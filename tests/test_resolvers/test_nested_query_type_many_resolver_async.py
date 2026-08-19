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
from undine.resolvers import NestedQueryTypeManyResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__nested_query_type_many_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.NestedQueryTypeManyResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "Test assignee"


async def test_resolvers__nested_query_type_many_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.NestedQueryTypeManyResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())
    assert len(result) == 1
    assert len(called_with) == 1


async def test_resolvers__nested_query_type_many_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with (
        patch(
            "undine.resolvers.query.NestedQueryTypeManyResolver.get_instances",
            return_value=instances,
        ),
        pytest.raises(GraphQLPermissionError),
    ):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_many_resolver__async__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person]):
        @classmethod
        async def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with (
        patch(
            "undine.resolvers.query.NestedQueryTypeManyResolver.get_instances",
            return_value=instances,
        ),
        pytest.raises(GraphQLPermissionError),
    ):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_many_resolver__async__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person]):
        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with (
        patch(
            "undine.resolvers.query.NestedQueryTypeManyResolver.get_instances",
            return_value=instances,
        ),
        pytest.raises(GraphQLPermissionError),
    ):
        await resolver.run_async(root=task, info=mock_gql_info())


async def test_resolvers__nested_query_type_many_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Test assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.NestedQueryTypeManyResolver.get_instances", return_value=instances):
        result = await resolver(root=task, info=mock_gql_info())

    assert len(result) == 1
    assert result[0] == assignee
