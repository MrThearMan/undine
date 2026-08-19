from __future__ import annotations

import pytest

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import Field, GQLInfo, QueryType
from undine.exceptions import GraphQLFieldNotNullableError, GraphQLPermissionError
from undine.resolvers import NestedQueryTypeSingleResolver

pytestmark = pytest.mark.django_db


def test_resolvers__nested_query_type_single_resolver() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = TaskFactory.create(project__name="Test project")

    assert resolver.run_sync(root=task, info=mock_gql_info()) == task.project


def test_resolvers__nested_query_type_single_resolver__field_permissions() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_query_type_single_resolver__query_type_permissions() -> None:
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

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        resolver.run_sync(root=task, info=mock_gql_info())


def test_resolvers__nested_query_type_single_resolver__query_type_permissions__related_field() -> None:
    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            # Not called because 'TaskType.project' has a permissions check already
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: str) -> None:
            return

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = TaskFactory.create(project__name="Test project")

    assert resolver.run_sync(root=task, info=mock_gql_info()) == task.project


def test_resolvers__nested_query_type_single_resolver__run_sync__not_nullable_null() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType, nullable=False)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = TaskFactory.create(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        resolver.run_sync(root=task, info=mock_gql_info())
