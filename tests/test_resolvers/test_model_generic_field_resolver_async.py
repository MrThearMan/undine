from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Comment, Project, Task
from tests.factories import CommentFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import ModelGenericForeignKeyResolver

pytestmark = pytest.mark.django_db(transaction=True)


async def test_resolvers__model_generic_foreign_key_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = await sync_to_async(TaskFactory.create)(name="foo")
    comment = await sync_to_async(CommentFactory.create)(contents="bar", target=task)

    result = await resolver.run_async(root=comment, info=mock_gql_info())

    assert isinstance(result, Task)
    assert result == task


async def test_resolvers__model_generic_foreign_key_resolver__async__null(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    comment = await sync_to_async(CommentFactory.create)(contents="bar")

    result = await resolver.run_async(root=comment, info=mock_gql_info())
    assert result is None


async def test_resolvers__model_generic_foreign_key_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

        @target.permissions
        def target_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = await sync_to_async(TaskFactory.create)(name="foo")
    comment = await sync_to_async(CommentFactory.create)(contents="bar", target=task)

    result = await resolver.run_async(root=comment, info=mock_gql_info())

    assert result == task
    assert called_with == [task]


async def test_resolvers__model_generic_foreign_key_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

        @target.permissions
        async def target_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = await sync_to_async(TaskFactory.create)(name="foo")
    comment = await sync_to_async(CommentFactory.create)(contents="bar", target=task)

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=comment, info=mock_gql_info())


async def test_resolvers__model_generic_foreign_key_resolver__async__call(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = await sync_to_async(TaskFactory.create)(name="foo")
    comment = await sync_to_async(CommentFactory.create)(contents="bar", target=task)

    result = await resolver(root=comment, info=mock_gql_info())
    assert isinstance(result, Task)
    assert result == task
