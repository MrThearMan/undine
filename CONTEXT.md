# Undine

A batteries-included GraphQL library for Django that maps Django models to schema types through declarative Python classes, with automatic query optimization, composable filtering and ordering, mutations, Relay pagination, subscriptions, and lifecycle hooks.

## Language

### Django foundation

**Model**:
A Django ORM class representing a database table and its rows.
_Avoid_: Entity, table (when meaning the ORM class)

**Model instance**:
A single row of a model, loaded from or about to be written to the database.
_Avoid_: Model (when an instance is meant), record, object (unqualified)

**Queryset**:
A lazy, chainable collection of model instances produced by a model's manager.
_Avoid_: Result set, query result, rows

**Lookup**:
A Django ORM filter expression passed to `queryset.filter()` — field name plus optional lookup type (e.g. `name__icontains`).
_Avoid_: Filter (when the Django ORM mechanism is meant), predicate

**Manager**:
The interface on a model for obtaining querysets — typically the default `objects` manager.
_Avoid_: Repository, DAO

**Primary key**:
The unique identifier for a model instance, exposed as `pk` or `id` on the instance.
_Avoid_: ID (ambiguous with global object ID), key

### Schema assembly

**Schema**:
The complete GraphQL schema produced from Query, Mutation, and Subscription root types.
_Avoid_: API, endpoint (when meaning the whole schema)

**Root type**:
A Python class representing a GraphQL root object type for one operation kind — Query (required), Mutation, or Subscription.
_Avoid_: RootType (in prose), operation root, top-level type

**Entrypoint**:
A top-level field on a root type — the place inside the schema where a query, mutation, or subscription operation starts.
_Avoid_: Root field, operation field, resolver (when meaning the schema field itself)

**List entrypoint**:
An entrypoint on the query root type with `many=True` that returns a list of model instances — typically referencing a query type.
_Avoid_: Many entrypoint, plural entrypoint, bulk query

**Bulk mutation entrypoint**:
An entrypoint on the mutation root type with `many=True` that operates on a list of inputs — typically referencing a mutation type.
_Avoid_: Bulk entrypoint (ambiguous with list entrypoint), many mutation

**Connection entrypoint**:
An entrypoint on the query root type referencing a Connection — typically wrapping a query type, union type, or interface type — returning Relay cursor-paginated results.
_Avoid_: Paginated entrypoint (ambiguous with offset pagination)

**Reference**:
The source Undine uses to derive a resolver, GraphQL type, and arguments for an entrypoint, field, input, or filter. Common kinds include functions, Django model fields, ORM expressions, query types, mutation types, interface types, union types, connections, calculations, and scalars.
_Avoid_: Ref (in prose), backing, source type

**Schema name**:
The name of a type or field in the generated GraphQL schema, which may differ from the Python attribute name.
_Avoid_: GraphQL name, field name (ambiguous with Python)

### Federation

**Federation schema**:
A schema built with `create_federation_schema` that is compliant with the Apollo Federation 2 subgraph spec. Distinct from a plain (non-federated) schema built with `create_schema`.
_Avoid_: Federated schema (when meaning a supergraph)

**Subgraph**:
A single Undine service participating in an Apollo Federation 2 supergraph. Every federation schema exposes exactly one subgraph.
_Avoid_: Federated schema (ambiguous with supergraph)

**Supergraph**:
The composed schema an Apollo router assembles from multiple subgraphs. Undine does not compose supergraphs — it only produces subgraphs.
_Avoid_: Federated schema (ambiguous with subgraph)

**Federation entity**:
An object type marked with `@KeyDirective` that the router can fetch across subgraphs by its key fields.
_Avoid_: Federated type, keyed type

**Entity representation**:
A dict of the shape `{ "__typename": "Foo", ...keyFields }` that the router sends to `Query._entities` when it needs an entity resolved. Each representation is dispatched by `__typename` and passed to the corresponding reference resolver.
_Avoid_: Reference, entity payload

**Federation type**:
A Undine class for defining non-model backed contributing entities and stub references.
_Avoid_: Federated type, keyed type

**Federation field**:
A field on a federation type. Distinct from `Field`.
_Avoid_: Field (unqualified — that name is reserved for the `QueryType` field), extension field

**Owning entity**:
An entity whose canonical data lives in this subgraph. Query type with `@KeyDirective(..., resolvable=True)`.
_Avoid_: Primary entity, source entity

**Contribution entity**:
An entity owned by another subgraph whose extra fields this subgraph contributes. Federation type with `@KeyDirective(..., resolvable=True)`.
_Avoid_: Extension type, contribution type

**Stub reference**:
It declares an entity so this subgraph can reference it in its own fields without resolving it locally. Appears in `_service.sdl` but not in the `_Entity` union. Federation type with `@KeyDirective(..., resolvable=False)`.
_Avoid_: Stub entity, non-resolvable entity

**Reference resolver**:
The `__resolve_reference__` hook on a `QueryType` or `FederationType` that turns a entity representation data into an instance.
_Avoid_: Entity resolver (ambiguous with the `_entities` resolver itself)

**Subgraph SDL**:
The subgraph schema string returned by `Query._service.sdl`. The router fetches it during composition to learn about the subgraph's types, entities, and federation directives.
_Avoid_: Schema SDL (unqualified), service SDL

**Compatibility subgraph**:
The runnable Django project under `tests/test_federation/compatibility/` that implements Apollo's `products` reference schema as an Undine subgraph. Packaged as a Docker deliverable for Apollo's compliance harness.
_Avoid_: Compat harness, compliance project

**Apollo compliance runner**:
The `@apollo/federation-subgraph-compatibility` CLI that boots the compatibility subgraph alongside Apollo's own `users` / `inventory` / router containers and runs the `COMPATIBILITY.md` query set against the composed supergraph.
_Avoid_: Compat runner, harness runner

### Read model

**Query type**:
A GraphQL object type backed by a Django model, defining how that model is read through the API.
_Avoid_: QueryType (in prose), output type (without qualifier), ObjectType (GraphQL term alone)

**Field**:
A queryable attribute declared on a query type, exposed as a GraphQL field on that type. In Undine discussions, "field" alone means this — not a Django model field or a generic GraphQL field elsewhere in the schema.
_Avoid_: Attribute, column, model field, GraphQL field (without qualifier)

**Query type registry**:
The mapping from each Django model to its registered query type, used to wire relations and mutation outputs.
_Avoid_: Registry (unqualified), type map

**Calculation**:
A computed value on a query type defined by a database expression with optional arguments, rather than a plain model attribute.
_Avoid_: Computed field, annotation (Django term alone)

**Autogeneration**:
Introspection of a Django model to produce fields, inputs, filters, or orders without hand-declaring each one.
_Avoid_: Auto, codegen, schema generation

### Write model

**Output type**:
The GraphQL object type returned by a mutation entrypoint — by default the registered query type for the model, overridable on the mutation type.
_Avoid_: Return type, response type, query type (when the GraphQL output is meant)

**Mutation type**:
A GraphQL input object type backed by a Django model, defining how that model is created, updated, or deleted.
_Avoid_: MutationType (in prose), input type (without qualifier)

**Input**:
A single mutation argument declared on a mutation type.
_Avoid_: Argument (GraphQL term alone), parameter

**Mutation kind**:
The operation a mutation type performs — create, update, delete, related, or custom.
_Avoid_: Kind (unqualified), mutation type (when meaning the kind)

**Related mutation**:
A mutation kind that creates, updates, or deletes related model instances through nested input in a single operation.
_Avoid_: Nested mutation, relation mutation

**Related action**:
What happens to existing related objects not mentioned in a related mutation input — null, delete, or ignore.
_Avoid_: Orphan handling, cascade policy

**Input-only input**:
A mutation input present in the schema but stripped before the database write.
_Avoid_: Write-only, passthrough

**Hidden input**:
A mutation input not exposed in the schema; its value is injected before the mutation runs.
_Avoid_: Internal input, server-side input

**Atomic mutation**:
A group of mutations executed inside a single database transaction, triggered by the @atomic directive.
_Avoid_: Transaction batch, grouped mutation

### Filtering and ordering

**Filter set**:
A collection of filters exposed as a GraphQL input object for narrowing a queryset.
_Avoid_: FilterSet (in prose), filter input

**Filter**:
A single filter condition on a filter set, corresponding to a Django queryset lookup.
_Avoid_: Lookup (Django term alone), predicate

**Order set**:
A collection of sort options exposed as a GraphQL enum for ordering a queryset.
_Avoid_: OrderSet (in prose), sort enum

**Order**:
A single sort option within an order set, including direction and null placement.
_Avoid_: Sort, orderBy (GraphQL argument name alone)

### Abstract types and pagination

**Interface type**:
A GraphQL interface whose fields are implemented by one or more query types.
_Avoid_: InterfaceType (in prose), abstract type (GraphQL term alone)

**Interface field**:
A field declared on an interface type that implementing query types must provide.
_Avoid_: InterfaceField (in prose)

**Union type**:
A GraphQL union of multiple query types, resolved to a concrete type at runtime.
_Avoid_: UnionType (in prose)

**Relay Node**:
The Relay interface that adds an opaque global object ID to a query type.
_Avoid_: Node (unqualified), Node interface (implementation detail)

**Global object ID**:
An opaque, client-opaque identifier encoding type name and primary key, used by Relay's node refetch entrypoint.
_Avoid_: Global ID (in prose when precision matters), Relay ID

**Connection**:
A Relay pagination wrapper around a query type, union type, or interface type, exposing edges, nodes, and page info.
_Avoid_: Paginated list (when Relay cursors are meant), Connection type (GraphQL term alone)

**Page info**:
Relay metadata describing whether more pages exist before or after the current window.
_Avoid_: Pagination info, cursor info

**Offset pagination**:
Simpler pagination using offset and limit instead of Relay cursors.
_Avoid_: Limit/offset, basic pagination

### Execution and infrastructure

**Operation**:
A single GraphQL request — parsed, validated, then executed through parsing, validation, and execution phases.
_Avoid_: Request (HTTP term alone), query (when mutations/subscriptions are included)

**Root value**:
The object passed as the first argument to a field resolver — always null at entrypoints, the model instance at query type fields.
_Avoid_: Root, self (Python convention), parent

**GQL info**:
Typed resolve info carrying the GraphQL execution context and Django request.
_Avoid_: Info, context (ambiguous with Django request context)

**Query optimizer**:
The component that inspects an incoming query's selection set and applies select_related, prefetch_related, and annotations to avoid N+1 queries and over-fetching.
_Avoid_: Optimizer (unqualified), ORM optimizer

**Optimization data**:
Per-queryset state accumulated by the query optimizer — selects, prefetches, annotations, filters, orders, and pagination.
_Avoid_: Optimization results (when meaning the in-flight accumulator)

**Data loader**:
A request-scoped batch loader for resolving related objects asynchronously without N+1 queries.
_Avoid_: DataLoader (in prose), batch loader

**Lifecycle hook**:
A callback invoked during parsing, validation, execution, or individual field resolution of an operation.
_Avoid_: Hook (unqualified), middleware (Django term)

**Directive**:
Metadata attached to schema types or operations — for example @atomic, cache rules, or complexity limits.
_Avoid_: Decorator (Python term), annotation

**Persisted document**:
A GraphQL operation stored server-side and referenced by document ID instead of sending the full query string.
_Avoid_: Stored query, allow-listed query

**Cache time**:
The number of seconds to cache a query response, settable on entrypoints, fields, query types, interface types, interface fields, and union types.
_Avoid_: TTL (unqualified), cache duration

**Per-user cache**:
Caching keyed to the authenticated user, enabled via `cache_per_user` alongside cache time.
_Avoid_: User cache, authenticated cache

**Restrictive cache rule**:
When nested objects define their own cache time, the shortest cache time among entrypoint and nested objects wins.
_Avoid_: Cache inheritance, cache override

**Query complexity**:
A cost score assigned to fields and entrypoints, summed for an operation and capped by the maximum query complexity validation rule.
_Avoid_: Complexity (unqualified), cost limit

**Subscription**:
A long-lived operation that pushes events to the client over WebSocket, SSE, or multipart HTTP.
_Avoid_: Live query, push notification

**Signal subscription**:
A subscription backed by a Django signal, typically for model create, update, or delete events.
_Avoid_: Model subscription, event subscription

### Hooks

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
A class-level check on a mutation type that validates input before the write.
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

## Relationships

- A **schema** is built from one **Query** root type (required) and optional **Mutation** and **Subscription** root types
- Each **root type** exposes one or more **entrypoints**
- Each **entrypoint** requires a **reference** — a query type, mutation type, interface type, union type, connection, node, function, or subscription class
- On a query root type, `many=True` with a **query type** reference creates a **list entrypoint**; with a **mutation type** reference on a mutation root type, it creates a **bulk mutation entrypoint**
- **Connection** and **offset pagination** references define their own entrypoint shapes regardless of the `many` parameter
- Interface type and union type references always resolve as lists
- A **query type** belongs to exactly one Django model and registers in the **query type registry**
- A **mutation type** belongs to exactly one Django model; its **output type** defaults to the registered **query type** for that model but can be overridden
- A **query type** may have at most one **filter set** and one **order set**, attached as class decorators or bases
- **Fields** on a **query type** that reference related models resolve through registered **query types** for those models
- **Related mutations** nest **mutation types** for related models inside a parent **mutation type**
- A **connection** wraps a **query type** (or union/interface) for Relay cursor pagination
- **Node** on a **query type** plus a `node` **entrypoint** enables **global object ID** refetch
- The **query optimizer** runs for entrypoints and fields that return querysets, building **optimization data** before queryset execution
- An **operation** passes through **lifecycle hooks** at parse, validate, execute, and per-field resolve phases

## Example dialogue

> **Dev:** "I added a `tasks` **entrypoint** with a **connection** around `TaskType`. Do clients filter through the **filter set** on the **query type**?"

> **Domain expert:** "Yes. The **filter set** on `TaskType` becomes the `filter` argument on the **connection** **entrypoint**. Client-supplied filters combine with any **queryset filter** on the **query type**."

> **Dev:** "And when they call `createTask`, the **mutation type** output is the same **query type**?"

> **Domain expert:** "Right. The **mutation type** resolves to an **output type** — usually the registered **query type**, but overridable. **Mutation type permission checks** and **mutation type validation checks** run before the write; **input-only inputs** are stripped after validation."

> **Dev:** "What does the **query optimizer** do for nested **fields**?"

> **Domain expert:** "It walks the operation's selection set and fills **optimization data** — `select_related`, `prefetch_related`, annotations — so resolving related **fields** doesn't cause N+1 queries."

## Flagged ambiguities

- **Field** means an Undine query type field unless qualified as "Django field" or "GraphQL field"
- **Input** vs GraphQL input object vs the runtime input dict passed to mutation hooks — prefer **input** for the Undine declaration, "input data" for the resolved dict
- **Model** may mean the Django model class or a model instance — mutation **permission checks** and **validation checks** receive an instance (unsaved for create)
- **Root value** vs Python `self` in decorated methods — docs recommend renaming to `root`; meaning differs at **entrypoints** (always null) vs **fields** (the model instance)
- **Node** (Relay interface decorator) vs `node` (the refetch **entrypoint**) — capitalize **Node** for the interface, lowercase for the entrypoint name
- **Connection** (Relay pagination type) vs a transport connection for **subscriptions** — specify "Relay connection" or "transport connection"
- **Query type** vs **Query** root type — `TaskType` is a query type; `class Query(RootType)` is the Query root type
- **Filter** (client-supplied via **filter set**) vs **query type queryset filter** (always applied) — distinct mechanisms with different lifecycles
