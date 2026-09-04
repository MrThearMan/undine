from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import AsyncGenerator, AsyncIterable, AsyncIterator, Self

import pytest
from asgiref.sync import sync_to_async
from django.db.models import QuerySet
from django.db.models.signals import post_save
from graphql import FormattedExecutionResult, GraphQLError, GraphQLFormattedError

from example_project.app.models import Task, TaskTypeChoices
from tests.factories.task import TaskFactory
from tests.helpers import TEST_WAIT_TIME, cancel_from_thread_after, exact, saving_in_separate_thread
from undine import Entrypoint, GQLInfo, QueryType, RootType, create_schema
from undine.exceptions import GraphQLErrorGroup, GraphQLPermissionError, GraphQLSubscriptionBacklogFullError
from undine.subscriptions import (
    ModelCreateSubscription,
    ModelDeleteSubscription,
    ModelSaveSubscription,
    ModelUpdateSubscription,
)


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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"savedTasks": {"pk": task.pk, "name": "Task"}},
        )

        task.name = "Updated task"
        await sync_to_async(task.save)()

        result = await websocket.receive(timeout=TEST_WAIT_TIME)
        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"savedTasks": {"pk": task.pk, "name": "Updated task"}},
        )


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__signal_from_non_loop_thread() -> None:
    class TaskType(QueryType[Task], auto=True): ...

    subscription = ModelSaveSubscription(TaskType)
    subscriber = subscription.create_subscriber()

    task = await sync_to_async(TaskFactory.create)(name="Task")

    events = subscriber.subscribe()
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber register itself and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    task.name = "Updated task"

    with (
        cancel_from_thread_after(receive_task, timeout=TEST_WAIT_TIME * 20) as watchdog,
        saving_in_separate_thread(task, delay=TEST_WAIT_TIME),
    ):
        try:
            event = await receive_task
        except asyncio.CancelledError:
            event = None

    await events.aclose()

    assert not watchdog.is_set(), "The event loop was not woken by the signal, so nothing was delivered."
    assert event == str(task.pk)


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__backlog_full() -> None:
    class TaskType(QueryType[Task], auto=True): ...

    subscription = ModelSaveSubscription(TaskType, max_backlog=1)
    subscriber = subscription.create_subscriber()

    first_task = await sync_to_async(TaskFactory.create)(name="Task 1")
    second_task = await sync_to_async(TaskFactory.create)(name="Task 2")

    events = subscriber.subscribe()
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber register itself and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    # Sent directly rather than by saving, so that both events are queued in the same pass
    # of the event loop. A real save yields to the loop, which lets the subscriber drain the
    # first event before the second one arrives, and then the backlog never fills.
    signal_params = {"sender": Task, "created": False, "raw": False, "using": None, "update_fields": None}
    post_save.send(instance=first_task, **signal_params)
    post_save.send(instance=second_task, **signal_params)

    assert await receive_task == str(first_task.pk)

    message = "Subscriber cannot keep up with the rate of incoming events"
    with pytest.raises(GraphQLSubscriptionBacklogFullError, match=exact(message)):
        await anext(events)


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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"createdTasks": {"pk": task.pk, "name": "Task"}},
        )

        task.name = "Updated task"
        await sync_to_async(task.save)()

        # Updates are not sent through the subscription.
        with pytest.raises(TimeoutError):
            await websocket.receive(timeout=TEST_WAIT_TIME)


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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        # Creates are not sent through the subscription.
        with pytest.raises(TimeoutError):
            await websocket.receive(timeout=TEST_WAIT_TIME)

        task.name = "Updated task"
        await sync_to_async(task.save)()

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"updatedTasks": {"pk": task.pk, "name": "Updated task"}},
        )


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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        pk = task.pk
        await task.adelete()

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"deletedTasks": {"pk": pk, "name": "Task"}},
        )


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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Permission denied.",
                path=["savedTasks"],
                extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
            )
        ]


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__timeout(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        saved_tasks = Entrypoint(ModelSaveSubscription(TaskType, timeout=0.01))

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { savedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Subscribe and wait for the timeout error message
        result = await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME * 10)

        assert result["type"] == "error"
        assert result["payload"][0]["message"] == "Subscription timed out"


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__instance_not_found(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True):
        @classmethod
        def __get_queryset__(cls, info: GQLInfo) -> QuerySet[Task]:
            return Task.objects.exclude(name="Hidden task")

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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        # This task is not visible through the QueryType, so nothing is sent for it.
        await sync_to_async(Task.objects.create)(name="Hidden task", type=TaskTypeChoices.STORY)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "next"
        assert result["payload"] == FormattedExecutionResult(
            data={"savedTasks": {"pk": task.pk, "name": "Task"}},
        )


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__async_permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        saved_tasks = Entrypoint(ModelSaveSubscription(TaskType))

        @saved_tasks.permissions
        async def saved_tasks_permissions(self, info: GQLInfo, instance: Task) -> None:
            if instance.name == "Task":
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { savedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Permission denied.",
                path=["savedTasks"],
                extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
            )
        ]


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__query_type_async_permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True):
        @classmethod
        async def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            if instance.name == "Task":
                raise GraphQLPermissionError

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
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Permission denied.",
                path=["savedTasks"],
                extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
            )
        ]


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__save__error_group(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        saved_tasks = Entrypoint(ModelSaveSubscription(TaskType))

        @saved_tasks.permissions
        def saved_tasks_permissions(self, info: GQLInfo, instance: Task) -> None:
            raise GraphQLErrorGroup([GraphQLError("Error 1"), GraphQLError("Error 2")])

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { savedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Error 1",
                path=["savedTasks"],
                extensions={"status_code": 400},
            ),
            GraphQLFormattedError(
                message="Error 2",
                path=["savedTasks"],
                extensions={"status_code": 400},
            ),
        ]


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__delete__async_permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        deleted_tasks = Entrypoint(ModelDeleteSubscription(TaskType))

        @deleted_tasks.permissions
        async def deleted_tasks_permissions(self, info: GQLInfo, instance: Task) -> None:
            raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { deletedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)
        await task.adelete()

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Permission denied.",
                path=["deletedTasks"],
                extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
            )
        ]


@pytest.mark.django_db(transaction=True)
async def test_signal_subscription__delete__error_group(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class TaskType(QueryType[Task], auto=True): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class Subscription(RootType):
        deleted_tasks = Entrypoint(ModelDeleteSubscription(TaskType))

        @deleted_tasks.permissions
        def deleted_tasks_permissions(self, info: GQLInfo, instance: Task) -> None:
            raise GraphQLErrorGroup([GraphQLError("Error 1"), GraphQLError("Error 2")])

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    payload = {"query": "subscription { deletedTasks { pk name } }"}

    async with graphql.websocket() as websocket:
        await websocket.connection_init()

        # Must await the subscription so that the subscriber is created.
        with suppress(TimeoutError):
            await websocket.subscribe(payload=payload, timeout=TEST_WAIT_TIME)

        task = await sync_to_async(Task.objects.create)(name="Task", type=TaskTypeChoices.STORY)
        await task.adelete()

        result = await websocket.receive(timeout=TEST_WAIT_TIME)

        assert result["type"] == "error"
        assert result["payload"] == [
            GraphQLFormattedError(
                message="Error 1",
                path=["deletedTasks"],
                extensions={"status_code": 400},
            ),
            GraphQLFormattedError(
                message="Error 2",
                path=["deletedTasks"],
                extensions={"status_code": 400},
            ),
        ]


@pytest.mark.django_db(transaction=True)
async def test_function_subscription__async_generator(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self, info: GQLInfo) -> AsyncGenerator[int, None]:
            for i in range(2, 0, -1):
                yield i

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]

    assert responses == [
        FormattedExecutionResult(data={"countdown": 2}),
        FormattedExecutionResult(data={"countdown": 1}),
    ]


@pytest.mark.django_db(transaction=True)
async def test_function_subscription__async_iterator(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class ExampleIterator:
        def __init__(self) -> None:
            self.values = [2, 1]
            self.index = 0

        def __aiter__(self) -> Self:
            return self

        async def __anext__(self) -> int:
            if self.index >= len(self.values):
                raise StopAsyncIteration
            value = self.values[self.index]
            self.index += 1
            return value

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterator[int]:
            return ExampleIterator()

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]

    assert responses == [
        FormattedExecutionResult(data={"countdown": 2}),
        FormattedExecutionResult(data={"countdown": 1}),
    ]


@pytest.mark.django_db(transaction=True)
async def test_function_subscription__async_iterable(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class ExampleIterable:
        def __aiter__(self) -> AsyncIterator[int]:
            return self.gen()

        async def gen(self) -> AsyncGenerator[int, None]:
            for i in range(2, 0, -1):
                yield i

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncIterable[int]:
            return ExampleIterable()

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]

    assert responses == [
        FormattedExecutionResult(data={"countdown": 2}),
        FormattedExecutionResult(data={"countdown": 1}),
    ]


@pytest.mark.django_db(transaction=True)
async def test_function_subscription__info_param_only(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        @staticmethod
        async def field_name(info: GQLInfo) -> AsyncGenerator[str, None]:
            yield info.field_name

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { fieldName }"

    responses = [response.json async for response in graphql.over_websocket(query)]

    assert responses == [FormattedExecutionResult(data={"fieldName": "fieldName"})]


@pytest.mark.django_db(transaction=True)
async def test_function_subscription__async_permissions(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True

    class Query(RootType):
        @Entrypoint
        def test(self) -> str:
            return "Hello, World!"

    class Subscription(RootType):
        @Entrypoint
        async def countdown(self) -> AsyncGenerator[int, None]:
            for i in range(2, 0, -1):
                yield i

        @countdown.permissions
        async def countdown_permissions(self, info: GQLInfo, value: int) -> None:
            if value == 1:
                raise GraphQLPermissionError

    undine_settings.SCHEMA = create_schema(query=Query, subscription=Subscription)

    query = "subscription { countdown }"

    responses = [response.json async for response in graphql.over_websocket(query)]

    assert responses == [
        FormattedExecutionResult(data={"countdown": 2}),
        FormattedExecutionResult(
            data=None,
            errors=[
                GraphQLFormattedError(
                    message="Permission denied.",
                    path=["countdown"],
                    extensions={"error_code": "PERMISSION_DENIED", "status_code": 403},
                ),
            ],
        ),
    ]
