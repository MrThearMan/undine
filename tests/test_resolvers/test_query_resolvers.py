from __future__ import annotations

from inspect import isawaitable
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Model, Q, QuerySet
from graphql import GraphQLResolveInfo

from example_project.app.models import Comment, Person, Project, Task
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import Entrypoint, Field, QueryType, RootType
from undine.exceptions import GraphQLPermissionError
from undine.resolvers import (
    EntrypointFunctionResolver,
    ModelAttributeResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
)
from undine.resolvers.query import ModelGenericForeignKeyResolver
from undine.typing import GQLInfo


def test_resolvers__function_resolver() -> None:
    def func() -> str:
        return "foo"

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__root() -> None:
    def func(root: Any) -> Any:
        return root

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__info() -> None:
    def func(info: GQLInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    gql_info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=gql_info)
    assert result == gql_info


def test_resolvers__function_resolver__adapt() -> None:
    def func() -> str:
        return "foo"

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root() -> None:
    def func(root: Any) -> Any:
        return root

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__self() -> None:
    def func(self: Any) -> Any:
        return self

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__root__cls() -> None:
    def func(cls: Any) -> Any:
        return cls

    class Query(RootType):
        example = Entrypoint(func)

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root="foo", info=mock_gql_info())
    assert result == "foo"


def test_resolvers__function_resolver__adapt__info() -> None:
    def func(info: GQLInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__adapt__info__graphql_resolver_info() -> None:
    def func(info: GraphQLResolveInfo) -> Any:
        return info

    class Query(RootType):
        example = Entrypoint(func)

    info = mock_gql_info()
    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=info)
    assert result == info


def test_resolvers__function_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        @Field
        def name(self) -> str:
            return "foo"

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = TaskType.name.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    assert resolver(root=task, info=mock_gql_info()) == "Test task"


@pytest.mark.django_db
def test_resolvers__model_field_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test task")

    with pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = ProjectFactory.create(name="Project")
    task = TaskFactory.create(project=project)

    result = resolver(root=task, info=mock_gql_info())

    assert isinstance(result, int)
    assert result == project.pk


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__null() -> None:
    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project=None)

    result = resolver(root=task, info=mock_gql_info())
    assert result is None


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        project = Field()

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project__name="Project")

    with pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = PersonFactory.create(name="Assignee")
    task = TaskFactory.create(assignees=[assignee])

    result = resolver(root=task, info=mock_gql_info())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == assignee.pk


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver__field_permissions() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_generic_foreign_key_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    task = TaskFactory.create(name="foo")
    comment = CommentFactory.create(contents="bar", target=task)

    result = resolver(root=comment, info=mock_gql_info())

    # Should return an instance so that union can determine which type to use.
    assert isinstance(result, Task)
    assert result == task


@pytest.mark.django_db
def test_resolvers__model_generic_foreign_key_resolver__null() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    comment = CommentFactory.create(contents="bar")

    result = resolver(root=comment, info=mock_gql_info())
    assert result is None


@pytest.mark.django_db
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
        resolver(root=comment, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver(root=task, info=mock_gql_info(), pk=task.pk) == task


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        coroutine = resolver(root=task, info=mock_gql_info(), pk=task.pk)
        assert isawaitable(coroutine)

        result = await coroutine
        assert result == task


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], model=Task):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        assert resolver(root=task, info=mock_gql_info()) == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_many_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        coroutine = resolver(root=task, info=mock_gql_info())
        assert isawaitable(coroutine)

        result = await coroutine
        assert result == [task]


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__permissions(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Model, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__additional_filtering(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    TaskFactory.create()
    task = TaskFactory.create()

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
        additional_filter=Q(pk=task.pk),
    )

    with patch_optimizer():
        assert resolver(root=task, info=mock_gql_info()) == [task]


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = TaskFactory.create(project__name="Test project")

    assert resolver(root=task, info=mock_gql_info()) == task.project


@pytest.mark.django_db
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
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__nested_query_type_single_resolver__query_type_permissions__related_field() -> None:
    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            # Not called because 'TaskType.project' has a permissions check already
            raise GraphQLPermissionError  # pragma: no cover

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

    assert resolver(root=task, info=mock_gql_info()) == task.project


@pytest.mark.django_db
def test_resolvers__nested_query_type_many_resolver() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType, many=True)

    resolver: NestedQueryTypeManyResolver[Person] = NestedQueryTypeManyResolver(
        query_type=PersonType,
        field=TaskType.assignees,
    )

    task = TaskFactory.create(assignees__name="Test assignee")

    instances = resolver(root=task, info=mock_gql_info())

    assert isinstance(instances, list)
    assert len(instances) == 1
    assert instances[0].name == "Test assignee"


@pytest.mark.django_db
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
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
        resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db
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

    resolver(root=task, info=mock_gql_info())
