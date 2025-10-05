description: Documentation on GraphQL Unions in Undine.

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

By default, the an `Entrypoint` for a `UnionType` will return all instances of all `QueryTypes` it contains.
However, if those `QueryTypes` implement a [`FilterSet`](filtering.md#filterset) or an
[`OrderSet`](ordering.md#orderset), those will also be available on the `UnionType` `Entrypoint`.

```python
-8<- "unions/union_type_entrypoint_query_type_filtersets_and_ordersets.py"
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

This allows filtering and ordering the different types of models in the `UnionType` separately.

To filter and order across different models in the `UnionType`, you can implement
a [`FilterSet`](filtering.md#filterset) or an [`OrderSet`](ordering.md#orderset)
for the same models as the `UnionType` and add it to the `UnionType`.

```python
-8<- "unions/union_type_entrypoint_union_type_filtersets_and_ordersets.py"
```

This creates the following `Entrypoint`:

```graphql
type Query {
  searchObjects(
    filter: SearchObjectsFilterSet
    orderBy: [SearchObjectsOrderSet!]
  ): [Commentable!]!
}
```

Note that a `FilterSet` or `OrderSet` created for multiple models like this
should only contain `Filters` and `Orders` which will work on all models in the `UnionType`,
i.e. they are of the same type.

#### Pagination

To paginate `UnionTypes`, you can use the [`Connection`](pagination.md#connection) `Entrypoint`.

```python
-8<- "unions/union_type_entrypoint_connection.py"
```

See the [Pagination](pagination.md) section for more details on pagination.

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
