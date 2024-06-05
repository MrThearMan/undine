# Interfaces

In this section, we'll cover how GraphQL Interfaces work in Undine.
Interfaces are abstract GraphQL types that represent a group of fields
that an `ObjectType` can implement.

## InterfaceType

In Undine, a GraphQL Interface is implemented using the `InterfaceType` class
and defining a number of [`InterfaceFields`](#interfacefield) in its class body.

```python
-8<- "interfaces/interface.py"
```

`QueryTypes` can implement `InterfaceTypes` by adding them to the `QueryType` using
the `interfaces` argument in their class definition.

```python
-8<- "interfaces/interface_implement.py"
```

`InterfaceTypes` can also implement other `InterfaceTypes`.

```python
-8<- "interfaces/interface_implement_interface.py"
```

### Usage in Entrypoints

By default, an `Entrypoint` for an `InterfaceType` can be created that returns
all implementations of the `InterfaceType`.

```python
-8<- "interfaces/interface_entrypoint.py"
```

This `Entrypoint` can be queried like this:

```graphql
query {
  named {
    name
    ... on TaskType {
      createdAt
    }
    ... on StepType {
      done
    }
    __typename
  }
}
```

#### Filtering

By default, the `InterfaceType` will return all instances of the `QueryTypes` that implement it.
However, if those `QueryTypes` implement a [`FilterSet`](filtering.md#filterset) or an
[`OrderSet`](ordering.md#orderset), those will also be available on the `InterfaceType` `Entrypoint`.

```python
-8<- "interfaces/interface_entrypoint_filtersets_and_ordersets.py"
```

This creates the following `Entrypoint`:

```graphql
type Query {
  named(
    filterTask: TaskFilterSet
    orderByTask: [TaskOrderSet!]
    filterStep: StepFilterSet
    orderByStep: [StepOrderSet!]
  ): [Named!]!
}
```

This allows filtering the different types of models in the `InterfaceType` separately.

The `InterfaceType` also provides a `__process_results__` method that can be used to filter the
results of the union after everything has been fetched.

```python
-8<- "interfaces/interface_entrypoint_process_results.py"
```

By default, the number of items returned is limited _per model implementing the `InterfaceType`_.
This is set by the [`ENTRYPOINT_LIMIT_PER_MODEL`](settings.md#entrypoint_limit_per_model) setting,
but can also be changed per `Entrypoint` using the `limit` argument:

```python
-8<- "interfaces/interface_entrypoint_limit.py"
```

/// details | What about pagination?

Pagination of `InterfaceTypes` is not supported yet.

///

### Schema name

By default, the name of the generated `Interface` is the same as the name of the `InterfaceType` class.
If you want to change the name, you can do so by setting the `schema_name` argument:

```python
-8<- "interfaces/interface_schema_name.py"
```

### Description

To provide a description for the `InterfaceType`, you can add a docstring to the class.

```python
-8<- "interfaces/interface_description.py"
```

### GraphQL Extensions

You can provide custom extensions for the `InterfaceType` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `InterfaceType`.

```python
-8<- "interfaces/interface_extensions.py"
```

`InterfaceType` extensions are made available in the GraphQL `Interface` extensions
after the schema is created. The `InterfaceType` itself is found in the `extensions`
under a key defined by the [`INTERFACE_TYPE_EXTENSIONS_KEY`](settings.md#interface_type_extensions_key)
setting.

## InterfaceField

The `Fields` required by an interface are defined using `InterfaceFields`.
Minimally, an `InterfaceField` requires the output type.

```python
-8<- "interfaces/interface_field.py"
```

Optionally, you can define arguments that the `InterfaceField` requires.

```python
-8<- "interfaces/interface_field_arguments.py"
```

### Schema name

A `schema_name` can be provided to override the name of the `InterfaceField` in the GraphQL schema.
This can be useful for renaming fields for the schema, or when the desired name is a Python keyword
and cannot be used as the `InterfaceField` attribute name.

```python hl_lines="13"
-8<- "interfaces/interface_field_schema_name.py"
```

### Description

A description for a field can be provided in one of two ways:

1) By setting the `description` argument.

```python
-8<- "interfaces/interface_field_description.py"
```

2) As class attribute docstrings.

```python
-8<- "interfaces/interface_field_description_class.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `InterfaceField` as deprecated.
This is for documentation purposes only, and does not affect the use of the `InterfaceField`.

```python hl_lines="13"
-8<- "interfaces/interface_field_deprecation_reason.py"
```

### GraphQL Extensions

You can provide custom extensions for the `InterfaceField` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `InterfaceField`.

```python
-8<- "interfaces/interface_field_extensions.py"
```

`InterfaceField` extensions are made available in the GraphQL `InterfaceField` extensions
after the schema is created. The `InterfaceField` itself is found in the `extensions`
under a key defined by the [`INTERFACE_FIELD_EXTENSIONS_KEY`](settings.md#interface_field_extensions_key)
setting.
