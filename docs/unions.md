# Unions

In this section, we'll cover how GraphQL Unions work in Undine.
Unions are abstract GraphQL types that represent a group of `ObjectTypes`
that need to be returned together, e.g. for a search result.

## UnionType

In Undine, a GraphQL Union between two or more `QueryTypes` is implemented using a `UnionType`.

```python
-8<- "unions/union_type.py"
```

A `UnionType` can be added to a schema using an `Entrypoint`.
Note that `UnionType` should always be added using a list `Entrypoint` (e.g. `many=True`).

```python
-8<- "unions/union_type_entrypoint.py"
```

This `Entrypoint` can be queried like this:

```graphql
query {
  searchObjects {
    __typename
    ... on TaskType {
      name
    }
    ... on ProjectType {
      name
    }
  }
}
```

### Filtering

By default, the `UnionType` will return all instances of the `QueryTypes` it contains.
However, if those `QueryTypes` implement a [`FilterSet`](filtering.md#filterset) or an
[`OrderSet`](ordering.md#orderset), those will also be available on the `UnionType` `Entrypoint`.

```python
-8<- "unions/union_type_entrypoint_filtersets_and_ordersets.py"
```

This creates the following `Entrypoint`:

```graphql
type Query {
  searchObjects(
    filterTask: TaskFilterSet
    orderByTask: [TaskOrderSet!]
    filterProject: ProjectFilterSet
    orderByProject: [ProjectOrderSet!]
  ): [Commentable!]!
}
```

This allows filtering the different types of models in the `UnionType` separately.

The `UnionType` also provides a `__process_results__` method that can be used to filter the
results of the union after everything has been fetched.

```python
-8<- "unions/union_type_entrypoint_process_results.py"
```

By default, the number of items returned is limited _per model in the `UnionType`_.
This is set by the [`ENTRYPOINT_LIMIT_PER_MODEL`](settings.md#entrypoint_limit_per_model) setting,
but can also be changed per `Entrypoint` using the `limit` argument:

```python
-8<- "unions/union_type_entrypoint_limit.py"
```

/// details | What about pagination?

Pagination of `UnionTypes` is not supported yet.

///

### Schema name

By default, the name of the generated GraphQL `Union` is the same as the name of the `UnionType` class.
If you want to change the name, you can do so by setting the `schema_name` argument:

```python
-8<- "unions/union_type_schema_name.py"
```

### Description

A description for a `UnionType` can be provided as a docstring.

```python
-8<- "unions/union_type_description.py"
```

### GraphQL Extensions

You can provide custom extensions for the `UnionType` by providing a
`extensions` argument with a dictionary containing them.

```python
-8<- "unions/union_type_extensions.py"
```

`UnionType` extensions are made available in the GraphQL `UnionType` extensions
after the schema is created. The `UnionType` itself is found in the `extensions`
under a key defined by the [`UNION_TYPE_EXTENSIONS_KEY`](settings.md#union_type_extensions_key)
setting.
