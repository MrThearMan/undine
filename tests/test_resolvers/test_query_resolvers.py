from __future__ import annotations

from typing import Any

import pytest
from django.db.models import Model, QuerySet
from graphql import GraphQLResolveInfo

from example_project.app.models import Person, Project, Task
from tests.factories import TaskFactory
from tests.helpers import MockGQLInfo, patch_optimizer
from undine import Field, QueryType
from undine.errors.exceptions import GraphQLPermissionDeniedError
from undine.resolvers import (
    FunctionResolver,
    ModelFieldResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
    QueryTypeManyFilteredResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
)
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_resolvers__model_field_resolver():
    class TaskType(QueryType, model=Task):
        name = Field()

    resolver = ModelFieldResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    assert resolver(root=task, info=MockGQLInfo()) == "Test task"


@pytest.mark.django_db
def test_resolvers__model_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        name = Field()

        @name.permissions
        def name_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = ModelFieldResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver():
    class TaskType(QueryType, model=Task):
        project = Field()

    resolver = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project__name="Project")

    result = resolver(root=task, info=MockGQLInfo())

    assert isinstance(result, Project)
    assert result.name == "Project"


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        project = Field()

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project__name="Project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver():
    class TaskType(QueryType, model=Task):
        assignees = Field()

    resolver = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    result = resolver(root=task, info=MockGQLInfo())

    assert isinstance(result, QuerySet)
    assert result.count() == 1
    assignee = result.first()
    assert assignee.name == "Assignee"


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver():
    class TaskType(QueryType, model=Task): ...

    resolver = QueryTypeSingleResolver(query_type=TaskType)

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver(root=task, info=MockGQLInfo()) == task


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__permissions():
    class TaskType(QueryType, model=Task):
        @classmethod
        def __permissions_single__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    resolver = QueryTypeSingleResolver(query_type=TaskType)

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    resolver = NestedQueryTypeSingleResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    assert resolver(root=task, info=MockGQLInfo()) == task.project


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver__field_permissions():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = NestedQueryTypeSingleResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver__query_type_permissions():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permissions_single__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    resolver = NestedQueryTypeSingleResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver__field_and_query_type_permissions():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permissions_single__(cls, instance: Project, info: GQLInfo) -> bool:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = NestedQueryTypeSingleResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver__skip_query_type_perms():
    class ProjectType(QueryType, model=Project):
        @classmethod
        def __permissions_single__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

        @project.permissions(skip_query_type_perms=True)
        def project_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            return

    resolver = NestedQueryTypeSingleResolver(field=TaskType.project, query_type=ProjectType)

    task = TaskFactory.create(project__name="Test project")

    assert resolver(root=task, info=MockGQLInfo()) == task.project


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver():
    class TaskType(QueryType, model=Task): ...

    resolver = QueryTypeManyResolver(query_type=TaskType)

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver(root=task, info=MockGQLInfo()) == [task]


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__permissions():
    class TaskType(QueryType, model=Task):
        @classmethod
        def __permissions_many__(cls, instances: list[Model], info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    resolver = QueryTypeManyResolver(query_type=TaskType)

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionDeniedError):
        assert resolver(root=task, info=MockGQLInfo()) == [task]


@pytest.mark.django_db
def test_resolvers__query_type_many_filtered_resolver():
    class TaskType(QueryType, model=Task): ...

    TaskFactory.create()
    task = TaskFactory.create()

    resolver = QueryTypeManyFilteredResolver(query_type=TaskType)

    with patch_optimizer():
        assert resolver(root=task, info=MockGQLInfo(), pk=task.pk) == [task]


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    instances: list[Task] = resolver(root=task, info=MockGQLInfo())
    assert isinstance(instances, list)
    assert len(instances) == 1
    assert instances[0].name == "Test assignee"


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver__field_permissions():
    class PersonType(QueryType, model=Person): ...

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver__query_type_permissions():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permissions_many__(cls, queryset: QuerySet, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver__query_type_permissions__also_field_permissions():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permissions_many__(cls, queryset: QuerySet, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            return

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=task, info=MockGQLInfo())


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver__query_type_permissions__skip_object_perms():
    class PersonType(QueryType, model=Person):
        @classmethod
        def __permissions_many__(cls, queryset: QuerySet, info: GQLInfo) -> None:
            raise GraphQLPermissionDeniedError

    class TaskType(QueryType, model=Task):
        assignees = Field(PersonType, many=True)

        @assignees.permissions(skip_query_type_perms=True)
        def assignees_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            return

    resolver = NestedQueryTypeManyResolver(field=TaskType.assignees, query_type=PersonType)

    task = TaskFactory.create(assignees__name="Test assignee")

    resolver(root=task, info=MockGQLInfo())


def test_resolvers__function_resolver():
    def func():
        return "foo"

    resoler = FunctionResolver(func=func)
    result = resoler(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver(func=func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__info():
    def func(info: GQLInfo):
        return info

    gql_info = MockGQLInfo()
    resolver = FunctionResolver(func=func)
    result = resolver(root=None, info=gql_info)
    assert result == gql_info


def test_resolvers__function_resolver__adapt():
    def func():
        return "foo"

    resolver = FunctionResolver(func=func)
    result = resolver(root=None, info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root():
    def func(root: Any):
        return root

    resolver = FunctionResolver(func=func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__self():
    def func(self: Any):
        return self

    resolver = FunctionResolver(func=func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__cls():
    def func(cls: Any):
        return cls

    resolver = FunctionResolver(func=func)
    result = resolver(root="foo", info=MockGQLInfo())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__info():
    def func(info: GQLInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver(func=func)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__adapt__info__graphql_resolver_info():
    def func(info: GraphQLResolveInfo):
        return info

    info = MockGQLInfo()
    resolver = FunctionResolver(func=func)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__field_permissions():
    class TaskType(QueryType, model=Task):
        @Field
        def name(self) -> str:
            return "foo"

        @name.permissions
        def name_permissions(self: Field, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionDeniedError

    resolver = TaskType.name.get_resolver()

    with pytest.raises(GraphQLPermissionDeniedError):
        resolver(root=None, info=MockGQLInfo())
