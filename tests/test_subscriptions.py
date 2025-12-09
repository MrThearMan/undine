from __future__ import annotations

from contextlib import suppress

import pytest
from asgiref.sync import sync_to_async
from graphql import FormattedExecutionResult, GraphQLFormattedError

from example_project.app.models import Task, TaskTypeChoices
from undine import Entrypoint, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.subscriptions import (
    ModelCreateSubscription,
    ModelDeleteSubscription,
    ModelSaveSubscription,
    ModelUpdateSubscription,
)

TIMEOUT = 0.1  # TODO: Don't hardcode timeout

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        saved_tasks = Entrypoint(ModelSaveSubscription(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { savedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TIMEOUT)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TIMEOUT)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"savedTasks": {"pk": task.pk, "name": "Task"}},
        )

        task.name = "Updated task"
        await sync_to_async(task.save)()

        result = await websocket.receive(timeout=TIMEOUT)
        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"savedTasks": {"pk": task.pk, "name": "Updated task"}},
        )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__create(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        created_tasks = Entrypoint(ModelCreateSubscription(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { createdTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TIMEOUT)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TIMEOUT)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"createdTasks": {"pk": task.pk, "name": "Task"}},
        )

        task.name = "Updated task"
        await sync_to_async(task.save)()

        # Updates are not sent through the subscription.
        with pytest.raises(TimeoutError):
            await websocket.receive(timeout=TIMEOUT)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__update(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        updated_tasks = Entrypoint(ModelUpdateSubscription(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { updatedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TIMEOUT)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        # Creates are not sent through the subscription.
        with pytest.raises(TimeoutError):
            await websocket.receive(timeout=TIMEOUT)

        task.name = "Updated task"
        await sync_to_async(task.save)()

        result = await websocket.receive(timeout=TIMEOUT)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"updatedTasks": {"pk": task.pk, "name": "Updated task"}},
        )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__delete(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        deleted_tasks = Entrypoint(ModelDeleteSubscription(TaskType))

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { deletedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TIMEOUT)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        pk = task.pk
        await task.adelete()

        result = await websocket.receive(timeout=TIMEOUT)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"deletedTasks": {"pk": pk, "name": "Task"}},
        )


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        saved_tasks = Entrypoint(ModelSaveSubscription(TaskType))

        @saved_tasks.permissions
        def saved_tasks_permissions(self, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { savedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TIMEOUT)

        await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TIMEOUT)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Permission denied.",
                path=["savedTasks"],
                extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
            )
        ]
