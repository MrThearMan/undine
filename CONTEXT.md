# Topic index

Undine's ubiquitous language is split across topical guides in `.agents/docs/`. Load the guide that matches what you're working on:

- [Django foundation](.agents/docs/django-foundation.md) — Model, model instance, queryset, lookup, manager, primary key
- [Schema assembly](.agents/docs/schema-assembly.md) — Schema, root type, entrypoint kinds, reference, schema name, GraphQL Element
- [Read model](.agents/docs/read-model.md) — Query type, field, query type registry, calculation, autogeneration
- [Write model](.agents/docs/write-model.md) — Output type, mutation type, input, mutation kind, related mutation, atomic mutation
- [Filtering and ordering](.agents/docs/filtering-and-ordering.md) — Filter set, filter, order set, order
- [Abstract types and pagination](.agents/docs/abstract-types-and-pagination.md) — Interface type, union type, Relay Node, connection, page info, offset pagination
- [Execution and infrastructure](.agents/docs/execution-and-infrastructure.md) — Operation, root value, GQL info, query optimizer, data loader, directives, caching, complexity, subscriptions
- [Hooks](.agents/docs/hooks.md) — Query type / mutation type / field / input / entrypoint permission checks, resolvers, visibility, errors as data
- [Federation](.agents/docs/federation.md) — Federation schema, subgraph, entity kinds, reference resolver, compatibility harness
- [Relationships](.agents/docs/relationships.md) — How the pieces fit together, plus an example dialogue

## Adding new terms

If you introduce a genuinely new concept, add its entry to the topic file it best fits and (if it's a new area) add a bullet here.
Keep this index a one-sentence-per-topic pointer; details live in the topic files.

## Flagged ambiguities

Keep these in mind whenever the domain language comes up. They apply across all the guides above.

- **Field** means an Undine query type field unless qualified as "Django field" or "GraphQL field"
- **Input** vs GraphQL input object vs the runtime input dict passed to mutation hooks — prefer **input** for the Undine declaration, "input data" for the resolved dict
- **Model** may mean the Django model class or a model instance — mutation **permission checks** and **validation checks** receive an instance (unsaved for create)
- **Root value** vs Python `self` in decorated methods — docs recommend renaming to `root`; meaning differs at **entrypoints** (always null) vs **fields** (the model instance)
- **Node** (Relay interface decorator) vs `node` (the refetch **entrypoint**) — capitalize **Node** for the interface, lowercase for the entrypoint name
- **Connection** (Relay pagination type) vs a transport connection for **subscriptions** — specify "Relay connection" or "transport connection"
- **Query type** vs **Query** root type — `TaskType` is a query type; `class Query(RootType)` is the Query root type
- **Filter** (client-supplied via **filter set**) vs **query type queryset filter** (always applied) — distinct mechanisms with different lifecycles
