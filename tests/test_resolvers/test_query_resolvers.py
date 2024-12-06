from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from django.db import models

from example_project.app.models import Person, Project, Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo
from undine import Field, QueryType
from undine.errors.exceptions import GraphQLPermissionDeniedError
from undine.resolvers import (
    FunctionResolver,
    ModelFieldResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    QueryTypeManyRelatedFieldResolver,
    QueryTypeSingleRelatedFieldResolver,
)

if TYPE_CHECKING:
    from graphql import GraphQLResolveInfo

    from undine.typing import GQLInfo


@pytest.mark.django_db
def test_resolvers__model_field_resolver():
    class TaskType(QueryType, model=Task):
        name = Field()

    resolver = ModelFieldResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    assert resolver(instance=task, info=MockGQLInfo()) == "Test task"


@pytest.mark.django_db
def test_resolvers__model_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        name = Field()

        @name.permissions
        def name_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return False

    resolver = ModelFieldResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver():
    class TaskType(QueryType, model=Task):
        project = Field()

    resolver = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project__name="Project")

    result = resolver(instance=task, info=MockGQLInfo())

    assert isinstance(result, Project)
    assert result.name == "Project"


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        project = Field()

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return False

    resolver = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project__name="Project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver():
    class TaskType(QueryType, model=Task):
        assignees = Field()

    resolver = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    result = resolver(instance=task, info=MockGQLInfo())

    assert isinstance(result, models.QuerySet)
    assert result.count() == 1
    assignee = result.first()
    assert assignee.name == "Assignee"


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return False

    resolver = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    resolver = QueryTypeSingleRelatedFieldResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    assert resolver(instance=task, info=MockGQLInfo()) == task.project


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__field_permissions():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return False

    resolver = QueryTypeSingleRelatedFieldResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__query_type_permissions():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permission_single__(cls, instance: Project, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    resolver = QueryTypeSingleRelatedFieldResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__query_type_permissions__also_field_permissions():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permission_single__(cls, instance: Project, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return True

    resolver = QueryTypeSingleRelatedFieldResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__query_type_permissions__skip_object_perms():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permission_single__(cls, instance: Project, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions(skip_query_type_perms=True)
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return True

    resolver = QueryTypeSingleRelatedFieldResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    result = resolver(instance=task, info=MockGQLInfo())

    assert result == task.project


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

    resolver = QueryTypeManyRelatedFieldResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    queryset = resolver(instance=task, info=MockGQLInfo())
    assert isinstance(queryset, models.QuerySet)
    assert queryset.count() == 1
    assert queryset.first().name == "Test assignee"


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__field_permissions():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return False

    resolver = QueryTypeManyRelatedFieldResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__query_type_permissions():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permission_many__(cls, queryset: models.QuerySet, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

    resolver = QueryTypeManyRelatedFieldResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__query_type_permissions__also_field_permissions():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permission_many__(cls, queryset: models.QuerySet, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return True

    resolver = QueryTypeManyRelatedFieldResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(instance=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__query_type_permissions__skip_object_perms():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permission_many__(cls, queryset: models.QuerySet, info: GQLInfo) -> bool:
            return False

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions(skip_query_type_perms=True)
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> bool:
            return True

    resolver = QueryTypeManyRelatedFieldResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    resolver(instance=task, info=MockGQLInfo())


def test_resolvers__function_resolver():
    def func():
        return "foo"

    resoler = FunctionResolver(func)
    result = resoler(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver(func, root_param="root")
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver(func, info_param="info")
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__adapt():
    def func():
        return "foo"

    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__self():
    def func(self: Any):
        return self

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__cls():
    def func(cls: Any):
        return cls

    resolver = FunctionResolver.adapt(func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__adapt__info__graphql_resolver_info():
    def func(info: GraphQLResolveInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver.adapt(func)
    result = resolver(root=None, info=info)
    assert result == info
