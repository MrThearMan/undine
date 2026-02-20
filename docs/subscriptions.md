description: Documentation on subscriptions in Undine.

# Subscriptions

In this section, we'll cover how you can add subscriptions to your schema.
Subscriptions are a way to get real-time updates from your server through
your GraphQL Schema.

## Setup

To use subscriptions, you'll need to turn on Undine's [async support](async.md),
as subscription resolvers are always async. Then, you have two options
for a transport protocol: [WebSockets](#websockets) or [Server-Sent Events](#server-sent-events).

### WebSockets

WebSockets use a persistent TCP connection between the client and server.
They have broad client library support in the GraphQL ecosystem, making them
a good choice when your client tooling expects WebSocket-based subscriptions.

To use WebSockets, you'll need use Undine's [`channels` integration](integrations.md#channels).
See the [GraphQL over WebSocket protocol]{:target="_blank"} for details on how the protocol works.

[GraphQL over WebSocket protocol]: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverWebSocket.md

### Server-Sent Events

Server-Sent Events (SSE) use regular HTTP, which means they work through standard
load balancers, proxies, and firewalls without special configuration. Since
GraphQL subscriptions are inherently server-to-client, SSE is a natural fit
and can be simpler to deploy than WebSockets.

SSE can operate in two modes: [Distinct Connections mode](#distinct-connections-mode)
and [Single Connection mode](#single-connection-mode).

#### Distinct Connections mode

In [Distinct Connections]{:target="_blank"} mode, each subscription opens its own SSE connection.
This is the simpler mode and requires no extra setup beyond [async support](async.md).

However, when using HTTP/1.1, browsers limit SSE connections to 6 per browser and domain,
so you should use a web server capable of HTTP/2 in production.
You can use [`USE_SSE_DISTINCT_CONNECTIONS_FOR_HTTP_1`](settings.md#use_sse_distinct_connections_for_http_1)
to allow Distinct Connections mode over HTTP/1.1, if you know this isn't going to be an issue for your use case.

[Distinct Connections]: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverSSE.md#distinct-connections-mode

#### Single Connection mode

In [Single Connection]{:target="_blank"} mode, all operations are multiplexed over a single SSE connection,
which avoids the HTTP/1.1 connection limit. This mode requires Undine's
[`channels` integration](integrations.md#channels).

[Single Connection]: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverSSE.md#single-connection-mode

Unlike the [reference implementation]{:target="_blank"}, which keeps state
in-memory within a single process, Undine stores stream and operation state in
[Django sessions]{:target="_blank"} to guarantee a single connection in multi-worker deployments.
This changes the implementation slightly compared to the reference implementation:

[reference implementation]: https://github.com/enisdenjo/graphql-sse/
[Django sessions]: https://docs.djangoproject.com/en/stable/topics/http/sessions/

1. Due to the possibility of session state becoming stale in case the client
   loses its stream connection, Undine's implementation allows creating a new stream
   even if one is already open. In this case, the existing stream is closed
   and replaced with a new one. The reference implementation always returns
   `409 Conflict` if a stream is already open.

2. Using sessions also means that Undine's implementation requires authentication,
   while the reference implementation does not enforce this.

Single Connection mode uses [Django's cache framework]{:target="_blank"} and [channel layers]{:target="_blank"}
for state coordination. This requires both the cache backend and channel layer to work in multi-worker deployments.
The cache backend should also support atomic `cache.add`. For example, using [redis cache]{:target="_blank"}
and [`channels-redis`][channels-redis]{:target="_blank"} satisfies both requirements:

[Django's cache framework]: https://docs.djangoproject.com/en/stable/topics/cache
[channel layers]: https://channels.readthedocs.io/en/stable/topics/channel_layers.html
[redis cache]: https://docs.djangoproject.com/en/stable/topics/cache/#redis
[channels-redis]: https://github.com/django/channels_redis

```python
-8<- "subscriptions/sse_redis_settings.py"
```

## AsyncGenerators

The simplest way of creating subscriptions is by using an [`AsyncGenerator`][AsyncGenerator] function.
Let's take a look at a simple example of a subscription that counts down from 10 to 0.

[AsyncGenerator]: https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes:~:text=__aiter__-,AsyncGenerator,-%5B1%5D

```python
-8<- "subscriptions/subscription.py"
```

/// details | About method signature

A method decorated with `@Entrypoint` is treated as a static method by the `Entrypoint`.

The `self` argument is not an instance of the `RootType`,
but `root` argument of the `GraphQLField` resolver. To clarify this,
it's recommended to change the argument's name to `root`,
as defined by the [`RESOLVER_ROOT_PARAM_NAME`](settings.md#resolver_root_param_name)
setting.

The value of the `root` argument for an `Entrypoint` is `None` by default,
but can be configured using the [`ROOT_VALUE`](settings.md#root_value)
setting if desired.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

This will create the following subscription in the GraphQL schema:

```graphql
type Subscription {
    countdown: Int!
}
```

Using this subscription, you'll receive the following response 10 times on 1 second intervals,
while the value of the `countdown` field is decreases from 10 to 1.

```json
{
  "data": {
    "countdown": 10
  }
}
```

The subscription's output type will be determined based on the first generic type parameter
on the `AsyncGenerator` return type (in this case `int`), so typing it is required.

To add arguments for the subscription, you can add them to the function signature.
Typing these arguments is also required to determine their input type.

```python
-8<- "subscriptions/subscription_arguments.py"
```

This will create the following subscription in the GraphQL schema:

```graphql
type Subscription {
    countdown(start: Int! = 10): Int!
}
```

If an exception is raised in the function, the subscription will be closed
and an error message will be sent to the client. You should raise exceptions
subclassing `GraphQLError` for better error messages, or use the `GraphQLErrorGroup`
to raise multiple errors at once.

```python
-8<- "subscriptions/subscription_exception.py"
```

You can also yield a `GraphQLError` from the function, which will send
an error while keeping the subscription open. Furthermore, adding the error to the return
type does not change the return type of the subscription.

```python
-8<- "subscriptions/subscription_exception_return.py"
```

## AsyncIterables

You can also use an [`AsyncIterable`][AsyncIterable] instead of creating an `AsyncGenerator` function.
Note that the `AsyncIterable` needs to be returned from the `Entrypoint` function,
not used as the `Entrypoint` reference itself. Otherwise, they work similarly to
`AsyncGenerators`.

[AsyncIterable]: https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes:~:text=close-,AsyncIterable,-%5B1%5D

```python
-8<- "subscriptions/subscription_async_iterable.py"
```

## Signal subscriptions

Undine also supports creating subscriptions for [Django signals]{:target="blank"}
using `SignalSubscriptions`. For example, if you wanted to listen to new `Tasks`
being created, you could add a `ModelCreateSubscription` for the `Task` Model like this.

[Django signals]: https://docs.djangoproject.com/en/stable/ref/signals/

```python
-8<- "subscriptions/subscription_signals.py"
```

Similar subscriptions exists for Model updates (`ModelUpdateSubscription`), deletes (`ModelDeleteSubscription`),
and overall saves (`ModelSaveSubscription`). These subscriptions return data through `QueryTypes`
so queries to them are optimized just like any other query.

> For delete subscriptions, note that the Model instance may have been deleted by the time
> the subscription is executed. You should not rely on the instance existing in the database
> or its relations being connected like you would with a normal query.
>
> However, a copy of the instance is made just before deletion so that you can query
> its details, but not its relations since those have not been prefetched.

For other signals, you can create custom subscriptions by subclassing `undine.subscriptions.SignalSubscription`
and adding the appropriate converters in order to use it in your schema.
See the ["Hacking Undine"](hacking-undine.md#entrypoints) section for more information on how to do this.

## Permissions

As subscriptions use `Entrypoints`, you can use their [permission checks](schema.md#permissions)
to set per-value permissions for the subscription. Raising an exception from
a permission check will close the subscription and send an error message
to the client.

```python
-8<- "subscriptions/subscription_permissions.py"
```

When using GraphQL over WebSocket, you can also configure permission checks for establishing a websocket connection
using the [`WEBSOCKET_CONNECTION_INIT_HOOK`](settings.md#websocket_connection_init_hook)
setting.

```python
-8<- "subscriptions/subscription_permissions_connection_init.py"
```
