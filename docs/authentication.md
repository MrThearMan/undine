---
description: Session authentication with Undine.
---

# Authentication

In this section, we'll cover how to log users in and out with GraphQL mutations
using Django's session authentication. Undine doesn't include ready-made authentication
entrypoints. Instead, you can use Django's [authentication functions]{:target="_blank"}
in [function entrypoints](schema.md#function-references) directly.

[authentication functions]: https://docs.djangoproject.com/en/stable/topics/auth/default/#how-to-log-a-user-in

The examples on this page assume that `SessionMiddleware` and `AuthenticationMiddleware`
are in your `MIDDLEWARE` setting.

## Current user

The request is available from the `GQLInfo` object as `info.context.request`,
and the current user as `info.context.request.user`. An entrypoint that returns
the current user, or `null` for anonymous users, can be written like this:

```python
-8<- "authentication/entrypoint_me.py"
```

```graphql
type UserType {
  email: Email!
  username: String!
}

type Query {
  me: UserType
}
```

## Logging in

To log a user in, call `authenticate()` to check the credentials,
and then `login()` to store the user in the session.

```python
-8<- "authentication/entrypoint_login.py"
```

```graphql
type Mutation {
  login(username: String!, password: String!): UserType!
}
```

Note that the request is `info.context.request`, not `info.context`.

After a successful login, the response sets the session cookie, so the following requests
from the client are made as the logged-in user.

> Django rotates the CSRF token when a user logs in. If you use CSRF protection,
> the client must read the new token from the `csrftoken` cookie before making
> the next mutation.

## Logging out

To log a user out, call `logout()`. This removes the user from the session.

```python
-8<- "authentication/entrypoint_logout.py"
```

```graphql
type Mutation {
  logout: Boolean!
}
```

## Async

When using Undine in [async mode](async.md), use the async versions of the functions:
`aauthenticate()`, `alogin()` and `alogout()`. Read the current user with
`await request.auser()`.

```python
-8<- "authentication/entrypoint_async.py"
```

## WebSockets

Logging in and out is not supported over [WebSockets](subscriptions.md).
A WebSocket connection is authenticated once, when the connection opens,
with the session cookie that the browser sends in the handshake.
After that, the server cannot set cookies on the connection, so a login
during the connection could not be stored for the client.

Log in with a normal HTTP request before opening the WebSocket connection.
If the user logs in or out while the connection is open, open a new connection.
