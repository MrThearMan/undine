description: Documentation on GraphQL Unions in Undine.

# Unions

In this section, we'll cover how GraphQL Unions work in Undine.
Unions are abstract GraphQL types that represent a group of `ObjectTypes`
that need to be returned together, e.g. for a search result.

## UnionType

In Undine, a GraphQL `Union` between two or more `QueryTypes` is implemented using a `UnionType`.
The `QueryTypes` in the `Union` should be added as generic type parameters to the `UnionType`.

```python
-8<- "unions/union_type.py"
```

### Usage in Entrypoints

An `Entrypoint` created using a `UnionType` as the reference will return
all instances of all `QueryTypes` it contains.

```python
-8<- "unions/union_type_entrypoint.py"
```

This `Entrypoint` can be queried like this:

```graphql
query {
  searchObjects {
    ... on TaskType {
      name
    }
    ... on ProjectType {
      name
    }
    __typename
  }
}
```

### Filtering

By default, an `Entrypoint` for a `UnionType` will return all instances of all `QueryTypes` it contains.
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

To filter and order _across_ different Models in the `Union`, you can implement
a [`FilterSet`](filtering.md#filterset) or an [`OrderSet`](ordering.md#orderset)
for the same Models as the `QueryTypes` in the `UnionType` and add it to the `UnionType`.

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

Note that a `FilterSet` or `OrderSet` created for multiple Models like this
should only contain `Filters` and `Orders` which will work on all Models in the `UnionType`.
For example, a "name" `Filter` can be added to the `FilterSet` if all Models contain
a "name" field of type `CharField`.

#### Pagination

`UnionTypes` can be paginated just like any `QueryType`.

```python
-8<- "unions/union_type_entrypoint_connection.py"
```

See the [Pagination](pagination.md) section for more details on pagination.

### Schema name

By default, the name of the generated GraphQL `Union` for a `UnionType` class
is the name of the `UnionType` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "unions/union_type_schema_name.py"
```

### Description

A description for a `UnionType` can be provided as a docstring.

```python
-8<- "unions/union_type_description.py"
```

### Directives

You can add directives to the `UnionType` by providing them using the `directives` argument.
The directive must be usable in the `UNION` location.

```python
-8<- "unions/union_type_directives.py"
```

You can also add directives using decorator syntax.

```python
-8<- "unions/union_type_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `UnionType` from certain users by using the `__is_visible__` method.
Hiding the `UnionType` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `UnionType` didn't exist in the first place.

```python
-8<- "unions/union_type_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL Extensions

You can provide custom extensions for the `UnionType` by providing an
`extensions` argument with a dictionary containing them.

```python
-8<- "unions/union_type_extensions.py"
```

`UnionType` extensions are made available in the GraphQL `Union` extensions
after the schema is created. The `UnionType` itself is found in the GraphQL `Union` extensions
under a key defined by the [`UNION_TYPE_EXTENSIONS_KEY`](settings.md#union_type_extensions_key)
setting.
