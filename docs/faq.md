---
description: Frequently asked questions about Undine.
---

# FAQ

Here are some common questions you might have when it comes to using Undine
or why it's designed the way it is. If you don't find an answer here,
please ask a question on [the discussion page](https://github.com/MrThearMan/undine/discussions).

## Why are all the methods dunder methods on, e.g., the `QueryType` class?

This is to avoid name collisions with possible names of `Fields` that
can be added to the class body of a `QueryType` class. In GraphQL, all names
starting with two underscores are reserved by GraphQL, e.g. `__typename`,
so by this logic, all dunder methods cannot collide with any fields you might want.

## How do I serve multiple schemas from one project?

Undine serves one schema, set with the [`SCHEMA`](settings.md#schema) setting.
If you need, for example, a public API and an admin API, you have two options.

If the schemas are mostly the same, use [visibility](visibility.md) to hide parts of
the schema from some users. This way you only need one schema and one service.

If the schemas are very different, or the per-request overhead of visibility is too much,
run two services from the same codebase. Point the `SCHEMA` setting of each service to
a different schema file, for example using a separate settings module or an environment variable.
This also lets the services use different settings, since all Undine settings are global.

Note that the [`QueryType` registry](queries.md#querytype-registry) allows only one `QueryType`
for each model. If a service imports both schemas, two `QueryTypes` for the same model will
conflict. Make sure each service only imports its own schema, or set `register=False` on
the additional `QueryType`.
