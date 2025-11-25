description: Documentation on GraphQL directives in Undine.

# Directives

In this section, we'll cover how you can use GraphQL directives in Undine.
Directives are a way to add metadata to your GraphQL schema,
which can be accessed during query execution or by clients consuming your schema.

## Directive

In Undine, a GraphQL directive is implemented by subclassing the `Directive` class.

```python
-8<- "directives/directive.py"
```

Note that a `Directive` by itself doesn't do anything. It is only used as a way to define
additional metadata, which the GraphQL server or client can use at runtime.
If the directive implies some behavior, you'll need to add it, e.g., using a [`ValidationRule`](validation-rules.md).

Note that declared `Directives` are automatically added to the schema, even if they are not used.

A `Directive` always requires the _**locations**_ it can be used in to be set using the `locations` argument.
The locations can be divided into two categories: [_executable locations_](#executable-locations)
and [_type system locations_](#type-system-locations).

### Executable locations

Executable locations identify places in a GraphQL _document_ (i.e. "request") where a directive can be used.
See the example below on what these locations are.

#### `QUERY`

The `QUERY` location corresponds to _query_ operation.

```python
-8<- "directives/directive_location_query.py"
```

In schema definition:

```graphql
query ($pk: Int!) @new {
  task(pk: $pk) {
    pk
    name
    done
  }
}
```

#### `MUTATION`

The `MUTATION` location corresponds to _mutation_ operation.

```python
-8<- "directives/directive_location_mutation.py"
```

In schema definition:

```graphql
mutation ($input: CreateTaskMutation!) @new {
  createTask(input: $input) {
    pk
  }
}
```

#### `SUBSCRIPTION`

The `SUBSCRIPTION` location corresponds to _subscription_ operation.

```python
-8<- "directives/directive_location_subscription.py"
```

In schema definition:

```graphql
subscription @new {
  comments {
    username
    message
  }
}
```

#### `FIELD`

The `FIELD` location corresponds to a field selection on an operation.

```python
-8<- "directives/directive_location_field.py"
```

In schema definition:

```graphql
query {
  task(pk: 1) {
    pk @new
    name
    done
  }
}
```

#### `FRAGMENT_DEFINITION`

The `FRAGMENT_DEFINITION` location corresponds to a fragment definition.

```python
-8<- "directives/directive_location_fragment_definition.py"
```

In schema definition:

```graphql
query {
  task(pk: 1) {
    ...taskFragment
  }
}

fragment taskFragment on TaskType @new {
  pk
  name
  done
}
```

#### `FRAGMENT_SPREAD`

The `FRAGMENT_SPREAD` location corresponds to a fragment spread.

```python
-8<- "directives/directive_location_fragment_spread.py"
```

In schema definition:

```graphql
query {
  task(pk: 1) {
    ...taskFragment @new
  }
}

fragment taskFragment on TaskType {
  pk
  name
  done
}
```

#### `INLINE_FRAGMENT`

The `INLINE_FRAGMENT` location corresponds to an inline fragment.

```python
-8<- "directives/directive_location_inline_fragment.py"
```

In schema definition:

```graphql
query {
  node(id: "U3Vyc29yOnVzZXJuYW1lOjE=") {
    id
    ... on TaskType @new {
      name
    }
  }
}
```

#### `VARIABLE_DEFINITION`

The `VARIABLE_DEFINITION` location corresponds to a variable definition.

```python
-8<- "directives/directive_location_variable_fragment.py"
```

In schema definition:

```graphql
query ($pk: Int! @new) {
  task(pk: $pk) {
    pk
    name
    done
  }
}
```

### Type system locations

Type system locations identify places in a GraphQL _schema_ (i.e. "API") where a directive can be used.
Since Undine is used to define the schema, each type system location corresponds to an Undine
object that accepts that "type" of directive.

#### `SCHEMA`

The `SCHEMA` location corresponds to the schema definition itself.
Directives can be added here by using the `schema_definition_directives` argument
in the `create_schema` function.

```python hl_lines="16"
-8<- "directives/directive_location_schema.py"
```

In schema definition:

```graphql
directive @new on SCHEMA

schema @new {
  query: Query
}
```

#### `SCALAR`

The `SCALAR` location corresponds to the scalars defined in the schema.
In Undine, `ScalarType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_scalar.py"
```

In schema definition:

```graphql
directive @new on SCALAR

scalar Vector3 @new
```


#### `OBJECT`

The `OBJECT` location corresponds to the ObjectTypes defined in the schema.
In Undine, `QueryTypes` and `RootTypes` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_object.py"
```

In schema definition:

```graphql
directive @new on OBJECT

type TaskType @new {
  name: String!
  createdAt: DateTime!
}

type Query @new {
  tasks: [TaskType!]!
}
```

#### `FIELD_DEFINITION`

The `FIELD_DEFINITION` location corresponds to the fields defined in the schema.
In Undine, `Fields`, `InterfaceFields` and `Entrypoints` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_field_definition.py"
```

In schema definition:

```graphql
directive @new on FIELD_DEFINITION

interface Named {
  name: String! @new
}

type TaskType implements Named {
  name: String!
  createdAt: DateTime! @new
}

type Query {
  tasks: [TaskType!]! @new
}
```

#### `ARGUMENT_DEFINITION`

The `ARGUMENT_DEFINITION` location corresponds to the field arguments defined in the schema.
In Undine, `CalculationArguments` and `DirectiveArguments` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_argument_definition.py"
```

In schema definition:

```graphql
directive @new on ARGUMENT_DEFINITION

directive @version (
  value: String! @new
) on FIELD_DEFINITION

type TaskType {
  calc(
    value: Int! @new
  ): Int!
}
```

#### `INTERFACE`

The `INTERFACE` location corresponds to the interfaces defined in the schema.
In Undine, `InterfaceType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_interface.py"
```

In schema definition:

```graphql
directive @new on INTERFACE

interface Named @new {
  name: String!
}
```

#### `UNION`

The `UNION` location corresponds to the unions defined in the schema.
In Undine, `UnionType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_union.py"
```

In schema definition:

```graphql
directive @new on UNION

union SearchObject @new = TaskType | ProjectType
```

#### `ENUM`

The `ENUM` location corresponds to the enums defined in the schema.
In Undine, `OrderSet` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_enum.py"
```

In schema definition:

```graphql
directive @new on ENUM

enum TaskOrderSet @new {
  nameAsc
  nameDesc
}
```

#### `ENUM_VALUE`

The `ENUM_VALUE` location corresponds to the enum values defined in the schema.
In Undine, `Order` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_enum_value.py"
```

In schema definition:

```graphql
directive @new on ENUM_VALUE

enum TaskOrderSet {
  nameAsc @new
  nameDesc @new
}  
```

#### `INPUT_OBJECT`

The `INPUT_OBJECT` location corresponds to the input objects defined in the schema.
In Undine, `MutationType` and `FilterSet` accept `Directives` declared for this location.

```python
-8<- "directives/directive_location_input_object.py"
```

In schema definition:

```graphql
directive @new on INPUT_OBJECT

input TaskFilterSet @new {
  name: String
}

input TaskCreateMutation @new {
  name: String
}
```

#### `INPUT_FIELD_DEFINITION`

The `INPUT_FIELD_DEFINITION` location corresponds to the input field definitions defined in the schema.
In Undine, `Input` and `Filter` accept `Directives` declared for this location.

```python
-8<- "directives/directive_location_input_field_definition.py"
```

In schema definition:

```graphql
directive @new on INPUT_FIELD_DEFINITION

input TaskFilterSet {
  name: String @new
}

input TaskCreateMutation {
  name: String @new
}
```

### Is repeatable

A directive can be declared as repeatable using the `is_repeatable` argument.
This means that the directive can be used multiple times in the same location.

```python
-8<- "directives/directive_is_repeatable.py"
```

In schema definition:

```graphql
directive @new repeatable on FIELD_DEFINITION

type Query {
  example: String! @new @new
}
```

### Schema name

By default, the name of the generated GraphQL directive for a `Directive` class
is the name of the `Directive` class. If you want to change the name separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "directives/directive_schema_name.py"
```

### Extensions

You can provide custom extensions for the `Directive` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Directive`.

```python
-8<- "directives/directive_extensions.py"
```

`Directive` extensions are made available in the GraphQL directive extensions
after the schema is created. The `Directive` itself is found in the GraphQL directive extensions
under a key defined by the [`DIRECTIVE_EXTENSIONS_KEY`](settings.md#directive_extensions_key)
setting.

## DirectiveArgument

A `Directive` can optionally have a number of [`DirectiveArguments`](#directiveargument)
defined in the class body. These define the arguments that can or must be used with the directive.
A `DirectiveArgument` always requires _input type_ of the argument, which needs to be a GraphQL input type.

```python
-8<- "directives/directive_argument.py"
```

### Schema name

By default, the name of the GraphQL directive argument generated from a `DirectiveArgument` is the same
as the name of the `DirectiveArgument` on the `Directive` class (converted to _camelCase_ if
[`CAMEL_CASE_SCHEMA_FIELDS`](settings.md#camel_case_schema_fields) is enabled).
If you want to change the name of the GraphQL directive argument separately,
you can do so by setting the `schema_name` argument:

```python
-8<- "directives/directive_argument_schema_name.py"
```

This can be useful when the desired name of the GraphQL directive argument is a Python keyword
and cannot be used as the `DirectiveArgument` attribute name.

### Description

A description for a `DirectiveArgument` can be provided in on of two ways:

1) By setting the `description` argument.

```python
-8<- "directives/directive_argument_description.py"
```

2) As class attribute docstring, if [`ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS`](settings.md#enable_class_attribute_docstrings) is enabled.

```python
-8<- "directives/directive_argument_description_class.py"
```

### Default value

A `default_value` can be provided to set the default value for the `DirectiveArgument`.

```python
-8<- "directives/directive_argument_default_value.py"
```

### Deprecation reason

A `deprecation_reason` can be provided to mark the `DirectiveArgument` as deprecated.

```python
-8<- "directives/directive_argument_deprecation_reason.py"
```

### Directives

You can add directives to the `DirectiveArgument` by providing them using the `directives` argument.
The directive must be usable in the `ARGUMENT_DEFINITION` location.

```python
-8<- "directives/directive_argument_directives.py"
```

You can also add them using the `@` operator (which kind of looks like GraphQL syntax):

```python
-8<- "directives/directive_argument_directives_matmul.py"
```

### Visibility

> This is an experimental feature that needs to be enabled using the
> [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) setting.

You can hide a `DirectiveArgument` from certain users by decorating a method with the
`<arg_name>.visible` decorator. Hiding a `DirectiveArgument` means that it will not be included in introspection queries,
and trying to use it in operations will result in an error that looks exactly like
the `DirectiveArgument` didn't exist in the first place.

```python
-8<- "directives/directive_argument_visible.py"
```

/// details | About method signature

The decorated method is treated as a static method by the `DirectiveArgument`.

The `self` argument is not an instance of the `Directive`,
but the instance of the `DirectiveArgument` that is being used.

Since visibility checks occur in the validation phase of the GraphQL request,
GraphQL resolver info is not yet available. However, you can access the
Django request object using the `request` argument.
From this, you can, e.g., access the request user for permission checks.

///

> When using visibility checks, you should also disable "did you mean" suggestions
> using the [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) setting.
> Otherwise, a hidden field might show up in them.

### Extensions

You can provide custom extensions for the `DirectiveArgument` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `DirectiveArgument`.

```python
-8<- "directives/directive_argument_extensions.py"
```

`DirectiveArgument` extensions are made available in the GraphQL argument extensions
after the schema is created. The `DirectiveArgument` itself is found in the GraphQL argument extensions
under a key defined by the [`DIRECTIVE_ARGUMENT_EXTENSIONS_KEY`](settings.md#directive_argument_extensions_key)
setting.
