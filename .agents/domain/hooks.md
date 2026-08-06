# Hooks

**Query type permission check**:
A class-level check on a query type that runs before resolving an instance and denies access when unauthorized.
_Avoid_: __permissions__ (implementation name)

**Query type queryset filter**:
A class-level filter applied to every queryset for a query type, regardless of client filter arguments.
_Avoid_: __filter_queryset__ (implementation name), base filter

**Query type optimization**:
Class-level hints that tell the query optimizer what related data to prefetch for a query type.
_Avoid_: __optimizations__ (implementation name)

**Field permission check**:
A per-field check that runs before resolving that field on a model instance.
_Avoid_: @field.permissions (implementation syntax)

**Field resolve**:
A custom resolver for a field, replacing the default reference-based resolution.
_Avoid_: @field.resolve (implementation syntax)

**Field optimize**:
A per-field hint telling the query optimizer what extra database data the custom resolver needs.
_Avoid_: @field.optimize (implementation syntax)

**Field visibility**:
A per-field check controlling whether the field appears in introspection and can be queried.
_Avoid_: @field.visible (implementation syntax)

**Mutation type permission check**:
A class-level check on a mutation type that runs before the mutation executes.
_Avoid_: __permissions__ (implementation name)

**Mutation type validation check**:
A class-level check on a mutation type that validates input data before the write.
_Avoid_: __validate__ (implementation name)

**Validation rule**:
A GraphQL-spec check run during the validation phase of an operation, before execution — distinct from mutation type validation checks.
_Avoid_: Validator, schema validation (when mutation hooks are meant)

**Mutation type after hook**:
Class-level logic that runs after a mutation completes successfully.
_Avoid_: __after__ (implementation name)

**Custom mutate**:
Class-level logic that replaces the default create/update/delete behavior for a custom mutation kind.
_Avoid_: __mutate__ (implementation name)

**Bulk mutate**:
Class-level logic that replaces default behavior for bulk mutation entrypoints.
_Avoid_: __bulk_mutate__ (implementation name)

**Input permission check**:
A per-input check that runs before the mutation executes.
_Avoid_: @input.permissions (implementation syntax)

**Input visibility**:
A per-input check controlling whether the input appears in introspection.
_Avoid_: @input.visible (implementation syntax)

**Entrypoint permission check**:
A per-entrypoint check that runs before the entrypoint resolver executes.
_Avoid_: @entrypoint.permissions (implementation syntax)

**Entrypoint resolve**:
A custom resolver for an entrypoint, replacing the default reference-based resolution.
_Avoid_: @entrypoint.resolve (implementation syntax)

**Entrypoint visibility**:
A per-entrypoint check controlling whether the entrypoint appears in introspection.
_Avoid_: @entrypoint.visible (implementation syntax)

**Errors as data**:
An error handling mode where declared exceptions become union members in the response type instead of GraphQL execution errors.
_Avoid_: Error union, typed errors

**Visibility**:
Whether a type or field appears in introspection and can be queried, controlled by visibility hooks at type or member level.
_Avoid_: Hidden, schema hiding
