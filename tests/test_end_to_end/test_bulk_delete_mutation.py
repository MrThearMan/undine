from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_bulk_delete_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": task_2.pk},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTasks": [
            {"pk": task_1.pk},
            {"pk": task_2.pk},
        ],
    }


@pytest.mark.django_db
def test_bulk_delete_mutation__missing_instances(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": -1},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": "Expected 2 instances to delete, but found 1.",
            "extensions": {
                "error_code": "MISSING_INSTANCES_TO_DELETE",
                "status_code": 400,
            },
            "path": ["deleteTasks"],
        }
    ]
