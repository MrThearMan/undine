description: Documentation on schema root types and entrypoints in Undine.

# Schema

In this section, we'll cover how you can set up entrypoints
to you GraphQL schema in Undine, expanding on the basics introduced
in the [Tutorial](tutorial.md).

## RootTypes

A GraphQL schema defines a `RootType` for each kind of operation that it supports.
In GraphQL terms, a `RootType` is just a regular `ObjectType` that just happens
to be the root of the GraphQL Schema.

Let's take a look at the basic setup from the [Tutorial](tutorial.md#part-2-creating-the-schema).

```python
-8<- "schema/creating_schema_query.py"
```

Here you created the `Query` `RootType`. The `Query` `RootType` is
required to be able to crate a GraphQL schema. Each `RootType` must also have at
least one [`Entrypoint`](#entrypoints) in its class body.

As the name implies, the `Query` `RootType` is for querying data.
For mutating data, you'd create a `Mutation` `RootType`.

```python hl_lines="3 12 13 14 15 18"
-8<- "schema/creating_schema_mutation.py"
```

The `Mutation` `RootType` is optional, but if created, it must also include at least
one `Entrypoint`, just like the `Query` `RootType`.

For subscription support, see the [Subscriptions](subscriptions.md) section.

### Schema name

By default, the name of the `RootType` type is the name of the created class.
If you need to change this without changing the class name,
you can do so by providing the `schema_name` argument.

```python
-8<- "schema/root_type_schema_name.py"
```

### Description

To provide a description for the `RootType`, you can add a docstring to the class.

```python
-8<- "schema/root_type_docstring.py"
```

### Directives

You can add directives to the `RootType` by providing them using the `directives` argument.

```python
-8<- "schema/root_type_directives.py"
```

See the [Directives](directives.md) section for more details on directives.

### GraphQL extensions

You can provide custom extensions for the `RootType` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `RootType`.

```python
-8<- "schema/root_type_extensions.py"
```

`RootType` extensions are made available in the GraphQL `ObjectType` extensions
after the schema is created. The `RootType` itself is found in the `extensions`
under a key defined by the [`ROOT_TYPE_EXTENSIONS_KEY`](settings.md#root_type_extensions_key)
setting.

## Entrypoints

`Entrypoints` can be thought of as the _"API endpoints inside the GraphQL schema"_.
They are the fields in a `RootType` from which you can execute operations like queries
or mutations.

An `Entrypoint` always requires a _**reference**_ from which it will create the
proper GraphQL resolver, output type, and arguments for the operation.

### Function references

Using a function/method as a reference is the most basic way of creating an `Entrypoint`.

Function references can be used for both query and mutation `Entrypoints`.
See the example from the [Tutorial](tutorial.md#part-1-setup).

```python
-8<- "schema/entrypoint_function_reference.py"
```

With a function reference, the `Entrypoint` will use the decorated function as its GraphQL resolver.
The function's return type will be used as the `Entrypoint's` output type, so typing it is required.
You can even use a TypedDict to return an object with multiple fields.

/// details | About method signature

A method decorated with `@Entrypoint` is treated as a static method by the `Entrypoint`.

The `self` argument is not an instance of the `RootType`,
but `root` argument of the `GraphQLField` resolver. To clarify this,
it's recommended to change the argument's name to `root`,
as defined by the [`RESOLVER_ROOT_PARAM_NAME`](settings.md#resolver_root_param_name)
setting.

The value of the `root` argument for an `Entrypoint` is `None` by default,
but can be configured using the [`ROOT_VALUE`](settings.md#root_value)
setting if desired.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

You can add arguments to the `Entrypoint` by adding them to the function signature.
Typing these arguments is required to determine their input type.

```python
-8<- "schema/entrypoint_arguments_1.py"
```

This will add a non-null `name` string argument to the `Entrypoint`.
Note that non-null arguments are required by GraphQL, so if you wanted to make the argument
optional, you'd need to make it nullable (in which case it will be `None` by default)
or add a default value ourselves.

```python
-8<- "schema/entrypoint_arguments_2.py"
```

You can add a description to the `Entrypoint` by adding a docstring to the method.
If the method has arguments, you can add descriptions to those arguments by using
[reStructuredText docstrings format]{:target="_blank"}.

[reStructuredText docstrings format]: https://peps.python.org/pep-0287/

```python
-8<- "schema/entrypoint_docstring.py"
```

/// details | What about other docstring formats?

Other types of docstrings can be used by parsed by providing a custom parser to the
[`DOCSTRING_PARSER`](settings.md#docstring_parser) setting that conforms to the
`DocstringParserProtocol` from `undine.typing`.

///

### QueryType references

A `QueryType` represents a GraphQL `ObjectType` for querying data from a Django model
in the GraphQL schema. You should read more on `QueryTypes` in the [Queries](queries.md) section
since this section will only cover using them in `Entrypoints`.

For querying a single model instance, simply use the `QueryType` class
as the reference for the `Entrypoint`.

```python
-8<- "schema/entrypoint_query_type_reference.py"
```

This would create the following field in the `Query` `RootType`:

```graphql
type Query {
    task(pk: Int!): TaskType
}
```

To query a list of model instances, simply add the `many` argument
to the `Entrypoint` in addition to the `QueryType`.

```python
-8<- "schema/entrypoint_query_type_reference_many.py"
```

This would create the following field in the `Query` `RootType`:

```graphql
type Query {
    tasks: [TaskType!]!
}
```

If a [`FilterSet`](filtering.md#filterset) or an [`OrderSet`](ordering.md#orderset)
has been added to your `QueryType`, those filters and orders will be added to the `Entrypoint`.

```graphql
type Query {
  tasks(
    filter: TaskFilterSet
    orderBy: [TaskOrderSet!]
  ): [TaskType!]!
}
```

### MutationType references

A `MutationType` represents a possible mutation operation based on a Django model.
You should read more on `MutationTypes` in the [Mutations](mutations.md) section
since this section will only cover using them in `Entrypoints`.

To create a mutation for a model instance (a create mutation in this example),
simply use the `MutationType` class as the reference for the `Entrypoint`.

```python
-8<- "schema/entrypoint_mutation_type_reference.py"
```

This would create the following field in the `Mutation` `RootType`:

```graphql
type Mutation {
    createTask(input: TaskCreateMutation!): TaskType!
}
```

To make this a bulk mutation, you can add the `many` argument to the `Entrypoint`.

```python
-8<- "schema/entrypoint_mutation_type_reference_many.py"
```

This would create the following field in the `Mutation` `RootType`:

```graphql
type Mutation {
    bulkCreateTask(input: [TaskCreateMutation!]!): [TaskType!]!
}
```

> Note that the total amount of objects that can be mutated in a bulk mutation
> is limited by the [`MUTATION_INSTANCE_LIMIT`](settings.md#mutation_instance_limit) setting.

### Schema name

By default, the name of the `Entrypoint` is the name of the method or class attribute
it's defined in. If you need to change this without changing the method or class attribute name,
for example if the desired name is a Python keyword (e.g. `if` or `from`),
you can do so by providing the `schema_name` argument.

```python
-8<- "schema/entrypoint_schema_name.py"
```

### Description

You can add a description in one of two ways:

1) By setting the `description` argument.

```python hl_lines="10"
-8<- "schema/entrypoint_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python hl_lines="11"
-8<- "schema/entrypoint_variable_docstring.py"
```

If a description is not provided in these ways, the `Entrypoint` will try
to determine a description from the given reference, e.g., for a method
reference, it will use the method's docstring, or for a `QueryType` reference,
it will use the `QueryType's` docstring.

### Many

As seen in this section, the `many` argument is used to indicate whether the `Entrypoint`
should return a non-null list of the referenced type. However, for for [function references](#function-references),
the `many` argument is not required, as the `Entrypoint` can determine the this
from the function's signature (i.e. whether it returns a list or not).

### Nullable

By default, all `Entrypoints` are non-null (except for [function references](#function-references),
which determine nullability from the function's signature). However, you can
make an `Entrypoint` nullable explicitly by adding the `nullable` argument.

```python hl_lines="10"
-8<- "schema/entrypoint_nullable.py"
```

### Limit

The `limit` argument is used by list `Entrypoints` (i.e. [`many=True`](#many)) based on either
[`QueryTypes`](queries.md#querytypes), [`UnionTypes`](unions.md#uniontype),
or [`InterfaceTypes`](interfaces.md#interfacetype) to limit the number of objects that are fetched.
It has no effect on other `Entrypoint` references, like [`Connections`](pagination.md#connection).

### Permissions

Usually, permissions for `Entrypoints` are checked using the `QueryType` or `MutationType`
that the `Entrypoint` is added for. However, you can override these by decorating a method
using the `@<entrypoint_name>.permissions` decorator.

```python
-8<- "schema/entrypoint_permissions.py"
```

### Custom resolver

> Before overriding an `Entrypoint`'s resolver, you should check if
> [QueryType filtering](queries.md#filtering) can be used instead.

You can override the resolver for an `Entrypoint` by decorating
a method using the `@<entrypoint_name>.resolve` decorator. This
can be used, e.g., to add special-case `Entrypoints` for `QueryTypes`.

```python
-8<- "schema/entrypoint_resolve.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Entrypoint`.

The `self` argument is not an instance of the `RootType`,
but `root` argument of the `GraphQLField` resolver. To clarify this,
it's recommended to change the argument's name to `root`,
as defined by the [`RESOLVER_ROOT_PARAM_NAME`](settings.md#resolver_root_param_name)
setting.

The value of the `root` argument for an `Entrypoint` is `None` by default,
but can be configured using the [`ROOT_VALUE`](settings.md#root_value)
setting if desired.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

Note that using this decorator, you'll override the resolver
and arguments based on the reference used in the `Entrypoint`.
Arguments will be taken from the additional arguments passed to the resolver,
e.g., "name" in the example above.

Be sure to call the optimizer, either directly or using the `optimize_sync` or `optimize_async`
helper functions, to queries are optimized.

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Entrypoint` as deprecated.
This is for documentation purposes only and does not affect the use of the `Entrypoint`.

```python
-8<- "schema/entrypoint_deprecation_reason.py"
```

### Directives

You can add directives to the `Entrypoint` by providing them using the `directives` argument.

```python
-8<- "schema/entrypoint_directives.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `Entrypoint` from certain users by adding the `visible` argument to the `Entrypoint`.
Hiding an entrypoint means that it will not be included in introspection queries for that user,
and it cannot be used in operations by that user.

```python
-8<- "schema/entrypoint_visible.py"
```

### GraphQL extensions

You can provide custom extensions for the `Entrypoint` by providing a extensions
argument with a dictionary containing them. These can then be used however you wish to
extend the functionality of the `Entrypoint`.

```python hl_lines="12"
-8<- "schema/entrypoint_extensions.py"
```

`Entrypoint` extensions are made available in the GraphQL field extensions
after the schema is created. The `Entrypoint` itself is found in the `extensions`
under a key defined by the [`ENTRYPOINT_EXTENSIONS_KEY`](settings.md#entrypoint_extensions_key)
setting.

## Schema export

Undine includes a management command to export your GraphQL schema.

```bash
python manage.py print_schema > schema.graphql
```
