from __future__ import annotations

import pytest

from example_project.app.models import ServiceRequest, Task, TaskStep
from tests.factories import TaskFactory, TaskStepFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

# Entrypoint


@pytest.mark.django_db
def test_end_to_end__query__entrypoint__permission_error(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.permissions
        def entry_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                ],
            },
        ],
    }


    response.assert_query_count(1)


# Single


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error__nested__single(graphql, undine_settings) -> None:
    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
            request {
              details
            }
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": {
            "task": {
                "name": "Test task",
                "request": None,
            },
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                    "request",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error__nested__many(graphql, undine_settings) -> None:
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")
    TaskStepFactory.create(name="Test person 1", task=task)
    TaskStepFactory.create(name="Test person 2", task=task)

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
            steps {
              name
            }
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                    "steps",
                ],
            },
        ],
    }


    response.assert_query_count(2)


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error__field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                    "name",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error__field__nested__single(graphql, undine_settings) -> None:
    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

        @details.permissions
        def details_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
            request {
              details
            }
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": {
            "task": {
                "name": "Test task",
                "request": None,
            }
        },
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                    "request",
                    "details",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__single__permission_error__field__nested__many(graphql, undine_settings) -> None:
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @name.permissions
        def name_permission(self, info: GQLInfo, value: str):
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    class Query(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="Test task")
    TaskStepFactory.create(name="Test request 1", task=task)
    TaskStepFactory.create(name="Test request 2", task=task)

    query = """
        query($pk: Int!) {
          task(pk: $pk) {
            name
            steps {
              name
            }
          }
        }
    """

    response = graphql(query, variables={"pk": task.pk})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "task",
                    "steps",
                    0,
                    "name",
                ],
            },
        ],
    }


    response.assert_query_count(2)


# Many


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Test task 1")
    TaskFactory.create(name="Test task 2")

    query = """
        query {
          tasks {
            name
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
                "path": [
                    "tasks",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error__nested__single(graphql, undine_settings) -> None:
    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Test task 1", request__details="Test request 1")
    TaskFactory.create(name="Test task 2", request__details="Test request 2")

    query = """
        query {
          tasks {
            name
            request {
              details
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Test task 1",
                    "request": None,
                },
                {
                    "name": "Test task 2",
                    "request": None,
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
                "path": [
                    "tasks",
                    0,
                    "request",
                ],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "tasks",
                    1,
                    "request",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error__nested__many(graphql, undine_settings) -> None:
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Test task 1")
    task_2 = TaskFactory.create(name="Test task 2")

    TaskStepFactory.create(name="Test step 1", task=task_1)
    TaskStepFactory.create(name="Test step 2", task=task_1)
    TaskStepFactory.create(name="Test step 3", task=task_2)
    TaskStepFactory.create(name="Test step 4", task=task_2)

    query = """
        query {
          tasks {
            name
            steps {
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
                "path": [
                    "tasks",
                    0,
                    "steps",
                ],
            },
        ],
    }


    response.assert_query_count(2)


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error__field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Test task 1")
    TaskFactory.create(name="Test task 2")

    query = """
        query {
          tasks {
            name
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
                "path": [
                    "tasks",
                    0,
                    "name",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error__field__nested__single(graphql, undine_settings) -> None:
    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

        @details.permissions
        def details_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="Test task 1", request__details="Test request 1")
    TaskFactory.create(name="Test task 2", request__details="Test request 2")

    query = """
        query {
          tasks {
            name
            request {
              details
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": {
            "tasks": [
                {
                    "name": "Test task 1",
                    "request": None,
                },
                {
                    "name": "Test task 2",
                    "request": None,
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
                "path": [
                    "tasks",
                    0,
                    "request",
                    "details",
                ],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": [
                    "tasks",
                    1,
                    "request",
                    "details",
                ],
            },
        ],
    }


    response.assert_query_count(1)


@pytest.mark.django_db
def test_end_to_end__query__many__permission_error__field__nested__many(graphql, undine_settings) -> None:
    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str):
            raise GraphQLPermissionError

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="Test task")
    task_2 = TaskFactory.create(name="Test task")

    TaskStepFactory.create(name="Test step 1", task=task_1)
    TaskStepFactory.create(name="Test step 2", task=task_1)
    TaskStepFactory.create(name="Test step 3", task=task_2)
    TaskStepFactory.create(name="Test step 4", task=task_2)

    query = """
        query {
          tasks {
            name
            steps {
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
                "path": [
                    "tasks",
                    0,
                    "steps",
                    0,
                    "name",
                ],
            },
        ],
    }


    response.assert_query_count(2)
