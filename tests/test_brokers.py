from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

from tests.helpers import TEST_WAIT_TIME, ExampleSubscriptionBroker, exact
from undine.brokers import InMemorySubscriptionBroker, get_subscription_broker
from undine.exceptions import GraphQLSubscriptionBacklogFullError


async def test_in_memory_broker__publish() -> None:
    broker = InMemorySubscriptionBroker()

    events = broker.subscribe("topic", max_backlog=10)
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber register itself and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    broker.publish("topic", {"pk": "1"})

    assert await receive_task == {"pk": "1"}

    await events.aclose()


async def test_in_memory_broker__publish__other_topic() -> None:
    broker = InMemorySubscriptionBroker()

    events = broker.subscribe("topic", max_backlog=10)
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber register itself and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    broker.publish("other-topic", {"pk": "1"})

    await asyncio.sleep(TEST_WAIT_TIME)

    assert not receive_task.done()

    receive_task.cancel()
    with suppress(asyncio.CancelledError):
        await receive_task

    await events.aclose()


async def test_in_memory_broker__backlog_full() -> None:
    broker = InMemorySubscriptionBroker()

    events = broker.subscribe("topic", max_backlog=1)
    receive_task = asyncio.create_task(anext(events))

    # Let the subscriber register itself and start waiting for an event.
    await asyncio.sleep(TEST_WAIT_TIME)

    broker.publish("topic", {"pk": "1"})
    broker.publish("topic", {"pk": "2"})

    assert await receive_task == {"pk": "1"}

    message = "Subscriber cannot keep up with the rate of incoming events"
    with pytest.raises(GraphQLSubscriptionBacklogFullError, match=exact(message)):
        await anext(events)


def test_in_memory_broker__event_loop_closed() -> None:
    broker = InMemorySubscriptionBroker()

    loop = asyncio.new_event_loop()

    async def start_subscribing() -> None:
        events = broker.subscribe("topic", max_backlog=10)
        receive_task = loop.create_task(anext(events))

        # Let the subscriber register itself and start waiting for an event.
        await asyncio.sleep(TEST_WAIT_TIME)

        assert not receive_task.done()

    loop.run_until_complete(start_subscribing())
    loop.close()

    # The subscriber is still registered, since closing the loop skipped the generator's cleanup.
    broker.publish("topic", {"pk": "1"})

    buffer = next(iter(broker.buffers["topic"].values()))
    assert buffer.events.empty()


def test_get_subscription_broker(undine_settings) -> None:
    broker = get_subscription_broker()

    assert isinstance(broker, InMemorySubscriptionBroker)
    assert get_subscription_broker() is broker

    undine_settings.SUBSCRIPTION_BROKER_CLASS = ExampleSubscriptionBroker

    assert isinstance(get_subscription_broker(), ExampleSubscriptionBroker)
