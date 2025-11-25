description: Documentation on mutations in Undine.

# Mutations

In this section, we'll cover Undine's [`MutationTypes`](#mutationtypes)
which allow you to create mutations base on your Django Models.

For mutations not concerning your Django Models,
you can create [function](schema.md#function-references) `Entrypoints`.

## MutationTypes

A `MutationType` represents a GraphQL `InputObjectType` for mutating a Django Model in the GraphQL schema.
A basic `MutationType` is created by subclassing `MutationType`
and adding a Django Model to it as a generic type parameter. You must also add at least one
[`Input`](#inputs) to the class body of the `MutationType`.

```python
-8<- "mutations/mutation_type_basic.py"
```

### Mutation kind

How a mutation using a `MutationType` resolves is determined by its `kind`.
The basic types of mutations are `create`, `update`, and `delete`, which can be used
to create, update and delete instances of a `MutationType's` Model respectively.
There are also two special mutation kinds: `custom` and `related`, which are covered
in [custom mutations](#custom-mutations) and [related mutations](#related-mutations) respectively.

```python
-8<- "mutations/mutation_type_kind.py"
```

`kind` can also be omitted, in which case the `MutationType`
will determine the mutation `kind` using these rules:

1. If the word `create` can be found in the name of the `MutationType`, `kind` will be `create`.
2. If the word `update` can be found in the name of the `MutationType`, `kind` will be `update`.
3. If the word `delete` can be found in the name of the `MutationType`, `kind` will be `delete`.
4. If either the `__mutate__` or `__bulk_mutate__` method has been defined on the `MutationType`,
   `kind` will be `custom`.
5. Otherwise, an error will be raised.

```python
-8<- "mutations/mutation_type_create.py"
```

### Auto-generation

A `MutationType` can automatically introspect its Django Model and convert the Model's fields
to `Inputs` on the `MutationType`. For example, if the `Task` model has the following fields:

```python
-8<- "mutations/models_1.py"
```

Then the GraphQL `InputObjectType` for a `MutationType` for a `create` mutation using auto-generation would be:

```graphql
input TaskCreateMutation {
    name: String!
    done: Boolean! = true
    # `createdAt` not included since it has `auto_now_add=True`
}
```

For an `update` mutation, the `pk` field is included for selecting the
mutation target, the rest of the fields are all made nullable (=not required),
and no default values are added. This is essentially a fully partial update mutation.

```graphql
input TaskUpdateMutation {
    pk: Int!
    name: String
    done: Boolean
}
```

For a `delete` mutation, only the `pk` field is included for selecting the
instance to delete.

```graphql
input TaskDeleteMutation {
    pk: Int!
}
```

To use auto-generation, either set [`AUTOGENERATION`](settings.md#autogeneration) setting to `True`
to enable it globally, or set the `auto` argument to `True` in the `MutationType` class definition.
With this, you can leave the `MutationType` class body empty.

```python
-8<- "mutations/mutation_type_auto.py"
```

You can exclude some Model fields from the auto-generation by setting the `exclude` argument:

```python
-8<- "mutations/mutation_type_exclude.py"
```

### Output type

By default, a `MutationType` uses a `QueryType` with the same Model as its output type.
This means that one must be created, even if not used for querying outside of the `MutationType`.
You don't need to explicitly link the `QueryType` to the `MutationType`
since the `MutationType` will automatically look up the `QueryType`
from the [`QueryType` registry](queries.md#querytype-registry).

```python
-8<- "mutations/mutation_type_output_type.py"
```

This would create the following mutation in the GraphQL schema:

```graphql
type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
}

input TaskCreateMutation {
    name: String!
    done: Boolean! = false
}

type Mutation {
    createTask(input: TaskCreateMutation!): TaskType!
}
```

If you wanted to link the `QueryType` explicitly, you could do so by overriding the
`__query_type__` classmethod.

```python
-8<- "mutations/mutation_type_query_type.py"
```

If you wanted a fully custom output type, you can override the `__output_type__` classmethod.

```python
-8<- "mutations/mutation_type_output_type_custom.py"
```

### Permissions

You can add mutation-level permission checks to mutations executed using a `MutationType`
by defining the `__permissions__` classmethod.

```python
-8<- "mutations/mutation_type_permissions.py"
```

/// details | About method signature

For `create` mutations, the `instance` is a brand new instance of the model.
Note that this also means that it doesn't have a primary key yet.

For `update` and `delete` mutations, `instance` is the existing model
instance that is being mutated.

///

This method will be called for each instance of `Task` that is mutated
by this `MutationType`.

You can raise any `GraphQLError` when a permission check fails, but it's recommended to
raise a `GraphQLPermissionError` from the `undine.exceptions` module.

### Validation

You can add mutation-level validation to mutations executed using a `MutationType`
by defining the `__validate__` classmethod.

```python
-8<- "mutations/mutation_type_validate.py"
```

/// details | About method signature

For `create` mutations, the `instance` is a brand new instance of the model.
Note that this also means that it doesn't have a primary key yet.

For `update` and `delete` mutations, `instance` is the existing model
instance that is being mutated.

///

You can raise any `GraphQLError` when a validation check fails, but it's recommended to
raise a `GraphQLValidationError` from the `undine.exceptions` module.

### After mutation handling

You can add custom handling that happens after the mutation is done by defining the`__after__`
classmethod on the `MutationType`.

```python
-8<- "mutations/mutation_type_after.py"
```

/// details | About method signature

For `create` and `update` mutations, `instance` is the model instance that was either
created or updated.

For `delete` mutations, `instance` is the instance that was deleted.
This means that its relations have been disconnected, and its primary key
has been set to `None`.

`input_data` contains the input data that was used in the mutation.

///

This can be useful for doing things like sending emails.

### Custom mutations

You can define your own custom logic by defining the `__mutate__` or `__bulk_mutate__` method on
the `MutationType` class for single or bulk mutations respectively.

```python
-8<- "mutations/mutation_type_custom.py"
```

In the above example, the `MutationType` still a `create` mutation,
just with some custom mutation logic. The `MutationType` `kind` still affects [auto-generation](#auto-generation),
which resolvers are used (whether the mutation creates a new instance or modifies an existing one),
as well as some inference rules for its `Inputs`.

You can also use a special `custom` mutation `kind` when using custom resolvers.

```python
-8<- "mutations/mutation_type_custom_kind.py"
```

This affects the creation of the `MutationType` in the following ways:

- [Auto-generation](#auto-generation) is not used, even if it is enabled
- No `Input` is [input-only](#input-only-inputs) by default

`Custom` mutations will resolve like create or update mutations, depending
on if an `Input` named `pk` is present on the `MutationType`.

By default, the output type of a custom mutation is still the `ObjectType`
from the `QueryType` matching the `MutationType's` Model. If your custom
mutation returns an instance of that Model, it will work without additional changes.
However, if you want to return a different type, you can do so by overriding
the `__output_type__` classmethod on the `MutationType`.

```python
-8<- "mutations/mutation_type_output_type_custom.py"
```

### Related mutations

Let's say you have the following models:

```python
-8<- "mutations/models_2.py"
```

If you wanted to create both a `Task` and its related `Project` in a single mutation,
you could link two mutation types using a special `related` `kind` of `MutationType`.

```python
-8<- "mutations/mutation_type_related.py"
```

This creates the following `InputObjectTypes`:

```graphql hl_lines="9"
input TaskProject {
    pk: Int
    name: String
}

input TaskCreateMutation {
    name: String!
    done: Boolean! = false
    project: TaskProject!
}
```

[Auto-generation](#auto-generation) and inference rules for `related` `MutationTypes`
are the same as for `update` `MutationTypes`, except the `pk` field is also not required.
This allows you to create, update, link, or unlink new or existing related models
during the mutation as you see fit.

Let's give a few examples. Assuming you added the `TaskCreateMutation` to the schema with
an `Entrypoint` `create_task`, you can create a new `Task` together with a new `Project` like this:

```graphql
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        name: "New project"
      }
    }
  ) {
    pk
  }
}
```

Or you can link an existing `Project` to a new `Task` like this:

```graphql
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        pk: 1
      }
    }
  ) {
    pk
    name
  }
}
```

Or you can link an existing project while modifying it:

```graphql
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        pk: 1
        name: "Updated project"
      }
    }
  ) {
    pk
    name
  }
}
```

Permission an validation checks are run for `related` `MutationTypes` and their `Inputs` as well,
although existing instances are not fetched from the database even if the input contains its primary key
(for performance reasons).

```python
-8<- "mutations/mutation_type_related_permissions.py"
```

Note that if the `Input` connecting the `related` `MutationType` defines a permission or validation check,
that check is run instead of the `related` `MutationType` permission or validation check.

### Related mutation action

When updating an instance and its relations using a related mutation,
that instance may already have existing related objects. For some relations,
it's clear what should happen to relations that are not selected in the related mutation.

- **Forward one-to-one relation**: Selects the new related object to attach to, or set the relation to null.
  Reverse one-to-one relation can always be missing.
- **Forward foreign key (many-to-one) relation**: Selects the new related object to attach to, or set the relation to null.
  Reverse relations do not have any constraints.
- **Many-to-many relations**: Selects the new related objects that the current instance should be linked to.
  Non-selected objects are unlinked, meaning through table rows are deleted.

For other relations, you might need different behavior depending on the situation:

- **Reverse one-to-one relation**: You might want to delete the exiting related object, or set the relation to null
  (although the forward part of the relation might not be nullable).
- **Reverse foreign key (one-to-many) relation**: You might want to delete exiting related objects,
  or set their relation to null (although the forward part of the relation might not be nullable).
  You might even want to leave the existing relations as they are.

The action that should be taken for the relations is defined by the `MutationType` `related_action` argument.
The actions are as follows:

- `null`: Set the relaton to null. If the relation is not nullable, an error is raised. Default action.
- `delete`: Delete the related objects.
- `ignore`: Leave the existing relations as they are. For one-to-one relations, an error is raised.

```python
-8<- "mutations/mutation_type_related_action.py"
```

Note that this action applies to all related mutations executed from the "parent" `MutationType`.
If you need more granular control, you should make the mutation a [custom mutation](#custom-mutations)
instead.

### Order of operations

The order of operations for executing a mutation using a `MutationType` is as follows:

1. [Model inputs](#model-field-references) have their Model instances fetched.
2. [Hidden inputs](#hidden-inputs) are be added to the input data.
3. [Function inputs](#function-references) are run.
4. `MutationType` [permissions](#permissions) and `Input` [permissions](#permissions_1) are checked.
5. `MutationType` [validation](#validation) and `Input` [validation](#validation_1) are run.
6. [Input-only inputs](#input-only-inputs) are removed from the input data.
7. Mutation is executed.
8. `MutationType` [after handling](#after-mutation-handling) is run.

If multiple `GraphQLErrors` are raised in the permission or validation steps for different inputs,
those errors are returned together. The error's `path` will point to the `Input` where
the exception was raised.

/// details | Example result with multiple errors

```json hl_lines="10 18"
{
    "data": null,
    "errors": [
        {
            "message": "Validation error.",
            "extensions": {
                "status_code": 400,
                "error_code": "VALIDATION_ERROR"
            },
            "path": ["createTask", "name"]
        },
        {
            "message": "Validation error.",
            "extensions": {
                "status_code": 400,
                "error_code": "VALIDATION_ERROR"
            },
            "path": ["createTask", "done"]
        }
    ]
}
```

///

### Schema name

By default, the name of the generated GraphQL `InputObjectType` for a `MutationType` class
is the name of the `MutationType` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "mutations/mutation_type_schema_name.py"
```

### Description

To provide a description for the `MutationType`, you can add a docstring to the class.

```python
-8<- "mutations/mutation_type_description.py"
```

### Directives

You can add directives to the `MutationType` by providing them using the `directives` argument.
The directive must be usable in the `INPUT_OBJECT` location.

```python
-8<- "mutations/mutation_type_directives.py"
```

You can also add them using the decorator syntax.

```python
-8<- "mutations/mutation_type_directives_decorator.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `MutationType` from certain users using the `__is_visible__` method.
Hiding an `MutationType` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Entrypoint` or `Input` using the `MutationType` didn't exist in the first place.

```python
-8<- "mutations/mutation_type_visible.py"
```

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `MutationType` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `MutationType`.

```python
-8<- "mutations/mutation_type_extensions.py"
```

`MutationType` extensions are made available in the GraphQL `InputObjectType` extensions
after the schema is created. The `MutationType` itself is found in the GraphQL `InputObjectType` extensions
under a key defined by the `MUTATION_TYPE_EXTENSIONS_KEY` setting.

## Inputs

An `Input` is used to define a possible input in a `MutationType`.
Usually `Inputs` correspond to fields on the Django Model for their respective `MutationType`.
In GraphQL, an `Input` represents a `GraphQLInputField` on an `InputObjectType`.

An `Input` always requires a _**reference**_ from which it will create the proper
input type and default value for the `Input`.

### Model field references

For `Inputs` corresponding to Django Model fields, the `Input` can be used without passing in a reference,
as its attribute name in the `MutationType` class body can be used to identify
the corresponding model field.

```python
-8<- "mutations/input.py"
```

To be a bit more explicit, you could use a string referencing the model field:

```python
-8<- "mutations/input_string.py"
```

For better type safety, you can also use the model field itself:

```python
-8<- "mutations/input_field.py"
```

### Function references

Functions (or methods) can also be used to create `Inputs`.
This can be done by decorating a method with the `Input` class.

```python
-8<- "mutations/input_decorator.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Input`.

The `self` argument is not an instance of the `MutationType`,
but the **_Model instance_** that is being mutated.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

///

The `value` argument determines the input given by the user, which can then be transformed
into the input data for the mutation in the function. The type of the `value` argument
determines the input type of the function input in. The `value` argument can also be left out,
in which case the input will become a [`hidden`](#hidden-inputs) input.

```python
-8<- "mutations/input_decorator_hidden.py"
```

### Model references

A Model class can also be used as an `Input` reference.
In this case, a Model instance will be fetched to the input data from a primary key
provided to the `Input` before permission and validation checks (see [order of operation](#order-of-operations)).
If an instance is not found, the `Input` will raise an error before any other checks are run.

```python
-8<- "mutations/input_model_reference.py"
```

The Model doesn't necessarily need to be a related Model of the parent `MutationType` Model,
but if it is not, the input will be an [input-only](#input-only-inputs) input by default.

### Permissions

You can restrict the use of an `Input` by first defining the `Input` in the class body
of the `MutationType` and then adding a method with the `@<input_name>.permissions` decorator.

```python
-8<- "mutations/input_permissions.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Input`.

The `self` argument is not an instance of the `MutationType`,
but the **_model instance_** that is being mutated.

The `info` argument is the GraphQL resolve info for the request.

The `value` argument is the value provided for the input.

///

You can raise any `GraphQLError` when validation fails, but it's recommended to
raise a `GraphQLPermissionError` from the `undine.exceptions` module.

### Validation

You can validate the value of an `Input` by first defining the `Input` in the class body
of the `MutationType` and then adding a method with the `@<input_name>.validate` decorator.

```python
-8<- "mutations/input_validate.py"
```

/// details | About method signature

The `self` argument is not an instance of the `MutationType`,
but the **_model instance_** that is being mutated.

The `info` argument is the GraphQL resolve info for the request.

The `value` argument is the value provided for the input.

///

You can raise any `GraphQLError` when validation fails, but it's recommended to
raise a `GraphQLValidationError` from the `undine.exceptions` module.

### Conversion

Normally, values for `Inputs` are parsed and converted based on the `Input's` [`Scalar`](scalars.md).
However, you can add additional convertion for an individual `Input` by first defining
the `Input` in the class body of the `MutationType` and then adding a method with
the `@<input_name>.convert` decorator.

```python
-8<- "mutations/input_convert.py"
```

/// details | About method signature

The `self` argument is not an instance of the `MutationType`,
but the `Input` whose value is being converted.

The `value` argument is the value provided for the `Input`.

///

Note that conversion functions are also run for [default values](#default-values).

### Default values

By default, an `Input` is able to determine its default value based on its reference.
For example, for a [Model field](#model-field-references), the default value is taken
from its `default` attribute. However, default values are only added automatically for
create mutations, as update mutations should only update fields that have been provided.

If you want to set the default value for an `Input` manually, you can set
the `default_value` argument on the `Input`.

```python
-8<- "mutations/input_default_value.py"
```

Note that the default value needs to be a valid GraphQL default value,
i.e., a string, integer, float, boolean, or null, or a list or dictionary of these.

> Note that you, indeed, can use lists and dictionaries as default values, even though they
> are mutable. Undine will make a copy of any non-hashable default value before
> mutating it, so that you won't accidentally change the default value.

### Input-only inputs

Input-only `Inputs` show up in the GraphQL schema, but their values are removed from the mutation data
before the actual mutation (see [order of operations](#order-of-operations)),
usually because they are not part of the Model being mutated. They can be used as additional data for
validation and permissions checks, e.g. flags to control the behavior of the mutation.

```python
-8<- "mutations/input_input_only.py"
```

Notice that the `Input` reference is `bool`. This is to indicate the input type,
as there is no Model field to infer the type from.

### Hidden inputs

Hidden `Inputs` are not included in the GraphQL schema, but their values are added before
the mutation is executed (see [order of operations](#order-of-operations)).
They can be used, for example, to set default values for fields that should not be overridden by users.

```python
-8<- "mutations/input_hidden.py"
```

One common use case for hidden inputs is to set the current user
as the default value for a relational field. Let's suppose that
the `Task` model has a foreign key `user` to the `User` Model.
To assign a new task to the current user during creation,
you can define a hidden input for the `user` field:

```python
-8<- "mutations/input_current_user.py"
```

See [Function References](#function-references) for more details.

### Required inputs

By default, an `Input` is able to determine whether it's required or not based on
its reference, as well as the `kind` of `MutationType` it's used in. If you want to
set this manually, you can set the `required` argument on the `Input`.

```python
-8<- "mutations/input_required.py"
```

> Note that due to GraphQL implementation details, there is no distinction between
> _required_ and _nullable_. Therefore, non-required `Inputs` can always accept `null` values,
> and required inputs cannot accept `null` values.

### Field name

A `field_name` can be provided to explicitly set the Django Model field
that the `Input` corresponds to.

```python
-8<- "mutations/input_field_name.py"
```

This can be useful when the `Input` has a different name and type in the GraphQL schema than in the Model.

### Schema name

By default, the name of the `InputObjectType` field generated from an `Input` is the same
as the name of the `Input` on the `MutationType` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the `InputObjectType` field separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "mutations/input_schema_name.py"
```

This can be useful when the desired name of the `InputObjectType` field is a Python keyword
and cannot be used as the `Input` attribute name.

### Descriptions

By default, an `Input` is able to determine its description based on its reference.
For example, for a [Model field](#model-field-references), the description is taken from its `help_text`.
If the reference has no description, or you wish to add a different one,
this can be done in two ways:

1) By setting the `description` argument.

```python
-8<- "mutations/input_description.py"
```

2) As class attribute docstrings, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "mutations/input_description_class.py"
```

When using [function references](#function-references), instead of a class attribute docstring,
you add a docstring to the function/method used as the reference instead.

```python
-8<- "mutations/input_decorator_docstring.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Input` as deprecated.
This is for documentation purposes only, and does not affect the use of the `Field`.

```python hl_lines="13"
-8<- "mutations/input_deprecation_reason.py"
```

### Directives

You can add directives to the `Input` by providing them using the `directives` argument.
The directive must be usable in the `INPUT_FIELD_DEFINITION` location.

```python
-8<- "mutations/input_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "mutations/input_directives_matmul.py"
```

See the [Directives](directives.md) section for more details on directives.

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide an `Input` from certain users by decorating a method with the
`<input_name>.visible` decorator. Hiding an `Input` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `Input` didn't exist in the first place.

```python
-8<- "mutations/input_visible.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `Input`.

The `self` argument is not an instance of the `MutationType`,
but the instance of the `Input` that is being used.

Since visibility checks occur in the validation phase of the GraphQL request,
GraphQL resolver info is not yet available. However, you can access the
Django request object using the `request` argument.
From this, you can, e.g., access the request user for permission checks.

///

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### GraphQL extensions

You can provide custom extensions for the `Input` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Input`.

```python
-8<- "mutations/input_extensions.py"
```

`Input` extensions are made available in the GraphQL `InputObjectType` field extensions
after the schema is created. The `Input` itself is found in the GraphQL input field extensions
under a key defined by the [`INPUT_EXTENSIONS_KEY`](settings.md#input_extensions_key)
setting.
