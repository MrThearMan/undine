# Mutations

In this section, we'll cover Undine's [`MutationTypes`](#mutationtypes)
which allow you to expose your Django models through the GraphQL schema for mutations,
expanding on the basics introduced in the [Tutorial](tutorial.md).

If you to mutate data outside of your Django models,
see the [Function References](schema.md#function-references) section
in the Schema documentation.

## MutationTypes

A `MutationType` represents a GraphQL `InputObjectType` for mutating a Django model
in the GraphQL schema. A basic `MutationType` is created by subclassing `MutationType`
and adding a Django model to it as a generic type parameter:

```python
-8<- "mutations/mutation_type_basic.py"
```

### Mutation kind

`MutationType` can be used for `create`, `update`, `delete` as well as `custom` mutations.
The _kind_ of mutation a certain `MutationType` is for is determined by its
`kind`, which can be set in the `MutationType` class definition.
This allows Undine to generate the correct fields using [auto-generation](#auto-generation),
as well as link the correct mutation resolver to the `MutationType`.

```python
-8<- "mutations/mutation_type_kind.py"
```

`kind` can also be omitted, in which case the `MutationType`
will determine the mutation `kind` using this algorithm:

1. If `__mutate__` method has been defined on the `MutationType`, `kind` will be `custom` (see [custom mutations](#custom-mutations)).
2. If the word `create` can be found in the name of the `MutationType`, `kind` will be `create`.
3. If the word `update` can be found in the name of the `MutationType`, `kind` will be `update`.
4. If the word `delete` can be found in the name of the `MutationType`, `kind` will be `delete`.
5. If the word `related` can be found in the name of the `MutationType`, `kind` will be `related` (see [related mutations](#related-mutations)).
6. Otherwise, `kind` will be `custom`.

```python
-8<- "mutations/mutation_type_create.py"
```

### Auto-generation

By default, a `MutationType` automatically introspects its model and converts the model's fields
to input fields on the generated `InputObjectType`. For example, if the `Task` model has the following fields:

```python
-8<- "mutations/models_1.py"
```

Then the GraphQL `InputObjectType` for a `MutationType` for a `create` mutation would be:

```graphql
input TaskCreateMutation {
    name: String!
    done: Boolean = true
    # `createdAt` not included since it has `auto_now_add=True`
}
```

For an `update` mutation, the `pk` field is included for selecting the
mutation target, the rest of the fields are all made nullable (=not required),
and no default values are added.

```graphql
input TaskUpdateMutation {
    pk: Int!
    name: String
    done: Boolean
}
```

For a `delete` mutation, only the `pk` field is included for selecting the
mutation target.

```graphql
input TaskDeleteMutation {
    pk: Int!
}
```

You can disable auto-generation globally using the [`AUTOGENERATION`](settings.md#autogeneration) setting,
or the `MutationType` by setting the `auto` argument to `False` in the class definition:

```python
-8<- "mutations/mutation_type_no_auto.py"
```

Alternatively, you could exclude some `Inputs` from the auto-generation by setting the `exclude` argument:

```python
-8<- "mutations/mutation_type_exclude.py"
```

### Output type

A `MutationType` requires a `QueryType` for the same model to exist in the schema,
since the `MutationType` will use the `ObjectType` generated from the `QueryType`
as the output type of the mutation.

You don't need to explicitly link the `QueryType` to the `MutationType`
since `MutationType` will automatically look up the `QueryType` for the same model
from the [`QueryType` registry](queries.md#querytype-registry).

```python
-8<- "mutations/mutation_type_output.py"
```

This would generate the following mutation in the GraphQL schema:

```graphql
type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
}

input TaskCreateMutation {
    name: String!
    done: Boolean = false
}

type Mutation {
    createTask(input: TaskCreateMutation!): TaskType!
}
```

If you wanted to link the `QueryType` explicitly, you could do so by overriding the
`__query_type__` classmethod.

```python
-8<- "mutations/mutation_type_output_explicit.py"
```

### Permissions

You can add mutation-level permission checks for a `MutationType` by defining the `__permissions__` classmethod.

```python
-8<- "mutations/mutation_type_permissions.py"
```

/// details | About method signature

For `create` mutations, the `instance` is a brand new instance of the model,
without any of the `input_data` values applied. This also means that it doesn't
have a primary key yet.

For `update` and `delete` mutations, the `instance` is the instance that is being
mutated, with the `input_data` values applied.

///

This method will be called for each instance of `Task` that is mutated
by this `MutationType`. For bulk mutations, this means that the method will be called
for each item in the mutation input data.

You can raise any `GraphQLError` when validation fails, but it's recommended to
raise a `GraphQLPermissionError` from the `undine.exceptions` module.

### Validation

You can add mutation-level validation for a `MutationType` by defining the `__validate__` classmethod.

```python
-8<- "mutations/mutation_type_validate.py"
```

/// details | About method signature

For `create` mutations, the `instance` is a brand new instance of the model,
without any of the `input_data` values applied. This also means that it doesn't
have a primary key yet.

For `update` and `delete` mutations, the `instance` is the instance that is being
mutated, with the `input_data` values applied.

///

You can raise any `GraphQLError` when validation fails, but it's recommended to
raise a `GraphQLValidationError` from the `undine.exceptions` module.

### After mutation handling

You can add custom handling that happens after the mutation is done by defining the`__after__`
classmethod on the `MutationType`.

```python
-8<- "mutations/mutation_type_after.py"
```

/// details | About method signature

For `create` and `update` mutations, the `instance` is the instance that was either
created or updated, with the `input_data` values applied.

`previous_data` contains the field values in the instance before the mutation.
For `create` mutations, this will be empty. Related objects are not included.

For `delete` mutations, the `instance` is the instance that was deleted.
This means that its relations have been disconnected, and its primary key
has been set to `None`.

///

This can be useful for doing things like sending emails.

### Custom mutations

If the normal mutation flow is too restrictive for your use case, you can
define your own custom mutations by defining the `__mutate__` method on
the `MutationType` class.

```python
-8<- "mutations/mutation_type_custom.py"
```

Custom mutations have a few changes compared to normal mutations:

- [Auto-generation](#auto-generation) is not used
- [After-mutation handling](#after-mutation-handling) is not called
- `Inputs` are never [input-only](#input-only-inputs)
- [Validations](#validation) are run and [permissions](#permissions) are checked,
  but the instance argument for them will be the GraphQL `root` value
  instead of the instance being mutated (since there might not be one)

Note that by default, the output type of a custom mutation is still the `ObjectType`
from the `QueryType` matching the `MutationType's` model. So, if your custom
mutation returns an instance of that model, it will work without additional changes.

However, if you want to return a different type, you can do so by overriding
the `__output_type__` classmethod on the `MutationType`.

```python
-8<- "mutations/mutation_type_custom_output_type.py"
```

### Order of operations

The order of operations for executing a mutation using a `MutationType` is as follows:

1. `MutationType` [permissions](#permissions) are checked
2. For each `Input`:
    - `Input` [permissions](#permissions_1) are checked
    - `Input` [validation](#validation_1) is run
3. `MutationType` [validation](#validation) is run
4. Mutation is executed
5. `MutationType` [after handling](#after-mutation-handling) is run

If `GraphQLErrors` are raised during steps 1-3, the validation and permission checks continue until
step 4, and then all exceptions are raised at once. The error's `path` will point to the input where
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

By default, the name of the generated `InputObjectType` is the same as the name of the `MutationType` class.
If you want to change the name, you can do so by setting the `schema_name` argument:

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

```python
-8<- "mutations/mutation_type_directives.py"
```

See the [Directives](directives.md) section for more details on directives.

### GraphQL extensions

You can provide custom extensions for the `MutationType` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `MutationType`.

```python
-8<- "mutations/mutation_type_extensions.py"
```

`MutationType` extensions are made available in the GraphQL `InputObjectType` extensions
after the schema is created. The `MutationType` itself is found in the `extensions`
under a key defined by the `MUTATION_TYPE_EXTENSIONS_KEY` setting.

## Inputs

An `Input` is a class that is used to define a possible input for a `MutationType`.
Usually `Inputs` correspond to fields on the Django model for their respective `MutationType`.
In GraphQL, an `Input` represents a `GraphQLInputField` in an `InputObjectType`.

An `Input` always requires a _**reference**_ from which it will create the proper
input type and default value for the `Input`.

### Model field references

As seen in the [`MutationType`](#mutationtypes) section, you don't need to provide model fields
explicitly thanks to [auto-generation](#auto-generation), but if you wanted to be more explicit,
you could add the `Inputs` to the `MutationType` class body. In this case, the `Input` can be used
without a reference, as its attribute name in the `MutationType` class body can be used to identify
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

Being explicit like this is only required if the name of the argument in the GraphQL schema
is different from the model field name.

```python
-8<- "mutations/input_alias.py"
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
but the **_model instance_** that is being mutated.

The `info` argument can be left out, but if it's included, it should always
have the `GQLInfo` type annotation.

The `value` argument can be left out:

```python
-8<- "mutations/input_decorator_hidden.py"
```

This makes the `Input` [`hidden`](#hidden-inputs) in the GraphQL
schema since it takes no user input.

Also, since `current_user` is not a field on the `Task` model,
the `Input` is also [`input_only`](#input-only-inputs).

///

### Model references

Models can also be used as `Input` references, when the `Input` is for a related field.
In this case, the related model will be fetched to the input data between the [permission](#permissions_1)
checks and the [validation](#validation_1) checks.

```python
-8<- "mutations/input_model_reference.py"
```

Model references are mainly useful in [custom mutations](#custom-mutations),
as regular mutations have special handling for related fields.

### Related mutations

Let's say you have the following models:

```python
-8<- "mutations/models_2.py"
```

If you wanted to create both a `Task` and its related `Project` in a single mutation,
you could use a special `related` `kind` of `MutationType` as a `Input` reference.

```python
-8<- "mutations/mutation_type_kind_related.py"
```

This creates the following `InputObjectTypes`:

```graphql hl_lines="9"
input TaskProject {
    pk: Int
    name: String
}

input TaskCreateMutation {
    name: String!
    done: Boolean = false
    project: TaskProject!
}
```

Related `MutationTypes` are only allowed as references `Inputs`, not in `Entrypoints`.
They can be used to create, update, delete, or link existing related models, whether
the "main" mutation is for creating or updating the main model. That's why all the fields
in the the created `TaskProject` are nullable, even if the `Project` model requires
the `name` field to be provided when creating a new `Project`.

Let's give a few examples. Assuming you added the `TaskCreateMutation` to our Schema with
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

Since the `project` relation on the `Task` model is not nullable,
the input is required, but if it was nullable, you could also unlink relations
during update mutations like this:

```graphql
mutation {
  updateTask(
    input: {
      pk: 1
      name: "Updated task"
      project: null
    }
  ) {
    pk
  }
}
```

Since the relation's nullability also affects whether the `Input` is required or not,
a nullable relation can be left out during mutations. If left out during create mutations,
the relation will be set to `null`, and in update mutations, the relation won't be updated.

> Note that the total amount of objects that can be mutated in a single mutation
> is limited by the [`MUTATION_INSTANCE_LIMIT`](settings.md#mutation_instance_limit) setting.
> This also affects bulk mutations.

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

This method will be called for each instance of `Task` that is mutated
by this `MutationType`. For bulk mutations, this means that the method will be called
for each item in the mutation input data.

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

### Default values

By default, an `Input` is able to determine its default value based on its reference.
For example, for a model field, the default value is taken from its `default` attribute.
However, default values are only added automatically for create mutations,
as update mutations should only update fields that have been provided.

If you want to set the default value for an `Input` manually, you can set
the `default_value` argument on the `Input`.

```python
-8<- "mutations/input_default_value.py"
```

Note that the default value needs to be a valid GraphQL default value
(i.e. a string, integer, float, boolean, or null, or a list or dictionary of these).

### Input-only inputs

Input-only `Inputs` show up in the GraphQL schema, but are not part of the actual mutation,
usually because they are not part of the model being mutated.
They can be used as additional data for validation and permissions checks.

```python
-8<- "mutations/input_input_only.py"
```

Notice that the `Input` reference is `bool`. This is to indicate the input type,
as there is no model field to infer the type from. For the same reason, you don't
_actually_ need to specify the `input_only` argument.

### Hidden inputs

Hidden `Inputs` are not included in the GraphQL schema, but their values are added before
the mutation is executed. They can be used, for example, to set default values
for fields that should not be overridden by users.

```python
-8<- "mutations/input_hidden.py"
```

One common use case for hidden inputs is to set the current user
as the default value for a relational field. Let's suppose that
the `Task` model has a foreign key `user` to the `User` model.
To assign a new task to the current user during creation,
you can define a hidden input for the `user` field:

```python
-8<- "mutations/input_current_user.py"
```

See [Function References](#function-references) for more details.

### Required inputs

By default, an `Input` is able to determine whether it is required or not based on
is reference, as well as the `kind` of `MutationType` it is used in. If you want to
override this, you can set the `required` argument on the `Input`.

```python
-8<- "mutations/input_required.py"
```

### Field name

A `field_name` can be provided to explicitly set the Django model field name
that the `Input` corresponds to. This can be useful when the field has a different
name and type in the GraphQL schema than in the model.

```python
-8<- "mutations/input_field_name.py"
```

### Schema name

An `Input` is also able to override the name of the `Input` in the GraphQL schema.
This can be useful for renaming fields for the schema, or when the desired name is a Python keyword
and cannot be used as the `Input` attribute name.

```python
-8<- "mutations/input_schema_name.py"
```

### Descriptions

By default, an `Input` is able to determine its description based on its reference.
For example, for a model field, the description is taken from its `help_text`.

If the reference has no description, or you wish to add a different one,
this can be done in two ways:

1) By setting the `description` argument.

```python
-8<- "mutations/input_description.py"
```

2) As class variable docstrings.

```python
-8<- "mutations/input_description_class.py"
```

When using [function references](#function-references), instead of a class variable docstring,
you add a docstring to the function/method used as the reference instead.

```python
-8<- "mutations/input_decorator_docstring.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `Input` Input
This is for documentation purposes only, and does not affect the use of the `Field`.

```python hl_lines="13"
-8<- "mutations/input_deprecation_reason.py"
```

### Directives

You can add directives to the `Input` by providing them using the `directives` argument.

```python
-8<- "mutations/input_directives.py"
```

See the [Directives](directives.md) section for more details on directives.

### GraphQL extensions

You can provide custom extensions for the `Input` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Input`.

```python
-8<- "mutations/input_extensions.py"
```

`Input` extensions are made available in the GraphQL `InputField` extensions
after the schema is created. The `Input` itself is found in the `extensions`
under a key defined by the [`INPUT_EXTENSIONS_KEY`](settings.md#input_extensions_key)
setting.
