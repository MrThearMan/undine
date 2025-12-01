# Validation rules

> This is an advanced GraphQL core feature. For validating mutations, see
> the [Mutations](mutations.md#validation) documentation.

A GraphQL operation is executed in a series of steps. These steps are:

1. **Parsing** the GraphQL source document to a GraphQL AST.
2. **Validation** of the GraphQL AST against the GraphQL schema.
3. **Execution** of the GraphQL operation according to the GraphQL AST.

By default, [graphql-core]{:target="_blank"} (which Undine uses under the hood) comes with a set of validation rules
which make sure that a GraphQL operation is valid according to the GraphQL specification.
Undine adds a few more validation rules of its own, and allows you to add your own as well.

[graphql-core]: https://github.com/graphql-python/graphql-core

## Additional Rules

### `MaxAliasCountRule`

This validation rule checks that the number of aliases in a GraphQL operation does not exceed the maximum allowed,
as set by the [`MAX_ALLOWED_ALIASES`](settings.md#max_allowed_aliases) setting.
This is used to prevent denial-of-service attacks and heap overflow from "alias overloading" which happens
when a GraphQL operation is executed multiple times in a single request by aliasing it over and over again,
leading to high execution time and thus high CPU and memory usage.

### `MaxComplexityRule`

This validation rule checks that the complexity of a GraphQL operation does not exceed the maximum allowed,
as set by the [`MAX_QUERY_COMPLEXITY`](settings.md#max_query_complexity) setting.
This is used to prevent denial-of-service attacks that could arise from slow execution of
a GraphQL operation due to the complexity of generated database queries or API calls.
See the [complexity](queries.md#complexity) documentation for more information.

### `MaxDirectiveCountRule`

This validation rule checks that the number of directives in a GraphQL operation does not exceed the maximum allowed,
as set by the [`MAX_ALLOWED_DIRECTIVES`](settings.md#max_allowed_directives) setting.
This is used to prevent denial-of-service attacks, heap overflow or server overloading from "directive overloading"
that could arise from having to parse, validate, and process too many directives.

### `OneOfInputObjectTypeRule`

This validation rule checks that a one-of input object is used correctly.
Only added when `graphql-core` version is below [v3.2.7]{:target="_blank"}
since `oneOf` input object support was added in that version.

[v3.2.7]: https://github.com/graphql-python/graphql-core/releases/tag/v3.2.7

### `VisibilityRule`

When [`EXPERIMENTAL_VISIBILITY_CHECKS`](settings.md#experimental_visibility_checks) are enabled,
this validation rule checks that users cannot use parts of the schema that are not visible to them.

## Custom validation rules

To add your own validation rules, you'll need to create a class that inherits from
`graphql.validation.rules.ValidationRule`. This class implements the visitor pattern
to traverse the GraphQL AST. Different `Nodes` in the AST can be visited by defining either
`enter_<node_type>` or `leave_<node_type>` methods, depending on whether you want to
visit the node before or after its children.

These methods have the following signature (example for `NameNode`):

```python
-8<- "validation_rules/custom_rule.py"
```

When you have created your custom validation rule, you can register it using the
[`ADDITIONAL_VALIDATION_RULES`](settings.md#additional_validation_rules) setting.

For clarity, here is a list of `Node` types that can be visited during
the GraphQL document validation phase:

/// details | `DocumentNode`
    attrs: {id: document_node}

Hooks `enter_document` and `leave_document` | Node: `graphql.language.ast.DocumentNode`

A `DocumentNode` is visited at the root of the GraphQL document AST.
It can define multiple operations and fragments.

///

/// details | `OperationDefinitionNode`
    attrs: {id: operation_definition_node}

Hooks `enter_operation_definition` and `leave_operation_definition` | Node: `graphql.language.ast.OperationDefinitionNode`

An `OperationDefinitionNode` is visited for each operation in the GraphQL document.
Note that a GraphQL document can contain multiple operations, although only one operation
can be executed in a single request.

///

/// details | `VariableDefinitionNode`
    attrs: {id: variable_definition_node}

Hooks `enter_variable_definition` and `leave_variable_definition` | Node: `graphql.language.ast.VariableDefinitionNode`

A `VariableDefinitionNode` is visited for each variable definition in the GraphQL document.
Variables are defined at the start of an operation using dollar signs (`$`).

///

/// details | `NameNode`
    attrs: {id: name_node}

Hooks `enter_name` and `enter_name` | Node: `graphql.language.ast.NameNode`

A `NameNode` is visited for each named entity in the GraphQL document.
This includes field names, argument names, and type names, etc.

///

/// details | `SelectionSetNode`
    attrs: {id: selection_set_node}

Hooks `enter_selection_set` and `leave_selection_set` | Node: `graphql.language.ast.SelectionSetNode`

A `SelectionSetNode` is visited for each selection set in the GraphQL document.
A selection set is a set of fields or fragments requested from a GraphQL type.

///

/// details | `FieldNode`
    attrs: {id: field_node}

Hooks `enter_field` and `leave_field` | Node: `graphql.language.ast.FieldNode`

A `FieldNode` is visited for each field in the GraphQL document.

///

/// details | `ArgumentNode`
    attrs: {id: argument_node}

Hooks `enter_argument` and `leave_argument` | Node: `graphql.language.ast.ArgumentNode`

An `ArgumentNode` is visited for each field argument in the GraphQL document.

///

/// details | `FragmentSpreadNode`
    attrs: {id: fragment_spread_node}

Hooks `enter_fragment_spread` and `leave_fragment_spread` | Node: `graphql.language.ast.FragmentSpreadNode`

A `FragmentSpreadNode` is visited for each fragment spread in the GraphQL document.

///

/// details | `InlineFragmentNode`
    attrs: {id: inline_fragment_node}

Hooks `enter_inline_fragment` and `leave_inline_fragment` | Node: `graphql.language.ast.InlineFragmentNode`

A `InlineFragmentNode` is visited for each inline fragment in the GraphQL document.

///

/// details | `FragmentDefinitionNode`
    attrs: {id: fragment_definition_node}

Hooks `enter_fragment_definition` and `leave_fragment_definition` | Node: `graphql.language.ast.FragmentDefinitionNode`

A `FragmentDefinitionNode` is visited for each fragment definition in the GraphQL document.

///

/// details | `NamedTypeNode`
    attrs: {id: named_type_node}

Hooks `enter_named_type` and `leave_named_type` | Node: `graphql.language.ast.NamedTypeNode`

A `NamedTypeNode` is visited for each named type referenced in the GraphQL document.
Named types are referenced when using inline fragments or defining fragments.

Example:

```graphql
query {
  node(id: "123") {
    ... on User {  # NamedTypeNode "User"
      ...Data
    }
  }
}

fragment Data on User {  # NamedTypeNode "User"
  id
  name
}
```

///

/// details | `ListTypeNode`
    attrs: {id: list_type_node}

Hooks `enter_list_type` and `leave_list_type` | Node: `graphql.language.ast.ListTypeNode`

A `ListTypeNode` is visited for each list type in the GraphQL document.

///

/// details | `NonNullTypeNode`
    attrs: {id: non_null_type_node}

Hooks `enter_non_null_type` and `leave_non_null_type` | Node: `graphql.language.ast.NonNullTypeNode`

A `NonNullTypeNode` is visited for each non-null type in the GraphQL document.

///

/// details | `DirectiveNode`
    attrs: {id: directive_node}

Hooks `enter_directive` and `leave_directive` | Node: `graphql.language.ast.DirectiveNode`

A `DirectiveNode` is visited for each directive used in the GraphQL document.

///

/// details | `VariableNode`
    attrs: {id: variable_node}

Hooks `enter_variable` and `leave_variable` | Node: `graphql.language.ast.VariableNode`

A `VariableNode` is visited for each variable used in the GraphQL document.

///

/// details | `IntValueNode`
    attrs: {id: int_value_node}

Hooks `enter_int_value` and `leave_int_value` | Node: `graphql.language.ast.IntValueNode`

A `IntValueNode` is visited for each integer value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `FloatValueNode`
    attrs: {id: float_value_node}

Hooks `enter_float_value` and `leave_float_value` | Node: `graphql.language.ast.FloatValueNode`

A `FloatValueNode` is visited for each float value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `StringValueNode`
    attrs: {id: string_value_node}

Hooks `enter_string_value` and `leave_string_value` | Node: `graphql.language.ast.StringValueNode`

A `StringValueNode` is visited for each string value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `BooleanValueNode`
    attrs: {id: boolean_value_node}

Hooks `enter_boolean_value` and `leave_boolean_value` | Node: `graphql.language.ast.BooleanValueNode`

A `BooleanValueNode` is visited for each boolean value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `NullValueNode`
    attrs: {id: null_value_node}

Hooks `enter_null_value` and `leave_null_value` | Node: `graphql.language.ast.NullValueNode`

A `NullValueNode` is visited for each null value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `EnumValueNode`
    attrs: {id: enum_value_node}

Hooks `enter_enum_value` and `leave_enum_value` | Node: `graphql.language.ast.EnumValueNode`

A `EnumValueNode` is visited for each enum value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `ListValueNode`
    attrs: {id: list_value_node}

Hooks `enter_list_value` and `leave_list_value` | Node: `graphql.language.ast.ListValueNode`

A `ListValueNode` is visited for each list value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `ObjectValueNode`
    attrs: {id: object_value_node}

Hooks `enter_object_value` and `leave_object_value` | Node: `graphql.language.ast.ObjectValueNode`

A `ObjectValueNode` is visited for each object value in the GraphQL document.
Values can be used in arguments or variables.

///

/// details | `ObjectFieldNode`
    attrs: {id: object_field_node}

Hooks `enter_object_field` and `leave_object_field` | Node: `graphql.language.ast.ObjectFieldNode`

A `ObjectFieldNode` is visited for each object field in the GraphQL document.
Values can be used in arguments or variables.

///

> There are other node types which can be visited if validation rules are run against
> the GraphQL schema, but these are not covered in this documentation.

A `ValidationRule` instance has access to the [`ValidationContext`][ValidationContext]{:target="_blank"}
instance, through which you can access to useful contextual information relative to the visited node.
For example, you can access the current GraphQL type for the node using `self.context.get_type()`.

[ValidationContext]: https://github.com/graphql-python/graphql-core/blob/main/src/graphql/validation/validation_context.py
