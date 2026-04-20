from __future__ import annotations

from collections import namedtuple
from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.db.models import Model, Prefetch, Q, QuerySet, Value
from graphql import GraphQLEnumType, GraphQLEnumValue, GraphQLNonNull, GraphQLResolveInfo, GraphQLString

from example_project.app.models import Comment, Person, Project, Task
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory
from tests.helpers import mock_gql_info, patch_optimizer
from undine import (
    Entrypoint,
    Field,
    FilterSet,
    InterfaceField,
    InterfaceType,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)
from undine.dataclasses import FilterResults, OrderResults, QuerySetMapWithPagination
from undine.exceptions import (
    GraphQLFieldNotNullableError,
    GraphQLModelNotFoundError,
    GraphQLNodeIDFieldTypeError,
    GraphQLNodeTypeNotObjectTypeError,
    GraphQLPermissionError,
)
from undine.pagination import PaginationHandler
from undine.relay import Connection, Node, to_global_id
from undine.resolvers import (
    ConnectionResolver,
    EntrypointFunctionResolver,
    InterfaceTypeConnectionResolver,
    InterfaceTypeResolver,
    ModelAttributeResolver,
    ModelManyRelatedFieldResolver,
    ModelSingleRelatedFieldResolver,
    NestedConnectionResolver,
    NestedQueryTypeManyResolver,
    NestedQueryTypeSingleResolver,
    NodeResolver,
    QueryTypeManyResolver,
    QueryTypeSingleResolver,
    UnionTypeConnectionResolver,
    UnionTypeResolver,
)
from undine.resolvers.query import ModelGenericForeignKeyResolver, NamedTupleFieldResolver, TypedDictFieldResolver
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

    assert resolver.run_sync(root=task, info=mock_gql_info()) == "Test task"


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
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver() -> None:
    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = ProjectFactory.create(name="Project")
    task = TaskFactory.create(project=project)

    result = resolver.run_sync(root=task, info=mock_gql_info())

    assert isinstance(result, int)
    assert result == project.pk


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__null() -> None:
    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project=None)

    result = resolver.run_sync(root=task, info=mock_gql_info())
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
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db
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
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_resolvers__model_generic_foreign_key_resolver__null() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class CommentType(QueryType[Comment]):
        target = Field()

    resolver: ModelGenericForeignKeyResolver[Task] = ModelGenericForeignKeyResolver(field=CommentType.target)

    comment = CommentFactory.create(contents="bar")

    result = resolver.run_sync(root=comment, info=mock_gql_info())
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
        resolver.run_sync(root=comment, info=mock_gql_info())


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
        assert resolver.run_sync(root=task, info=mock_gql_info(), pk=task.pk) == task


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
        result = await resolver.run_async(root=task, info=mock_gql_info(), pk=task.pk)

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
        resolver.run_sync(root=task, info=mock_gql_info())


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
        assert resolver.run_sync(root=task, info=mock_gql_info()) == [task]


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
        result = await resolver.run_async(root=task, info=mock_gql_info())

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
        resolver.run_sync(root=task, info=mock_gql_info())


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
        assert resolver.run_sync(root=task, info=mock_gql_info()) == [task]


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

    assert resolver.run_sync(root=task, info=mock_gql_info()) == task.project


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
        resolver.run_sync(root=task, info=mock_gql_info())


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
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db
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

    instances = resolver.run_sync(root=task, info=mock_gql_info())

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
        resolver.run_sync(root=task, info=mock_gql_info())


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
        resolver.run_sync(root=task, info=mock_gql_info())


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

    resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__fetch_instances_async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    project = await sync_to_async(ProjectFactory.create)(name="Project 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    project_qs = Project.objects.filter(pk=project.pk).annotate(__typename=Value(ProjectType.__schema_name__))

    queryset_map = {TaskType: task_qs, ProjectType: project_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        results = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert task.pk in pks
    assert project.pk in pks


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__check_permissions_async__sync_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__check_permissions_async__async_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    await resolver.check_permissions_async(
        root=None,
        info=mock_gql_info(),
        query_type=TaskType,
        instances=[task],
    )

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__check_permissions_async__query_type_sync_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__check_permissions_async__query_type_async_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            root=None,
            info=mock_gql_info(),
            query_type=TaskType,
            instances=[task],
        )


def test_resolvers__function_resolver__check_permissions__many_with_permissions_func() -> None:
    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    def func() -> list[str]:
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


def test_resolvers__function_resolver__check_permissions__single_with_permissions_func() -> None:
    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    def func() -> str:
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


def test_resolvers__function_resolver__check_permissions__query_type_permissions() -> None:
    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    def func() -> Any:
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__many_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    async def func() -> list[str]:  # noqa: RUF029
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__many_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:  # noqa: RUF029
        called_with.append(item)

    async def func() -> list[str]:  # noqa: RUF029
        return ["a", "b"]

    class Query(RootType):
        example = Entrypoint(func, many=True)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__single_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:  # noqa: RUF029
        called_with.append(item)

    async def func() -> str:  # noqa: RUF029
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__single_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, item: Any) -> None:
        called_with.append(item)

    async def func() -> str:  # noqa: RUF029
        return "result"

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.permissions_func = permissions_func

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "result"
    assert called_with == ["result"]


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__query_type_async_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    async def func() -> Any:  # noqa: RUF029
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


@pytest.mark.asyncio
async def test_resolvers__function_resolver__async__check_permissions_async__query_type_sync_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    async def func() -> Any:  # noqa: RUF029
        return object()

    class Query(RootType):
        example = Entrypoint(func)

    Query.example.ref = TaskType

    resolver = EntrypointFunctionResolver(func=func, entrypoint=Query.example)

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "async_result"

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "async_result"


def test_resolvers__field_function_resolver__check_permissions__many_with_permissions_func() -> None:
    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        def tags(self) -> list[str]:
            return ["a", "b"]

        @tags.permissions
        def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = resolver(root=None, info=mock_gql_info())

    assert result == ["a", "b"]
    assert called_with == ["a", "b"]


def test_resolvers__field_function_resolver__check_permissions__query_type_permissions() -> None:
    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        resolver(root=None, info=mock_gql_info())


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__many_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        async def tags(self) -> list[str]:
            return ["x", "y"]

        @tags.permissions
        def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["x", "y"]
    assert called_with == ["x", "y"]


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__many_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field(many=True)
        async def tags(self) -> list[str]:
            return ["x", "y"]

        @tags.permissions
        async def tags_permissions(self, info: GQLInfo, item: str) -> None:
            called_with.append(item)

    resolver = TaskType.tags.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == ["x", "y"]
    assert called_with == ["x", "y"]


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__single_async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "val"

        @computed.permissions
        async def computed_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "val"
    assert called_with == ["val"]


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__single_sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        @Field
        async def computed(self) -> str:
            return "val"

        @computed.permissions
        def computed_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = TaskType.computed.get_resolver()
    result = await resolver(root=None, info=mock_gql_info())

    assert result == "val"
    assert called_with == ["val"]


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        async def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        def __permissions__(cls, instance: Any, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self) -> Any:
            return object()

    resolver = TaskType.project.get_resolver()

    with pytest.raises(GraphQLPermissionError):
        await resolver(root=None, info=mock_gql_info())


@pytest.mark.django_db
def test_resolvers__model_field_resolver__not_nullable_null_value() -> None:
    class TaskType(QueryType[Task]):
        name = Field(nullable=False)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = TaskFactory.create(name="Test")
    task.name = None  # type: ignore[assignment]

    with pytest.raises(GraphQLFieldNotNullableError):
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field()

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == "Async Task"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_field_resolver__async__not_nullable_null_value(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field(nullable=False)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Test")
    task.name = None  # type: ignore[assignment]

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            called_with.append(value)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == "Async Task"
    assert called_with == ["Async Task"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field()

        @name.permissions
        async def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Async Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == project.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field(nullable=False)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        project = Field()

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == project.pk
    assert called_with == [project]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

        @project.permissions
        async def project_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_many_related_field_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == assignee.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_many_related_field_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver.run_async(root=task, info=mock_gql_info())

    assert len(result) == 1
    assert len(called_with) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_many_related_field_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with (
        patch(
            "undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances",
            return_value=instances,
        ),
        pytest.raises(GraphQLPermissionError),
    ):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    with patch("undine.resolvers.query.optimize_sync", return_value=None):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert result is None


@pytest.mark.django_db
def test_resolvers__query_type_single_resolver__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    with patch("undine.resolvers.query.optimize_sync", return_value=None), pytest.raises(GraphQLModelNotFoundError):
        resolver.run_sync(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    async def mock_optimize_async(*args: Any, **kwargs: Any) -> None:  # noqa: RUF029
        return None

    with patch("undine.resolvers.query.optimize_async", side_effect=mock_optimize_async):
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=False)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    async def mock_optimize_async(*args: Any, **kwargs: Any) -> None:  # noqa: RUF029
        return None

    with (
        patch("undine.resolvers.query.optimize_async", side_effect=mock_optimize_async),
        pytest.raises(GraphQLModelNotFoundError),
    ):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)

    assert result == task
    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__check_permissions_async__sync_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)


@pytest.mark.django_db
def test_resolvers__query_type_many_resolver__entrypoint_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = TaskFactory.create()

    with patch_optimizer():
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert result == [task]
    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_many_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result == [task]
    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_many_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_many_resolver__async__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_many_resolver__async__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    resolver: QueryTypeManyResolver[Task] = QueryTypeManyResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    await sync_to_async(TaskFactory.create)()

    with patch_optimizer(), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == task.project


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__null_not_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType, nullable=False)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result == task.project
    assert called_with == [task.project]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

        @project.permissions
        async def project_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]):
        @classmethod
        async def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__async__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

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

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    with pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db
def test_resolvers__union_type_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = TaskFactory.create(name="Task 1")

    resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])

    assert called_with == [task]


@pytest.mark.django_db
def test_resolvers__interface_type_resolver(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = TaskFactory.create(name="Test Task")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert any(r.name == "Test Task" for r in result)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver.run_sync_async(root=None, info=mock_gql_info())

    assert any(r.name == "Test Task" for r in result)


@pytest.mark.django_db
def test_resolvers__interface_type_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    Query.named.permissions_func = permissions_func

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = TaskFactory.create(name="Test Task")

    resolver.check_permissions(info=mock_gql_info(), root=None, query_type=TaskType, instances=[task])

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__sync_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    called_with = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    Query.named.permissions_func = permissions_func

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    await resolver.check_permissions_async(info=mock_gql_info(), root=None, query_type=TaskType, instances=[task])

    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__async_func(undine_settings) -> None:
    undine_settings.ASYNC = True

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    Query.named.permissions_func = permissions_func

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_async(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__check_permissions_async__query_type_sync(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Test Task")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(
            info=mock_gql_info(),
            root=None,
            query_type=TaskType,
            instances=[task],
        )


def test_resolvers__typed_dict_field_resolver() -> None:
    resolver = TypedDictFieldResolver(key="my_key")
    result = resolver(root={"my_key": "value"}, info=mock_gql_info())
    assert result == "value"


def test_resolvers__typed_dict_field_resolver__missing_key() -> None:
    resolver = TypedDictFieldResolver(key="missing")
    result = resolver(root={"other": "value"}, info=mock_gql_info())
    assert result is None


def test_resolvers__named_tuple_field_resolver() -> None:
    Point = namedtuple("Point", ["x", "y"])  # noqa: PYI024
    point = Point(x=10, y=20)

    resolver = NamedTupleFieldResolver(attr="x")
    result = resolver(root=point, info=mock_gql_info())
    assert result == 10


def test_resolvers__named_tuple_field_resolver__missing_attr() -> None:
    resolver = NamedTupleFieldResolver(attr="z")
    result = resolver(root=object(), info=mock_gql_info())
    assert result is None


@pytest.mark.asyncio
async def test_resolvers__field_function_resolver__async__set_kwargs__info_only(undine_settings) -> None:
    undine_settings.ASYNC = True

    captured = []

    class TaskType(QueryType[Task]):
        @Field
        @staticmethod
        async def computed(info: GQLInfo) -> str:  # no root param
            captured.append(info)
            return "result"

    resolver = TaskType.computed.get_resolver()
    info = mock_gql_info()
    result = await resolver(root=None, info=info)

    assert result == "result"
    assert captured == [info]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_attribute_resolver__async__null_nullable(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        name = Field(nullable=True)

    resolver = ModelAttributeResolver(field=TaskType.name)

    task = await sync_to_async(TaskFactory.create)(name="Test")
    task.name = None  # type: ignore[assignment]

    result = await resolver.run_async(root=task, info=mock_gql_info())
    assert result is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field()

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    project = await sync_to_async(ProjectFactory.create)(name="Project")
    task = await sync_to_async(TaskFactory.create)(project=project)

    result = await resolver(root=task, info=mock_gql_info())
    assert result == project.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_single_related_field_resolver__async__not_nullable_null(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        project = Field(nullable=False)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_many_related_field_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")
    task = await sync_to_async(TaskFactory.create)(assignees=[assignee])

    instances = [assignee]
    with patch("undine.resolvers.query.ModelManyRelatedFieldResolver.get_instances", return_value=instances):
        result = await resolver(root=task, info=mock_gql_info())

    assert len(result) == 1
    assert result[0] == assignee.pk


@pytest.mark.django_db
def test_resolvers__model_many_related_field_resolver__check_permissions__no_func() -> None:
    class TaskType(QueryType[Task]):
        assignees = Field()

    resolver: ModelManyRelatedFieldResolver[Person] = ModelManyRelatedFieldResolver(field=TaskType.assignees)

    task = TaskFactory.create(assignees__name="Assignee")
    assignee = next(iter(task.assignees.all()))

    # No permissions_func: should be a no-op, returning normally
    resolver.check_permissions(root=task, info=mock_gql_info(), instances=[assignee])


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__model_generic_foreign_key_resolver__call__async(undine_settings) -> None:
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


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__query_type_single_resolver__async__check_permissions_async__async_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    called_with = []

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        called_with.append(instance)

    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    Query.task.permissions_func = permissions_func

    resolver: QueryTypeSingleResolver[Task] = QueryTypeSingleResolver(
        query_type=TaskType,
        entrypoint=Query.task,
    )

    task = await sync_to_async(TaskFactory.create)()

    with patch_optimizer():
        result = await resolver.run_async(root=None, info=mock_gql_info(), pk=task.pk)

    assert result == task
    assert called_with == [task]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project__name="Test project")

    result = await resolver(root=task, info=mock_gql_info())
    assert result == task.project


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_query_type_single_resolver__call__async__null_not_nullable(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType, nullable=False)

    resolver: NestedQueryTypeSingleResolver[Project] = NestedQueryTypeSingleResolver(
        query_type=ProjectType,
        field=TaskType.project,
    )

    task = await sync_to_async(TaskFactory.create)(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        await resolver(root=task, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
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


@pytest.mark.django_db
def test_resolvers__node_resolver__type_not_object_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename="SomeEnum", object_id=task.pk)

    # Patch schema.get_type to return an Enum (not a GraphQLObjectType)
    enum_type = GraphQLEnumType("SomeEnum", {"A": GraphQLEnumValue("A")})
    with (
        patch.object(undine_settings.SCHEMA, "get_type", return_value=enum_type),
        pytest.raises(GraphQLNodeTypeNotObjectTypeError),
    ):
        resolver(root=task, info=info, id=object_id)


@pytest.mark.django_db
def test_resolvers__node_resolver__id_field_wrong_type(undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    class Query(RootType):
        node = Entrypoint(Node)
        tasks = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create()

    resolver: NodeResolver[Task] = NodeResolver(entrypoint=Query.node)

    info = mock_gql_info(schema=undine_settings.SCHEMA)
    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    # Make the id field have a non-ID type by patching get_field_type
    id_field = TaskType.__field_map__["id"]
    with (
        patch.object(id_field, "get_field_type", return_value=GraphQLNonNull(GraphQLString)),
        pytest.raises(GraphQLNodeIDFieldTypeError),
    ):
        resolver(root=task, info=info, id=object_id)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    await sync_to_async(TaskFactory.create)()

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination):
        result = await resolver(root=None, info=mock_gql_info())

    assert isinstance(result, dict)
    assert "edges" in result


@pytest.mark.django_db
def test_resolvers__connection_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    task = TaskFactory.create()

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert called_with == [task]
    assert len(result["edges"]) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__check_permissions_async__sync_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    task = await sync_to_async(TaskFactory.create)()

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination):
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert called_with == [task]
    assert len(result["edges"]) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__check_permissions_async__async_permissions_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]): ...

    connection = Connection(TaskType)

    async def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:  # noqa: RUF029
        raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(connection)

    Query.tasks.permissions_func = permissions_func

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__connection_resolver__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(connection)

    resolver: ConnectionResolver[Task] = ConnectionResolver(connection=connection, entrypoint=Query.tasks)

    await sync_to_async(TaskFactory.create)()

    pagination = PaginationHandler(typename=TaskType.__schema_name__, first=10)
    with patch_optimizer(pagination=pagination), pytest.raises(GraphQLPermissionError):
        await resolver.run_async(root=None, info=mock_gql_info())


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    await sync_to_async(TaskFactory.create)(assignees__name="Test assignee")

    task: Task = await Task.objects.prefetch_related(  # type: ignore[assignment]
        Prefetch(
            "assignees",
            queryset=Person.objects.annotate(
                **{
                    undine_settings.PAGINATION_TOTAL_COUNT_KEY: Value(10),
                    undine_settings.PAGINATION_START_INDEX_KEY: Value(0),
                    undine_settings.PAGINATION_STOP_INDEX_KEY: Value(1),
                },
            ),
        ),
    ).afirst()

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    result = await resolver(root=task, info=mock_gql_info())
    assert isinstance(result, dict)
    assert "edges" in result
    assert len(result["edges"]) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_connection_resolver__check_permissions_async__sync_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    called_with: list[Any] = []

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            called_with.append(value)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])

    assert called_with == [assignee]


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_connection_resolver__check_permissions_async__async_func(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]): ...

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_connection_resolver__check_permissions_async__async_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]):
        @classmethod
        async def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__nested_connection_resolver__check_permissions_async__sync_query_type_permissions(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class PersonType(QueryType[Person], auto=False, interfaces=[Node]):
        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    connection = Connection(PersonType)

    class TaskType(QueryType[Task], auto=False, interfaces=[Node]):
        assignees = Field(connection)

    resolver: NestedConnectionResolver[Person] = NestedConnectionResolver(
        connection=connection, field=TaskType.assignees
    )

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee")

    with pytest.raises(GraphQLPermissionError):
        await resolver.check_permissions_async(root=None, info=mock_gql_info(), instances=[assignee])


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with (
        patch.object(UnionTypeResolver, "optimize", return_value={TaskType: task_qs}),
        patch("undine.resolvers.query.get_arguments", return_value={}),
    ):
        result = await resolver(root=None, info=mock_gql_info())

    assert len(result) == 1
    assert result[0].pk == task.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__async__fetch_instances_filter_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert result == []


@pytest.mark.django_db
def test_resolvers__union_type_resolver__filter_union__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with patch.object(SearchableFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


@pytest.mark.django_db
def test_resolvers__union_type_resolver__fetch_instances__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True, limit=1)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        result = resolver.fetch_instances(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__async__fetch_instances_order(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableOrderSet, "__build__", return_value=order_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__async__fetch_instances_with_limit(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True, limit=1)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    with patch("undine.resolvers.query.get_arguments", return_value={}):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__filter_union__none_early_return(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with patch.object(SearchableFilterSet, "__build__", return_value=none_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is True


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__filter_union__with_filters(undine_settings) -> None:

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[Q(pk__isnull=False)],
        aliases={},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__order_union__with_order_by(undine_settings) -> None:

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__run_sync__empty_connection(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    empty_result = QuerySetMapWithPagination(queryset_map={}, pagination=None)  # type: ignore[arg-type]

    with patch.object(UnionTypeConnectionResolver, "optimize", return_value=empty_result):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert result["totalCount"] == 0
    assert result["edges"] == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs},
        pagination=pagination,
    )

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(UnionTypeConnectionResolver, "optimize", return_value=result_with_pagination),
    ):
        result = await resolver(root=None, info=mock_gql_info())

    assert isinstance(result, dict)
    assert "edges" in result


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__fetch_instances__filter_none(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result = QuerySetMapWithPagination(queryset_map={TaskType: task_qs}, pagination=pagination)

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        instances = resolver.fetch_instances(root=None, info=mock_gql_info(), result=result)

    assert instances == []


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__fetch_instances__order(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = TaskFactory.create(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result = QuerySetMapWithPagination(queryset_map={TaskType: task_qs}, pagination=pagination)

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableOrderSet, "__build__", return_value=order_result),
    ):
        instances = resolver.fetch_instances(root=None, info=mock_gql_info(), result=result)

    assert len(instances) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__fetch_instances_async__filter_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result = QuerySetMapWithPagination(queryset_map={TaskType: task_qs}, pagination=pagination)

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        instances = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), result=result)

    assert instances == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__fetch_instances_async__order(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result = QuerySetMapWithPagination(queryset_map={TaskType: task_qs}, pagination=pagination)

    order_result = OrderResults(order_by=["pk"], aliases={})

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableOrderSet, "__build__", return_value=order_result),
    ):
        instances = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), result=result)

    assert len(instances) == 1


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__check_permissions__with_permissions_func(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    called_with: list[Any] = []

    def permissions_func(root: Any, info: GQLInfo, instance: Any) -> None:
        called_with.append(instance)

    class Query(RootType):
        searchable = Entrypoint(connection)

    Query.searchable.permissions_func = permissions_func

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = TaskFactory.create(name="Task 1")

    resolver.check_permissions(root=None, info=mock_gql_info(), query_type=TaskType, instances=[task])

    assert called_with == [task]


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__filter_union__with_aliases_distinct_filters(
    undine_settings,
) -> None:

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[Q(pk__isnull=False)],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__order_union__with_aliases_and_order_by(
    undine_settings,
) -> None:

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


@pytest.mark.django_db
def test_resolvers__interface_type_resolver__fetch_instances__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=1)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert len(result) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__fetch_instances_async__with_limit(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True, limit=1)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver.run_sync_async(root=None, info=mock_gql_info())

    assert len(result) == 1


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__run_sync(undine_settings) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    task = TaskFactory.create(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Named.__schema_name__, first=10)
    result_with_pagination = QuerySetMapWithPagination(
        queryset_map={TaskType: task_qs},
        pagination=pagination,
    )

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=result_with_pagination):
        result = resolver.run_sync(root=None, info=mock_gql_info())

    assert len(result["edges"]) == 1
    assert result["edges"][0]["node"].pk == task.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_connection_resolver__run_async__empty_connection(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    empty_result = QuerySetMapWithPagination(queryset_map={}, pagination=None)  # type: ignore[arg-type]

    with patch.object(InterfaceTypeConnectionResolver, "optimize", return_value=empty_result):
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result["totalCount"] == 0
    assert result["edges"] == []


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__optimize__with_filter_order_kwargs(
    undine_settings,
) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    TaskFactory.create(name="Task 1")

    # Pass filter and orderBy kwargs for the Task model to exercise lines 1728 and 1730
    filter_key = f"filter{Task.__name__}"
    order_key = f"orderBy{Task.__name__}"

    with patch_optimizer():
        result = resolver.optimize(
            info=mock_gql_info(),
            **{filter_key: {}, order_key: []},
        )

    # Should produce a non-empty queryset_map (Task is selected)
    assert result.queryset_map is not None


@pytest.mark.django_db
def test_resolvers__model_single_related_field_resolver__run_sync__not_nullable_null() -> None:
    class TaskType(QueryType[Task]):
        project = Field(nullable=False)

    resolver: ModelSingleRelatedFieldResolver[Project] = ModelSingleRelatedFieldResolver(field=TaskType.project)

    task = TaskFactory.create(project=None)

    with pytest.raises(GraphQLFieldNotNullableError):
        resolver.run_sync(root=task, info=mock_gql_info())


@pytest.mark.django_db
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


@pytest.mark.django_db
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


@pytest.mark.django_db
def test_resolvers__union_type_resolver__fetch_instances__filter_none_sync(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = TaskFactory.create(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    none_result = FilterResults(filters=[], aliases={}, distinct=False, none=True)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=none_result),
    ):
        result = resolver.fetch_instances(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert result == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_resolver__async__fetch_instances_filter_not_none(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=not_none_result),
    ):
        result = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), queryset_map=queryset_map)

    assert len(result) == 1
    assert result[0].pk == task.pk


@pytest.mark.django_db
def test_resolvers__union_type_resolver__filter_union__aliases_distinct_no_filters(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


@pytest.mark.django_db
def test_resolvers__union_type_resolver__order_union__aliases_and_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=["pk"], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == ["pk"]


@pytest.mark.django_db
def test_resolvers__union_type_resolver__order_union__aliases_no_order_by(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    class Query(RootType):
        searchable = Entrypoint(Searchable, many=True)

    resolver: UnionTypeResolver = UnionTypeResolver(
        union_type=Searchable,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__run_async__empty_connection(undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    empty_result = QuerySetMapWithPagination(queryset_map={}, pagination=None)  # type: ignore[arg-type]

    with patch.object(UnionTypeConnectionResolver, "optimize", return_value=empty_result):
        result = await resolver.run_async(root=None, info=mock_gql_info())

    assert result["totalCount"] == 0
    assert result["edges"] == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__union_type_connection_resolver__async__fetch_instances_filter_not_none(
    undine_settings,
) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))
    pagination = PaginationHandler(typename=Searchable.__schema_name__, first=10)
    result = QuerySetMapWithPagination(queryset_map={TaskType: task_qs}, pagination=pagination)

    not_none_result = FilterResults(filters=[], aliases={}, distinct=False, none=False)

    with (
        patch("undine.resolvers.query.get_arguments", return_value={}),
        patch.object(SearchableFilterSet, "__build__", return_value=not_none_result),
    ):
        instances = await resolver.fetch_instances_async(root=None, info=mock_gql_info(), result=result)

    assert len(instances) == 1
    assert instances[0].pk == task.pk


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__filter_union__aliases_distinct_no_filters(
    undine_settings,
) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableFilterSet(FilterSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], filterset=SearchableFilterSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    filter_result = FilterResults(
        filters=[],
        aliases={"__test_alias": Value(1)},
        distinct=True,
        none=False,
    )

    with patch.object(SearchableFilterSet, "__build__", return_value=filter_result):
        result = resolver.filter_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.none is False
    assert result.distinct is True


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__order_union__aliases_no_order_by(
    undine_settings,
) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class SearchableOrderSet(OrderSet[Task, Project], auto=False): ...

    class Searchable(UnionType[TaskType, ProjectType], orderset=SearchableOrderSet): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    task_qs = Task.objects.all().annotate(__typename=Value(TaskType.__schema_name__))
    queryset_map = {TaskType: task_qs}

    order_result = OrderResults(order_by=[], aliases={"__test_alias": Value(1)})

    with patch.object(SearchableOrderSet, "__build__", return_value=order_result):
        result = resolver.order_union(arg_values={}, info=mock_gql_info(), queryset_map=queryset_map)

    assert result.order_by == []


@pytest.mark.django_db
def test_resolvers__union_type_connection_resolver__optimize__empty_optimizations(undine_settings) -> None:
    undine_settings.ASYNC = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class Searchable(UnionType[TaskType, ProjectType]): ...

    connection = Connection(Searchable)

    class Query(RootType):
        searchable = Entrypoint(connection)

    resolver: UnionTypeConnectionResolver = UnionTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.searchable,
    )

    with patch_optimizer():
        result = resolver.optimize(info=mock_gql_info())

    assert result.queryset_map == {}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_resolvers__interface_type_resolver__call__async(undine_settings) -> None:
    undine_settings.ASYNC = True

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], auto=False, interfaces=[Named]):
        name = Field()

    class Query(RootType):
        named = Entrypoint(Named, many=True)

    resolver = InterfaceTypeResolver(interface=Named, entrypoint=Query.named)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")

    task_qs = Task.objects.filter(pk=task.pk).annotate(__typename=Value(TaskType.__schema_name__))

    with patch.object(InterfaceTypeResolver, "optimize", return_value={TaskType: task_qs}):
        result = await resolver(root=None, info=mock_gql_info())

    assert len(result) == 1
    assert result[0].pk == task.pk


@pytest.mark.django_db
def test_resolvers__interface_type_connection_resolver__optimize__filter_order_kwargs_non_empty(
    undine_settings,
) -> None:
    undine_settings.ASYNC = False

    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    class TaskType(QueryType[Task], interfaces=[Named], auto=False):
        name = Field()

    connection = Connection(Named)

    class Query(RootType):
        named = Entrypoint(connection)

    resolver: InterfaceTypeConnectionResolver = InterfaceTypeConnectionResolver(
        connection=connection,
        entrypoint=Query.named,
    )

    TaskFactory.create(name="Task 1")

    filter_key = f"filter{Task.__name__}"
    order_key = f"orderBy{Task.__name__}"

    with patch_optimizer(annotations={"__test_annotation__": Value("test")}):
        result = resolver.optimize(
            info=mock_gql_info(),
            **{filter_key: {}, order_key: []},
        )

    assert result.queryset_map is not None
