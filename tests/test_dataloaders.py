from __future__ import annotations

import asyncio
from asyncio import Future, gather

import pytest
from asgiref.sync import sync_to_async
from pytest_django import DjangoDbBlocker

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import count_db_accesses
from undine import DataLoader, Entrypoint, GQLInfo, QueryType, RootType, create_schema
from undine.dataloaders import DataLoaderFuture
from undine.exceptions import GraphQLDataLoaderPrimingError, GraphQLModelNotFoundError
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
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            nonlocal resolves
            resolves += 1
            return loader.load(pk)

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
    assert loader.reusable_loads == {}


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
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            return loader.load(pk)

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

    async def load_tasks(keys: list[int]) -> set[Task]:
        instances = [task async for task in Task.objects.filter(id__in=keys)]
        return set(instances)

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

        @task.resolve
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            return loader.load(pk)

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

    async def load_tasks(keys: list[int]) -> list[Task]:
        instances = [task async for task in Task.objects.filter(id__in=keys)]
        instances.append(task_two)
        return instances

    loader = DataLoader(load_fn=load_tasks)

    class Query(RootType):
        task = Entrypoint(TaskType, nullable=True)

        @task.resolve
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            return loader.load(pk)

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
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            nonlocal resolves
            resolves += 1
            return loader.load(pk)

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
    assert loader.reusable_loads == {}


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
        def resolve_task(self, info: GQLInfo, pk: int) -> Future[Task]:
            return loader.load(pk)

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
async def test_dataloader__prime_another_dataloader(graphql_async, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"

    class TaskType(QueryType[Task]): ...

    loaded_by_name = False
    loaded_by_id = False

    async def load_tasks_by_name(keys: list[str]) -> list[Task]:
        nonlocal loaded_by_name, name_loader, pk_loader
        loaded_by_name = True
        tasks = [task async for task in Task.objects.filter(name__in=keys)]
        keys = [task.pk for task in tasks]
        pk_loader.prime_many(keys=keys, values=tasks, can_prime_pending_loads=True)
        return tasks

    async def load_tasks_by_id(keys: list[int]) -> list[Task]:
        nonlocal loaded_by_id, name_loader, pk_loader
        loaded_by_id = True
        tasks = [task async for task in Task.objects.filter(id__in=keys)]
        keys = [task.name for task in tasks]
        name_loader.prime_many(keys=keys, values=tasks, can_prime_pending_loads=True)
        return tasks

    lock = asyncio.Lock()
    name_loader = DataLoader(load_fn=load_tasks_by_name, lock=lock)
    pk_loader = DataLoader(load_fn=load_tasks_by_id, lock=lock)

    class Query(RootType):
        task_by_name = Entrypoint(TaskType)
        task_by_pk = Entrypoint(TaskType)

        @task_by_name.resolve
        def resolve_task_by_name(self, info: GQLInfo, name: str) -> Future[Task]:
            return name_loader.load(name)

        @task_by_pk.resolve
        def resolve_task_by_pk(self, info: GQLInfo, pk: int) -> Future[Task]:
            return pk_loader.load(pk)

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query($name: String! $pk: Int!) {
            taskByName(name: $name) {
                pk
                name
            }
            taskByPk(pk: $pk) {
                pk
                name
            }
        }
    """

    task_1 = await sync_to_async(TaskFactory.create)(name="Task 1")

    result = await graphql_async(query, variables={"name": task_1.name, "pk": task_1.pk})

    assert result.has_errors is False, result.errors

    assert result.data == {
        "taskByName": {"pk": task_1.pk, "name": task_1.name},
        "taskByPk": {"pk": task_1.pk, "name": task_1.name},
    }

    # Only one of the loaders should have run, but not both.
    assert loaded_by_name ^ loaded_by_id


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__cancelled__task_group(django_db_blocker: DjangoDbBlocker) -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    async def load_task(task_id: int) -> Task:
        return await loader.load(task_id)

    async def load_project(project_id: int) -> None:  # noqa: RUF029
        msg = "Project not found"
        raise ValueError(msg)

    with count_db_accesses(django_db_blocker) as log:
        with pytest.raises(ExceptionGroup):  # noqa: PT012
            async with asyncio.TaskGroup() as group:
                task_1 = group.create_task(load_project(1))
                task_2 = group.create_task(load_task(ts.pk))

        # Wait for all tasks to complete
        await asyncio.sleep(0.1)

    # Task 1 was no cancelled, but resulted in an exception.
    assert task_1.done() is True
    assert task_1.cancelled() is False
    assert task_1.exception() is not None

    # Task 2 was cancelled by task group.
    assert task_2.cancelled() is True

    # No database accesses since the task group cancelled all other tasks.
    assert log.count == 0


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__cancelled__gather(django_db_blocker: DjangoDbBlocker) -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    async def load_task(task_id: int) -> Task:
        return await loader.load(task_id)

    msg = "Project not found"

    async def load_project(project_id: int) -> None:  # noqa: RUF029
        raise ValueError(msg)

    task_1 = asyncio.create_task(load_project(1))
    task_2 = asyncio.create_task(load_task(ts.pk))

    with count_db_accesses(django_db_blocker) as log:
        with pytest.raises(ValueError, match=msg):
            await gather(task_1, task_2)

        # Wait for all tasks to complete
        await asyncio.sleep(0.1)

    # Task 1 was no cancelled, but resulted in an exception.
    assert task_1.done() is True
    assert task_1.cancelled() is False
    assert task_1.exception() is not None

    # Task 2 executed and finished.
    assert task_2.done() is True
    assert task_2.cancelled() is False
    assert task_2.result() == ts

    # One access in the dataloader since no cancellation from gather.
    assert log.count == 1


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__load() -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    future = loader.load(ts.pk)

    assert future.done() is False

    result = await future
    assert result == ts

    assert future.done() is True
    assert future.result() == ts

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)

    future_2 = loader_2.load(ts.pk)
    assert ts.pk not in loader_2.reusable_loads

    future_2.cancel()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__load_many() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    future = loader.load_many([ts_1.pk, ts_2.pk])

    assert future.done() is False

    results = await future

    assert future.done() is True

    assert len(results) == 2
    assert results[0] == ts_1
    assert results[1] == ts_2

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)

    future_2 = loader_2.load_many(keys=[ts_1.pk, ts_2.pk])
    assert ts_1.pk not in loader_2.reusable_loads
    assert ts_2.pk not in loader_2.reusable_loads

    future_2.cancel()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__load_many__exception() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    error = ValueError("foo")

    async def load_tasks(keys: list[int]) -> list[Task]:  # noqa: RUF029
        return [ts_1, error]

    loader = DataLoader(load_fn=load_tasks)

    future = loader.load_many([ts_1.pk, ts_2.pk])

    assert future.done() is False

    results = await future

    assert future.done() is True

    assert len(results) == 2
    assert results[0] == ts_1
    assert results[1] == error


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__prime() -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    result = loader.prime(key=ts.pk, value=ts)
    assert result == loader

    assert ts.pk in loader.reusable_loads

    future = loader.load(ts.pk)
    assert future == loader.reusable_loads[ts.pk].future

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)

    loader_2.prime(key=ts.pk, value=ts)
    assert ts.pk not in loader_2.reusable_loads


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__prime__clear_then_prime_also_updates_current_batch() -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    # Scheduled a load for the current batch
    future = loader.load(key=ts.pk)
    load = DataLoaderFuture(key=ts.pk, future=future)
    assert ts.pk in loader.reusable_loads
    assert loader.current_batch.loads == [load]
    assert load.future.done() is False

    # Clear the reusable load for the key, load still persists in the current batch
    loader.clear(key=ts.pk)
    assert ts.pk not in loader.reusable_loads
    assert loader.current_batch.loads == [load]
    assert load.future.done() is False

    # Prime a reusable load for the same key, load is now done and removed from the current batch
    loader.prime(key=ts.pk, value=ts)
    assert ts.pk in loader.reusable_loads
    assert loader.current_batch.loads == []
    assert load.future.done() is True
    assert load.future.result() == ts


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__prime_many() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    result = loader.prime_many(keys=[ts_1.pk, ts_2.pk], values=[ts_1, ts_2])
    assert result == loader

    assert ts_1.pk in loader.reusable_loads
    assert ts_2.pk in loader.reusable_loads

    future_1 = loader.load(ts_1.pk)
    assert future_1 == loader.reusable_loads[ts_1.pk].future

    future_2 = loader.load(ts_2.pk)
    assert future_2 == loader.reusable_loads[ts_2.pk].future

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)
    loader_2.prime_many(keys=[ts_1.pk, ts_2.pk], values=[ts_1, ts_2])
    assert ts_1.pk not in loader_2.reusable_loads
    assert ts_2.pk not in loader_2.reusable_loads


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__prime_many__different_lengths() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    with pytest.raises(GraphQLDataLoaderPrimingError):
        loader.prime_many(keys=[ts_1.pk, ts_2.pk], values=[ts_1])

    with pytest.raises(GraphQLDataLoaderPrimingError):
        loader.prime_many(keys=[ts_1.pk], values=[ts_1, ts_2])


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__clear() -> None:
    ts = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    loader.prime(key=ts.pk, value=ts)
    assert ts.pk in loader.reusable_loads

    result = loader.clear(key=ts.pk)
    assert result == loader

    assert ts.pk not in loader.reusable_loads

    # Clearing missing key should not raise an error
    loader.clear(key=ts.pk)

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)
    loader_2.reusable_loads[ts.pk] = DataLoaderFuture(key=ts.pk, future=loader.loop.create_future())
    loader_2.clear(key=ts.pk)

    assert ts.pk in loader_2.reusable_loads


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__clear_many() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    loader.prime_many(keys=[ts_1.pk, ts_2.pk], values=[ts_1, ts_2])

    assert ts_1.pk in loader.reusable_loads
    assert ts_2.pk in loader.reusable_loads

    result = loader.clear_many(keys=[ts_1.pk, ts_2.pk])
    assert result == loader

    assert ts_1.pk not in loader.reusable_loads
    assert ts_2.pk not in loader.reusable_loads

    # Clearing missing key should not raise an error
    loader.clear_many(keys=[ts_1.pk, ts_2.pk])

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)
    loader_2.reusable_loads[ts_1.pk] = DataLoaderFuture(key=ts_1.pk, future=loader.loop.create_future())
    loader_2.reusable_loads[ts_2.pk] = DataLoaderFuture(key=ts_2.pk, future=loader.loop.create_future())
    loader_2.clear_many(keys=[ts_1.pk, ts_2.pk])

    assert ts_1.pk in loader_2.reusable_loads
    assert ts_2.pk in loader_2.reusable_loads


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__clear_all() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 2")

    async def load_tasks(keys: list[int]) -> list[Task]:
        return [task async for task in Task.objects.filter(id__in=keys)]

    loader = DataLoader(load_fn=load_tasks)

    loader.prime_many(keys=[ts_1.pk, ts_2.pk], values=[ts_1, ts_2])

    assert ts_1.pk in loader.reusable_loads
    assert ts_2.pk in loader.reusable_loads

    result = loader.clear_all()
    assert result == loader

    assert ts_1.pk not in loader.reusable_loads
    assert ts_2.pk not in loader.reusable_loads

    loader_2 = DataLoader(load_fn=load_tasks, reuse_loads=False)
    loader_2.reusable_loads[ts_1.pk] = DataLoaderFuture(key=ts_1.pk, future=loader.loop.create_future())
    loader_2.reusable_loads[ts_2.pk] = DataLoaderFuture(key=ts_2.pk, future=loader.loop.create_future())
    loader_2.clear_all()

    assert ts_1.pk in loader_2.reusable_loads
    assert ts_2.pk in loader_2.reusable_loads


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_dataloader__key_hash_fn() -> None:
    ts_1 = await sync_to_async(TaskFactory.create)(name="Task 1")
    ts_2 = await sync_to_async(TaskFactory.create)(name="Task 1")

    async def load_tasks(keys: list[Task]) -> list[Task]:  # noqa: RUF029
        return keys

    def key_hash_fn(key: Task) -> int:
        return key.pk

    loader = DataLoader(load_fn=load_tasks, key_hash_fn=key_hash_fn)

    future = loader.load(ts_1)

    assert ts_1.pk in loader.reusable_loads

    result = await future
    assert result == ts_1

    loader.prime(key=ts_2, value=ts_2)

    assert ts_2.pk in loader.reusable_loads

    loader.clear(key=ts_2)

    assert ts_2.pk not in loader.reusable_loads

    loader.clear_many([ts_1, ts_2])

    assert ts_1.pk not in loader.reusable_loads
    assert ts_2.pk not in loader.reusable_loads
