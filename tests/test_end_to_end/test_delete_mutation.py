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
