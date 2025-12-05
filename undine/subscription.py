from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save

from undine.utils.text import dotpath

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from django.dispatch import Signal

    from undine.typing import M2MChangedParams, PostDeleteParams, PostSaveParams, PreDeleteParams, PreSaveParams

__all__ = [
    "M2MChangedSignalSubscription",
    "PostDeleteSignalSubscription",
    "PostSaveSignalSubscription",
    "PreDeleteSignalSubscription",
    "PreSaveSignalSubscription",
    "SignalSubscriber",
    "SignalSubscription",
]


class SignalSubscription(ABC):  # TODO: Test
    """A subscription that forwards data from a signal."""

    def __init__(self, sender: Any, *, dispatch_uid: str | None = None) -> None:
        self.subscribers: dict[uuid.UUID, SignalSubscriber] = {}
        self.signal.connect(self.receiver, sender=sender, dispatch_uid=dispatch_uid)

    @abstractmethod
    @property
    def signal(self) -> Signal: ...

    @abstractmethod
    def transform(self, params: dict[str, Any]) -> dict[str, Any]: ...

    def subscribe(self) -> SignalSubscriber:
        return SignalSubscriber(self)

    def receiver(self, *args: Any, **kwargs: Any) -> None:
        if args:
            kwargs["sender"] = args[0]

        for subscriber in self.subscribers.values():
            subscriber.events.put(kwargs)


class SignalSubscriber:  # TODO: Test
    """Subscriber that receives events from a signal subscription."""

    def __init__(self, subscription: SignalSubscription) -> None:
        self.subscription = subscription
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def wait_for_events(self) -> AsyncGenerator[dict[str, Any], None]:
        key = uuid.uuid4()
        self.subscription.subscribers[key] = self
        try:
            while True:
                data = await asyncio.wait_for(self.events.get(), timeout=None)
                yield self.subscription.transform(data)
        finally:
            self.subscription.subscribers.pop(key, None)


# Built-in signals


class PreSaveSignalSubscription(SignalSubscription):
    signal = pre_save

    def transform(self, params: PreSaveParams) -> dict[str, Any]:
        return {
            "model": dotpath(params["sender"]),
            "instance": params["instance"].pk,
            "updated_fields": sorted(params["update_fields"] or []),
        }


class PostSaveSignalSubscription(SignalSubscription):
    signal = post_save

    def transform(self, params: PostSaveParams) -> dict[str, Any]:
        return {
            "model": dotpath(params["sender"]),
            "instance": params["instance"].pk,
            "created": params["created"],
            "updated_fields": sorted(params["update_fields"] or []),
        }


class PreDeleteSignalSubscription(SignalSubscription):
    signal = pre_delete

    def transform(self, params: PreDeleteParams) -> dict[str, Any]:
        return {
            "model": dotpath(params["sender"]),
            "instance": params["instance"].pk,
        }


class PostDeleteSignalSubscription(SignalSubscription):
    signal = post_delete

    def transform(self, params: PostDeleteParams) -> dict[str, Any]:
        return {
            "model": dotpath(params["sender"]),
            "instance": params["instance"].pk,
        }


class M2MChangedSignalSubscription(SignalSubscription):
    signal = m2m_changed

    def transform(self, params: M2MChangedParams) -> dict[str, Any]:
        return {
            "model": dotpath(params["sender"]),
            "instance": params["instance"].pk,
            "action": params["action"],
            "reverse": params["reverse"],
            "pk_set": sorted(params["pk_set"]),
        }
