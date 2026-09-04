from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Hashable
from threading import Lock
from typing import Generic, TypeVar

from graphql import DocumentNode, GraphQLError

from undine.settings import undine_settings
from undine.typing import ParseCacheKey, ValidationCacheKey

__all__ = [
    "ParseCache",
    "ValidationCache",
]


TKey = TypeVar("TKey", bound=Hashable)
TValue = TypeVar("TValue")


class _LRUCache(ABC, Generic[TKey, TValue]):
    """A thread-safe cache that discards the least recently used value when it becomes too large."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.values: OrderedDict[TKey, TValue] = OrderedDict()

    @property
    @abstractmethod
    def max_size(self) -> int: ...

    def get(self, key: TKey) -> TValue | None:
        """Get the value for the given key. Returns `None` if the key is not in the cache."""
        with self.lock:
            if key not in self.values:
                return None

            self.values.move_to_end(key)
            return self.values[key]

    def set(self, key: TKey, value: TValue) -> None:
        """Set the value for the given key, discarding the least recently used values above `max_size`."""
        with self.lock:
            self.values[key] = value
            self.values.move_to_end(key)

            while len(self.values) > self.max_size:
                self.values.popitem(last=False)

    def clear(self) -> None:
        """Remove all values from the cache."""
        with self.lock:
            self.values.clear()


class ParseCache(_LRUCache[ParseCacheKey, DocumentNode]):
    @property
    def max_size(self) -> int:
        return undine_settings.PARSE_CACHE_MAX_SIZE


class ValidationCache(_LRUCache[ValidationCacheKey, list[GraphQLError]]):
    @property
    def max_size(self) -> int:
        return undine_settings.VALIDATION_CACHE_MAX_SIZE
