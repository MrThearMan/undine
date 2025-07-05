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

- `UnionType` and `InterfaceType` `Entrypoint` pagination using `Connections`
- `UnionType` and `InterfaceType` filtering and ordering across types
- Optimizations for bulk and nested mutations
- `@defer` and `@stream` using [StreamingHttpResponse]{:target="_blank"} (requires `graphql-core` >= 3.3.0)
- [Multipart HTTP protocol for GraphQL Subscriptions]{:target="_blank"}
- [Server-side events]{:target="_blank"}

[StreamingHttpResponse]: https://docs.djangoproject.com/en/stable/ref/request-response/#django.http.StreamingHttpResponse
[Multipart HTTP protocol for GraphQL Subscriptions]: https://www.apollographql.com/docs/graphos/routing/operations/subscriptions/multipart-protocol
[Server-side events]: https://github.com/enisdenjo/graphql-sse

If you have a feature request, please [open an issue](contributing.md#i-have-a-feature-request)!
