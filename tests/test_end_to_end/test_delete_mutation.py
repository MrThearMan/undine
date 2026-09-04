from __future__ import annotations

from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Input, MutationType, QueryType, RootType, create_schema
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_delete_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
    }
    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTask": {
            "pk": task.pk,
        },
    }

    assert Task.objects.count() == 0


@pytest.mark.django_db(transaction=True)
async def test_delete_mutation__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)()

    data = {
        "pk": task.pk,
    }
    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTask": {
            "pk": task.pk,
        },
    }

    assert (await Task.objects.acount()) == 0


@pytest.mark.django_db
def test_delete_mutation__instance_not_found(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    TaskFactory.create()

    data = {
        "pk": -1,
    }
    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": "Primary key -1 on model 'example_project.app.models.Task' did not match any row.",
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["deleteTask"],
        }
    ]

    assert Task.objects.count() == 1


@pytest.mark.django_db
def test_delete_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    first_task = TaskFactory.create()
    second_task = TaskFactory.create()

    query = """
        mutation($firstInput: TaskDeleteMutation! $secondInput: TaskDeleteMutation!) {
            first: deleteTask(input: $firstInput) {
                pk
            }
            second: deleteTask(input: $secondInput) {
                pk
            }
        }
    """
    variables = {
        "firstInput": {"pk": first_task.pk},
        "secondInput": {"pk": second_task.pk},
    }

    response = graphql(query, variables=variables)

    assert response.errors == [
        {
            "message": "Cannot mutate more than 1 objects in a single request (counted 2).",
            "extensions": {
                "error_code": "MUTATION_TOO_MANY_OBJECTS",
                "status_code": 400,
            },
            "path": ["second"],
        }
    ]

    assert list(Task.objects.values_list("pk", flat=True)) == [second_task.pk]


@pytest.mark.django_db
def test_delete_mutation__missing_lookup_field(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
        pk = Input(required=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": {}})

    assert response.errors == [
        {
            "message": (
                "Input data is missing value for the mutation lookup field 'pk'. "
                "Cannot fetch 'example_project.app.models.Task' object for mutation."
            ),
            "path": ["deleteTask"],
            "extensions": {
                "status_code": 400,
                "error_code": "LOOKUP_VALUE_MISSING",
            },
        }
    ]

    assert Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db(transaction=True)
async def test_delete_mutation__missing_lookup_field__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
        pk = Input(required=False)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = await sync_to_async(TaskFactory.create)()

    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": {}})

    assert response.errors == [
        {
            "message": (
                "Input data is missing value for the mutation lookup field 'pk'. "
                "Cannot fetch 'example_project.app.models.Task' object for mutation."
            ),
            "path": ["deleteTask"],
            "extensions": {
                "status_code": 400,
                "error_code": "LOOKUP_VALUE_MISSING",
            },
        }
    ]

    assert await Task.objects.filter(pk=task.pk).aexists()


@pytest.mark.django_db
def test_delete_mutation__hooks__call_order(graphql, undine_settings):
    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
        pk = Input()

        @pk.validate
        def _(self: Task, info: GQLInfo, value: int) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @pk.permissions
        def _(self: Task, info: GQLInfo, value: int) -> None:
            nonlocal input_permission_called
            input_permission_called = next(counter)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal permission_called
            permission_called = next(counter)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_task = Entrypoint(TaskDeleteMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
    }
    query = """
        mutation($input: TaskDeleteMutation!) {
            deleteTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTask": {
            "pk": task.pk,
        },
    }

    assert Task.objects.count() == 0

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4
