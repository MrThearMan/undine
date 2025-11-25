description: Relay Global Object Identification specification support in Undine.

# Global Object IDs

In this section, we'll cover how you can add support for object refetching and client caching using the
[Global Object Identification]{:target="_blank"} specification.

[Global Object Identification]: https://relay.dev/graphql/objectidentification.htm

For Relay-compliant clients, see the [Connection](pagination.md#cursor-pagination) section
for adding support for pagination with `Connections`.

## Node Interface

Your `QueryTypes` can implement the `Node` [interface](interfaces.md) to add support for _Global Object IDs_.

```python
-8<- "global_object_ids/node_interface.py"
```

This will add an `id` field to the `TaskType` for resolving _Global Object IDs_.

```graphql hl_lines="2 6"
interface Node {
  id: ID!
}

type TaskType implements Node {
  id: ID!
  pk: Int!
  name: String!
  # Rest of the fields...
}
```

Note that most Django models already contain an `id` field for as the primary key of the table,
and that implementing this interface will override it with the _Global Object ID_ field. To access the
model `id` field, you can use the `pk` field instead.

## Node Entrypoint

A _Global Object ID_ can be used for refetching objects from a special `Node` `Entrypoint`.

```python hl_lines="11"
-8<- "global_object_ids/node_entrypoint.py"
```

To use this `Entrypoint`, we must first query the schema in some other way, for example
using the `tasks` Connection `Entrypoint` in the above example. Then, we can use the
fetched _Global Object ID_ to refetch the `Task` from the `Node` `Entrypoint`.

```graphql
query {
  node(id: "U3Vyc29yOnVzZXJuYW1lOjE=") {
    id
    ... on TaskType {
      name
    }
  }
}
```

Note that _Global Object IDs_ (e.g. `U3Vyc29yOnVzZXJuYW1lOjE=` in the above example)
are meant to be opaque to the client, meaning they aren't supposed to know what they
contain or how to parse them.
