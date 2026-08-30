from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Person, Project, Task
from tests.factories import PersonFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

# Single


@pytest.mark.django_db
def test_nested_query_type__single(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": {"name": "Project 1"},
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": {"name": "Project 1"},
                },
            ],
        },
    }


@pytest.mark.django_db
def test_nested_query_type__single__null_nullable(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__null_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
    }


@pytest.mark.django_db
def test_nested_query_type__single__null_not_nullable(graphql, undine_settings) -> None:
    """'Task.project' is nullable in the database, so a non-nullable field can still resolve to null."""

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType, nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "'TaskType.project' returned null, but field is not nullable.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "FIELD_NOT_NULLABLE",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__null_not_nullable__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType, nullable=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project=None)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "'TaskType.project' returned null, but field is not nullable.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "FIELD_NOT_NULLABLE",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db
def test_nested_query_type__single__field_permissions(graphql, undine_settings) -> None:
    called_with: list[Any] = []

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Project) -> None:
            called_with.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": {"name": "Project 1"},
                },
            ],
        },
    }
    assert called_with == [task.project]


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__field_permissions__async(graphql_async, undine_settings) -> None:
    """A sync permission hook still runs on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    called_with: list[Any] = []

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Project) -> None:
            called_with.append(value)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": {"name": "Project 1"},
                },
            ],
        },
    }
    assert called_with == [task.project]


@pytest.mark.django_db
def test_nested_query_type__single__field_permissions__denied(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Project) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__field_permissions__denied__async(graphql_async, undine_settings) -> None:
    """An 'async def' permission hook is awaited on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.permissions
        async def project_permissions(self, info: GQLInfo, value: Project) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db
def test_nested_query_type__single__query_type_permissions(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__query_type_permissions__async(graphql_async, undine_settings) -> None:
    """An 'async def' '__permissions__' is awaited on the async resolver path."""
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

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__single__query_type_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    """A sync '__permissions__' still runs on the async resolver path."""
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

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": None,
                },
            ],
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "project"],
            },
        ],
    }


@pytest.mark.django_db
def test_nested_query_type__single__field_permissions_replace_query_type_permissions(graphql, undine_settings) -> None:
    """A field level permission hook replaces the query type's '__permissions__'."""

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

        @project.permissions
        def project_permissions(self, info: GQLInfo, value: Project) -> None:
            return

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", project__name="Project 1")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "project": {"name": "Project 1"},
                },
            ],
        },
    }


# Many


@pytest.mark.django_db
def test_nested_query_type__many(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [{"name": "Person 1"}],
                },
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__many__async(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [{"name": "Person 1"}],
                },
            ],
        },
    }


@pytest.mark.django_db
def test_nested_query_type__many__empty(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees=[])

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [],
                },
            ],
        },
    }


@pytest.mark.django_db
def test_nested_query_type__many__aliased(graphql, undine_settings) -> None:
    """An aliased field is prefetched to the alias, so the resolver reads a list instead of a manager."""

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            people: assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "people": [{"name": "Person 1"}],
                },
            ],
        },
    }


@pytest.mark.django_db
def test_nested_query_type__many__field_permissions(graphql, undine_settings) -> None:
    called_with: list[Any] = []

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Person) -> None:
            called_with.append(value.name)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="Person 1")
    person_2 = PersonFactory.create(name="Person 2")
    TaskFactory.create(name="Task 1", assignees=[person_1, person_2])

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [{"name": "Person 1"}, {"name": "Person 2"}],
                },
            ],
        },
    }
    assert called_with == ["Person 1", "Person 2"]


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__many__field_permissions__async(graphql_async, undine_settings) -> None:
    """A sync permission hook still runs on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    called_with: list[Any] = []

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Person) -> None:
            called_with.append(value.name)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = await sync_to_async(PersonFactory.create)(name="Person 1")
    await sync_to_async(TaskFactory.create)(name="Task 1", assignees=[person])

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [{"name": "Person 1"}],
                },
            ],
        },
    }
    assert called_with == ["Person 1"]


@pytest.mark.django_db
def test_nested_query_type__many__field_permissions__denied(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Person) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "assignees"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__many__field_permissions__denied__async(graphql_async, undine_settings) -> None:
    """An 'async def' permission hook is awaited on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

        @assignees.permissions
        async def assignees_permissions(self, info: GQLInfo, value: Person) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "assignees"],
            },
        ],
    }


@pytest.mark.django_db
def test_nested_query_type__many__query_type_permissions(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "assignees"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__many__query_type_permissions__async(graphql_async, undine_settings) -> None:
    """An 'async def' '__permissions__' is awaited on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class PersonType(QueryType[Person], auto=False):
        name = Field()

        @classmethod
        async def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "assignees"],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
async def test_nested_query_type__many__query_type_permissions__sync_func__async(
    graphql_async,
    undine_settings,
) -> None:
    """A sync '__permissions__' still runs on the async resolver path."""
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class PersonType(QueryType[Person], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    await sync_to_async(TaskFactory.create)(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = await graphql_async(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["tasks", 0, "assignees"],
            },
        ],
    }


@pytest.mark.django_db
def test_nested_query_type__many__field_permissions_replace_query_type_permissions(graphql, undine_settings) -> None:
    """A field level permission hook replaces the query type's '__permissions__'."""

    class PersonType(QueryType[Person], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Person, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

        @assignees.permissions
        def assignees_permissions(self, info: GQLInfo, value: Person) -> None:
            return

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Task 1", assignees__name="Person 1")

    query = """
        query {
          tasks {
            name
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Task 1",
                    "assignees": [{"name": "Person 1"}],
                },
            ],
        },
    }
