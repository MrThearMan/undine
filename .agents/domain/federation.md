# Federation

## Federation schema

A schema built with `create_federation_schema` that is compliant with the Apollo
Federation 2 subgraph spec. Distinct from a plain (non-federated) schema built with
`create_schema`.

Avoid: Federated schema (when meaning a supergraph)

## Subgraph

A single Undine service participating in an Apollo Federation 2 supergraph.
Every federation schema exposes exactly one subgraph.

Avoid: Federated schema (ambiguous with supergraph)

## Supergraph

The composed schema an Apollo router assembles from multiple subgraphs.
Undine does not compose supergraphs. It only produces subgraphs.

Avoid: Federated schema (ambiguous with subgraph)

## Federation entity

An object type marked with `@KeyDirective` that the router can fetch across
subgraphs by its key fields.

Avoid: Federated type, keyed type

## Entity representation

A dict of the shape `{ "__typename": "Foo", ...keyFields }` that the router sends to
`Query._entities` when it needs an entity resolved. Each representation is dispatched by
`__typename` and passed to the corresponding reference resolver.

Avoid: Reference, entity payload

## Federation type

A Undine class for defining non-model backed contributing entities and stub references.

Avoid: Federated type, keyed type

## Federation field

A field on a federation type. Distinct from `Field`.

Avoid: Field (unqualified, reserved for the`QueryType` field), extension field

## Owning entity

An entity whose canonical data lives in this subgraph.
Query type with `@KeyDirective(..., resolvable=True)`.

Avoid: Primary entity, source entity

## Contribution entity

An entity owned by another subgraph whose extra fields this subgraph contributes.
Federation type with `@KeyDirective(..., resolvable=True)`.

Avoid: Extension type, contribution type

## Stub reference

It declares an entity so this subgraph can reference it in its own fields without
resolving it locally. Appears in `_service.sdl` but not in the `_Entity` union.
Federation type with `@KeyDirective(..., resolvable=False)`.

Avoid: Stub entity, non-resolvable entity

## Reference resolver

The `__resolve_reference__` hook on a `QueryType` or `FederationType` that
turns a entity representation data into an instance.

Avoid: Entity resolver (ambiguous with the `_entities` resolver itself)

## Subgraph SDL

The subgraph schema string returned by `Query._service.sdl`.
The router fetches it during composition to learn about the subgraph's types,
entities, and federation directives.

Avoid: Schema SDL (unqualified), service SDL

## Compatibility subgraph

The runnable Django project under `../../tests/test_federation/compatibility`
that implements Apollo's `products` reference schema as an Undine subgraph.
Packaged as a Docker deliverable for Apollo's compliance harness.

Avoid: Compat harness, compliance project

## Apollo compliance runner

The `@apollo/federation-subgraph-compatibility` CLI that boots the
compatibility subgraph alongside Apollo's own `users` / `inventory` / router
containers and runs the `COMPATIBILITY.md` query set against the composed supergraph.

Avoid: Compat runner, harness runner
