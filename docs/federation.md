description: Documentation on Apollo Federation 2 support in Undine.

# Federation

Undine provides support for [Apollo Federation 2]{:target="_blank"}, letting you expose
an Undine schema as a subgraph in a federated supergraph. Federation 2 lets a router combine
multiple subgraphs into a single GraphQL API, so different teams can own different parts of the
schema.

[Apollo Federation 2]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas

## Setup

You can build a Federation 2 subgraph-compliant schema by importing `create_federation_schema` instead of
`create_schema`.

```python hl_lines="2 16"
-8<- "federation/create_federation_schema.py"
```

Compared with `create_schema`, `create_federation_schema` additionally:

1. Validates [`FEDERATION_VERSION`](settings.md#federation_version) is supported.
2. Auto-generates a schema-level `@link` directive.
3. Injects `Query._service` which returns the subgraph SDL for the router.
4. Injects `Query._entities` which fetches entities by their representations.

## Directives

### `LinkDirective`

Subgraph schemas opt in to Apollo Federation 2 by applying the [`@link`][link directive]{:target="_blank"}
directive to the schema type. Undine automatically compiles the correct directive for you in `create_federation_schema`
based on the directives in use in your schema.

[link directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#the-link-directive

```graphql
extend schema @link(url: "https://specs.apollo.dev/federation/v2.11", import: ["@key"])
```

The `@link` directive also accepts two optional arguments: `as` renames the linked spec's namespace prefix,
so directives are addressed as `@<as>__key` instead of `@key`, and `for` declares the purpose of the link,
either `SECURITY` or `EXECUTION`, which Apollo Router uses to decide how to compose the subgraph.
See the [spec][Link spec]{:target="_blank"} for more information.

[Link spec]: https://specs.apollo.dev/link/v1.0/

### `KeyDirective`

The [`@key`][key directive]{:target="_blank"} directive marks a `QueryType` as an [entity](#entities).

[key directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#key

To use the directive, you must define a set of `fields` that a subgraph can use to uniquely identify
any instance of the entity. These fields must be defined on the `QueryType`.

```python hl_lines="2 7"
-8<- "federation/key_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String!
}
```

Set `resolvable=False` when this subgraph only references the entity but does not resolve it. The
router uses the declaration to stitch results together, but never routes resolution requests here.

```python hl_lines="2 7"
-8<- "federation/key_directive_resolvable.py"
```

```graphql
type TaskType @key(fields: "id", resolvable: false) {
  id: Int!
}
```

### `ShareableDirective`

the [`@shareable`][shareable directive]{:target="_blank"} directive indicates that a field, or all fields of a type,
are allowed to be resolved by multiple subgraphs.

[shareable directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#shareable

```python hl_lines="2 9"
-8<- "federation/shareable_directive.py"
```

```graphql
type TaskType {
  id: Int!
  name: String! @shareable
}
```

> Note: if a field is included in an entity's [`@key`](#keydirective) directive, that field is automatically
> considered [`@shareable`](#shareabledirective) and the directive is not required in the corresponding subgraph(s).

### `ExternalDirective`

The [`@external`][external directive]{:target="_blank"} directive marks a field as owned by another subgraph.
This subgraph declares the field so it can be referenced (e.g. by [`@requires`](#requiresdirective)) but does
not resolve it.

[external directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#external

```python hl_lines="2 10"
-8<- "federation/external_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @external
}
```

### `RequiresDirective`

The [`@requires`][requires directive]{:target="_blank"} directive declares that resolving a field on this
subgraph requires additional [`@external`](#externaldirective) fields from the entity to be fetched first.

[requires directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#requires

```python hl_lines="2 11"
-8<- "federation/requires_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @external
  displayName: String! @requires(fields: "name")
}
```

### `ProvidesDirective`

The [`@provides`][provides directive]{:target="_blank"} directive tells the router that this subgraph can
resolve the listed fields of a referenced entity, avoiding an extra round-trip to the owning subgraph.

[provides directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#provides

```python hl_lines="2 10"
-8<- "federation/provides_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  project: ProjectType! @provides(fields: "name")
}
```

### `OverrideDirective`

The [`@override`][override directive]{:target="_blank"} directive tells the router that this subgraph takes
over resolution of a field previously owned by another subgraph. `from_` names the subgraph being overridden.

Pass an optional `label` to opt into **progressive override** — the router uses the label to route a
configurable fraction of traffic to this subgraph rather than switching over all at once.

> Requires `FEDERATION_VERSION` `"2.7"` or higher for the `label` argument.

[override directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#override

```python hl_lines="2 10"
-8<- "federation/override_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @override(from: "legacy")
}
```

### `InaccessibleDirective`

The [`@inaccessible`][inaccessible directive]{:target="_blank"} directive hides a schema element from the
supergraph. The element remains defined in the subgraph but the router never exposes it to clients.

[inaccessible directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#inaccessible

```python hl_lines="2 10"
-8<- "federation/inaccessible_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  internalNote: String @inaccessible
}
```

### `TagDirective`

The [`@tag`][tag directive]{:target="_blank"} directive attaches arbitrary metadata strings to schema
elements. Contract composition and other Apollo tooling read the tags for filtering. Repeatable.

[tag directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#tag

```python hl_lines="2 10"
-8<- "federation/tag_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @tag(name: "public") @tag(name: "v2")
}
```

### `ComposeDirectiveDirective`

The [`@composeDirective`][compose directive]{:target="_blank"} directive tells the router to preserve a
custom directive from this subgraph in the supergraph schema. Apply it at the schema level via
`schema_definition_directives`.

> Requires `FEDERATION_VERSION` `"2.1"` or higher.

[compose directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#composedirective

```python hl_lines="2 17"
-8<- "federation/compose_directive_directive.py"
```

```graphql
extend schema @composeDirective(name: "@custom")
```

### `InterfaceObjectDirective`

The [`@interfaceObject`][interface object directive]{:target="_blank"} directive lets a subgraph contribute
fields to an entity that is declared as an interface in another subgraph. Apply it to a `QueryType` alongside
[`@key`](#keydirective).

> Requires `FEDERATION_VERSION` `"2.3"` or higher.

[interface object directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#interfaceobject

```python hl_lines="2 7"
-8<- "federation/interface_object_directive.py"
```

```graphql
type TaskType @interfaceObject @key(fields: "id") {
  id: Int!
}
```

### `AuthenticatedDirective`

The [`@authenticated`][authenticated directive]{:target="_blank"} directive marks a schema element as
requiring an authenticated request. Enforcement happens at the router.

> Requires `FEDERATION_VERSION` `"2.5"` or higher.

[authenticated directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#authenticated

```python hl_lines="2 10"
-8<- "federation/authenticated_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @authenticated
}
```

### `RequiresScopesDirective`

The [`@requiresScopes`][requires scopes directive]{:target="_blank"} directive marks a schema element as
requiring the caller to hold one of the listed scope sets. Each inner list is an "all-of" group; the outer
list is "any-of".

> Requires `FEDERATION_VERSION` `"2.5"` or higher.

[requires scopes directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#requiresscopes

```python hl_lines="2 10"
-8<- "federation/requires_scopes_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @requiresScopes(scopes: [["read:task"]])
}
```

### `PolicyDirective`

The [`@policy`][policy directive]{:target="_blank"} directive marks a schema element as gated by named
authorization policies. The list-of-lists shape matches [`@requiresScopes`](#requiresscopesdirective).

> Requires `FEDERATION_VERSION` `"2.6"` or higher.

[policy directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#policy

```python hl_lines="2 10"
-8<- "federation/policy_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @policy(policies: [["policy_a"], ["policy_b"]])
}
```

### `ContextDirective`

The [`@context`][context directive]{:target="_blank"} directive names a context that the annotated type
contributes to. Arguments elsewhere resolve their value from that context via
[`@fromContext`](#fromcontextdirective). Repeatable.

> Requires `FEDERATION_VERSION` `"2.8"` or higher.

[context directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#context

```python hl_lines="2 7"
-8<- "federation/context_directive.py"
```

```graphql
type TaskType @context(name: "workspace") @key(fields: "id") {
  id: Int!
}
```

### `FromContextDirective`

The [`@fromContext`][from context directive]{:target="_blank"} directive populates a directive argument from
a named context declared via [`@context`](#contextdirective).

> Requires `FEDERATION_VERSION` `"2.8"` or higher.

[from context directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#fromcontext

```python hl_lines="4 14"
-8<- "federation/from_context_directive.py"
```

### `CostDirective`

The [`@cost`][cost directive]{:target="_blank"} directive attaches a demand-control weight to a schema
element. The router's cost analyzer sums these to estimate the total cost of a query.

> Requires `FEDERATION_VERSION` `"2.9"` or higher.

[cost directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#cost

```python hl_lines="2 10"
-8<- "federation/cost_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String! @cost(weight: 5)
}
```

### `ListSizeDirective`

The [`@listSize`][list size directive]{:target="_blank"} directive tells the demand-control cost analyzer
how large a list-returning field can grow. `assumed_size` is a fixed upper bound; `slicing_arguments` and
`sized_fields` describe pagination-based bounds.

> Requires `FEDERATION_VERSION` `"2.9"` or higher.

[list size directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#listsize

```python hl_lines="2 10-14"
-8<- "federation/list_size_directive.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  comments: [String!]! @listSize(
    assumedSize: 100,
    sizedFields: ["edges"],
    slicingArguments: ["first", "last"]
  )
}
```

### `CacheTagDirective`

The [`@cacheTag`][cache tag directive]{:target="_blank"} directive attaches a cache-tag template to a schema
element. The router uses the rendered tags to invalidate response cache entries. Repeatable, and applicable
to both object types and individual fields.

> Requires `FEDERATION_VERSION` `"2.12"` or higher.

[cache tag directive]: https://www.apollographql.com/docs/graphos/schema-design/federated-schemas/reference/directives#cachetag

```python hl_lines="2 7 11"
-8<- "federation/cache_tag_directive.py"
```

```graphql
type TaskType @cacheTag(format: "task") @key(fields: "id") {
  id: Int!
  name: String! @cacheTag(format: "task:{$response.id}:name")
}
```

## Entities

An **entity** is an object type marked with [`@key`](#keydirective) that can be fetched with one or more
unique keys and resolve its fields from multiple data sources in a federated graph. The router fetches
entities across subgraphs by sending **representations** (dicts like `{ "__typename": "TaskType", "id": 1 }`)
to your subgraph and expects the matching entities back.

Undine wires this up automatically in [`create_federation_schema`](#setup) whenever the schema contains at
least one resolvable `@key` entity, adding an `_entities` field to the `Query` type that the router calls
to fetch entities by their representations.

### Reference resolver

The reference resolver runs for each representation after the router dispatches by `__typename`. By default,
Undine builds one for you, but the default resolver only supports a `QueryType` with a single resolvable
`@key` whose `fields` is a single, unaliased token that maps to a declared `Field`. In any other case,
you need define a custom `__resolve_reference__` on the `QueryType`.

```python hl_lines="2 12"
-8<- "federation/resolve_reference.py"
```

Returning `None` from `__resolve_reference__` yields `null` for that entry. Raising propagates as a
GraphQL error on that entry's response slot.

## FederationType

A `FederationType` contributes fields to an entity that is owned by another subgraph
and is not backed by a Django model. You still mark it with [`@KeyDirective`](#keydirective)
so the router knows how to identify entities of this type.

```python
-8<- "federation/federation_type.py"
```

```graphql
type User @key(fields: "id") {
  id: Int!
  assignedTaskCount: Int!
}
```

> Note: `schema_name` must match the name to the shared entity name across subgraphs.

### FederationField

A `FederationField` is used to define a queryable value on a `FederationType`.
It mirrors [`Field`](queries.md#field) on a `QueryType`.

A `FederationField` resolves via one of three rules:

1. **Explicit resolver** — `@<field>.resolve` was used, or the decorator form `@FederationField(...)`
   wrapped a function.
2. **Key field** — the field's name appears in some `@KeyDirective(fields=...)`. The router populates
   the attribute from the representation; the resolver is a plain attribute lookup on the instance.
3. **`@external`** — the field carries [`@ExternalDirective()`](#externaldirective). Populated by
   another subgraph via `@requires`; again, a plain attribute lookup.

Anything else — a computed field with no resolver, no key membership, and no `@external` — is a definition
error and raises an exception when the schema is built.

The following declares a computed `overdue_task_count` that depends on `timezone` from another subgraph:

```python
-8<- "federation/federation_field_external.py"
```

```graphql
type User @key(fields: "id") {
  id: Int!
  timezone: String! @external
  overdueTaskCount: Int! @requires(fields: "timezone")
}
```

Both `timezone` (an `@external` attribute) and `id` (a key field) are populated by the router; only
`overdue_task_count` needs an explicit resolver.

### Stub references

A stub declares an entity type this subgraph *references* but does not resolve — the router routes
resolution requests elsewhere. Mark the key as `resolvable=False`, declare the key field(s) explicitly,
and leave the rest of the type empty. You can then use the stub as a `Field` reference on a resolvable
`QueryType`, and return a representation dict from the resolver so the router can fetch the rest of the
entity from the owning subgraph:

```python
-8<- "federation/federation_type_stub.py"
```

```graphql
type TaskType @key(fields: "id") {
  id: Int!
  name: String!
  assignedTo: User
}

type User @key(fields: "id", resolvable: false) {
  id: Int!
}
```

The stub still appears in `_service.sdl` (so the router can compose it), but it does not appear in the
`_Entity` union and no `_entities` dispatch is wired for it.

## Permissions

When the router fetches entities through the injected [`_entities`](#entities) endpoint, it bypasses your
top-level query entrypoints. To keep authorization consistent, Undine invokes the entity's
`__permissions__` classmethod on every entity resolved through `_entities`, whether the entity is backed
by a `QueryType` or by a `FederationType`.

For a `QueryType`, the same [`__permissions__`](queries.md#permissions) that runs on regular entrypoints
runs here too — no extra wiring is needed.

For a `FederationType`, define `__permissions__` on the class; the `_entities` resolver invokes it right
after `__resolve_reference__` builds the instance:

```python
-8<- "federation/federation_type_permissions.py"
```

To gate an individual `FederationField`, decorate a method with `@<field>.permissions`. Sibling fields
keep resolving independently:

```python
-8<- "federation/federation_field_permissions.py"
```

Both hooks may also be defined `async`. If a permission check fails, the failing entity slot or field
becomes `null` with the error attached, leaving the rest of the batch intact.

## Apollo compatibility

Undine is verified against Apollo's [subgraph compatibility harness]{:target="_blank"}, which
composes a subgraph with Apollo's `users` and `inventory` subgraphs plus a router and runs
Apollo's canonical query set against the composed supergraph.

[subgraph compatibility harness]: https://github.com/apollographql/apollo-federation-subgraph-compatibility

A reference implementation of Apollo's `products` subgraph in Undine lives at
`tests/test_federation/compatibility/`. It contains a small Django project you can read end-to-end to see
entities, `FederationType` extensions, `@key`/`@requires`/`@provides`/`@override`, custom directives
via `@composeDirective`, and reference resolvers wired against real models. See its `README.md` for
how to boot it locally and run Apollo's compliance runner.

-8<- "federation/compatibility_results.md"

## Federated tracing

Undine ships `FederatedTracingHook`, a [lifecycle hook](lifecycle-hooks.md) that implements Apollo's
Federated Tracing v1 (`ftv1`) protocol. Register it in [`LIFECYCLE_HOOKS`](settings.md#lifecycle_hooks) to opt in:

```python hl_lines="5"
UNDINE = {
    "LIFECYCLE_HOOKS": [
        "undine.hooks.RequestCacheHook",
        "undine.hooks.AtomicMutationHook",
        "undine.federation.tracing.FederatedTracingHook",
    ],
}
```

The hook requires the `protobuf` package, which is not installed by default.
Install it via the `federation-tracing` extra:

```shell
pip install 'undine[federation-tracing]'
```

When a request carries the `apollo-federation-include-trace: ftv1` header, the
hook records timings for every resolver call and attaches a message under `extensions.ftv1` on the response.
See [Apollo docs][federated tracing]{:target="_blank"} for more information.

[federated tracing]: https://www.apollographql.com/docs/federation/v1/metrics
