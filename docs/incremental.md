# Incremental Delivery

> Note that incremental delivery is currently experimental and may change in the future.

Undine has experimental support for [incremental delivery][incremental]{:target="_blank"} of data
using the `@defer` and `@stream` directives. To enable incremental delivery,
all of the following must be true:

[incremental]: https://github.com/graphql/graphql-wg/blob/main/rfcs/DeferStream.md

1. [`graphql-core`][graphql-core]{:target="_blank"} version must be `3.3.0a12`
   (note alpha version, later versions might not work)
2. [`EXPERIMENTAL_INCREMENTAL_DELIVERY`](settings.md#experimental_incremental_delivery) must be set to `True`
3. [Async support](async.md) must be enabled

[graphql-core]: https://github.com/graphql-python/graphql-core/

Let's look at an example of incremental delivery using the `@defer` and `@stream` directives.
Given the following schema:

```python
-8<- "incremental/schema.py"
```

If we wanted to query the "slow" field, the client would need to wait for
five seconds for the server to resolve it before it can show any of the other data.

```graphql hl_lines="6"
query {
  tasks {
    id
    name
    done
    slow
  }
}
```

However, using the `@defer` directive, the client can receive the rest of the data immediately and
the deferred data when its complete. The `@defer` directive works on fragment spreads an inline fragments.

```graphql hl_lines="6 7 8"
query {
  tasks {
    id
    name
    done
    ... @defer {
      slow
    }
  }
}
```

Similarly, if we wanted to query the "countdown" field, the client would need to wait for
ten seconds for the entire countdown to end before it can show any of the other data.

```graphql hl_lines="6"
query {
  tasks {
    id
    name
    done
    countdown
  }
}
```

However, using the `@stream` directive, the client can receive the rest of the data immediately
and stream in each countdown result as they become available. The `@stream` directive works on list fields.

```graphql hl_lines="6"
query {
  tasks {
    id
    name
    done
    countdown @stream
  }
}
```
