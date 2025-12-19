description: DataLoader support in Undine

# DataLoaders

In this section, we'll cover Undine's `DataLoader`, which is a utility for loading data in batches.
`DataLoaders` can be used to optimize the performance of queries that require I/O operations,
like fetching data from an external API.

`DataLoaders` are implemented using python's [asyncio]{:target="_blank"} library,
so you'll need to turn on Undine's [async support](async.md) to use them.

[asyncio]: https://docs.python.org/3/library/asyncio.html

> In most cases, using `DataLoaders` to optimize database queries is not necessary,
> as Undine's [Optimizer](optimizer.md) already handles this for you.

## DataLoader

A `DataLoader` always requires a "load function" (`load_fn`) which implements the actual logic for fetching data.
This function receives a list of "keys" that identify the data that should be fetched.
Let's look at an example which fetches a list of pokemon from an external API by their name.

```python hl_lines="17 18 19 20 21 22 23 24 25"
-8<- "dataloaders/dataloader.py"
```

Here, the `DataLoader` load function `load_pokemon` receives a list of keys (pokemon names in this case)
and makes an equal number of concurrent HTTP requests to an external API to fetch these pokemon information.

The keys which the load function receives for a given GraphQL operation are defined by
calls to `DataLoader.load`, like in the `pokemon_by_name` `Entrypoint` resolver in the above example.
Note that the resolver returns a [`Future`][Furure]{:target="_blank"} object from the `DataLoader`,
and that the function is not async — this is important for the `DataLoader` to work correctly.
This is discussed more thoroughly in the [Technical Details](#technical-details) section.

[Furure]: https://docs.python.org/3/library/asyncio-future.html#asyncio.Future

Given the above setup, if you query `pokemon_by_name` multiple times like this:

```graphql
query {
  slotOne: pokemonByName(name: "pikachu") {
    id
    name
    height
    weight
  }
  slotTwo: pokemonByName(name: "eevee") {
    id
    name
    height
    weight
  }
}
```

The `DataLoader` will run the load function `load_pokemon` once with keys `["pikachu", "eevee"]` to fetch
pokemon information for both `slotOne` and `slotTwo`.

Note that the load function needs to return the loaded values in the same order that it received the keys in,
so that the values can be matched up with the keys by the `DataLoader`. You also cannot return less or more
values than the number of keys you received.

### Returning errors

If the load for a particular key fails, you can return an exception from the load function for that key.
This exception will be converted into a GraphQL error in the response to the client.

```python hl_lines="20 21 22"
-8<- "dataloaders/dataloader_error.py"
```

Note that in this case the `Entrypoint` is made nullable so that only the requests for pokemon that fail to load
will return `null` with an error, and the rest will return the loaded pokemon information.
For example, given the query we defined above, if load for `slotOne` fails, the response will be:

```json
{
  "data": {
    "slotOne": null,
    "slotTwo": {
      "id": 12,
      "name": "eevee",
      "height": 3,
      "weight": 65
    }
  },
  "errors": [
    {
      "message": "Pokemon not found",
      "path": ["slotOne"]
    }
  ]
}
```

### Max batch size

By default, a `DataLoader` will load all keys requested in a GraphQL operation in a single batch.
If you want to limit the number of keys that are loaded in a single batch, you can use the `max_batch_size` parameter.

```python hl_lines="12"
-8<- "dataloaders/dataloader_max_batch_size.py"
```

In this case, limiting the maximum batch size will ensure that we don't send too many
concurrent requests to the external API, which can help avoid timeouts and rate limits.

### Reusing loads

By default, if a `DataLoader` receives a request to load the same key multiple times,
it will reuse the previous load and share the result between them. For example, if you
query the `pokemon_by_name` `Entrypoint` with the following query:

```graphql
query {
  slotOne: pokemonByName(name: "pikachu") {
    name
  }
  slotTwo: pokemonByName(name: "pikachu") {
    name
  }
}
```

The `DataLoader` will run the load function `load_pokemon` once with keys `["pikachu"]` and reuse the result
for both `slotOne` and `slotTwo`. Reuse will happen even if the load happens in a different batches when
a [`max_batch_size`](#max-batch-size) has been set.

If you want to disable reuse, you can set the `reuse_loads` parameter to `False`.

```python hl_lines="12"
-8<- "dataloaders/dataloader_reuse_loads.py"
```

This will result in the `DataLoader` running the load function `load_pokemon` with keys `["pikachu", "pikachu"]` instead,
where the first key matches load for `slotOne` and the second for `slotTwo`.

Note that reused loads should not be treated as a cache, as they are not shared between requests
or web service workers. Since load reuse stores [`Future`][asyncio Future]{:target="_blank"} objects
(see [Technical Details](#technical-details)), it's much easier to add caching in the load function
or in application code using Django's cache API.

[asyncio Future]: https://docs.python.org/3/library/asyncio-future.html#asyncio.Future

### Priming loads

When `DataLoader` [load reuse](#reusing-loads) is enabled, you can prime the `DataLoader` with completed load results
for specific keys without going through the load function. This way if a load would be requested
for a primed key, that primed value would be returned immediately. If batch size is limited using
[`max_batch_size`](#max-batch-size), that load would also not contribute to the size of the batch.

```python hl_lines="30"
-8<- "dataloaders/dataloader_prime.py"
```

Priming can also be useful when loads for the same object can happen by different keys,
for example, if loads for a pokemon can happen by the pokemon's name or its ID.
In this case, you should also provide a common `asyncio.Lock` for the `DataLoaders` so
that one load function can run before the other load functions. You might also want to set
the `can_prime_pending_loads` parameter to `True` so that already pending loads from the
other `DataLoaders` can be set.

```python hl_lines="28 29 30 44 45 46 49 50 51"
-8<- "dataloaders/dataloader_prime_many.py"
```

### Clearing loads

When `DataLoader` [load reuse](#reusing-loads) is enabled, you can also clear reused loads.
A potential use case for this would be if a mutation on the loaded data would be performed
during the GraphQL operation, and the load would therefore need to be re-fetched.

```python hl_lines="19"
-8<- "dataloaders/dataloader_clear.py"
```

### Custom key hash function

When `DataLoader` [load reuse](#reusing-loads) is enabled, loads are mapped internally by the `DataLoader`
from the load key to a [`Future`][asyncio Future]{:target="_blank"} object where the load result will be
stored once it's available. For the load key to be used as a key in a map, it needs to be hashable,
but you can use non-hashable keys by providing a custom key hash function (`key_hash_fn`). A key hash function
is also useful when two different objects should be considered equal when loading them using a `DataLoader`.

[asyncio Future]: https://docs.python.org/3/library/asyncio-future.html#asyncio.Future

```python hl_lines="13 14 15 16 17"
-8<- "dataloaders/dataloader_key_hash_fn.py"
```

## Technical Details

In this section, we'll go over how Undine's `DataLoader` works during a GraphQL operation.
Knowing these details can help you in debugging `DataLoaders`, but are not necessary
for getting started with them.

When a `DataLoder` is created, it adds a signal receiver for the `request_finished` signal.
This receiver is responsible for clearing the `DataLoader's` [reusable loads](#reusing-loads)
when a request finishes, freeing up memory. This ensures that you can reuse the same `DataLoader`
for the next request.

`DataLoaders` can be used in GraphQL resolvers by calling `load` on them.
This creates a new [`Future`][asyncio Future]{:target="_blank"} that will be set when
the data is loaded using the `DataLoader` load function (`load_fn`). If [load reuse](#reusing-loads)
is enabled, calling `load` might also reuse an existing `Future` created by a previous call to `load`
with the same key. The existing `Future` is likely pending, but it can be already completed
if a [maximum batch size](#max-batch-size) has been set and the `Future` was set in a previous batch,
or it can be [primed](#priming-loads) manually.

[asyncio Future]: https://docs.python.org/3/library/asyncio-future.html#asyncio.Future

If a reusable load is found, its `Future` is returned immediately.
Otherwise, the `DataLoader` will check if a new batch needs to be created.
New batches are needed when the previous batch has already been dispatched,
or when the [maximum batch size](#max-batch-size) has been reached.
For the first load of a new request, a new batch will always be created.
This batch is then scheduled in the event loop as a [`Task`][asyncio Task]{:target="_blank"}.

[asyncio Task]: https://docs.python.org/3/library/asyncio-task.html#asyncio.Task

Whether a call to `DataLoder.load` returns an existing `Future` or creates a new one,
the resolver should then return that `Future`. During the execution of a GraphQL operation,
when a resolver returns an awaitable value (like a coroutine or `Future`), that awaitable
is wrapped in a coroutine and saved until all other fields have been resolved.
This allows all resolvers to run before any awaitables are awaited, which makes sure
that `DataLoaders` are populated from all resolvers before the event loop next runs
and any batches are dispatched.

Next, all these resolver coroutines are executed concurrently using [`gather`][asyncio gather]{:target="_blank"},
which turns them into `Tasks` and schedules them to run in the event loop. Then, the `Future` returned by
`gather` is awaited, which hands control back to the event loop. The event loop then decides which order
it runs the batch and resolver `Tasks`. In a resolver `Task`, the resolver
will begin awaiting its awaitable, which in case of `DataLoader` is the `Future` returned by the `load`.

[asyncio gather]: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather

In a batch `Task`, the `DataLoader` load function is scheduled to run using yet another `Task`.
Additionally, all `Futures` in the batch that are waiting for results from the load function `Task` will have
a [done callback]{:target="_blank"} added at this point. This callback will cancel the load function `Task`
if any of the `Futures` waiting for its results are canceled and all other `Futures` are also done.
This can happen, for example, when a [`TaskGroup`][asyncio TaskGroup]{:target="_blank"} is canceled
due to an exception in one of its `Tasks`. Cancelling the load function `Task` in this case ensures that
it won't use resources that are no longer available (e.g. a database connection).

[done callback]: https://docs.python.org/3/library/asyncio-future.html#asyncio.Future.add_done_callback
[asyncio TaskGroup]: https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup

The batch `Task` then begins awaiting for the load function `Task` to complete.
If multiple `DataLoaders` are used in the operation, their batch `Tasks` might also schedule
their load function `Tasks` in the event loop as well. Then each `DataLoader's`
load function `Tasks` are executed, until they have all finished running. Then execution
resumes in the one of the batch `Tasks`, which sets its `Futures` with the results from the load function.

After a batch `Task` returns, the resolver `Tasks` that were waiting for the `Futures` to be set
from this batch can resume and return the `Future` results. The other batch `Tasks` will follow suit
until each batch and resolver `Task` has finished running. Finally, the `gather` `Future` resolves
and fills the response data with the results from each awaitable field resolver.
