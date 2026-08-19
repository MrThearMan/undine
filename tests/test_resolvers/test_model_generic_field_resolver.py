from __future__ import annotations

import pytest

from example_project.app.models import Comment, Project, Task
from tests.factories import CommentFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import ModelGenericForeignKeyResolver

pytestmark = pytest.mark.django_db


def test_resolvers__model_generic_foreign_key_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = TaskFactory.create(name="foo")
    comment = CommentFactory.create(contents="bar", target=task)

    result = resolver.run_sync(root=comment, info=mock_gql_info())

    # Should return an instance so that union can determine which type to use.
    assert isinstance(result, Task)
    assert result == task


def test_resolvers__model_generic_foreign_key_resolver__null() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    comment = CommentFactory.create(contents="bar")

    result = resolver.run_sync(root=comment, info=mock_gql_info())
    assert result is None


def test_resolvers__model_generic_foreign_key_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

        @target.permissions
        def target_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = TaskFactory.create(name="foo")
    comment = CommentFactory.create(contents="bar", target=task)

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=comment, info=mock_gql_info())
