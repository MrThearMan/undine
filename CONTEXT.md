# Topic index

Read only the topics that match what you're working on.

- [Django foundation](.agents/domain/django-foundation.md): Model, model instance, queryset, lookup, manager, primary key
- [Schema assembly](.agents/domain/schema-assembly.md): Schema, root type, entrypoint kinds, reference, schema name, GraphQL Element
- [Read model](.agents/domain/read-model.md): Query type, field, query type registry, calculation, autogeneration
- [Write model](.agents/domain/write-model.md): Output type, mutation type, input, input data, mutation kind, related mutation, atomic mutation
- [Filtering and ordering](.agents/domain/filtering-and-ordering.md): Filter set, filter, order set, order
- [Abstract types and pagination](.agents/domain/abstract-types-and-pagination.md): Interface type, union type, Relay Node, connection, page info, offset pagination
- [Execution and infrastructure](.agents/domain/execution-and-infrastructure.md): Operation, root value, GQL info, query optimizer, data loader, directives, caching, complexity, subscriptions
- [Hooks](.agents/domain/hooks.md): Query type / mutation type / field / input / entrypoint permission checks, resolvers, visibility, errors as data
- [Federation](.agents/domain/federation.md): Federation schema, subgraph, entity kinds, reference resolver, compatibility harness

## Adding new terms

This file follows **progressive disclosure**. If you introduce a genuinely new concept,
add its entry to the topic file it best fits and (if it's a new area) add a bullet here.
Keep this index a one-sentence-per-topic pointer. Details live in the topic files.

## Flagged ambiguities

Keep these in mind whenever the domain language comes up. They apply across all the guides above.

- Field means an Undine query type field unless qualified as "Django field" or "GraphQL field"
- Input vs GraphQL input object vs the runtime input dict passed to mutation hooks. Prefer input for the Undine declaration, "input data" for the resolved dict
- Model may mean the Django model class or a model instance. Mutation permission checks and validation checks receive an instance (unsaved for create)
- Root value vs Python `self` in decorated methods. Docs recommend renaming to `root`, meaning differs at entrypoints (always null) vs fields (the model instance)
- Node (Relay interface decorator) vs `node` (the refetch entrypoint). Capitalize Node for the interface, lowercase for the entrypoint name
- Connection (Relay pagination type) vs a transport connection for subscriptions. Specify "Relay connection" or "transport connection"
- Query type vs Query root type. `TaskType` is a query type, `class Query(RootType)` is the Query root type
- Filter (client-supplied via filter set) vs query type queryset filter (always applied). Distinct mechanisms with different lifecycles
