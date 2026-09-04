from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from contextlib import aclosing
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic

from django.db.models.signals import post_save, pre_delete

from undine.brokers import get_subscription_broker
from undine.exceptions import GraphQLSubscriptionTimeoutError
from undine.typing import T, TModel
from undine.utils.model_utils import deserialize_model_instance, serialize_model_instance, serialize_model_pk

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from django.dispatch import Signal

    from undine import QueryType
    from undine.typing import ModelDeleteEvent, ModelSaveEvent, PostDeleteParams, PostSaveParams

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

        # Connected under the topic rather than the given dispatch uid, so that a process
        # publishes each event to a topic once, however many subscriptions share the topic.
        self.signal.connect(self.receiver, sender=sender, dispatch_uid=self.topic)

    @cached_property
    def topic(self) -> str:
        """
        The name of the stream this subscription's events are published to and received from.

        Every process must arrive at the same name, or an event published in one process
        never reaches the subscribers in another one. The name is therefore built from
        values that do not depend on the process that computes it. Subscriptions that
        share a name must also serialize their events the same way, since only one
        of them publishes to it.
        """
        identity = "|".join([
            type(self).__module__,
            type(self).__qualname__,
            str(self.sender),
            str(self.dispatch_uid),
        ])
        digest = hashlib.md5(identity.encode(), usedforsecurity=False).hexdigest()
        return f"undine.signal.{digest}"

    @property
    @abstractmethod
    def signal(self) -> Signal:
        """The signal to subscribe to."""

    @abstractmethod
    def serialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Turn the signal's arguments into an event that a broker can carry to another process.

        Runs in the process that dispatched the signal. Only values that the broker's transport
        can carry survive the trip, so model instances and querysets must be reduced to
        primitives here.
        """

    @abstractmethod
    def transform(self, event: dict[str, Any]) -> T:
        """Transform the given event into the desired output."""

    def filter(self, event: dict[str, Any]) -> bool:
        """Should the given event be filtered out?"""
        return False

    def create_subscriber(self) -> SignalSubscriber[T]:
        return SignalSubscriber(self)

    def receiver(self, *args: Any, **kwargs: Any) -> None:
        """Receiver for the Django signal."""
        # Some signals might send the 'sender' argument as a positional argument
        if args:  # pragma: no cover
            kwargs["sender"] = args[0]

        broker = get_subscription_broker()
        broker.publish(self.topic, self.serialize(kwargs))


class SignalSubscriber(Generic[T]):
    """Subscriber that receives events from a signal subscription."""

    def __init__(self, subscription: SignalSubscription) -> None:
        """
        Create a new subscriber.

        :param subscription: The subscription this subscriber is for.
        """
        self.subscription = subscription

    async def subscribe(self) -> AsyncGenerator[T, None]:
        """Begin receiving events from the subscription."""
        subscription = self.subscription
        broker = get_subscription_broker()
        events = broker.subscribe(subscription.topic, max_backlog=subscription.max_backlog)

        async with aclosing(events):
            while True:
                try:
                    event = await asyncio.wait_for(anext(events), timeout=subscription.timeout)
                except TimeoutError as error:
                    raise GraphQLSubscriptionTimeoutError from error

                if subscription.filter(event):
                    continue

                yield subscription.transform(event)


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

    def serialize(self, params: PostSaveParams[TModel]) -> ModelSaveEvent:  # type: ignore[override]
        return {"pk": serialize_model_pk(params["instance"]), "created": params["created"]}

    def transform(self, event: ModelSaveEvent) -> Any:  # type: ignore[override]
        # Only the primary key travels with the event, so that the instance is read through
        # the QueryType in the process that receives it, and the optimizer stays in play.
        return event["pk"]


class ModelCreateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been created."""

    def filter(self, event: ModelSaveEvent) -> bool:  # type: ignore[override]
        return not event["created"]


class ModelUpdateSubscription(ModelSaveSubscription[TModel]):
    """Subscription that sends an event after a model instance has been updated."""

    def filter(self, event: ModelSaveEvent) -> bool:  # type: ignore[override]
        return event["created"]


class ModelDeleteSubscription(QueryTypeSignalSubscription[TModel]):
    """Subscription that sends an event before a model instance has been deleted."""

    signal = pre_delete

    def serialize(self, params: PostDeleteParams[TModel]) -> ModelDeleteEvent:  # type: ignore[override]
        # The row is gone by the time a subscriber receives the event, so the instance's own
        # columns travel with it. Its many-to-many relations do not, since reading them
        # queries rows that may already be deleted.
        return {"snapshot": serialize_model_instance(params["instance"])}

    def transform(self, event: ModelDeleteEvent) -> TModel:  # type: ignore[override]
        return deserialize_model_instance(event["snapshot"])  # type: ignore[return-value]
