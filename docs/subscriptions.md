# Subscriptions

In this section, we'll cover how you can add subscriptions to your schema.
Subscriptions are a way to get real-time updates from your server through
your GraphQL Schema.

## Setup

To use subscriptions, you'll need to turn on Undine's [async support](async.md),
and use the [channels integration](integrations.md#channels). This will set you up
with a web server capable of [GraphQL over WebSocket] protocol. You'll also need
a client capable of using the protocol.

[GraphQL over WebSocket]: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverWebSocket.md

Now, you can create a new [`RootType`](schema.md#roottypes) called `Subscription`
and add `Entrypoints` that return an [AsyncIterable]{:target="_blank"}, usually
an [AsyncGenerator]{:target="_blank"}.

[AsyncIterable]: https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes:~:text=close-,AsyncIterable,-%5B1%5D
[AsyncGenerator]: https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes:~:text=__aiter__-,AsyncGenerator,-%5B1%5D

## AsyncGenerators

Let's take a look at a simple example of a subscription that counts down from 10 to 0.
This subscription is set up using an `AsyncGenerator` function.

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
on the function's return type, so typing it is required.

To add arguments for the subscription, you can add them to the function signature.
Typing these arguments is required to determine their input type.

```python
-8<- "subscriptions/subscription_arguments.py"
```

This will create the following subscription in the GraphQL schema:

```graphql
type Subscription {
    countdown(start: Int! = 10): Int!
}
```

## AsyncIterables

You can also use an `AsyncIterable` instead of creating an `AsyncGenerator` function.
Note that the `AsyncIterable` needs to be returned from the `Entrypoint` function,
not used as the `Entrypoint` reference itself. Otherwise, they work similarly to
`AsyncGenerators`.

```python
-8<- "subscriptions/subscription_async_iterable.py"
```

## Exceptions

If an exception is raised in the subscription, the subscription will be closed
and an error message will be sent to the client. You should raise exceptions
subclassing `GraphQLError` for better error messages, or use the `GraphQLErrorGroup`
to raise multiple errors at once.

```python
-8<- "subscriptions/subscription_exception.py"
```

You can also yield a `GraphQLError` from the subscription, which will send
an error while keeping the subscription open. Adding the error to the return
type does not change the return type of the subscription.

```python
-8<- "subscriptions/subscription_exception_return.py"
```

## Permissions

As subscriptions use `Entrypoints`, you can use their permission checks to
set per-value permissions for the subscription. Raising an exception from
a permission check will close the subscription and send an error message
to the client.

```python
-8<- "subscriptions/subscription_permissions.py"
```

You can also configure permission checks for establishing a websocket connection
using the [`WEBSOCKET_CONNECTION_INIT_HOOK`](settings.md#websocket_connection_init_hook)
setting.

```python
-8<- "subscriptions/subscription_permissions_connection_init.py"
```
