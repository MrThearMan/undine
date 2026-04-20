from __future__ import annotations

from typing import TypedDict

import pytest
from django.db.models import QuerySet

from example_project.app.models import Task, TaskTypeChoices
from tests.conftest import skip_if_async
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
@skip_if_async
def test_optimizer__mutation__custom(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        @Entrypoint
        def delete_task(self, info: GQLInfo, *, pk: int) -> bool:
            Task.objects.filter(pk=pk).delete()
            return True

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="to-delete")

    query = "mutation ($pk: Int!) { deleteTask(pk: $pk) }"
    response = graphql(query, variables={"pk": task.pk})

    assert response.has_errors is False, response.errors
    assert response.data == {"deleteTask": True}


@pytest.mark.django_db
def test_optimizer__mutation__query_type_output(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        task = Entrypoint(TaskType)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="test-task")

    query = "mutation ($pk: Int!) { task(pk: $pk) { name } }"
    response = graphql(query, variables={"pk": task.pk})

    assert response.has_errors is False, response.errors
    assert response.data == {"task": {"name": "test-task"}}


@pytest.mark.django_db
def test_optimizer__mutation__filter_queryset(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset.filter(done=False)

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="active", done=False)

    query = "mutation ($input: TaskUpdateMutation!) { updateTask(input: $input) { name } }"
    response = graphql(query, variables={"input": {"pk": task.pk, "name": "renamed"}})

    assert response.has_errors is False, response.errors
    assert response.data == {"updateTask": {"name": "renamed"}}


@pytest.mark.django_db
@skip_if_async
def test_optimizer__mutation__input_not_mutation_type(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    class TaskInput(TypedDict):
        name: str

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        @Entrypoint
        def create_task(self, info: GQLInfo, *, input: TaskInput) -> int:  # noqa: A002
            task = TaskFactory.create(name=input["name"], type=TaskTypeChoices.TASK.value)
            return task.pk

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = 'mutation { createTask(input: { name: "New Task" }) }'
    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data["createTask"] is not None
