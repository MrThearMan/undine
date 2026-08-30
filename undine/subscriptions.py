from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Generic

from django.db.models.signals import post_save, pre_delete

from undine.exceptions import GraphQLSubscriptionBacklogFullError, GraphQLSubscriptionTimeoutError
from undine.typing import T, TModel
from undine.utils.logging import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from django.dispatch import Signal

    from undine import QueryType
    from undine.typing import PostDeleteParams, PostSaveParams

__all__ = [
    "ModelCreateSubscription",
    "ModelDeleteSubscription",
    "ModelSaveSubscription",
    "ModelUpdateSubscription",
    "SignalSubscriber",
    "SignalSubscription",
]


class SignalSubscription(ABC, Generic[T]):
    """A subscription that forwards data from a signal."""

    def __init__(
        self,
        sender: Any,
        *,
        dispatch_uid: str | None = None,
        description: str | None = None,
        timeout: float | None = None,
        max_backlog: int = 100,
    ) -> None:
        """
        Create a new subscription.

        :param sender: The model class to subscribe to.
        :param dispatch_uid: The dispatch uid for the signal.
        :param description: The description for the subscription.
        :param timeout: How long to wait between signals before timing out.
        :param max_backlog: How many events a subscriber may fall behind by before
                            its subscription ends. Set to 0 for no limit.
        """
        self.sender = sender
        self.dispatch_uid = dispatch_uid
        self.description = description
        self.timeout = timeout
        self.max_backlog = max_backlog

        self.subscribers: dict[uuid.UUID, SignalSubscriber] = {}

        self.signal.connect(self.receiver, sender=sender, dispatch_uid=dispatch_uid)

    @property
    @abstractmethod
    def signal(self) -> Signal:
        """The signal to subscribe to."""

    @abstractmethod
    def transform(self, params: dict[str, Any]) -> T:
        """Transform the given event data into the desired output."""

    def filter(self, params: dict[str, Any]) -> bool:
        """Should the given event be filtered out?"""
        return False

    def process(self, params: dict[str, Any]) -> dict[str, Any]:
        """Process the given signal data before handing it out to subscribers."""
        return params

    def create_subscriber(self) -> SignalSubscriber[T]:
        return SignalSubscriber(self)

    def receiver(self, *args: Any, **kwargs: Any) -> None:
        """Receiver for the Django signal."""
        # Some signals might send the 'sender' argument as a positional argument
        if args:  # pragma: no cover
            kwargs["sender"] = args[0]

        data = self.process(kwargs)
        for subscriber in self.subscribers.values():
            subscriber.put(data)


class SignalSubscriber(Generic[T]):
    """Subscriber that receives events from a signal subscription."""

    loop: asyncio.AbstractEventLoop

    def __init__(self, subscription: SignalSubscription) -> None:
        """
        Create a new subscriber.

        :param subscription: The subscription this subscriber is for.
        """
        self.subscription = subscription
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=subscription.max_backlog)
        self.backlog_full = False

    def put(self, data: dict[str, Any]) -> None:
        """
        Add an event for this subscriber to receive.

        Django dispatches a signal on whichever thread made the change, and mutations run their
        ORM work in a thread executor, so this is usually not the event loop's thread.
        `asyncio.Queue` is not thread-safe: adding to it from another thread marks the waiting
        subscriber as ready but does not wake the event loop, which then stays asleep until
        something else happens to wake it.
        """
        try:
            self.loop.call_soon_threadsafe(self._put, data)
        except RuntimeError:
            logger.debug("Event loop is closed, dropping event for subscriber.")

    def _put(self, data: dict[str, Any]) -> None:
        # Runs on the event loop's thread, so the queue and the flag are safe to touch here.
        try:
            self.events.put_nowait(data)
        except asyncio.QueueFull:
            self.backlog_full = True

    async def subscribe(self) -> AsyncGenerator[T, None]:
        """Begin receiving events from the subscription."""
        self.loop = asyncio.get_running_loop()
        key = uuid.uuid4()
        self.subscription.subscribers[key] = self
        try:
            while True:
                # Events have been lost, so the stream has a gap in it. Clients cannot detect
                # that themselves, so end the subscription and let them resubscribe.
                if self.backlog_full:
                    raise GraphQLSubscriptionBacklogFullError

                try:
                    event = await asyncio.wait_for(self.events.get(), timeout=self.subscription.timeout)
                except TimeoutError as error:
                    raise GraphQLSubscriptionTimeoutError from error

                if self.subscription.filter(event):
                    continue

                yield self.subscription.transform(event)
        finally:
            self.subscription.subscribers.pop(key, None)


class QueryTypeSignalSubscription(SignalSubscription[TModel], ABC):
    """Signal subscription for returning model instances through a QueryType."""

    def __init__(
        self,
        query_type: type[QueryType],
        /,
        *,
        dispatch_uid: str | None = None,
        description: str | None = None,
        timeout: float | None = None,
        max_backlog: int = 100,
    ) -> None:
        """
        Create a new signal subscription that resolves using a QueryType.

        :param query_type: The QueryType to use for the subscription.
        :param dispatch_uid: The dispatch uid for the signal.
        :param description: The description for the subscription.
        :param timeout: How long to wait between signals before timing out.
        :param max_backlog: How many events a subscriber may fall behind by before
                            its subscription ends. Set to 0 for no limit.
        """
        self.query_type = query_type
        super().__init__(
            sender=query_type.__model__,
            dispatch_uid=dispatch_uid,
            description=description,
            timeout=timeout,
            max_backlog=max_backlog,
        )


class ModelSaveSubscription(QueryTypeSignalSubscription[TModel]):
    """Subscription that sends an event after a model instance has been saved."""

    signal = post_save

    def transform(self, params: PostSaveParams[TModel]) -> TModel:  # type: ignore[override]
        return params["instance"]


class ModelCreateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been created."""

    def filter(self, params: PostSaveParams[TModel]) -> bool:  # type: ignore[override]
        return not params["created"]


class ModelUpdateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been updated."""

    def filter(self, params: PostSaveParams[TModel]) -> bool:  # type: ignore[override]
        return params["created"]


class ModelDeleteSubscription(QueryTypeSignalSubscription[TModel]):
    """Subscription that sends an event before a model instance has been deleted."""

    signal = pre_delete

    def process(self, params: PostDeleteParams[TModel]) -> PostDeleteParams[TModel]:  # type: ignore[override]
        # It's possible that the instance is no longer in the database when
        # a subscriber receives the event. Therefore, make a deepcopy of it
        # so that its pk is still available when querying for the output.
        # However, relations cannot be queried since they are not prefetched.
        params["instance"] = deepcopy(params["instance"])
        return params

    def transform(self, params: PostDeleteParams[TModel]) -> TModel:  # type: ignore[override]
        return params["instance"]
