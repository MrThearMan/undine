from __future__ import annotations

import dataclasses
from asyncio import create_task, gather, get_event_loop
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from django.core import signals

from undine.exceptions import (
    GraphQLDataLoaderDidNotReturnSortedSequenceError,
    GraphQLDataLoaderWrongNumberOfValuesReturnedError,
)

if TYPE_CHECKING:
    import asyncio
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
    ) -> None:
        """
        Create a new DataLoader.

        :param load_fn: Coroutine function used to load the data for the given keys.
        :param max_batch_size: Maximum number of keys to load in a single batch.
        :param reuse_loads: Whether loads should be reused for the same load key.
        :param key_hash_fn: Function used to generate a hash from a load key. Required if load key is not hashable.
        """
        self.load_fn = load_fn
        self.max_batch_size = max_batch_size
        self.reuse_loads = reuse_loads
        self.key_hash_fn = key_hash_fn

        self.loads_map: MutableMapping[Hashable, DataLoaderTask[TKey, TResult]] = {}
        """Loads that have been scheduled or completed. Only used if `reuse_loads` is `True`."""

        self.current_batch: DataLoaderBatch[TKey, TResult] = DataLoaderBatch(loader=self)
        """Current batch of loads."""

        # Loads are only reused during the same request.
        # For reusing across requests and web server workers, you should implement caching yourself.
        # This should likely be done in the `load_fn` function.
        signals.request_finished.connect(self._request_finished)

    @property
    def loop(self) -> AbstractEventLoop:
        return get_event_loop()

    def load(self, key: TKey) -> Future[TResult]:
        """Schedule a load for the given key."""
        if self.reuse_loads:
            task = self.loads_map.get(self.key_hash_fn(key))
            if task is not None and not task.future.cancelled():
                return task.future

        if self.current_batch.should_create_new_batch:
            self.current_batch = DataLoaderBatch(loader=self)

        future = self.loop.create_future()
        task = DataLoaderTask(key=key, future=future)

        self.current_batch.tasks.append(task)
        if self.reuse_loads:
            self.loads_map[self.key_hash_fn(key)] = task

        return future

    def load_many(self, keys: Iterable[TKey]) -> Future[list[TResult]]:
        """Schedule loads for the given keys."""
        return gather(*map(self.load, keys))

    def clear(self, key: TKey) -> Self:
        """Remove reusable load by the given key."""
        if self.reuse_loads:
            self.loads_map.pop(self.key_hash_fn(key), None)
        return self

    def clear_many(self, keys: Iterable[TKey]) -> Self:
        """Remove reusable loads by the given keys."""
        if self.reuse_loads:
            for key in keys:
                self.loads_map.pop(self.key_hash_fn(key), None)
        return self

    def clear_all(self) -> Self:
        """Remove all reusable loads."""
        if self.reuse_loads:
            self.loads_map.clear()
        return self

    def prime(self, key: TKey, value: TResult) -> Self:
        """Add a value as a completed load for the given key."""
        return self.prime_many(keys=[key], values=[value])

    def prime_many(self, keys: SortedSequence[TKey], values: SortedSequence[TResult]) -> Self:
        """
        Add values to as completed loads for the given keys.
        A key in the keys sequence should match the value at the same index in the values sequence.
        """
        if not self.reuse_loads:
            return self

        if len(keys) != len(values):
            msg = "`keys` and `values` must have the same length"
            raise ValueError(msg)

        for key, value in zip(keys, values, strict=False):
            key_hash = self.key_hash_fn(key)
            if key_hash in self.loads_map:
                continue

            future = self.loop.create_future()
            future.set_result(value)
            task = DataLoaderTask(key=key, future=future)
            self.loads_map[key_hash] = task

        if not self.current_batch.dispatched:
            for task in self.current_batch.tasks:
                if task.key in keys:
                    index = keys.index(task.key)
                    task.future.set_result(values[index])

            # Remove any tasks form the current batch which now have a result
            self.current_batch.tasks[:] = [task for task in self.current_batch.tasks if not task.future.done()]

        return self

    def _request_finished(self, sender: type, **kwargs: Any) -> None:
        """Clear all reusable loads when a request finishes."""
        self.clear_all()


@dataclasses.dataclass(slots=True, kw_only=True)
class DataLoaderBatch(Generic[TKey, TResult]):
    """A single batch of data to be loaded."""

    loader: DataLoader[TKey, TResult]
    """The DataLoader this batch belongs to."""

    tasks: list[DataLoaderTask[TKey, TResult]] = dataclasses.field(default_factory=list)
    """Load tasks that should be scheduled for this batch."""

    dispatched: bool = False
    """Whether the batch has been dispatched or not."""

    canceled: bool = False
    """Whether the batch has been canceled or not."""

    def __post_init__(self) -> None:
        # Immediately schedule the batch to be dispatched when GraphQL operation resolves.
        # This also retains the reference to the batch if a new batch is created.
        self.loader.loop.call_soon(create_task, self.dispatch())

    @property
    def should_create_new_batch(self) -> bool:
        return self.dispatched or (self.loader.max_batch_size and len(self.tasks) >= self.loader.max_batch_size)

    async def dispatch(self) -> None:
        self.dispatched = True

        self.tasks[:] = [task for task in self.tasks if not task.future.done()]
        if not self.tasks:
            return

        keys = [task.key for task in self.tasks]

        try:
            values = await self.load(keys)

            if not isinstance(values, list | tuple):
                raise GraphQLDataLoaderDidNotReturnSortedSequenceError(got=type(values))  # noqa: TRY301

            if len(values) != len(keys):
                raise GraphQLDataLoaderWrongNumberOfValuesReturnedError(got=len(values), expected=len(keys))  # noqa: TRY301

        except Exception as error:  # noqa: BLE001
            for task in self.tasks:
                if not task.future.done():
                    task.future.set_exception(error)
            return

        for task, value in zip(self.tasks, values, strict=True):
            if task.future.done():
                continue

            if isinstance(value, BaseException):
                task.future.set_exception(value)
            else:
                task.future.set_result(value)

    def load(self, keys: list[TKey]) -> asyncio.Task[list[TResult]]:
        load_task = self.loader.loop.create_task(self.loader.load_fn(keys))

        # Cachel the load in case a future is cancelled and all other tasks are done while the load is still running.
        # This can happen for example when a task group is cancelled due to an exception in one of its tasks.
        def callback(future: Future) -> None:
            if future.cancelled() and all(task_.future.done() for task_ in self.tasks):
                load_task.cancel()

        for task in self.tasks:
            task.future.add_done_callback(callback)

        return load_task


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class DataLoaderTask(Generic[TKey, TResult]):
    """A single task in a DataLoader batch that contains the future where the data is loaded."""

    key: TKey
    """The load key for this task."""

    future: Future[TResult]
    """The future that will be set when the task is completed."""
