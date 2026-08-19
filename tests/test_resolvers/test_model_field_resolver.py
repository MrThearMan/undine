from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLFieldNotNullableError, GraphQLPermissionError
from undine.resolvers import ModelAttributeResolver

pytestmark = pytest.mark.django_db


def test_resolvers__model_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    assert resolver.run_sync(root=task, info=mock_gql_info()) == "Test task"


def test_resolvers__model_field_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__model_field_resolver__not_nullable_null_value() -> None:
    class TaskType(QueryType[Task]):
        name = Field(nullable=False)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test")
    task.name = None  # type: ignore[assignment]

    with pytest.raises(GraphQLFieldNotNullableError):
        resolver.run_sync(root=task, info=mock_gql_info())
