# FAQ

Here are some common questions you might have when it comes to using Undine
or why it's designed the way it is. If you don't find an answer here,
please ask a question on [the discussion page](https://github.com/MrThearMan/undine/discussions).

## Why are all the methods dunder method on, e.g., the `QueryType` class?

This is to avoid name collisions with possible names of `Fields` that
can be added to the class body of a `QueryType` class. In GraphQL, all names
starting with two underscores are reserved by GraphQL, e.g. `__typename`,
so by this logic, all dunder methods cannot collide with any fields you might want.

## Is X feature coming in the future?

Here are some features that are planned for the future:

- Async support
- Subscriptions (requires async support)
- `UnionType` and `InterfaceType` `Entrypoint` pagination using `Connections`
- `UnionType` and `InterfaceType` filtering and ordering across types
- Optimizations for bulk and nested mutations
- `@defer` and `@stream` using [StreamingHttpResponse]{:target="_blank"} (requires `graphql-core` >= 3.3.0)

[StreamingHttpResponse]: https://docs.djangoproject.com/en/5.2/ref/request-response/#django.http.StreamingHttpResponse

If you have a feature request, please [open an issue](contributing.md#i-have-a-feature-request)!
