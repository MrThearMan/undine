from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Comment, Project, Task, TaskTypeChoices
from tests.factories import CommentFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

# Model attribute


@pytest.mark.django_db
def test_query_model_fields__attribute(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", points=10)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "points": 10}]}


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__attribute__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", points=10)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "points": 10}]}


@pytest.mark.django_db
def test_query_model_fields__attribute__null_nullable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", points=None)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "points": None}]}


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__attribute__null_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", points=None)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "points": None}]}


@pytest.mark.django_db
def test_query_model_fields__attribute__null_not_nullable(graphql, undine_settings) -> None:
    """A field declared non-nullable whose model value is null must not resolve to null."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field(nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", points=None)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is True
    assert response.error_message(0) == "'TaskType.points' returned null, but field is not nullable."


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__attribute__null_not_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        points = Field(nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", points=None)

    query = """
        query {
          tasks {
            name
            points
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "'TaskType.points' returned null, but field is not nullable."


@pytest.mark.django_db
def test_query_model_fields__attribute__field_permissions(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self: Task, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1")

    query = """
        query {
          tasks {
            name
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is True
    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__attribute__field_permissions__async_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        async def name_permissions(self: Task, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    query = """
        query {
          tasks {
            name
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__attribute__field_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    """A plain `def` permissions hook still runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    checked: list[str] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self: Task, info: GQLInfo, value: str) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1")

    query = """
        query {
          tasks {
            name
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1"}]}
    assert checked == ["Task 1"]


# Generic foreign key


@pytest.mark.django_db
def test_query_model_fields__generic_foreign_key(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1")
    project = ProjectFactory.create(name="Project 1")
    CommentFactory.create(contents="Comment 1", target=task)
    CommentFactory.create(contents="Comment 2", target=project)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {"contents": "Comment 1", "target": {"name": "Task 1"}},
            {"contents": "Comment 2", "target": {"name": "Project 1"}},
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__generic_foreign_key__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(CommentFactory.create)(contents="Comment 1", target=task)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"comments": [{"contents": "Comment 1", "target": {"name": "Task 1"}}]}


@pytest.mark.django_db
def test_query_model_fields__generic_foreign_key__null(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    CommentFactory.create(contents="Comment 1", target=None)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"comments": [{"contents": "Comment 1", "target": None}]}


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__generic_foreign_key__null__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(CommentFactory.create)(contents="Comment 1", target=None)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"comments": [{"contents": "Comment 1", "target": None}]}


@pytest.mark.django_db
def test_query_model_fields__generic_foreign_key__field_permissions(graphql, undine_settings) -> None:
    """The permissions hook receives the resolved target instance, not its primary key."""
    checked: list[Any] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

        @target.permissions
        def target_permissions(self: Comment, info: GQLInfo, value: Any) -> None:
            checked.append(value)

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1", type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="Comment 1", target=task)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"comments": [{"contents": "Comment 1", "target": {"name": "Task 1"}}]}
    assert checked == [task]


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__generic_foreign_key__field_permissions__async_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

        @target.permissions
        async def target_permissions(self: Comment, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(CommentFactory.create)(contents="Comment 1", target=task)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "Permission denied."


@pytest.mark.django_db(transaction=True)
async def test_query_model_fields__generic_foreign_key__field_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    checked: list[Any] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

        @target.permissions
        def target_permissions(self: Comment, info: GQLInfo, value: Any) -> None:
            checked.append(value)

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1")
    await sync_to_async(CommentFactory.create)(contents="Comment 1", target=task)

    query = """
        query {
          comments {
            contents
            target {
              ... on TaskType {
                name
              }
              ... on ProjectType {
                name
              }
            }
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"comments": [{"contents": "Comment 1", "target": {"name": "Task 1"}}]}
    assert checked == [task]
