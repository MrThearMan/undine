from __future__ import annotations

import asyncio
from contextlib import suppress
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from graphql import FormattedExecutionResult

from example_project.app.models import Task, TaskTypeChoices
from tests.helpers import TEST_WAIT_TIME, exact
from undine import Entrypoint, QueryType, RootType, create_schema
from undine.exceptions import ChannelLayerMissingError, GraphQLSubscriptionBacklogFullError
from undine.integrations.channels import ChannelLayerSubscriptionBroker
from undine.subscriptions import ModelSaveSubscription

pytestmark = [
    pytest.mark.django_db(transaction=True),
]


async def test_channels__subscription_broker__publish() -> None:
    broker = ChannelLayerSubscriptionBroker()

    events = broker.subscribe("undine.signal.test", max_backlog=10)
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber join the group and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    # Django dispatches a signal on whichever thread made the change, so publishing
    # happens off the event loop's thread, just like it does in production.
    await sync_to_async(broker.publish)("undine.signal.test", {"pk": "1"})

    assert await receive_task == {"pk": "1"}

    await events.aclose()


async def test_channels__subscription_broker__backlog_full() -> None:
    broker = ChannelLayerSubscriptionBroker()

    events = broker.subscribe("undine.signal.test", max_backlog=1)
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber join the group and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    await sync_to_async(broker.publish)("undine.signal.test", {"pk": "1"})

    assert await receive_task == {"pk": "1"}

    # Nothing reads from the stream now, so these two fill the buffer of one event.
    await sync_to_async(broker.publish)("undine.signal.test", {"pk": "2"})
    await sync_to_async(broker.publish)("undine.signal.test", {"pk": "3"})

    await asyncio.sleep(TEST_WAIT_TIME)

    message = "Subscriber cannot keep up with the rate of incoming events"
    with pytest.raises(GraphQLSubscriptionBacklogFullError, match=exact(message)):
        await anext(events)


def test_channels__subscription_broker__no_channel_layer() -> None:
    broker = ChannelLayerSubscriptionBroker()

    message = "No channel layer has been configured for the alias 'default'"

    with (
        patch("undine.integrations.channels.get_channel_layer", return_value=None),
        pytest.raises(ChannelLayerMissingError, match=exact(message)),
    ):
        broker.publish("undine.signal.test", {"pk": "1"})


async def test_channels__subscription_broker__signal_subscription(graphql, undine_settings) -> None:
    undine_settings.ASYNC = True
    undine_settings.SUBSCRIPTION_BROKER_CLASS = ChannelLayerSubscriptionBroker

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
