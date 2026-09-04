from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from functools import cache
from typing import TYPE_CHECKING, Any

from undine.exceptions import GraphQLSubscriptionBacklogFullError
from undine.settings import undine_settings
from undine.utils.logging import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

__all__ = [
    "InMemorySubscriptionBroker",
    "SubscriptionBroker",
    "SubscriptionEventBuffer",
    "get_subscription_broker",
]


def get_subscription_broker() -> SubscriptionBroker:
    """The broker that signal subscriptions publish their events to and receive them from."""
    return _subscription_broker(undine_settings.SUBSCRIPTION_BROKER_CLASS)


class SubscriptionBroker(ABC):
    """
    Carries signal subscription events from the process that publishes an event
    to the processes that have subscribers waiting for it.

    Delivery is at-most-once fan-out: every subscriber of a topic receives every event
    published to that topic while it is subscribed. Events are not stored, so an event
    published while nobody is subscribed is lost, and there is no replay after a reconnect.
    """

    @abstractmethod
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """
        Send an event to the subscribers of the given topic.

        Called on the thread that dispatched the Django signal, which is usually
        not the thread running the event loop of the subscribers.

        :param topic: The topic to publish the event to.
        :param payload: The event. Holds only values that the broker's transport can carry.
        """

    @abstractmethod
    def subscribe(self, topic: str, *, max_backlog: int) -> AsyncGenerator[dict[str, Any], None]:
        """
        Receive the events published to the given topic. Yields events until the generator is closed.

        :param topic: The topic to receive events from.
        :param max_backlog: How many events may wait for the subscriber before the stream ends
                            with a `GraphQLSubscriptionBacklogFullError`. Zero means no limit.
        """


class SubscriptionEventBuffer:
    """
    Bounded buffer a broker hands events to and a subscriber reads them from.

    Events may be handed over from any thread, since Django dispatches a signal on whichever
    thread made the change, and mutations run their ORM work in a thread executor. `asyncio.Queue`
    is not thread-safe: adding to it from another thread marks the waiting subscriber as ready
    but does not wake the event loop, which then stays asleep until something else happens
    to wake it. Every hand-over therefore goes through `loop.call_soon_threadsafe`.
    """

    def __init__(self, *, max_backlog: int) -> None:
        """
        Create a buffer for the subscriber running on the current event loop.

        :param max_backlog: How many events may wait in the buffer. Zero means no limit.
        """
        self.loop = asyncio.get_running_loop()
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_backlog)
        self.overflowed = False

    def put(self, payload: dict[str, Any]) -> None:
        """Add an event to the buffer from any thread."""
        try:
            self.loop.call_soon_threadsafe(self._put, payload)
        except RuntimeError:
            logger.debug("Event loop is closed, dropping event for subscriber.")

    def _put(self, payload: dict[str, Any]) -> None:
        # Runs on the event loop's thread, so the queue and the flag are safe to touch here.
        try:
            self.events.put_nowait(payload)
        except asyncio.QueueFull:
            self.overflowed = True

    async def stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """
        Yield the buffered events as they arrive.

        :raises GraphQLSubscriptionBacklogFullError: The buffer overflowed, so events were lost.
        """
        while True:
            # Events have been lost, so the stream has a gap in it. Clients cannot detect
            # that themselves, so end the subscription and let them resubscribe.
            if self.overflowed:
                raise GraphQLSubscriptionBacklogFullError

            yield await self.events.get()


class InMemorySubscriptionBroker(SubscriptionBroker):
    """
    Broker that keeps each event in the memory of the process that published it.

    Subscribers in other processes never receive the event, so a deployment running
    more than one worker needs a broker with a transport the workers share.
    """

    def __init__(self) -> None:
        self.buffers: dict[str, dict[uuid.UUID, SubscriptionEventBuffer]] = {}

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        # Copied, since the subscribers of a topic change on the event loop's thread.
        buffers = list(self.buffers.get(topic, {}).values())
        for buffer in buffers:
            buffer.put(payload)

    async def subscribe(self, topic: str, *, max_backlog: int) -> AsyncGenerator[dict[str, Any], None]:
        buffer = SubscriptionEventBuffer(max_backlog=max_backlog)
        key = uuid.uuid4()

        buffers = self.buffers.setdefault(topic, {})
        buffers[key] = buffer

        try:
            async for payload in buffer.stream():
                yield payload
        finally:
            buffers.pop(key, None)


@cache
def _subscription_broker(broker_class: type[SubscriptionBroker]) -> SubscriptionBroker:
    # A single broker per class, since a broker holds the state that ties publishers
    # and subscribers in this process together.
    return broker_class()
