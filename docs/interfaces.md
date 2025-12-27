description: Documentation on GraphQL Interfaces in Undine.

# Interfaces

In this section, we'll cover how GraphQL Interfaces work in Undine.
Interfaces are abstract GraphQL types that represent a group of fields
that an `ObjectType` can implement.

## InterfaceType

In Undine, a GraphQL Interface is implemented using the `InterfaceType` class
and defining a number of [`InterfaceFields`](#interfacefield) in its class body.

```python
-8<- "interfaces/interface_type.py"
```

`QueryTypes` can implement `InterfaceTypes` by adding them to the `QueryType` using
the `interfaces` argument in their class definition.

```python
-8<- "interfaces/interface_type_implement.py"
```

You can also use decorator syntax to add an `InterfaceType` to a `QueryType`.

```python
-8<- "interfaces/interface_type_implement_decorator.py"
```

Note that `InterfaceTypes` can also implement other `InterfaceTypes`.

```python
-8<- "interfaces/interface_type_implement_interface.py"
```

### Usage in Entrypoints

An `Entrypoint` created using an `InterfaceType` as the reference will return
all implementations of the `InterfaceType`.

```python
-8<- "interfaces/interface_type_entrypoint.py"
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

By default, an `InterfaceType` `Entrypoint` will return all instances of the `QueryTypes` that implement it.
However, if those `QueryTypes` implement a [`FilterSet`](filtering.md#filterset) or
an [`OrderSet`](ordering.md#orderset), those will also be available on the `InterfaceType` `Entrypoint`.

```python
-8<- "interfaces/interface_type_entrypoint_filtersets_and_ordersets.py"
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

#### Pagination

`InterfaceTypes` can be paginated just like any `QueryType`.

```python
-8<- "interfaces/interface_type_entrypoint_connection.py"
```

See the [Pagination](pagination.md) section for more details on pagination.

### Schema name

By default, the name of the generated GraphQL `Interface` for a `InterfaceType` class
is the name of the `InterfaceType` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "interfaces/interface_type_schema_name.py"
```

### Description

You can provide a description for the `InterfaceType` by adding a docstring to the class.

```python
-8<- "interfaces/interface_type_description.py"
```

### Directives

You can add directives to the `InterfaceType` by providing them using the `directives` argument.
The directive must be usable in the `INTERFACE` location.

```python
-8<- "interfaces/interface_type_directives.py"
```

You can also add directives using decorator syntax.

```python
-8<- "interfaces/interface_type_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `InterfaceType` from certain users by using the `__is_visible__` method.
Hiding the `InterfaceType` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `QueryTypes` or other `InterfaceTypes` didn't implement the `InterfaceType`.

```python
-8<- "interfaces/interface_type_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL Extensions

You can provide custom extensions for the `InterfaceType` by providing an
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `InterfaceType`.

```python
-8<- "interfaces/interface_type_extensions.py"
```

`InterfaceType` extensions are made available in the GraphQL `Interface` extensions
after the schema is created. The `InterfaceType` itself is found in the GraphQL `Interface` extensions
under a key defined by the [`INTERFACE_TYPE_EXTENSIONS_KEY`](settings.md#interface_type_extensions_key)
setting.

## InterfaceField

When a `QueryType` implements an `InterfaceType`, all of the `InterfaceFields` on
the `InterfaceType` are converted to `Fields` on the `QueryType`. The converted `Field` must
correspond to a Model field on the `QueryType` Model, and the `InterfaceField` output type
must match the GraphQL output type converted from Model field. In other words, all `InterfaceFields`
must correspond to Model fields when implemented on a `QueryType`.

An `InterfaceField` always requires its desired GraphQL output type to be defined.

```python
-8<- "interfaces/interface_field.py"
```

Optionally, you can define arguments that the `InterfaceField` requires.
If defined, these must also match the Model field of the implementing `QueryType`.

```python
-8<- "interfaces/interface_field_arguments.py"
```

### Field name

By default, the name of the field in the Django model is the same as the name of the `InterfaceField`.
If you want to change the name of the field in the Django model separately,
you can do so by setting the `field_name` argument:

```python
-8<- "interfaces/interface_field_field_name.py"
```

### Schema name

By default, the name of the `Interface` field generated from a `InterfaceField` is the same
as the name of the `InterfaceField` on the `InterfaceType` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the `Interface` field separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "interfaces/interface_field_schema_name.py"
```

This can be useful when the desired name of the `Interface` field is a Python keyword
and cannot be used as the `Field` attribute name.

### Description

A description for a field can be provided in one of two ways:

1) By setting the `description` argument.

```python
-8<- "interfaces/interface_field_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "interfaces/interface_field_description_class.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `InterfaceField` as deprecated.
This is for documentation purposes only, and does not affect the use of the `InterfaceField`.

```python hl_lines="13"
-8<- "interfaces/interface_field_deprecation_reason.py"
```

### Directives

You can add directives to the `IntefaceField` by providing them using the `directives` argument.
The directive must be usable in the `FIELD_DEFINITION` location.

```python
-8<- "interfaces/interface_field_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "interfaces/interface_field_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `InterfaceField` from certain users by decorating a method with the
`<interface_field_name>.visible` decorator. Hiding a `InterfaceField` means that it
will not be included in introspection queries, and trying to use it in operations
will result in an error that looks exactly like the `InterfaceField` or any
`QueryType` `Field` inherited from the `InterfaceField` didn't exist in the first place.

```python
-8<- "interfaces/interface_field_visible.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `InterfaceField`.

The `self` argument is not an instance of the `InterfaceType`,
but the instance of the `InterfaceField` that is being used.

Since visibility checks occur in the validation phase of the GraphQL request,
GraphQL resolver info is not yet available. However, you can access the
Django request object using the `request` argument.
From this, you can, e.g., access the request user for permission checks.

///

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL Extensions

You can provide custom extensions for the `InterfaceField` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `InterfaceField`.

```python
-8<- "interfaces/interface_field_extensions.py"
```

`InterfaceField` extensions are made available in the GraphQL `Interface` field extensions
after the schema is created. The `InterfaceField` itself is found in the GraphQL `Interface` field extensions
under a key defined by the [`INTERFACE_FIELD_EXTENSIONS_KEY`](settings.md#interface_field_extensions_key)
setting.
