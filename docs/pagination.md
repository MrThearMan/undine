# Pagination

In this section, we'll cover the everything necessary for adding pagination
to your GraphQL schema using the Relay [Connection]{:target="_blank"}
specification.

[Connection]: https://relay.dev/graphql/connections.htm

For Relay-compliant clients, see the [Global Object IDs](global-object-ids.md#node-interface) section
for adding support for the `Node` interface.

Here are the models used in the examples below:

```python
-8<- "pagination/models.py"
```

## Connection

To support pagination, you need to wrap `QueryTypes` in `Entrypoints` with the `Connection` class.

```python
-8<- "pagination/connection.py"
```

Querying this `Entrypoint` will return a response like this:

```json
-8<- "pagination/response_1.json"
```

One addition to the Relay specification is the inclusion of a `totalCount` field,
which returns the total number of items that can be queried from the `Connection`.

Many-related `Fields` can also be paginated using the `Connection` class.

```python
-8<- "pagination/connection_nested.py"
```

### Page size

The default page size of a `Connection` is set by the [`CONNECTION_PAGE_SIZE`](settings.md#connection_page_size)
setting. You can use a different page size by providing the `page_size` argument to the `Connection`.

```python
-8<- "pagination/connection_page_size.py"
```

### Custom pagination strategies

Both top-level and nested connections are optimized by the [Optimizer](optimizer.md)
to only query the items that are needed for the current page. Both optimizations
should be quite performant, but calculating `totalCount` for nested connections
can be slow, since it requires a subquery for each parent item.

If you need to modify the pagination behavior, you can do so by providing a custom
`PaginationHandler` to the `Connection`.

```python
-8<- "pagination/connection_pagination_handler.py"
```
