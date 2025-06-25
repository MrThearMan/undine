# Async support

In this section, we'll look at how you can make you schema support async operations.

## Setup

To enable async support, you need to set the [`ASYNC`](settings.md#async) setting to `True`.

```python
UNDINE = {
    "ASYNC": True,
}
```

With this, your GraphQL endpoint will change from a sync view to an async view.
This allows you to use async resolvers in your `Fields` and `Entrypoints`.
Permission checks and custom optimizations are still executed synchronously.

```python
-8<- "async/field_async.py"
```

_Custom_ mutations can also be made async. Validation, permission checks,
and after hooks are still executed synchronously.

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
the request user in synchronous parts of the code, like in permission checks (which
cannot be made async due to internal implementation details), without causing an
error due to using the Django ORM directly in an async context.

Asynchronous execution is also _slightly_ slower than synchronous execution
due to inherent overhead of the asyncio event loop.

See Django's [async documentation]{:target="_blank"} for changes that need to be made
for Django to work in async context.

[async documentation]: https://docs.djangoproject.com/en/stable/topics/async/
