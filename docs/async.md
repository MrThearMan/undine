description: Documentation on async support for Undine.

# Async support

In this section, we'll cover how you can make you schema support async operations.

> Note that asynchronous execution will require an [ASGI capable web server]{:target="_blank"}.

[ASGI capable web server]: https://asgi.readthedocs.io/en/latest/implementations.html

## Setup

To enable async support, you need to set the [`ASYNC`](settings.md#async) setting to `True`.

```python
UNDINE = {
    "ASYNC": True,
}
```

Now your GraphQL endpoint will change from a sync view to an async view.
This allows you to write your `Entrypoint` resolvers as coroutines.

```python
-8<- "async/entrypoint_async.py"
```

Various parts of the `QueryTypes`, `MutationTypes`, and their `Fields` and `Inputs`
can also be made async.

```python
-8<- "async/query_async.py"
```

```python
-8<- "async/mutation_async.py"
```

## Notes

Using async resolvers without `ASYNC` enabled will raise an error
when an operation resolves using that resolver. Existing resolvers e.g. for
`QueryTypes` and `MutationTypes` will automatically adapt to work in an async context
based on the `ASYNC` setting.

Another small detail that is worth noting when `ASYNC` is enabled is that `info.context.user`
is always fetched eagerly, even if it's not used in the operation. This allows using
the request user in synchronous parts of the code without causing an
error due to using the Django ORM directly in an async context.

Asynchronous execution is also _slightly_ slower than synchronous execution
due to inherent overhead of the asyncio event loop.

See Django's [async documentation]{:target="_blank"} for changes that need to be made
for Django to work in async context.

[async documentation]: https://docs.djangoproject.com/en/stable/topics/async/
