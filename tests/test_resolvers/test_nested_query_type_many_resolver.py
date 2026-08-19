from __future__ import annotations

import pytest
from django.db.models import Model, QuerySet

from example_project.app.models import Person, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import NestedQueryTypeManyResolver

pytestmark = pytest.mark.django_db


def test_resolvers__nested_query_type_many_resolver() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    task = TaskFactory.create(assignees__name="Test assignee")

    instances = resolver.run_sync(root=task, info=mock_gql_info())

    assert isinstance(instances, list)
    assert len(instances) == 1
    assert instances[0].name == "Test assignee"


def test_resolvers__nested_query_type_many_resolver__field_permissions() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_query_type_many_resolver__query_type_permissions() -> None:
    class PersonType(QueryType[Person]):
        @classmethod
        def __permissions__(cls, instance: Model, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_query_type_many_resolver__query_type_permissions__related_field() -> None:
    class PersonType(QueryType[Person]):
        @classmethod
        def __permissions_many__(cls, queryset: QuerySet, info: GQLInfo) -> None:
            # Not called because 'TaskType.assignees' has a permissions check already
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: str) -> None:
            return

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    resolver.run_sync(root=task, info=mock_gql_info())
