# Directives

In this section, we'll cover the GraphQL directives in Undine.
Directives are a way to add metadata to your GraphQL schema,
which can be accessed during query execution or by clients consuming your schema.

## Directive

In Undine, a GraphQL directive is implemented by subclassing the `Directive` class.

```python
-8<- "directives/directive.py"
```

Note that a `Directive` by itself does not do anything. It is only used as a way to define
additional metadata, which the GraphQL server can use at runtime.
If the directive implies some behavior, you'll need to add it, e.g., using a `ValidationRule`.
See the `ValidationRules` in the [graphql-core repository]{:target="_blank"}
for examples. Custom `ValidationRules` should be registered using the `ADDITIONAL_VALIDATION_RULES`
setting.

[graphql-core repository]: https://github.com/graphql-python/graphql-core/tree/main/src/graphql/validation/rules

Note that declared `Directives` are automatically added to the schema, even if they are not used.

A `Directive` always requires the _**locations**_ it will be used in to be set using the `locations` argument.
The locations can be divided into two categories: [_executable locations_](#executable-locations)
and [_type system locations_](#type-system-locations).

### Executable locations

Executable locations identify places in a GraphQL _document_ (i.e. "request") where a directive can be used.
See the example below on what these locations are.

#### `QUERY`

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

```graphql
mutation ($input: CreateTaskMutation!) @new {
  createTask(input: $input) {
    pk
  }
}
```

#### `SUBSCRIPTION`

```graphql
subscription @new {
  comments {
    username
    message
  }
}
```

#### `FIELD`

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
object that accepts that type of directive.

#### `SCHEMA`

The `SCHEMA` location corresponds to the schema definition itself.
Directives can be added here by using the `schema_definition_directives` argument
in the `create_schema` function.

```python
-8<- "directives/directive_location_schema.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on SCHEMA

schema @version(value: "v1.0.0") {
  query: Query
  mutation: Mutation
}
```

///

#### `SCALAR`

The `SCALAR` location corresponds to the scalars defined in the schema.
In Undine, `ScalarType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_scalar.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on SCALAR

scalar Vector3 @version(value: "1.0.0")
```

///

#### `OBJECT`

The `OBJECT` location corresponds to the ObjectTypes defined in the schema.
In Undine, `QueryTypes` and `RootTypes` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_object.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on OBJECT

type TaskType @version(value: "v1.0.0") {
  name: String!
  done: Boolean!
  createdAt: DateTime!
}

type Query @version(value: "v1.0.0") {
  tasks: [TaskType!]!
}
```

///

#### `FIELD_DEFINITION`

The `FIELD_DEFINITION` location corresponds to the fields defined in the schema.
In Undine, `Fields`, `InterfaceFields` and `Entrypoints` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_field_definition.py"
```

/// details | In schema definition

```graphql
directive @addedIn(version: String!) on FIELD_DEFINITION

interface Named {
  name: String! @addedIn(version: "v1.0.0")
}

type TaskType implements Named {
  name: String!
  done: Boolean!
  createdAt: DateTime! @addedIn(version: "v1.0.0")
}

type Query {
  tasks: [TaskType!]! @addedIn(version: "v1.0.0")
}
```

///

#### `ARGUMENT_DEFINITION`

The `ARGUMENT_DEFINITION` location corresponds to the field arguments defined in the schema.
In Undine, `CalculationArguments` and `DirectiveArguments` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_argument_definition.py"
```

/// details | In schema definition

```graphql
directive @addedIn(version: String!) on ARGUMENT_DEFINITION

directive @new (
  version: String! @addedIn(version: "v1.0.0")
) on FIELD_DEFINITION

type TaskType {
  calc(
    value: Int! @addedIn(version: "v1.0.0")
  ): Int!
}
```

///

#### `INTERFACE`

The `INTERFACE` location corresponds to the interfaces defined in the schema.
In Undine, `InterfaceType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_interface.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on INTERFACE

interface Named @version(value: "v1.0.0") {
  name: String!
}
```

///

#### `UNION`

The `UNION` location corresponds to the unions defined in the schema.
In Undine, `UnionType` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_union.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on UNION

union SearchObject @version(value: "v1.0.0") = TaskType | ProjectType
```

///

#### `ENUM`

The `ENUM` location corresponds to the enums defined in the schema.
In Undine, `OrderSet` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_enum.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on ENUM

enum TaskOrderSet @version(value: "v1.0.0") {
  nameAsc
  nameDesc
}
```

///

#### `ENUM_VALUE`

The `ENUM_VALUE` location corresponds to the enum values defined in the schema.
In Undine, `Order` accepts `Directives` declared for this location.

```python
-8<- "directives/directive_location_enum_value.py"
```

/// details | In schema definition

```graphql
directive @addedIn(version: String!) on ENUM_VALUE

enum TaskOrderSet {
  nameAsc @addedIn(version: "v1.0.0")
  nameDesc @addedIn(version: "v1.0.0")
}  
```

///


#### `INPUT_OBJECT`

The `INPUT_OBJECT` location corresponds to the input objects defined in the schema.
In Undine, `MutationType` and `FilterSet` accept `Directives` declared for this location.

```python
-8<- "directives/directive_location_input_object.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) on INPUT_OBJECT

input TaskFilterSet @version(value: "v1.0.0") {
  name: String
}

input TaskCreateMutation @version(value: "v1.0.0") {
  name: String
}
```

///

#### `INPUT_FIELD_DEFINITION`

The `INPUT_FIELD_DEFINITION` location corresponds to the input field definitions defined in the schema.
In Undine, `Input` and `Filter` accept `Directives` declared for this location.

```python
-8<- "directives/directive_location_input_field_definition.py"
```

/// details | In schema definition

```graphql
directive @addedIn(version: String!) on INPUT_FIELD_DEFINITION

input TaskFilterSet {
  name: String @addedIn(version: "v1.0.0")
}

input TaskCreateMutation {
  name: String @addedIn(version: "v1.0.0")
}
```

///

### Is repeatable

A directive can be declared as repeatable using the `is_repeatable` argument.
This means that the directive can be used multiple times in the same location.

```python
-8<- "directives/directive_is_repeatable.py"
```

/// details | In schema definition

```graphql
directive @version(value: String!) repeatable on FIELD_DEFINITION

type Query {
  example: String! @version(value: "v1.0.0") @version(value: "v2.0.0")
}
```

///

### Schema name

By default, the name of the generated `Directive` is the same as the name of the `Directive` class.
You can change this by setting the `schema_name` argument to the `Directive` class.

```python
-8<- "directives/directive_extensions.py"
```

### Extensions

You can provide custom extensions for the `Directive` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `Directive`.

```python
-8<- "directives/directive_extensions.py"
```

`Directive` extensions are made available in the GraphQL `Directive` extensions
after the schema is created. The `Directive` itself is found in the `extensions`
under a key defined by the `DIRECTIVE_EXTENSIONS_KEY` setting.

## DirectiveArgument

A `Directive` can optionally have a number of [`DirectiveArguments`](#directiveargument)
defined in the class body. These define the arguments that can or must be used with the directive.
A `DirectiveArgument` always requires _input type_ of the argument, which needs to be a GraphQL input type.

```python
-8<- "directives/directive_argument.py"
```

### Schema name

By default, the name of the argument is the same as the name of the attribute
to which the `DirectiveArgument` was defined to in the `Directive` class.
You can change this by setting the `schema_name` argument to the `DirectiveArgument` class.

```python
-8<- "directives/directive_argument_schema_name.py"
```

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

### Extensions

You can provide custom extensions for the `DirectiveArgument` by providing a
`extensions` argument with a dictionary containing them. These can then be used
however you wish to extend the functionality of the `DirectiveArgument`.

```python
-8<- "directives/directive_argument_extensions.py"
```

`DirectiveArgument` extensions are made available in the GraphQL `Argument` extensions
after the schema is created. The `DirectiveArgument` itself is found in the `extensions`
under a key defined by the `DIRECTIVE_ARGUMENT_EXTENSIONS_KEY` setting.
