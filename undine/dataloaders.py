from __future__ import annotations

import asyncio
import dataclasses
from asyncio import gather, get_running_loop
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from django.core import signals

from undine.exceptions import (
    GraphQLDataLoaderDidNotReturnSortedSequenceError,
    GraphQLDataLoaderPrimingError,
    GraphQLDataLoaderWrongNumberOfValuesReturnedError,
)

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop, Future
    from collections.abc import Callable, Coroutine, Hashable, Iterable, MutableMapping

    from undine.typing import SortedSequence


__all__ = [
    "DataLoader",
]


TKey = TypeVar("TKey")
TResult = TypeVar("TResult")


class DataLoader(Generic[TKey, TResult]):
    """A utility for loading data in batches. Requires an async server."""

    def __init__(
        self,
        *,
        load_fn: Callable[[list[TKey]], Coroutine[None, None, SortedSequence[TResult | BaseException]]],
        max_batch_size: int | None = None,
        reuse_loads: bool = True,
        key_hash_fn: Callable[[TKey], Hashable] = lambda x: x,
        lock: asyncio.Lock | None = None,
    ) -> None:
        """
        Create a new DataLoader.

        :param load_fn: Coroutine function used to load the data for the given keys.
        :param max_batch_size: Maximum number of keys to load in a single batch.
                                If `None`, all keys will be loaded in a single batch.
        :param reuse_loads: Whether loads should be reused for the same load key.
        :param key_hash_fn: Function used to generate a hash from a load key.
                            Loads with the same hash will be reused if `reuse_loads` is `True`.
                            Required if load key is not hashable.
        :param lock: A lock used to synchronize load function execution.
                     Can provide a common lock for multiple DataLoaders
                     if they can load the same object from different keys.
                     This way they don't fetch the same object twice.
        """
        self.load_fn = load_fn
        self.max_batch_size = max_batch_size
        self.reuse_loads = reuse_loads
        self.key_hash_fn = key_hash_fn
        self.lock = lock or asyncio.Lock()

        self.reusable_loads: MutableMapping[Hashable, DataLoaderFuture[TKey, TResult]] = {}
        """Loads that have been scheduled or completed and can be reused for the given key."""

        self.current_batch: DataLoaderBatch[TKey, TResult] = DataLoaderBatch(loader=self, dispatched=True)
        """Current batch of loads."""

        # Loads are only reused during the same request.
        # For reusing across requests or web server workers, you should implement caching yourself.
        # This should likely be done in the `load_fn` function.
        signals.request_finished.connect(self._request_finished)

    @property
    def loop(self) -> AbstractEventLoop:
        return get_running_loop()

    @property
    def should_create_new_batch(self) -> bool:
        current_batch = self.current_batch
        return current_batch.dispatched or (self.max_batch_size and len(current_batch.loads) >= self.max_batch_size)

    def load(self, key: TKey) -> Future[TResult | BaseException]:
        """Schedule a load for the given key."""
        if self.reuse_loads:
            load = self.reusable_loads.get(self.key_hash_fn(key))
            if load is not None and not load.future.cancelled():
                return load.future

        if self.should_create_new_batch:
            self.current_batch = DataLoaderBatch(loader=self)

        load = DataLoaderFuture(key=key, future=self.loop.create_future())

        self.current_batch.loads.append(load)
        if self.reuse_loads:
            self.reusable_loads[self.key_hash_fn(key)] = load

        return load.future

    def load_many(self, keys: Iterable[TKey]) -> Future[list[TResult | BaseException]]:
        """Schedule loads for the given keys."""
        return gather(*map(self.load, keys), return_exceptions=True)

    def clear(self, key: TKey) -> Self:
        """Remove a load by the given key from the reusable loads."""
        if self.reuse_loads:
            self.reusable_loads.pop(self.key_hash_fn(key), None)
        return self

    def clear_many(self, keys: Iterable[TKey]) -> Self:
        """Remove loads by the given keys from the reusable loads."""
        if self.reuse_loads:
            for key in keys:
                self.reusable_loads.pop(self.key_hash_fn(key), None)
        return self

    def clear_all(self) -> Self:
        """Remove all loads from the reusable loads."""
        if self.reuse_loads:
            self.reusable_loads.clear()
        return self

    def prime(
        self,
        key: TKey,
        value: TResult | BaseException,
        *,
        can_prime_pending_loads: bool = False,
    ) -> Self:
        """
        Add a value to reusable loads for the given key.

        :param key: The key to prime.
        :param value: The value to prime.
        :param can_prime_pending_loads: If `True`, pending loads for the key can also be primed.
        """
        return self.prime_many(keys=[key], values=[value], can_prime_pending_loads=can_prime_pending_loads)

    def prime_many(
        self,
        keys: SortedSequence[TKey],
        values: SortedSequence[TResult | BaseException],
        *,
        can_prime_pending_loads: bool = False,
    ) -> Self:
        """
        Add values to reusable loads for the given keys.
        A key in the keys sequence should match the value at the same index in the values sequence.

        :param keys: The keys to prime.
        :param values: The values to prime.
        :param can_prime_pending_loads: If `True`, pending loads for the key can also be primed.
        """
        if not self.reuse_loads:
            return self

        if len(keys) != len(values):
            raise GraphQLDataLoaderPrimingError(keys=len(keys), values=len(values))

        loads_changed = False

        for key, value in zip(keys, values, strict=False):
            key_hash = self.key_hash_fn(key)
            if key_hash in self.reusable_loads:
                if can_prime_pending_loads:
                    load = self.reusable_loads[key_hash]
                    if not load.future.done():
                        # Some loads in the current batch might now be completed and can be removed from it.
                        loads_changed = True
                        if isinstance(value, BaseException):
                            load.future.set_exception(value)
                        else:
                            load.future.set_result(value)

                continue

            # There might be loads for the same keys in the current batch
            # if a load was first cleared and then primed again.
            loads_changed = True
            load = DataLoaderFuture(key=key, future=self.loop.create_future())
            self.reusable_loads[key_hash] = load

            if isinstance(value, BaseException):
                load.future.set_exception(value)
            else:
                load.future.set_result(value)

        if loads_changed:
            self._prime_batch(keys, values)

        return self

    def _prime_batch(self, keys: SortedSequence[TKey], values: SortedSequence[TResult | BaseException]) -> None:
        """Set values for loads in the current batch for the given keys."""
        if self.current_batch.dispatched:
            return

        if len(keys) != len(values):
            raise GraphQLDataLoaderPrimingError(keys=len(keys), values=len(values))

        batch_updated = False

        for load in self.current_batch.loads:
            if load.future.done():
                continue

            if load.key in keys:
                batch_updated = True
                value = values[keys.index(load.key)]

                if isinstance(value, BaseException):
                    load.future.set_exception(value)
                else:
                    load.future.set_result(value)

        if batch_updated:
            self.current_batch.loads[:] = [load for load in self.current_batch.loads if not load.future.done()]

    def _request_finished(self, sender: type, **kwargs: Any) -> None:
        """Hook to run after each request to do some cleanup."""
        # Clear reusable loads so that we don't reuse them for the next request.
        self.clear_all()
        # Create a new empty dispatched batch so that completed loads from current batch can be freed from memory.
        self.current_batch = DataLoaderBatch(loader=self, dispatched=True)


@dataclasses.dataclass(slots=True, kw_only=True)
class DataLoaderBatch(Generic[TKey, TResult]):
    """A batch of loads to be loaded for a DataLoader."""

    loader: DataLoader[TKey, TResult]
    """The DataLoader this batch belongs to."""

    loads: list[DataLoaderFuture[TKey, TResult]] = dataclasses.field(default_factory=list)
    """Loads that have been scheduled in this batch."""

    dispatched: bool = False
    """Whether the batch has started loading data or not."""

    def __post_init__(self) -> None:
        if not self.dispatched:
            # Schedule the batch to be dispatched after all resolvers in the operation have been executed.
            # This also retains the reference to the batch if a new batch is created.
            self.loader.loop.create_task(self.dispatch())

    async def dispatch(self) -> None:
        """Execute the load function and set the results for the loads in the batch."""
        async with self.loader.lock:
            self.dispatched = True

            self.loads[:] = [load for load in self.loads if not load.future.done()]
            if not self.loads:
                return

            keys = [load.key for load in self.loads]

            try:
                values = await self.load(keys)

                if not isinstance(values, list | tuple):
                    raise GraphQLDataLoaderDidNotReturnSortedSequenceError(got=type(values))  # noqa: TRY301

                if len(values) != len(keys):
                    raise GraphQLDataLoaderWrongNumberOfValuesReturnedError(got=len(values), expected=len(keys))  # noqa: TRY301

            except Exception as error:  # noqa: BLE001
                for load in self.loads:
                    if not load.future.done():
                        load.future.set_exception(error)
                return

            for load, value in zip(self.loads, values, strict=True):
                if load.future.done():
                    continue

                if isinstance(value, BaseException):
                    load.future.set_exception(value)
                else:
                    load.future.set_result(value)

    def load(self, keys: list[TKey]) -> asyncio.Task[list[TResult]]:
        """Schedule the load function to run with the given keys."""
        load_function_task = self.loader.loop.create_task(self.loader.load_fn(keys))

        # Cancel the load function task in case a future expecting results from it is canceled
        # and all other futures are done while the load is still running. This can happen, for example,
        # when a TaskGroup is canceled due to an exception in one of its tasks. Otherwise,
        # the load function might use resources that are no longer available, e.g. a database connection.
        def callback(future: Future[TResult]) -> None:
            if future.cancelled() and all(load_.future.done() for load_ in self.loads):
                load_function_task.cancel()

        for load in self.loads:
            if not load.future.done():
                load.future.add_done_callback(callback)

        return load_function_task


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class DataLoaderFuture(Generic[TKey, TResult]):
    """A Future in a DataLoaderBatch where the data is loaded."""

    key: TKey
    """The load key for this load."""

    future: Future[TResult]
    """The future that will be set when the load is completed."""
