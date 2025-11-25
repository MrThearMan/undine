description: Documentation on queries in Undine.

# Queries

In this section, we'll cover Undine's [`QueryTypes`](#querytypes)
which allow you to expose your Django Models through the GraphQL schema for querying.

For queries not concerning your Django Models,
see the [function references](schema.md#function-references) section
in the Schema documentation.

## QueryTypes

A `QueryType` represents a GraphQL `ObjectType` for querying data from a Django Model
in the GraphQL schema. A basic `QueryType` is created by subclassing `QueryType`
and adding a Django Model to it as a generic type parameter. You must also add at least one
[`Field`](#fields) to the class body of the `QueryType`.

```python
-8<- "queries/query_type_basic.py"
```

### Auto-generation

A `QueryType` can automatically introspect its Django Model and convert the Model's fields
to `Fields` on the `QueryType`. For example, if the `Task` model has the following fields:

```python
-8<- "queries/models_1.py"
```

Then the GraphQL `ObjectType` for the `QueryType` using auto-generation would be:

```graphql
type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
}
```

To use auto-generation, either set [`AUTOGENERATION`](settings.md#autogeneration) setting to `True`
to enable it globally, or set the `auto` argument to `True` in the `QueryType` class definition.
With this, you can leave the `QueryType` class body empty, as fields will be automatically added
based on the Django Model.

```python
-8<- "queries/query_type_auto.py"
```

You can exclude some Model fields from the auto-generation by setting the `exclude` argument:

```python
-8<- "queries/query_type_exclude.py"
```

### Filtering

When a `QueryType` is used to return multiple items, either in a list [`Entrypoint`](schema.md#entrypoints)
or a many-related [`Field`](#fields), its results can be filtered in one of two ways:

1) Adding a `FilterSet` to the `QueryType`. These are explained in detail in the [Filtering](filtering.md) section.

2) Defining a `__filter_queryset__` classmethod. This method will always be called even if no
   other filtering is applied to the results. Use it to filter out items that should
   never be returned by the `QueryType`, e.g. archived items.

```python
-8<- "queries/query_type_filter.py"
```

### Ordering

When a `QueryType` is used to return multiple items, either in a list [`Entrypoint`](schema.md#entrypoints)
or a many-related [`Field`](#fields), its results can be ordered in one of two ways:

1) Adding an `OrderSet` to the `QueryType`. These are explained in detail in the [Ordering](ordering.md) section.

2) Defining a `__filter_queryset__` classmethod.
   Same as custom [filtering](#filtering), this ordering is always applied to results returned by the `QueryType`.
   However, since queryset ordering is reset when a new ordering is applied to the queryset,
   ordering added here serves as the default ordering for the `QueryType`, and is overridden if
   any ordering is applied using an `OrderSet`.

```python
-8<- "queries/query_type_order.py"
```

### Permissions

You can add a permission check for querying data from a `QueryType` by
adding a `__permissions__` classmethod it.

```python
-8<- "queries/query_type_permissions.py"
```

This method will be called for each instance of `Task` that is returned
by this `QueryType` in `Entrypoints` or related `Fields`.

You can raise any `GraphQLError` when a permission check fails, but it's recommended to
raise a `GraphQLPermissionError` from the `undine.exceptions` module.

Instead of raising an exception from a permission check, you might want to filter out items the user
doesn't have permission to access. You can do this using the `__filter_queryset__`
classmethod.

```python
-8<- "queries/query_type_permissions_filter_queryset.py"
```

Now, when the `QueryType` is used in a list `Entrypoint` or many related `Field`,
items that the user doesn't have permission to access will be filtered out.
For single-item entrypoints or "to-one" relations, a `null` value will be returned
instead. Note that you'll need to manually check all `Fields` and `Entrypoints`
where the `QueryType` is used and mark them as _nullable_ if they would otherwise not be.

If your permissions check requires data from outside of the GraphQL execution context,
you should check the [Optimizer](optimizer.md) section on how you can make sure permissions
checks don't cause an excessive database queries.

### QueryType registry

When a new `QueryType` is created, Undine automatically registers it for its given Model.
This allows other `QueryTypes` to look up the `QueryType` for linking related `Fields`
(see [relations](#relations)), and `MutationTypes` to find out their matching output type
(see [mutation output types](mutations.md#output-type)).

The `QueryType` registry only allows one `QueryType` to be registered for each Model.
During `QueryType` registration, if a `QueryType` is already registered for the Model,
an error will be raised.

If you need to create multiple `QueryTypes` for the same Model, you can choose to not
register a `QueryType` in the registry by setting the `register` argument to `False` in the
`QueryType` class definition.

```python
-8<- "queries/query_type_no_register.py"
```

You'll then need to use this `QueryType` explicitly when required.

### Custom optimizations

> The optimizer is covered more thoroughly in the [Optimizer](optimizer.md) section.

Usually adding `QueryType` optimizations is not necessary, but if required,
you can override the `__optimizations__` classmethod on the `QueryType` to do so.

```python
-8<- "queries/query_type_optimizations.py"
```

This hook can be helpful when you require data from outside the GraphQL execution context
to e.g. make permission checks.

### Schema name

By default, the name of the generated GraphQL `ObjectType` for a `QueryType` class
is the name of the `QueryType` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "queries/query_type_schema_name.py"
```

### Description

You can provide a description for the `QueryType` by adding a docstring to the class.

```python
-8<- "queries/query_type_description.py"
```

### Interfaces

You can add interfaces to the `QueryType` by providing them using the `interfaces` argument.

```python
-8<- "queries/query_type_interfaces.py"
```

You can also add interfaces using decorator syntax.

```python
-8<- "queries/query_type_interfaces_decorator.py"
```

See the [Interfaces](interfaces.md) section for more details on interfaces.

### Directives

You can add directives to the `QueryType` by providing them using the `directives` argument.
The directive must be usable in the `OBJECT` location.

```python
-8<- "queries/query_type_directives.py"
```

You can also add directives using decorator syntax.

```python
-8<- "queries/query_type_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `QueryType` from certain users by using the `__is_visible__` method.
Hiding the `QueryType` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Entrypoint` or `Field` using the `QueryType` didn't exist in the first place.

```python
-8<- "queries/query_type_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `QueryType` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `QueryType`.

```python
-8<- "queries/query_type_extensions.py"
```

`QueryType` extensions are made available in the GraphQL `ObjectType` extensions
after the schema is created. The `QueryType` itself is found in the GraphQL `ObjectType` extensions
under a key defined by the [`QUERY_TYPE_EXTENSIONS_KEY`](settings.md#query_type_extensions_key)
setting.

## Fields

A `Field` is used to define a queryable value on a `QueryType`.
Usually `Fields` correspond to fields on the Django Model for their respective `QueryType`.
In GraphQL, a `Field` represents a `GraphQLField` on an `ObjectType`.

A `Field` always requires a _**reference**_ from which it will create the proper GraphQL resolver,
output type, and arguments for the `Field`.

### Model field references

For `Fields` corresponding to Django Model fields, the `Field` can be used without passing in a reference,
as its attribute name in the `QueryType` class body can be used to identify
the corresponding Model field.

```python
-8<- "queries/field.py"
```

To be a bit more explicit, you could use a string referencing the Model field:

```python
-8<- "queries/field_string.py"
```

For better type safety, you can also use the Model field itself:

```python
-8<- "queries/field_field.py"
```

Being explicit like this is only required if the name of the field in the GraphQL schema
is different from the Model field name.

```python
-8<- "queries/field_alias.py"
```

### Expression references

Django ORM expressions can also be used as references.
These create an annotation on the Model instances when fetched.

```python
-8<- "queries/field_expression.py"
```

Remember that subqueries are also counted as expressions.

```python
-8<- "queries/field_subquery.py"
```

### Function references

Functions (or methods) can also be used to create `Fields`.
This can be done by decorating a method with the `Field` class.

```python
-8<- "queries/field_decorator.py"
```

The `Field` will use the decorated method as its GraphQL resolver.
The method's return type will be used as the output type for the `Field`, so typing it is required.
You can even use a `TypedDict` to return an object with multiple fields.

/// details | About method signature

The decorated method is treated as a static method by the `Field`.

The `self` argument is not an instance of the `QueryType`,
but `root` argument of the `GraphQLField` resolver. To clarify this,
it's recommended to change the argument's name to `root`,
as defined by the [`RESOLVER_ROOT_PARAM_NAME`](settings.md#resolver_root_param_name)
setting.

The value of the `root` argument for a `Field` is the **_Model instance_** being queried.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

Arguments added to the function signatures will be added as `Field` arguments in the GraphQL schema.
Typing these arguments is required to determine their input type.

```python
-8<- "queries/field_decorator_arguments.py"
```

> If the method requires fields from the `root` instance, you should add custom optimization
> rules for the `Field` so that the fields are available when the resolver is called.
> See [custom optimizations](#custom-optimizations) for how to add these, although it might be
> simpler to use a [Calculation reference](#calculation-references).

### Calculation references

A `Calculation` reference is like a combination of [function references](#function-references) and
[expression references](#expression-references). They can accept data from input arguments
like a function reference, and return an expression that should be annotated to a queryset
like an expression reference. A `Calculation` references can be created by subclassing
the `Calculation` class and adding the required `CalculationArguments` to its class body.

```python
-8<- "queries/field_calculation.py"
```

`Calculation` objects always require the generic type argument to be set,
which describes the return type of the calculation. This should be a python type
matching the Django ORM expression that is returned in the `__call__` method.

`CalculationArguments` can be defined in the class body of the `Calculation` class.
These define the input arguments for the calculation. When the calculation is executed,
the `CalculationArguments` can be used to access the input data for that specific argument.

The `__call__` method should always be defined in the `Calculation` class. This should
return a Django ORM expression that can be annotated to a queryset. You may
access other fields using `F`-expressions and use request-specific data from the `info` argument.

The `Field` will look like this in the GraphQL schema:

```graphql
type TaskType {
    calc(value: Int!): Int!
}
```

A `Calculation` reference is a good replacement for a function reference
when the calculation is expensive enough that resolving it for each field would be slow.
However, the calculation needs to be able to be executed in the database
since `__call__` needs to return a Django ORM expression to be annotated to a queryset.

A `Calculation` reference is a good replacement for an expression reference
when the expression requires input data from the request.

### Relations

Let's say there is a `Task` model with a `ForeignKey` to a `Project` model:

```python hl_lines="4 5 13"
-8<- "queries/models_2.py"
```

You can then create `QueryTypes` for both models and add `Fields` for the related fields.

```python hl_lines="9 17"
-8<- "queries/query_type_relations.py"
```

The `QueryTypes` will be linked together in the GraphQL schema by their relations:

```graphql hl_lines="4 12"
type ProjectType {
    pk: Int!
    name: String!
    tasks: [TaskType!]!
}

type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
    project: ProjectType!
}
```

Undine will make sure that queries between the relations are optimized.

### Permissions

You can add a permission check for querying any data from an individual `Field` by
decorating a method with `@<field_name>.permissions`.

```python
-8<- "queries/field_permissions.py"
```

If `Field` permissions are defined for a related field, the related `QueryType` permissions
are overridden by the `Field` permissions.

```python
-8<- "queries/field_permissions_related_field.py"
```

Instead of raising an exception, you might want a failed permission check to
result in a `null` value instead of an error. You can do this overriding the
`Field's` [resolver](#custom-resolvers) and manually checking the permissions there,
returning `None` when permission is denied. Note that you'll need to manually set the
`Field` as nullable if it would otherwise not be.

```python
-8<- "queries/field_permissions_resolver.py"
```

### Many

By default, a `Field` is able to determine whether it returns a list of items based on its reference.
For example, for a Model field, a `ManyToManyField` will return a list of items.
If you want to configure this manually, you can do so by adding the `many` argument to the `Field`.

```python
-8<- "queries/field_many.py"
```

### Nullable

By default, a `Field` is able to determine whether it's nullable or not based on its reference.
For example, for a Model field, nullability is determined from its `null` attribute.
If you want to configure this manually, you can do so by adding the `nullable` argument to the `Field`.

```python
-8<- "queries/field_nullable.py"
```

### Complexity

The complexity value of a `Field` is used by Undine to calculate how expensive a given query
to the schema would be. Queries are rejected by Undine if they would exceed the maximum allowed complexity,
as set by the [`MAX_QUERY_COMPLEXITY`](settings.md#max_query_complexity) setting.

By default, a `Field` is able to determine its complexity based on its reference.
For example, a related Model field has a complexity of 1, and a regular Model field has a complexity of 0.
If you want to configure this manually, you can do so by adding the `complexity` argument to the `Field`.

```python
-8<- "queries/field_complexity.py"
```

### Field name

A `field_name` can be provided to explicitly set the Django Model field
that the `Field` corresponds to.

```python
-8<- "queries/field_field_name.py"
```

This can be useful when the `Field` has a different name and type in the GraphQL schema than in the Model.

### Schema name

By default, the name of the `ObjectType` field generated from a `Field` is the same
as the name of the `Field` on the `QueryType` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the `ObjectType` field separately,
you can do so by setting the `schema_name` argument:

```python hl_lines="13"
-8<- "queries/field_schema_name.py"
```

This can be useful when the desired name of the `ObjectType` field is a Python keyword
and cannot be used as the `Field` attribute name.

### Descriptions

By default, a `Field` is able to determine its description based on its reference.
For example, for a [Model field](#model-field-references), the description is taken from its `help_text`.
If the reference has no description, or you wish to add a different one,
you can provide a description in one of two ways:

1) By setting the `description` argument.

```python
-8<- "queries/field_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "queries/field_description_class.py"
```

When using [function references](#function-references), instead of a class attribute docstring,
you add a docstring to the function/method used as the reference instead.

```python
-8<- "queries/field_decorator_docstring.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Field` as deprecated.
This is for documentation purposes only, and does not affect the use of the `Field`.

```python hl_lines="13"
-8<- "queries/field_deprecation_reason.py"
```

### Custom resolvers

> Usually using a custom `Field` resolver is not necessary, and should be avoided
> if possible. This is because use of Model fields in resolvers without
> [additional optimizations](#custom-optimizations) can result in a lot of database queries.

You can override the resolver for a `Field` by adding a method to the class body of the `QueryType`
and decorating it with the `@<field_name>.resolve` decorator.

```python
-8<- "queries/field_resolver.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Field`.

The `self` argument is not an instance of the `QueryType`,
but `root` argument of the `GraphQLField` resolver. To clarify this,
it's recommended to change the argument's name to `root`,
as defined by the [`RESOLVER_ROOT_PARAM_NAME`](settings.md#resolver_root_param_name)
setting.

The value of the `root` argument for a `Field` is the **_model instance_** being queried.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

### Custom optimizations

> The optimizer is covered more thoroughly in the [Optimizer](optimizer.md) section.

Usually touching the `Field` optimizations is not necessary, but if required,
you can do so by adding a method to the class body of the `QueryType` and
decorating it with the `@<field_name>.optimize` decorator.

```python
-8<- "queries/field_optimize.py"
```

This hook can be helpful when you require data from outside the GraphQL execution context
to e.g. make permission checks.

### Directives

You can add directives to the `Field` by providing them using the `directives` argument.
The directive must be usable in the `FIELD_DEFINITION` location.

```python
-8<- "queries/field_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "queries/field_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `Field` from certain users by decorating a method with the
`<field_name>.visible` decorator. Hiding a `Field` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Field` didn't exist in the first place.

```python
-8<- "queries/field_visible.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Field`.

The `self` argument is not an instance of the `QueryType`,
but the instance of the `Field` that is being used.

Since visibility checks occur in the validation phase of the GraphQL request,
GraphQL resolver info is not yet available. However, you can access the
Django request object using the `request` argument.
From this, you can, e.g., access the request user for permission checks.

///

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `Field` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Field`.

```python
-8<- "queries/field_extensions.py"
```

`Field` extensions are made available in the GraphQL `ObjectType` field extensions
after the schema is created. The `QueryType` itself is found in the GraphQL field extensions
under a key defined by the [`QUERY_TYPE_EXTENSIONS_KEY`](settings.md#query_type_extensions_key)
setting.
