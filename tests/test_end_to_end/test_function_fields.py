from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLResolveInfo

from example_project.app.models import Project, Task
from tests.conftest import skip_if_async
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

PERMISSION_DENIED_ERROR = {
    "message": "Permission denied.",
    "extensions": {
        "status_code": 403,
        "error_code": "PERMISSION_DENIED",
    },
}


# Entrypoint functions: signature adaptation


@pytest.mark.django_db
def test_function_fields__entrypoint(graphql, undine_settings) -> None:
    """A function `Entrypoint` that takes no parameters at all is resolved by calling it."""

    class Query(RootType):
        @Entrypoint
        def greeting() -> str:
            return "Hello"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {"data": {"greeting": "Hello"}}


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint
        async def greeting() -> str:
            return "Hello"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { greeting }")

    assert response.json == {"data": {"greeting": "Hello"}}


@pytest.mark.django_db
def test_function_fields__entrypoint__root_and_info(graphql, undine_settings) -> None:
    """A function `Entrypoint` receives the root value and the resolve info when it asks for them."""

    class Query(RootType):
        @Entrypoint
        def greeting(root: Any, info: GQLInfo) -> str:
            return f"{root!r} {info.field_name}"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {"data": {"greeting": "None greeting"}}


@pytest.mark.django_db
def test_function_fields__entrypoint__self_as_root(graphql, undine_settings) -> None:
    """A first parameter named `self` is the root value."""

    class Query(RootType):
        @Entrypoint
        def greeting(self) -> str:
            return f"{self!r}"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {"data": {"greeting": "None"}}


@pytest.mark.django_db
def test_function_fields__entrypoint__cls_as_root(graphql, undine_settings) -> None:
    """A first parameter named `cls` is the root value."""

    class Query(RootType):
        @Entrypoint
        def greeting(cls) -> str:  # noqa: N805
            return f"{cls!r}"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {"data": {"greeting": "None"}}


@pytest.mark.django_db
def test_function_fields__entrypoint__graphql_resolve_info(graphql, undine_settings) -> None:
    """The info parameter can also be annotated with graphql-core's `GraphQLResolveInfo`."""

    class Query(RootType):
        @Entrypoint
        def greeting(info: GraphQLResolveInfo) -> str:  # noqa: N805
            return info.field_name

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {"data": {"greeting": "greeting"}}


# Entrypoint functions: permissions


@pytest.mark.django_db
def test_function_fields__entrypoint__permissions(graphql, undine_settings) -> None:
    """The permission check of a function `Entrypoint` receives the resolved value."""

    class Query(RootType):
        @Entrypoint
        def greeting() -> str:
            return "Hello"

        @greeting.permissions
        def greeting_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Hello":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql("query { greeting }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["greeting"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__permissions__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint
        async def greeting() -> str:
            return "Hello"

        @greeting.permissions
        async def greeting_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Hello":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { greeting }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["greeting"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__permissions__sync_permissions__async(
    graphql_async,
    undine_settings,
) -> None:
    """An async function `Entrypoint` may have a synchronous permission check."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint
        async def greeting() -> str:
            return "Hello"

        @greeting.permissions
        def greeting_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Hello":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { greeting }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["greeting"]}],
    }


@pytest.mark.django_db
def test_function_fields__entrypoint__permissions__many(graphql, undine_settings) -> None:
    """For a list `Entrypoint`, the permission check runs once per item in the list."""

    class Query(RootType):
        @Entrypoint(many=True)
        def greetings(language: str) -> list[str]:  # noqa: N805
            return ["Hello", "Hi"] if language == "en" else ["Hei", "Moi"]

        @greetings.permissions
        def greetings_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Moi":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          allowed: greetings(language: "en")
          denied: greetings(language: "fi")
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["denied"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__permissions__many__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint(many=True)
        async def greetings(language: str) -> list[str]:  # noqa: N805
            return ["Hello", "Hi"] if language == "en" else ["Hei", "Moi"]

        @greetings.permissions
        async def greetings_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Moi":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          allowed: greetings(language: "en")
          denied: greetings(language: "fi")
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["denied"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__permissions__many__sync_permissions__async(
    graphql_async,
    undine_settings,
) -> None:
    """An async list `Entrypoint` may have a synchronous per-item permission check."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class Query(RootType):
        @Entrypoint(many=True)
        async def greetings() -> list[str]:
            return ["Hello", "Goodbye"]

        @greetings.permissions
        def greetings_permissions(self, info: GQLInfo, value: str) -> None:
            if value == "Goodbye":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    response = await graphql_async("query { greetings }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["greetings"]}],
    }


@pytest.mark.django_db
@skip_if_async
def test_function_fields__entrypoint__query_type_permissions(graphql, undine_settings) -> None:
    """Without a permission check of its own, a custom resolver falls back to the QueryType's permissions."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        def resolve_task(self, info: GQLInfo) -> Task | None:
            return Task.objects.first()

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql("query { task { name } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["task"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__entrypoint__query_type_permissions__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        async def resolve_task(self, info: GQLInfo) -> Task | None:
            return await Task.objects.afirst()

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async("query { task { name } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["task"]}],
    }


# Field functions: signature adaptation


@pytest.mark.django_db
def test_function_fields__field(graphql, undine_settings) -> None:
    """A function `Field` receives the model instance as its root value."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def shout(self: Task) -> str:
            return self.name.upper()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql("query { tasks { name shout } }")

    assert response.json == {"data": {"tasks": [{"name": "Task 1", "shout": "TASK 1"}]}}


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def shout(self: Task) -> str:
            return self.name.upper()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async("query { tasks { name shout } }")

    assert response.json == {"data": {"tasks": [{"name": "Task 1", "shout": "TASK 1"}]}}


@pytest.mark.django_db
def test_function_fields__field__info_only(graphql, undine_settings) -> None:
    """A function `Field` that only asks for the resolve info does not receive the model instance."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def field_name(info: GQLInfo) -> str:  # noqa: N805
            return info.field_name

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql("query { tasks { name fieldName } }")

    assert response.json == {"data": {"tasks": [{"name": "Task 1", "fieldName": "fieldName"}]}}


# Field functions: permissions


@pytest.mark.django_db
def test_function_fields__field__permissions(graphql, undine_settings) -> None:
    """The permission check of a function `Field` receives the resolved value."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def shout(self: Task) -> str:
            return self.name.upper()

        @shout.permissions
        def shout_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "TASK 1":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    response = graphql("query { tasks { name shout } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "shout"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__permissions__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def shout(self: Task) -> str:
            return self.name.upper()

        @shout.permissions
        async def shout_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "TASK 1":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async("query { tasks { name shout } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "shout"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__permissions__sync_permissions__async(graphql_async, undine_settings) -> None:
    """An async function `Field` may have a synchronous permission check."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        async def shout(self: Task) -> str:
            return self.name.upper()

        @shout.permissions
        def shout_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "TASK 1":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    response = await graphql_async("query { tasks { name shout } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "shout"]}],
    }


@pytest.mark.django_db
def test_function_fields__field__permissions__many(graphql, undine_settings) -> None:
    """For a list `Field`, the permission check runs once per item in the list."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(many=True)
        def tags(self: Task) -> list[str]:
            return [self.name, "common"]

        @tags.permissions
        def tags_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "Task 2":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    response = graphql("query { tasks { name tags } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 1, "tags"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__permissions__many__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(many=True)
        async def tags(self: Task) -> list[str]:
            return [self.name, "common"]

        @tags.permissions
        async def tags_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "Task 2":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async("query { tasks { name tags } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 1, "tags"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__permissions__many__sync_permissions__async(
    graphql_async,
    undine_settings,
) -> None:
    """An async list `Field` may have a synchronous per-item permission check."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(many=True)
        async def tags(self: Task) -> list[str]:
            return [self.name, "common"]

        @tags.permissions
        def tags_permissions(self: Task, info: GQLInfo, value: str) -> None:
            if value == "Task 2":
                raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(TaskFactory.create)(name="Task 2")

    response = await graphql_async("query { tasks { name tags } }")

    assert response.json == {
        "data": None,
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 1, "tags"]}],
    }


@pytest.mark.django_db
def test_function_fields__field__query_type_permissions(graphql, undine_settings) -> None:
    """Without a permission check of its own, a custom resolver falls back to the QueryType's permissions."""

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.resolve
        def resolve_project(self: Task, info: GQLInfo) -> Project | None:
            return self.project

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1")

    response = graphql("query { tasks { name project { name } } }")

    assert response.json == {
        "data": {"tasks": [{"name": "Task 1", "project": None}]},
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "project"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__query_type_permissions__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self: Task, info: GQLInfo) -> Project | None:
            return await Project.objects.afirst()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = await sync_to_async(ProjectFactory.create)(name="Project 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", project=project)

    response = await graphql_async("query { tasks { name project { name } } }")

    assert response.json == {
        "data": {"tasks": [{"name": "Task 1", "project": None}]},
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "project"]}],
    }


@pytest.mark.django_db(transaction=True)
async def test_function_fields__field__query_type_permissions__sync_permissions__async(
    graphql_async,
    undine_settings,
) -> None:
    """A QueryType reached through an async custom resolver may have synchronous permissions."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.resolve
        async def resolve_project(self: Task, info: GQLInfo) -> Project | None:
            return await Project.objects.afirst()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = await sync_to_async(ProjectFactory.create)(name="Project 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", project=project)

    response = await graphql_async("query { tasks { name project { name } } }")

    assert response.json == {
        "data": {"tasks": [{"name": "Task 1", "project": None}]},
        "errors": [PERMISSION_DENIED_ERROR | {"path": ["tasks", 0, "project"]}],
    }


# Structured return values


class Coordinates(NamedTuple):
    x: int
    y: int


class Metadata(TypedDict):
    kind: str
    weight: int


@pytest.mark.django_db
@skip_if_async
def test_function_fields__named_tuple_return_value(graphql, undine_settings) -> None:
    """A function `Field` returning a named tuple becomes an object type resolved by attribute access."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def coordinates(self: Task) -> Coordinates:
            return Coordinates(x=self.points, y=self.points * 2)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", points=3)

    response = graphql("query { tasks { name coordinates { x y } } }")

    assert response.json == {"data": {"tasks": [{"name": "Task 1", "coordinates": {"x": 3, "y": 6}}]}}


@pytest.mark.django_db
@skip_if_async
def test_function_fields__typed_dict_return_value(graphql, undine_settings) -> None:
    """A function `Field` returning a typed dict becomes an object type resolved by key access."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field
        def metadata(self: Task) -> Metadata:
            return Metadata(kind="task", weight=self.points)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", points=3)

    response = graphql("query { tasks { name metadata { kind weight } } }")

    assert response.json == {"data": {"tasks": [{"name": "Task 1", "metadata": {"kind": "task", "weight": 3}}]}}
