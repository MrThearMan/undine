from __future__ import annotations

import asyncio

import pytest
from asgiref.sync import sync_to_async
from django import db

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import DataLoader, Entrypoint, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLModelNotFoundError
from undine.utils.text import dotpath


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__success(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    resolves = 0
    loads = 0

    async def load_tasks(keys: list[int]) -> list[Task]:
        nonlocal loads
        loads += 1
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            nonlocal resolves
            resolves += 1
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pkOne: Int!, $pkTwo: Int!) {
            taskOne: task(pk: $pkOne) {
                name
            }
            taskTwo: task(pk: $pkTwo) {
                name
            }
        }
    """

    task_one = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_two = await sync_to_async(TaskFactory.create)(name="Task 2")

    result = await graphql_async(query, variables={"pkOne": task_one.pk, "pkTwo": task_two.pk})

    assert result.has_errors is False, result.errors

    assert result.data == {
        "taskOne": {"name": "Task 1"},
        "taskTwo": {"name": "Task 2"},
    }

    # The task resolver was called twice, but dataloader executed only once
    assert resolves == 2
    assert loads == 1

    # Loads were emptied after the request
    assert loader.loads_map == {}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__errors(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    async def load_tasks(keys: list[int]) -> list[Task]:  # noqa: RUF029
        return [task_one, GraphQLModelNotFoundError(model=Task, pk=task_two.pk)]

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pkOne: Int!, $pkTwo: Int!) {
            taskOne: task(pk: $pkOne) {
                name
            }
            taskTwo: task(pk: $pkTwo) {
                name
            }
        }
    """

    task_one = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_two = await sync_to_async(TaskFactory.create)(name="Task 2")

    result = await graphql_async(query, variables={"pkOne": task_one.pk, "pkTwo": task_two.pk})

    assert result.errors == [
        {
            "message": f"Primary key {task_two.pk} on model '{dotpath(Task)}' did not match any row.",
            "path": ["taskTwo"],
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
        }
    ]

    assert result.data == {
        "taskOne": {"name": "Task 1"},
        "taskTwo": None,
    }


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__loader_error__did_not_return_sorted_sequence(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    async def load_tasks(keys: list[int]) -> set[Task]:  # noqa: RUF029
        return {task_one, task_two}

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pkOne: Int!, $pkTwo: Int!) {
            taskOne: task(pk: $pkOne) {
                name
            }
            taskTwo: task(pk: $pkTwo) {
                name
            }
        }
    """

    task_one = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_two = await sync_to_async(TaskFactory.create)(name="Task 2")

    result = await graphql_async(query, variables={"pkOne": task_one.pk, "pkTwo": task_two.pk})

    assert result.errors == [
        {
            "message": "DataLoader returned wrong type of object, got 'set' but expected 'list' or 'tuple'",
            "path": ["taskOne"],
            "extensions": {
                "error_code": "DATA_LOADER_DID_NOT_RETURN_SORTED_SEQUENCE",
                "status_code": 500,
            },
        },
        {
            "message": "DataLoader returned wrong type of object, got 'set' but expected 'list' or 'tuple'",
            "path": ["taskTwo"],
            "extensions": {
                "error_code": "DATA_LOADER_DID_NOT_RETURN_SORTED_SEQUENCE",
                "status_code": 500,
            },
        },
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__loader_error__returned_wrong_length(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    async def load_tasks(keys: list[int]) -> list[Task]:  # noqa: RUF029
        return [task_one, task_two, task_two]

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pkOne: Int!, $pkTwo: Int!) {
            taskOne: task(pk: $pkOne) {
                name
            }
            taskTwo: task(pk: $pkTwo) {
                name
            }
        }
    """

    task_one = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_two = await sync_to_async(TaskFactory.create)(name="Task 2")

    result = await graphql_async(query, variables={"pkOne": task_one.pk, "pkTwo": task_two.pk})

    assert result.errors == [
        {
            "message": "Wrong number of values returned from a DataLoader, got 3 but expected 2",
            "path": ["taskOne"],
            "extensions": {
                "error_code": "DATA_LOADER_WRONG_NUMBER_OF_VALUES_RETURNED",
                "status_code": 500,
            },
        },
        {
            "message": "Wrong number of values returned from a DataLoader, got 3 but expected 2",
            "path": ["taskTwo"],
            "extensions": {
                "error_code": "DATA_LOADER_WRONG_NUMBER_OF_VALUES_RETURNED",
                "status_code": 500,
            },
        },
    ]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__multiple_batches(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    resolves = 0
    loads = 0

    async def load_tasks(keys: list[int]) -> list[Task]:
        nonlocal loads
        loads += 1
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks, max_batch_size=1)

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            nonlocal resolves
            resolves += 1
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pkOne: Int!, $pkTwo: Int!) {
            taskOne: task(pk: $pkOne) {
                name
            }
            taskTwo: task(pk: $pkTwo) {
                name
            }
        }
    """

    task_one = await sync_to_async(TaskFactory.create)(name="Task 1")
    task_two = await sync_to_async(TaskFactory.create)(name="Task 2")

    result = await graphql_async(query, variables={"pkOne": task_one.pk, "pkTwo": task_two.pk})

    assert result.has_errors is False, result.errors

    assert result.data == {
        "taskOne": {"name": "Task 1"},
        "taskTwo": {"name": "Task 2"},
    }

    # The task resolver was called twice, and the dataloader too,
    # since we made the requests in two batches
    assert resolves == 2
    assert loads == 2

    # Loads were emptied after the request
    assert loader.loads_map == {}


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__reuse_loaded(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    loaded: list[int] = []

    async def load_tasks(keys: list[int]) -> list[Task]:
        loaded.extend(keys)
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType)

        @task.resolve
        async def resolve_task(self, info: GQLInfo, pk: int) -> Task:
            return await loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($pk: Int!) {
            taskOne: task(pk: $pk) {
                name
            }
            taskTwo: task(pk: $pk) {
                name
            }
        }
    """

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1")

    result = await graphql_async(query, variables={"pk": task_1.pk})

    assert result.has_errors is False, result.errors

    assert result.data == {
        "taskOne": {"name": "Task 1"},
        "taskTwo": {"name": "Task 1"},
    }

    assert loaded == [task_1.pk]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__cancelled() -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    db_query = False

    def logger(*args, **kwargs):
        nonlocal db_query
        db_query = True

    async def load_tasks(keys: list[int]) -> list[Task]:
        with db.connection.execute_wrapper(logger):
            return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    async def load_task(task_id: int) -> Task:
        return await loader.load(task_id)

    async def load_project(post_id: int) -> None:  # noqa: RUF029
        msg = "Post not found"
        raise ValueError(msg)

    with pytest.raises(ExceptionGroup):  # noqa: PT012
        async with asyncio.TaskGroup() as group:
            task_1 = group.create_task(load_project(1))
            task_2 = group.create_task(load_task(ts.pk))

    # Task 1 was no cancelled, but resulted in an exception.
    assert task_1.done() is True
    assert task_1.cancelled() is False
    assert task_1.exception() is not None

    # Task 2 was cancelled.
    assert task_2.cancelled() is True

    # No database queries were executed since the load was cancelled.
    assert db_query is False
