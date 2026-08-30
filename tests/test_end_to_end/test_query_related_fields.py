from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Person, Project, Task
from tests.factories import PersonFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError


@pytest.mark.django_db
def test_query_related_fields__single_related_pk(graphql, undine_settings) -> None:
    """A to-one field without a nested query type resolves to the related object's primary key."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1", project__name="Project 1")
    project = task.project
    assert project is not None

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": project.pk}]}


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__single_related_pk__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")
    project = await sync_to_async(lambda: task.project)()
    assert project is not None

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": project.pk}]}


@pytest.mark.django_db
def test_query_related_fields__single_related_pk__null_not_nullable(graphql, undine_settings) -> None:
    """A non-nullable to-one field whose relation is null must not resolve to null."""

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is True
    assert response.error_message(0) == "'TaskType.project' returned null, but field is not nullable."


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__single_related_pk__null_not_nullable__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "'TaskType.project' returned null, but field is not nullable."


@pytest.mark.django_db
def test_query_related_fields__single_related_pk__null_nullable(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": None}]}


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__single_related_pk__null_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": None}]}


@pytest.mark.django_db
def test_query_related_fields__single_related_pk__field_permissions(graphql, undine_settings) -> None:
    checked: list[Project] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

        @project.permissions
        def project_permissions(self: Task, info: GQLInfo, value: Project) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1", project__name="Project 1")
    project = task.project
    assert project is not None

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": project.pk}]}
    # The permissions hook sees the related instance, while the field resolves to its primary key.
    assert checked == [project]


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__single_related_pk__field_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    """A plain `def` permissions hook still runs on the async path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    checked: list[Project] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

        @project.permissions
        def project_permissions(self: Task, info: GQLInfo, value: Project) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")
    project = await sync_to_async(lambda: task.project)()
    assert project is not None

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "project": project.pk}]}
    assert checked == [project]


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__single_related_pk__field_permissions__async_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field()

        @project.permissions
        async def project_permissions(self: Task, info: GQLInfo, value: Project) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "Permission denied."


# Many-related fields resolved to a list of primary keys


@pytest.mark.django_db
def test_query_related_fields__many_related_pks(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee_1 = PersonFactory.create(name="Assignee 1")
    assignee_2 = PersonFactory.create(name="Assignee 2")
    TaskFactory.create(name="Task 1", assignees=[assignee_1, assignee_2])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "assignees": [assignee_1.pk, assignee_2.pk]}]}


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__many_related_pks__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", assignees=[assignee])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "assignees": [assignee.pk]}]}


@pytest.mark.django_db
def test_query_related_fields__many_related_pks__empty(graphql, undine_settings) -> None:
    """A task with no assignees resolves to an empty list, and the permissions hook is never called."""
    checked: list[Person] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self: Task, info: GQLInfo, value: Person) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees=[])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "assignees": []}]}
    assert checked == []


@pytest.mark.django_db
def test_query_related_fields__many_related_pks__field_permissions(graphql, undine_settings) -> None:
    """The permissions hook is called once per related instance, and sees instances, not primary keys."""
    checked: list[Person] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self: Task, info: GQLInfo, value: Person) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee_1 = PersonFactory.create(name="Assignee 1")
    assignee_2 = PersonFactory.create(name="Assignee 2")
    TaskFactory.create(name="Task 1", assignees=[assignee_1, assignee_2])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "assignees": [assignee_1.pk, assignee_2.pk]}]}
    assert checked == [assignee_1, assignee_2]


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__many_related_pks__field_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    checked: list[Person] = []

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

        @assignees.permissions
        def assignees_permissions(self: Task, info: GQLInfo, value: Person) -> None:
            checked.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", assignees=[assignee])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = await graphql_async(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "Task 1", "assignees": [assignee.pk]}]}
    assert checked == [assignee]


@pytest.mark.django_db(transaction=True)
async def test_query_related_fields__many_related_pks__field_permissions__async_func__async(
    graphql_async,
    undine_settings,
) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field()

        @assignees.permissions
        async def assignees_permissions(self: Task, info: GQLInfo, value: Person) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    assignee = await sync_to_async(PersonFactory.create)(name="Assignee 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", assignees=[assignee])

    query = """
        query {
          tasks {
            name
            assignees
          }
        }
    """

    response = await graphql_async(query)

    assert response.has_errors is True
    assert response.error_message(0) == "Permission denied."
