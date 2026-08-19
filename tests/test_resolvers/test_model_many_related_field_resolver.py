from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import Person, Task
from tests.factories import PersonFactory, TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import ModelManyRelatedFieldResolver

pytestmark = pytest.mark.django_db


def test_resolvers__model_many_related_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = PersonFactory.create(name="Assignee")
    task = TaskFactory.create(assignees=[assignee])

    result = resolver.run_sync(root=task, info=mock_gql_info())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == assignee.pk


def test_resolvers__model_many_related_field_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__model_many_related_field_resolver__check_permissions__no_func() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")
    assignee = next(iter(task.assignees.all()))

    # No permissions_func: should be a no-op, returning normally
    resolver.check_permissions(root=task, info=mock_gql_info(), instances=[assignee])


def test_resolvers__model_many_related_field_resolver__check_permissions__empty_instances_with_func() -> None:
    called = []

    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called.append(value)

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create()
    resolver.check_permissions(root=task, info=mock_gql_info(), instances=[])

    assert called == []
