# Write model

## Output type

The GraphQL object type returned by a mutation entrypoint. By default the registered
query type for the model, overridable on the mutation type.

Avoid: Return type, response type, query type (when the GraphQL output is meant)

## Mutation type

A GraphQL input object type backed by a Django model, defining how that model is created,
updated, or deleted.

Avoid: MutationType (in prose), input type (without qualifier)

## Input

A single mutation argument declared on a mutation type.

Avoid: Argument (GraphQL term alone), parameter

## Input data

The runtime dict passed to mutation type hooks. By the time a hook sees it, model
foreign-key inputs have been resolved to instances, hidden inputs and function inputs have
been populated, and input-only inputs are still present. Input-only inputs are stripped
before the mutation type after hook runs; hidden and function inputs remain.

Avoid: Input dict (unqualified), payload, kwargs

## Mutation kind

The operation a mutation type performs. Create, update, delete, related, or custom.

Avoid: Kind (unqualified), mutation type (when meaning the kind)

## Related mutation

A mutation kind that creates, updates, or deletes related model instances through nested
input in a single operation.

Avoid: Nested mutation, relation mutation

## Related action

What happens to existing related objects not mentioned in a related mutation input. Null,
delete, or ignore.

Avoid: Orphan handling, cascade policy

## Input-only input

A mutation input present in the schema but stripped from input data before the mutation
type after hook and the database write. Visible in permission and validation checks;
absent in the after hook.

Avoid: Write-only, passthrough

## Hidden input

A mutation input not exposed in the schema; its value is injected into input data before
permission checks and remains visible through every mutation type hook including the after
hook.

Avoid: Internal input, server-side input

## Atomic mutation

A group of mutations executed inside a single database transaction, triggered by the
@atomic directive.

Avoid: Transaction batch, grouped mutation
