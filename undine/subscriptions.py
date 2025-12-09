from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Generic

from django.db.models.signals import post_save, pre_delete

from undine.exceptions import GraphQLSubscriptionTimeoutError
from undine.typing import T, TModel

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
    ) -> None:
        """
        Create a new subscription.

        :param sender: The model class to subscribe to.
        :param dispatch_uid: The dispatch uid for the signal.
        :param description: The description for the subscription.
        :param timeout: How long to wait between signals before timing out.
        """
        self.sender = sender
        self.dispatch_uid = dispatch_uid
        self.description = description
        self.timeout = timeout

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
        """Receiver fo the Django signal."""
        # Some signals might send the 'sender' argument as a positional argument
        if args:
            kwargs["sender"] = args[0]

        data = self.process(kwargs)
        for subscriber in self.subscribers.values():
            subscriber.events.put_nowait(data)


class SignalSubscriber(Generic[T]):
    """Subscriber that receives events from a signal subscription."""

    def __init__(self, subscription: SignalSubscription) -> None:
        """
        Create a new subscriber.

        :param subscription: The subscription this subscriber is for.
        """
        self.subscription = subscription
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def subscribe(self) -> AsyncGenerator[T, None]:
        """Begin receiving events from the subscription."""
        key = uuid.uuid4()
        self.subscription.subscribers[key] = self
        try:
            while True:
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
    ) -> None:
        """
        Create a new signal subscription that resolves using a QueryType.

        :param query_type: The QueryType to use for the subscription.
        :param dispatch_uid: The dispatch uid for the signal.
        :param description: The description for the subscription.
        :param timeout: How long to wait between signals before timing out.
        """
        self.query_type = query_type
        super().__init__(
            sender=query_type.__model__,
            dispatch_uid=dispatch_uid,
            description=description,
            timeout=timeout,
        )


class ModelSaveSubscription(QueryTypeSignalSubscription[TModel]):
    """Subscription that sends an event after a model instance has been saved."""

    signal = post_save

    def transform(self, params: PostSaveParams[TModel]) -> TModel:
        return params["instance"]


class ModelCreateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been created."""

    def filter(self, params: PostSaveParams[TModel]) -> bool:
        return not params["created"]


class ModelUpdateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been updated."""

    def filter(self, params: PostSaveParams[TModel]) -> bool:
        return params["created"]


class ModelDeleteSubscription(QueryTypeSignalSubscription[TModel]):
    """Subscription that sends an event before a model instance has been deleted."""

    signal = pre_delete

    def process(self, params: PostDeleteParams[TModel]) -> PostDeleteParams[TModel]:
        # It's possible that the instance is no longer in the database when
        # a subscriber receives the event. Therefore, make a deepcopy of it
        # so that its pk is still available when querying for the output.
        # However, relations cannot be queried since they are not prefetched.
        params["instance"] = deepcopy(params["instance"])
        return params

    def transform(self, params: PostDeleteParams[TModel]) -> TModel:
        return params["instance"]
