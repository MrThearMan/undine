from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, MutationType, QueryType, RootType, create_schema


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
                "error_code": "MODEL_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["deleteTask"],
        }
    ]
