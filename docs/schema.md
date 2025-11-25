description: Documentation on schema root types and entrypoints in Undine.

# Schema

In this section, we'll cover how you can set up entrypoints
to you GraphQL schema for executing operations in Undine.

## RootTypes

A GraphQL schema defines a `RootType` for each kind of operation that it supports.
In GraphQL terms, a `RootType` is just a regular `ObjectType` that just happens
to be the root of the GraphQL Schema.

Let's take a look at this example from the [Tutorial](tutorial.md#part-2-creating-the-schema).

```python
-8<- "schema/creating_schema_query.py"
```

Here you've created the `Query` `RootType`. In Undine, the `Query` `RootType` is
required to exist for a schema to be created. Each `RootType` must also have at
least one [`Entrypoint`](#entrypoints) in its class body.

As the name implies, the `Query` `RootType` is for querying data.
For mutating data, you'd create a `Mutation` `RootType`.

```python hl_lines="3 12 13 14 15 18"
-8<- "schema/creating_schema_mutation.py"
```

The `Mutation` `RootType` is optional, but if created, it must also include at least
one `Entrypoint`, just like the `Query` `RootType`.

For `Subscription` `RootTypes`, see the [Subscriptions](subscriptions.md) section.

### Schema name

By default, the name of the generated GraphQL `ObjectType` from a `RootType` class
is the name of the `RootType` class. If you need to change the name separately,
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
The directive must be usable in the `OBJECT` location.

```python
-8<- "schema/root_type_directives.py"
```

You can also add them using decorator syntax.

```python
-8<- "schema/root_type_directives_decorator.py"
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
after the schema is created. The `RootType` itself is found in the GraphQL `ObjectType` extensions
under a key defined by the [`ROOT_TYPE_EXTENSIONS_KEY`](settings.md#root_type_extensions_key)
setting.

## Entrypoints

`Entrypoints` can be thought of as the _"API endpoints inside the GraphQL schema"_
from which you can execute operations like queries or mutations.
In GraphQL terms, they are the fields on the `ObjectType` created from a `RootType`

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

A `QueryType` represents a GraphQL `ObjectType` for querying data from a Django Model.
You can read more on `QueryTypes` in the [Queries](queries.md) section.
This section will only cover using them in `Entrypoints`.

To create an `Entrypoint` for querying a single Model instance by its primary key,
simply use the `QueryType` class as the reference for the `Entrypoint`.

```python
-8<- "schema/entrypoint_query_type_reference.py"
```

This would create the following field in the `Query` `RootType`:

```graphql
type Query {
    task(pk: Int!): TaskType
}
```

To crete an Entrypoint for listing all instances of the Model,
add the `many` argument to the `Entrypoint`.

```python
-8<- "schema/entrypoint_query_type_reference_many.py"
```

This would create the following field in the `Query` `RootType`:

```graphql
type Query {
    tasks: [TaskType!]!
}
```

With a list `Entrypoint`, if a [`FilterSet`](filtering.md#filterset) or an [`OrderSet`](ordering.md#orderset)
has been added to your `QueryType`, they will show up as arguments on the `Entrypoint`.

```graphql
type Query {
  tasks(
    filter: TaskFilterSet
    orderBy: [TaskOrderSet!]
  ): [TaskType!]!
}
```

### MutationType references

A `MutationType` represents a possible mutation operation based on a Django Model.
You can read more on `MutationTypes` in the [Mutations](mutations.md) section.
This section will only cover using them in `Entrypoints`.

To create an `Entrypoint` for mutating a single Model instance (a create mutation in this example),
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

To create an Entrypoint for mutating multiple Model instances in bulk,
add the `many` argument to the `Entrypoint`.

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

### Nullable

By default, all `Entrypoints` are non-null (except for [function references](#function-references),
which determine nullability from the function's signature). However, you can
make an `Entrypoint` nullable explicitly by using the `nullable` argument.

```python hl_lines="10"
-8<- "schema/entrypoint_nullable.py"
```

### Limit

The `limit` argument is used by `Entrypoints` based on either [`QueryTypes`](queries.md#querytypes),
[`UnionTypes`](unions.md#uniontype), or [`InterfaceTypes`](interfaces.md#interfacetype) that return
a list of items (i.e. `many=True`) to limit the number of objects that are fetched.
By default, this is set by the [`LIST_ENTRYPOINT_LIMIT`](settings.md#list_entrypoint_limit) setting.

```python
-8<- "schema/entrypoint_limit.py"
```

### Permissions

To add permission checks to your Entrypoint, use the `@<entrypoint_name>.permissions` decorator.

```python
-8<- "schema/entrypoint_permissions.py"
```

Note that permissions for `Entrypoints` based on `QueryTypes` or `MutationTypes`
are checked using that `QueryType's` or `MutationType's` permissions if no permission checks
have been defined on the `Entrypoint`.

### Custom resolver

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

Note that when using this decorator, you'll override the resolver
and arguments based on the reference used in the `Entrypoint`.
Arguments will be taken from the additional arguments passed to the resolver,
e.g., "name" in the example above.

When overriding the resolver for `Entrypoints` based on `QueryTypes`,
the `QueryType's` [FilterSet](filtering.md#filterset) and [OrderSet](ordering.md#orderset)
will not be available on the `Entrypoint`

Overriding the resolver for `Entrypoints` using `MutationTypes` is not recommended,
as it bypasses the whole mutation process and many `MutationType` functions will not work.

If the resolver returns a Django Model that resolves using `QueryType`,
you should call the optimizer in the resolver using `optimize_sync` or `optimize_async`,
like in the above example, so that queries are optimized.

### Schema name

By default, the name of the `ObjectType` field generated from an `Entrypoint` is the same
as the name of the `Entrypoint` on the `RootType` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the `ObjectType` field separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "schema/entrypoint_schema_name.py"
```

This can be useful when the desired name of the `ObjectType` field is a Python keyword
and cannot be used as the `Entrypoint` attribute name.

### Description

By default, an `Entrypoint` is able to determine its description based on its reference.
For example, for a [QueryType](queries.md#querytypes), the description is taken from the class docstring.
If the reference has no description, or you wish to add a different one,
you can provide a description in one of two ways:

1) By setting the `description` argument.

```python hl_lines="10"
-8<- "schema/entrypoint_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python hl_lines="11"
-8<- "schema/entrypoint_variable_docstring.py"
```

When using [function references](#function-references), instead of a class attribute docstring,
you add a docstring to the function/method used as the reference instead.

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Entrypoint` as deprecated.
This is for documentation purposes only and does not affect the use of the `Entrypoint`.

```python
-8<- "schema/entrypoint_deprecation_reason.py"
```

### Complexity

The complexity value of an `Entrypoint` is used by Undine to calculate how expensive a given query
to the schema would be. Queries are rejected by Undine if they would exceed the maximum allowed complexity,
as set by the [`MAX_QUERY_COMPLEXITY`](settings.md#max_query_complexity) setting.

Usually, complexity is set by `QueryType` [`Fields`](queries.md#complexity), but you can also set
complexity on the `Entrypoint` itself. This can be useful for declaring complexity of
`Entrypoints` not based on `QueryTypes`. Note that when the `Entrypoint` _is_ based on a `QueryType`,
this complexity _adds_ to any complexity calculated from the `QueryType's` `Fields`.

### Directives

You can add directives to the `Entrypoint` by providing them using the `directives` argument.
The directive must be usable in the `FIELD_DEFINITION` location.

```python
-8<- "schema/entrypoint_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "schema/entrypoint_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `Entrypoint` from certain users by decorating a method with the
`<entrypoint_name>.visible` decorator. Hiding an `Entrypoint` means that it will
not be included in introspection queries, and trying to use it in operations will
result in an error that looks exactly like the `Entrypoint` didn't exist in the first place.

```python
-8<- "schema/entrypoint_visible.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Entrypoint`.

The `self` argument is not an instance of the `RootType`,
but the instance of the `Entrypoint` that is being used.

Since visibility checks occur in the validation phase of the GraphQL request,
GraphQL resolver info is not yet available. However, you can access the
Django request object using the `request` argument.
From this, you can, e.g., access the request user for permission checks.

///

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `Entrypoint` by providing a extensions
argument with a dictionary containing them. These can then be used however you wish to
extend the functionality of the `Entrypoint`.

```python
-8<- "schema/entrypoint_extensions.py"
```

`Entrypoint` extensions are made available in the GraphQL `ObjectType` field extensions
after the schema is created. The `Entrypoint` itself is found in the GraphQL field extensions
under a key defined by the [`ENTRYPOINT_EXTENSIONS_KEY`](settings.md#entrypoint_extensions_key)
setting.

## Schema export

Undine includes a management command to export your GraphQL schema.
It prints the schema to `STDOUT`, which can be redirected to a file like so:

```bash
python manage.py print_schema > schema.graphql
```
