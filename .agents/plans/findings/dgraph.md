# Dgraph findings

Versions checked: repo `dgraph-io/dgraph` (old URL `hypermodeinc/dgraph` redirects) default branch `main` at `317411f` (2026-10-08, "chore: prepare for v25.5.0"). Docs repo `dgraph-io/dgraph-docs` at `862b08a` (2026-08-19). Docs are Docusaurus. The GraphQL docs are in `docusaurus-docs/docs-graphql/` (71 pages, about 39k words), with versioned copies for v24.1 and v25.1 to v25.4.
Dgraph is a distributed graph database in Go. It has two query languages: DQL (its own language, formerly GraphQL+-) and a GraphQL API. The GraphQL API is generated from a GraphQL SDL schema that the user uploads. Dgraph turns the SDL into a DQL schema (predicates and indexes) and generates queries, mutations, subscriptions, filters and inputs. Each GraphQL request is rewritten to DQL and runs inside the database. There is no resolver code in user land. Custom logic is done with `@custom` (HTTP or DQL) and `@lambda` (JS lambda server). Apache-2.0.
This file focuses on the GraphQL API layer (`graphql/` package in the repo). DQL is mentioned only where the GraphQL API exposes it.

## Ownership history and maintenance status

- Ownership: Dgraph Labs (GitHub org `dgraph-io`) built Dgraph from 2015/2016. Hypermode acquired Dgraph Labs (I think in 2023, an AI-engineering directory says 2024). The repo then moved to `hypermodeinc/dgraph` and the Go module became `github.com/hypermodeinc/dgraph`.
- Istari Digital acquired Dgraph from Hypermode. Press release dated 2025-10-23 ([Istari](https://www.istaridigital.com/resources/istari-acquires-dgraph), [Fenwick](https://www.fenwick.com/insights/experience/fenwick-represents-hypermode-in-sale-of-dgraph-to-istari-digital)).
- After that the repo moved back to the restored `dgraph-io` org. PR #9522 (merged 2025-11-03) "updates links to the restored dgraph-io gh account". PR #9533 (merged 2025-11-25) changed the module path to `github.com/dgraph-io/dgraph/v25` and the copyright to "© 2017-2026 Istari Digital, Inc.".
- GitHub API for `hypermodeinc/dgraph` now returns `dgraph-io/dgraph`. Not archived. 21804 stars. 103 open issues plus PRs. Last push 2026-10-09.
- Active. Release about every 2 to 6 weeks. Recent releases: v25.4.1 (2026-08-24), v25.4.0 (2026-07-30), v25.3.8 (2026-07-09), v25.3.7 (2026-06-25), v25.3.6 (2026-06-19), v25.3.5 (2026-06-11), v25.3.4 (2026-05-11), v25.3.0 (2026-03-06), v25.2.0 (2026-01-29), v25.1.0 (2025-12-12), v25.0.0 (2025-10-07).
- The v24.1 line still gets patch releases (v24.1.9 on 2026-05-11).
- Unreleased: `CHANGELOG.md` has a `v25.5.0` section dated 2026-10-08, but there is no tag or GitHub release yet. Main items: `--rebalance_interval=0`, bulk loader `--tablet_placement`, `--security "anonymous=full|data|none"`, new `AccessController` that separates identity from tenancy. No GraphQL-API items in v25.5.0.
- Changelog date disagrees with GitHub: `CHANGELOG.md` says v25.0.0 is "2025-01-16". The GitHub release is 2025-10-07 (previews from 2025-04-18).
- Prerelease tags show work in progress: `v25.3.1-preview-federation-changes` (2026-03-20), `v25.3.0-preview-no-maxprocs`, `v25.4.0-preview1`.
- No `llms.txt` on https://docs.dgraph.io/llms.txt (404). No markdown variant of pages. The old URL https://dgraph.io/docs/graphql/ is 404. Current docs: https://docs.dgraph.io/graphql/.

## Architecture

- The user uploads a GraphQL SDL ("input schema") to `/admin/schema` (HTTP POST) or with the `updateGQLSchema` admin mutation. Dgraph validates it, adds generated types and root fields, and serves the result at `/graphql`.
- Each GraphQL type becomes a Dgraph type. Each field becomes a predicate named `<Type>.<field>` by default. `@dgraph(type:, pred:)` overrides the names.
- A GraphQL query is rewritten to one DQL query (`graphql/resolve/query_rewriter.go`) and runs in the database. Nested fields are graph traversals. No N+1. No dataloader. No resolver code for generated fields.
- Mutations are rewritten to DQL upserts (`graphql/resolve/mutation_rewriter.go`). Each mutation field is its own transaction (`CommitOrAbort` in `resolve/mutation.go`). Several mutation fields in one request are not atomic together.
- Mutation fields run serially. After the first failed mutation the rest are skipped with error "Mutation X was not executed because of a previous error." (`resolve/resolver.go`).
- Root query fields run in parallel goroutines and are independent. An error in one does not stop others.
- The final schema can be fetched with the `getGQLSchema` admin query. The generated schema prints sections: "Input Schema", "Extended Definitions", "Generated Types", "Generated Enums", "Generated Inputs", "Generated Query", "Generated Mutations", "Generated Subscriptions".
- Schema is per namespace when multi-tenancy is on.
- A schema change does not migrate data. The docs page "Schema Migration" (renaming a type or field, changing a field type, adding `@id`) only gives manual steps or `@dgraph` remapping. No migration tool.

## Schema input rules (types and scalars)

- Built-in scalars: `Int`, `Float`, `String`, `Boolean`, `ID`, `Int64`, `DateTime` (RFC3339 string). Custom scalars are not allowed. Defining a new `scalar` is a schema error.
- `ID`: auto-generated 64-bit uid, shown as hex string like `0x123`. At most one `ID` field per type. `[ID]` not allowed.
- Scalar lists (`[String]`, `[Int]` ...) are unordered sets. Duplicates are dropped and order is not kept. Lists of lists are not allowed.
- Exception: `[Float!] @embedding` is an ordered float32 vector.
- Enums are stored as strings.
- Interfaces: implementing types inherit fields. A type may omit inherited fields in the input SDL, Dgraph fills them in. A type can implement several interfaces, but two interfaces cannot share a field name except `ID`.
- Unions: allowed as field types. Union members must be object types. Union list fields get `filter: <Union>Filter` (with `<unionName>Types: [<Union>Type]`, for example `homeMemberTypes: [dog, parrot]`, and one `<member>Filter` per filterable member), `first`, `offset`. No `order` on union fields (ordered by uid).
- Fields with arguments are only allowed with `@custom` or `@lambda`.
- Geo types: `Point { longitude, latitude }`, `PointList`, `Polygon { coordinates: [PointList!]! }`, `MultiPolygon { polygons }`. Input variants `PointRef`, `PolygonRef`, `MultiPolygonRef`.
- Password: `@secret(field: "pwd", pred: String)` on a type adds a write-only `pwd: String!` to add input. Stored with bcrypt. Min length 6. Never returned. Checked with generated query `check<Type>Password(<id args>, pwd: String!): <Type>` (returns null on mismatch).
- Descriptions: `"""..."""` doc strings pass through to the generated schema. `#` comments are dropped. Comments starting with `# Dgraph.` are reserved for config (`# Dgraph.Authorization`, `# Dgraph.Allow-Origin`).
- Reserved names: `Int`, `Float`, `Boolean`, `String`, `DateTime`, `ID`, `uid`, `Subscription`, `as` (case-insensitive), `Query`, `Mutation`, `Point`, `PointList`, `Polygon`, `MultiPolygon`, and any name ending in `Aggregate`. Generated names like `<T>Filter`, `<T>Orderable`, `<T>Order`, `<T>Ref`, `Add<T>Input`, `Update<T>Input`, `<T>Patch`, `Add<T>Payload`, `Delete<T>Payload`, `Update<T>Payload`, `<T>AggregateResult` are also reserved.
- Language tags (documented only on the DQL interop page `graphql-dql/graphql-dgraph.md`): `@dgraph(pred: "Person.name@en")` maps a field to one language of a `@lang` predicate. `@dgraph(pred: "Person.name@hi:en")` (fallback list) and `"Person.name@."` (any language) are read only. They are left out of add, update, ref, filter and order inputs (`testdata/schemagen/input/language-tags.graphql`).
- Reverse edges: `posts: [Post] @dgraph(pred: "~Post.author")` makes a virtual field over the DQL `@reverse` index of `Post.author`. Data is stored once. Mutations only write the forward edge. Cannot be combined with `@hasInverse` (schema error). Documented on the page "GraphQL on existing Dgraph" (`graphql-dql/graphql-dgraph.md`), which recommends it over `@hasInverse` for new projects.
- `@hasInverse` stores two predicates (one per direction) and writes both on every mutation.

## Schema directives (full list from `graphql/schema/gqlschema.go`)

- `@id(interface: Boolean)` on field: external unique identifier. Code allows types `String`, `Int` and `Int64` (`idValidation` in `rules.go`). The docs say "must have the type `String!`". The docs and code disagree. The docs example uses `Int! @id` itself.
- `@id` effects: uniqueness check on add. Fields become arguments of `get<T>`. Several `@id` fields per type are allowed. With several, all `get` arguments are optional and combined with AND. With one `@id` or `ID` field, the argument is required. `add<T>` gets `upsert: Boolean`.
- `@id(interface: true)`: uniqueness across all types that implement the interface. Without it, uniqueness is per implementing type. `get<Interface>` only takes `@id(interface: true)` fields.
- `@search(by: [String!])` on field: builds a DQL index and the matching filter input. Values: `int`, `int64`, `float`, `bool`, `hash`, `exact`, `term`, `fulltext`, `trigram`, `regexp`, `year`, `month`, `day`, `hour`, `geo`, `ngram`, `"hnsw(metric: ..., exponent: ...)"` (enum `DgraphIndex`). `@search` with no args picks a default per type (DateTime defaults to `year`, enums to `hash`). `hash` and `exact` cannot be combined.
- `@hasInverse(field: String!)` on field: two-way edge. Adding or deleting one side updates the other. Without it, edges are one-way and the reverse is not stored.
- `@dgraph(type: String, pred: String)` on object, interface or field: map to existing DQL type and predicate names. Two GraphQL fields may map to the same predicate (they must share `@search`).
- `@embedding` on field: marks `[Float!]` as a vector. Used with `@search(by: ["hnsw(metric: euclidean|cosine|dotproduct, exponent: N)"])`.
- `@default(add: DgraphDefault, update: DgraphDefault)` on field. `DgraphDefault { value: String }`. Sets a value when a node is added or updated and the field is not given. Special value `"$now"` for `DateTime` (server time, RFC3339). Only scalar or enum, not list, not `@id`, not `ID`, not `@custom`/`@lambda`, not on `@remote` types. Added in v24.0.0 (#8017, #8837). Not in the docs at all. Example: `createdAt: DateTime @default(add: {value: "$now"})`, `updatedAt: DateTime @default(add: {value: "$now"}, update: {value: "$now"})` (test file `created-updated-directives.graphql`).
- `@withSubscription` on object, interface or field: adds `get<T>`, `query<T>` and `aggregate<T>` to the `Subscription` type. On a field it is for `@custom(dql:)` queries.
- `@secret(field: String!, pred: String)` on object or interface: password field (see above).
- `@auth(password: AuthRule, query: AuthRule, add: AuthRule, update: AuthRule, delete: AuthRule)` on object or interface. `AuthRule { and, or, not, rule: String }`. Not allowed on unions or `@remote` types. See Authorization section.
- `@custom(http: CustomHTTP, dql: String)` on field: custom query, mutation or field. See Custom logic section.
- `@remote` on object, interface, union, input, enum: type is not stored in Dgraph. Used as return or input type of `@custom` fields. No generated queries or mutations.
- `@remoteResponse(name: String)` on field of a `@remote` type: map a JSON key in the HTTP response to the field name.
- `@cascade(fields: [String])` on query field (executable directive): drop nodes that miss any (or the listed) fields.
- `@lambda` on field: resolve via the JavaScript lambda server.
- `@lambdaOnMutate(add: Boolean, update: Boolean, delete: Boolean)` on object or interface: call a lambda webhook after mutations.
- `@cacheControl(maxAge: Int!)` on query operation: sets `Cache-Control` response header.
- `@generate(query: GenerateQueryParams, mutation: GenerateMutationParams, subscription: Boolean)` on object or interface. `GenerateQueryParams { get, query, password, aggregate }`. `GenerateMutationParams { add, update, delete }`. Default: all true except `subscription` false.
- `@deprecated(reason:)` standard. `@skip` and `@include` standard.
- Apollo Federation directives when federation is used: `@key(fields:)`, `@extends`, `@external`, `@requires(fields:)`, `@provides(fields:)`. See Federation section.
- Unknown directives in the input schema: I think they are ignored (test `ignore-unsupported-directive.graphql`). I did not check if they are stripped from the output.

## Generated queries

- Per type `T` (unless turned off by `@generate`):
  - `getT(id: ID!, <@id fields>): T`. Lookup by `ID` or `@id` field(s). Not generated if the type has neither.
  - `queryT(filter: TFilter, order: TOrder, first: Int, offset: Int): [T]`.
  - `aggregateT(filter: TFilter): TAggregateResult`.
  - `checkTPassword(<id args>, pwd: String!): T` if the type has `@secret`.
  - `querySimilarTById(<id arg>, by: TEmbedding!, topK: Int!, ef: Int, distance_threshold: Float, filter: TFilter): [T]` and `querySimilarTByEmbedding(by: TEmbedding!, topK: Int!, vector: [Float!]!, ef: Int, distance_threshold: Float, filter: TFilter): [T]` if the type has an `@embedding` field with an hnsw index. `TEmbedding` is an enum of the vector fields.
- Interfaces get `getI`, `queryI` and `aggregateI` too. Results are the concrete types (use fragments).
- Every list field of an object type gets arguments `(filter:, order:, first:, offset:)`. Union list fields get `(filter:, first:, offset:)`.
- Every list field of an object or interface type gets a sibling `<field>Aggregate(filter: TFilter): TAggregateResult` field.
- Vector types get an extra output field `vector_distance: Float` on the type. Results of similarity queries are ordered by distance. Since v25.2.0 cosine and dot product distances are raw, not normalized to [0, 1].
- Docs and code disagree on vector queries: the docs show signatures named `getSimilar<T>ByEmbedding` and `getSimilar<T>ById`. The code generates `querySimilar<T>ByEmbedding` and `querySimilar<T>ById`. The `filter`, `ef` and `distance_threshold` arguments are only in the changelog and code, not in the docs page.

## Filtering grammar (`TFilter`)

- `TFilter` fields: `id: [ID!]` (named after the `ID` field), one field per `@search` field, `has: [THasFilter]`, `and: [TFilter]`, `or: [TFilter]`, `not: TFilter`.
- `and`/`or` take a list. A single object is coerced to a list. Fields in one object are ANDed. Infix style also works: `{ title: {...}, or: { ... } }`.
- `has: [THasFilter]`: enum of all fields. Matches nodes where all listed fields are non-null. This is the only way to filter on a relationship field.
- No filtering on fields of related nodes (no `author: { name: { eq: ... } }` in `PostFilter`). Filter nested lists with the field arguments instead, plus `@cascade` to drop parents.
- Filter input types per index (built-in, see `filterInputs` in `gqlschema.go`):
  - `IntFilter`, `Int64Filter`, `FloatFilter`, `DateTimeFilter`: `eq`, `in`, `le`, `lt`, `ge`, `gt`, `between: {min, max}`.
  - `StringExactFilter` (`exact`): `eq`, `in`, `le`, `lt`, `ge`, `gt`, `between` (lexicographic).
  - `StringHashFilter` (`hash`): `eq`, `in`.
  - `StringTermFilter` (`term`): `allofterms`, `anyofterms`.
  - `StringFullTextFilter` (`fulltext`): `alloftext`, `anyoftext` (stemming, stop words).
  - `StringRegExpFilter` (`regexp`, trigram index): `regexp: "/.*iggy.*/"`.
  - `StringNgramFilter` (`ngram`, added in v25.0.0): `ngram: "quick brown fox"` (contiguous word sequence).
  - Boolean: `filter: { isPublished: true }` directly, no filter object.
  - Enums: `<Enum>_hash` (`eq`, `in`), `<Enum>_exact` (comparisons), `regexp`.
  - `PointGeoFilter`: `near: { coordinate, distance }` (meters), `within: { polygon }`.
  - `PolygonGeoFilter` (Polygon, MultiPolygon): `near`, `within`, `contains: { point | polygon }`, `intersects: { polygon | multiPolygon }`.
- Several indexes on one field give a combined input named by joining, for example `StringFullTextFilter_StringTermFilter`.
- No `isNull` or `ne` operator. Negation is `not:`. Null check is `has` (inverted with `not`).
- No case-insensitive `eq`, `contains`, `startsWith` or `like`. Use `regexp` (`/.../i`) or term/fulltext.
- Filters need an index. A field without `@search` cannot be filtered (only `has`).

## Ordering and pagination

- `order: TOrder` with `TOrder { asc: TOrderable, desc: TOrderable, then: TOrder }`. `TOrderable` is an enum of the scalar fields of type `Int`, `Int64`, `Float`, `String`, `DateTime`. Multi-key sort with nested `then`.
- No ordering by related fields or by aggregates. No order on union fields.
- Pagination is offset based only: `first: Int`, `offset: Int`. On root `query` fields and on nested list fields.
- No cursor or Relay connection pagination. No `totalCount` on lists. Count via `aggregateT` or `<field>Aggregate { count }`.
- `@cascade` works with pagination since v21.03.

## Aggregates

- `TAggregateResult`: `count: Int`, and per scalar field `<f>Min`, `<f>Max` (String, DateTime, Int, Int64, Float), `<f>Sum`, `<f>Avg` (Int, Int64, Float). `Avg` is always `Float`.
- Root: `aggregateT(filter:)`. Nested: `<listField>Aggregate(filter:)`.
- Aggregates respect `@auth` query rules.
- Aggregates over no data return `null` (both root and nested).
- No group-by. No distinct count.

## Query directives and features

- `@cascade` / `@cascade(fields: ["a", "b"])` on a field. Drops nodes that miss any selected (or listed) fields. Applies down the tree. A nested `@cascade` overrides the parent one. Works with filters and pagination.
- `@skip(if:)`, `@include(if:)` standard.
- `@cacheControl(maxAge: Int!)` on the query operation. Adds `Cache-Control: public,max-age=N` and `Vary: Accept-Encoding`. Only HTTP caching. No server-side result cache.
- Automatic persisted queries in Apollo APQ format: `extensions: { persistedQuery: { sha256Hash } }`. Query plus hash stores it (hash is verified). Hash alone looks it up, else `PersistedQueryNotFound`. Stored in Dgraph as predicate `dgraph.graphql.p_query` (`edgraph/graphql.go` `ProcessPersistedQuery`). With ACL on, a valid ACL JWT is needed to use persisted queries. If query and hash are both sent and the stored query differs, the error is "query does not match persisted query". No allow-list or "persisted only" mode. Any query with text is accepted.
- Fragments, inline fragments, variables, aliases and introspection are supported.

## Generated mutations

- Per type `T` (unless turned off by `@generate`):
  - `addT(input: [AddTInput!]!, upsert: Boolean): AddTPayload`. `upsert` only exists if `T` has an `@id` field. Batch create is the default (input is a list).
  - `updateT(input: UpdateTInput!): UpdateTPayload` with `UpdateTInput { filter: TFilter!, set: TPatch, remove: TPatch }`. Bulk update by filter.
  - `deleteT(filter: TFilter!): DeleteTPayload`. Bulk delete by filter.
- Interfaces get `updateI` and `deleteI`, but no `addI`.
- Payloads: `AddTPayload { t(filter, order, first, offset): [T], numUids: Int }`. `UpdateTPayload` is the same. `DeleteTPayload` adds `msg: String` ("Deleted"). The delete payload `t` field returns the objects as they were before deletion.
- The payload list field is a full query field with filter, order and pagination. It reads the mutated nodes after commit.
- Input types: `AddTInput` (non-null fields are required, `ID` is left out), `TPatch` (all fields optional, `@id` fields included), `TRef` (all fields optional, `ID` included). Relationship fields take `TRef` or `[TRef]`.
- `TRef` semantics: if it has the `ID` or an `@id` value of an existing node, the node is linked and its other fields are ignored ("Deep mutations do not alter linked objects"). If the `@id` value does not exist, or there is no id, a new node is created. A non-existent `ID` is an error.
- Deep (nested) create and link in `add` and `update set`. No nested update of linked nodes. No nested delete. Use a separate `updateX` call.
- `update.remove`: removes the given values. For list edges it removes the listed references. For scalar lists it removes the listed items. I think for scalars the value is removed only when it matches (DQL delete semantics). I did not verify this.
- `@hasInverse` edges are kept in sync on add, update, delete. Changing a singular edge also removes the old inverse edge (`addAdditionalDeletes`).
- Deleting a node removes edges that point to it only for `@hasInverse` fields. Other edges in other nodes may dangle. I think this is why `author: Author!` can return null in practice (code comments in `mutation_rewriter.go` mention this case).
- Upsert: `addT(input: ..., upsert: true)` updates the root node if the `@id` value exists, otherwise creates it. Only root level fields are updated. Nested objects are not updated. Default `upsert: false`, then an existing `@id` value is an error ("id ... already exists").
- Union fields in mutations take a one-of style ref input: `{ dogRef: {...} }`, `{ parrotRef: {...} }`, `{ humanRef: {...} }` (`<Union>Ref` input with one field per member).
- `@default(add:, update:)` fills missing fields on create and update (see directives). A non-null field with `@default(add:)` becomes optional in `AddTInput` (`created: DateTime! @default(add: {value: "$now"})` gives `created: DateTime` in the input).
- No custom mutation input validation in the generated API (no length, min/max, regex constraints). Only GraphQL type checks, `@id` uniqueness, password min length 6, and `@auth` rules.
- No soft delete. No optimistic locking or version field. No "returning" of only changed fields. No `numUids` breakdown.
- `@lambdaOnMutate` webhooks fire after commit (async goroutine `sendWebhookEvent`).

## Subscriptions

- Opt in per type with `@withSubscription` (or `@generate(subscription: true)`). The `Subscription` type gets `getT`, `queryT` and `aggregateT` with the same arguments as the queries. No mutation event subscriptions (no "created", "updated", "deleted" payloads). The subscription returns the full live query result.
- `@withSubscription` on a `@custom(dql:)` query field adds that query to `Subscription`. Custom HTTP queries and `@lambda` queries cannot be subscribed.
- Implementation is polling, not change feeds (`graphql/subscription/poller.go`). Every `--graphql poll-interval` (default `1s`) the query is re-run. A result is pushed only when the farm hash of the JSON result changes.
- Identical subscriptions (same query, variables and auth variables) share one poller bucket. So many clients with the same query cost one poll.
- `@auth` query rules apply. JWT claims are part of the bucket key. The subscription ends when the JWT `exp` passes.
- A schema change terminates all subscriptions so clients reconnect.
- Transport: WebSocket with the legacy `subscriptions-transport-ws` protocol (subprotocol `graphql-ws`), via the fork `github.com/dgraph-io/graphql-transport-ws`. The newer `graphql-transport-ws` protocol (graphql-ws library) is not supported. No SSE.
- Auth headers can be sent in the WebSocket `connection_init` payload (`connectionParams`).
- `permessage-deflate` compression since v21.03.

## Authentication and authorization

- Default: `/graphql` is fully open. No JWT needed and no rules apply unless configured.
- Config is a comment line at the end of the schema: `# Dgraph.Authorization {"Header": ..., "Namespace": ..., "Algo": "HS256"|"RS256", "VerificationKey": ..., "JWKURL": ..., "JWKURLs": [...], "Audience": [...], "ClosedByDefault": bool}`. Keys are case-insensitive in the docs examples.
- JWT sources: HS256 secret, RS256 public key, or one or many JWK URLs (`JWKURL`/`JWKURLs`). With a JWK URL, `Audience` is required. Only one method at a time.
- Header value may be the bare token or `Bearer <token>`. Headers `Dg-Auth`, `X-Auth-Token` and `Authorization` are reserved by Dgraph.
- Claims come from the `Namespace` object and from the JWT root. Namespace claims win on conflict.
- `ClosedByDefault: true`: every request needs a valid JWT, even for types without `@auth`.
- No authentication API for end users in the GraphQL layer (no login, signup or token refresh). Use an external IdP (Auth0, Clerk, Firebase, Cognito). The `@secret` + `check<T>Password` query is the only built-in credential check, and it does not issue a token.
- `@auth` on types and interfaces only. No field-level auth. Not on unions or `@remote` types.
- Rule keys: `query`, `add`, `update`, `delete`, `password` (for `check<T>Password`). Each is an `AuthRule { and: [AuthRule], or: [AuthRule], not: AuthRule, rule: String }`.
- RBAC rule string: `"{$CLAIM: { eq: \"value\" } }"`. Operators in code: `eq`, `in` and `regexp` (`validateRBACOperators` in `graphql/schema/auth.go`). The docs only list `eq` and `in`. Array claims match if any element matches. A missing claim makes the rule false. `null` operands are not allowed.
- Graph traversal (ABAC) rule string: a GraphQL query on the same type, for example `query ($USER: String!) { queryTodo(filter: { owner: { eq: $USER } }) { id } }`. Variables are filled from JWT claims. The rule runs with implicit `@cascade`. So nested blocks must all match (use `__typename` in the innermost block). The query must be `query<SameType>`, checked at schema upload ("expected only queryActor rules, but found queryFilm").
- For queries, update and delete, rule evaluation is merged into the rewritten DQL query. It filters nodes. It does not raise an error. Unauthorized nodes are just missing.
- For add (and nested creates), a failed rule gives the error "authorization failed" and the transaction is aborted (`resolve/mutation.go`).
- `query` rules apply to `get`, `query`, `aggregate`, subscriptions and nested traversals into the type from other types.
- `add` rules are checked after the mutation on the new nodes (state after), inside the same transaction.
- `update` rules are checked before the mutation (state before). The after state is not checked. The docs say "Currently".
- `delete` rules filter which nodes the filter can delete (state before).
- An update that creates nested nodes must pass both the parent `update` rule and the child `add` rule.
- Interface `@auth` rules are ANDed with rules on the implementing types.
- `--graphql debug=true` returns auth error details to clients.
- CORS: `# Dgraph.Allow-Origin "https://example.com"` lines in the schema. Default is `Access-Control-Allow-Origin: *`. The docs say `https://cloud.dgraph.io` is always allowed. I did not find this origin in the code. I think it was a Dgraph Cloud gateway behavior.
- Dgraph ACL (DQL level users, groups, predicate permissions, `--acl`) is a separate layer. With ACL on, GraphQL requests also need an ACL access JWT in `X-Dgraph-AccessToken`. I think this is mainly for admin and multi-tenant setups.
- Not supported: per-field permissions, permission classes or hooks in code, rate limiting, query cost or depth limits (I found no depth or complexity limit in `graphql/`).

## Custom logic: `@custom(http:)`

- `@custom(http: CustomHTTP)` on fields of `Query`, `Mutation` or on fields of stored types. Dgraph does not run user code. It makes outgoing HTTP calls.
- `CustomHTTP { url: String!, method: HTTPMethod! (GET, POST, PUT, PATCH, DELETE), body: String, graphql: String, mode: Mode (SINGLE | BATCH), forwardHeaders: [String!], secretHeaders: [String!], introspectionHeaders: [String!], skipIntrospection: Boolean }`.
- URL template: `"https://api/person/$id/posts?limit=$n"`. Path variables must be non-null. Null or missing nullable args are dropped from the query string.
- Body template: `"{ title: $title, director: { id: $dir } }"`. JSON-like with `$var` placeholders. Only scalar args or fields in templates. Keys must be alphanumeric. No constant values in body templates.
- `graphql:` calls a remote GraphQL operation, for example `"query($id: ID!) { post(postID: $id) }"`. At schema upload Dgraph introspects the remote server and checks that args and return types match. `skipIntrospection: true` turns this off.
- `forwardHeaders`: copy headers from the incoming request. `secretHeaders: ["Authorization:Github-Api-Token"]`: send a secret from the schema under another header name. Secrets are lines `# Dgraph.Secret Github-Api-Token "long-token"` in the schema.
- `mode: BATCH` (custom fields with `graphql:`): one remote call for all parent objects. The remote query argument must have the form `[{param1: $var1, ...}]`. `SINGLE`: one call per parent.
- Custom fields on stored types: Dgraph first runs the DQL query, then resolves custom fields. It fetches the fields that the template needs, even if the client did not select them. Limits: the type needs an `ID` or `@id` field. Custom fields cannot take arguments. A custom field cannot depend on another custom field.
- Result type can be a stored type or a `@remote` type. `@remote` types have no CRUD and no search. `@custom` inside `@remote` types is not supported (docs roadmap). `@remoteResponse(name:)` maps a JSON key to a field.
- Errors: an HTTP error on a custom field nulls that field and adds an error. Other fields still resolve.
- The docs say custom logic "is still in beta". This text is old (it lists plans like "removing or customizing the generated CRUD mutations", which `@generate` already does).

## Custom logic: `@custom(dql:)`

- `@custom(dql: """ query q($arg: string) { q(func: ...) { alias: Pred } } """)` on `Query` fields. The DQL block name must equal the GraphQL field name. DQL aliases map to GraphQL fields. Variables are the GraphQL arguments by name.
- Only scalar arguments are allowed as DQL variables. No lists, no input objects.
- Only the levels mapped by the DQL query can be selected in GraphQL.
- For interface return types, select `dgraph.type` in DQL so `__typename` works.
- This is the escape hatch for features the generated API lacks: group-by (`@groupby` + `@remoteResponse`), ordering by count or by related fields, recursive queries, math, `@facets`.
- `@withSubscription` works on DQL custom queries.
- `@custom(dql:)` is query-only. Schema error "@custom directive with `dql` can be used only on queries." (`customDirectiveValidation` in `rules.go`). The DQL text is not validated at upload (a TODO in the code).
- `@auth` rules are not applied inside custom DQL. I think this is true because the DQL is sent as is. The docs do not say it.

## Custom logic: `@lambda` and lambda webhooks

- `@lambda` on `Query` fields, `Mutation` fields and fields of types or interfaces. Dgraph calls a JavaScript lambda server at `--graphql lambda-url=...`.
- Resolvers are registered in a JS script: `self.addGraphQLResolvers({"Type.field": fn, "Query.name": fn})` gets `{ parent, args, graphql, dql, authHeader }`. `self.addMultiParentGraphQLResolvers` gets `{ parents, ... }` and returns a list (batching for fields). `self.addWebHookResolvers` for webhooks.
- `graphql(query, variables, authHeader?)` calls back into the generated API with the user's auth header. `dql.query(...)` / `dql.mutate(...)` run DQL.
- Lambda fields default to BATCH mode (`schema/wrappers.go`).
- `@lambdaOnMutate(add:, update:, delete:)` on a type: after commit, Dgraph sends an event `{ __typename, operation, commitTs, add: { rootUIDs, input }, update: { rootUIDs, setPatch, removePatch }, delete: { rootUIDs } }` to the lambda server. Only root-level mutation nodes fire events. Fire and forget.
- Status: the reference lambda server repo `dgraph-io/dgraph-lambda` is archived (last push 2025-07-22). The Dgraph side still has the `lambda-url` flag and code. So `@lambda` needs a self-written or archived server. Dgraph Cloud, which hosted lambdas, is not mentioned in recent changes. I think lambda is effectively unmaintained.

## Admin API (`/admin`)

- `/admin` is a separate GraphQL endpoint. Protected by `--security "token=..."` (`X-Dgraph-AuthToken`), IP whitelist, and ACL (guardians group).
- Schema ops: `getGQLSchema { schema, generatedSchema }`, `updateGQLSchema(input: { set: { schema } })`, HTTP `POST /admin/schema`, `POST /admin/schema/validate` (dry-run validation, returns "Schema is valid" or errors).
- Cluster ops: `health`, `state`, `config`, `draining`, `shutdown`, `export`, `backup`, `restore`, `listBackups`, `task`, `removeNode`, `moveTablet`, `assign`.
- ACL ops: `login(userId, password, namespace, refreshToken)`, `getCurrentUser`, `addUser`, `updateUser`, `deleteUser`, `addGroup`, `updateGroup`, `deleteGroup`, `queryUser`, `queryGroup`, `resetPassword`.
- Multi-tenancy ops: `addNamespace`, `deleteNamespace`. Each namespace has its own GraphQL schema.
- Docs and code disagree: `docs-graphql/admin/admin-api.md` still lists `enterpriseLicense(...)`. The code removed the enterprise license in v25.0.0 (#9367, #9371). All former enterprise features are open source now.
- Schema changes add predicates and rebuild indexes. They never delete data. Removing a field from the schema leaves data in the database. Removing `@search` drops the index.

## Apollo Federation

- Federation v1 only, since v21.03. Directives: `@key(fields:)`, `@extends` (or `extend type`), `@external`, `@requires(fields:)`, `@provides(fields:)`. Adds `_service { sdl }` and `_entities(representations:)`.
- Limits: one `@key` per type. Single-field keys only (no compound keys). The key field must be `ID` or `@id`.
- No Federation v2 (`@link`, `@shareable`, `@override`, `@inaccessible`, `@tag`, `@interfaceObject`, `@composeDirective`). No `@key(resolvable: false)`.
- Extended types with `@key` on an `ID` field get `ID` as a required input in `addT` (the id comes from the owning service).
- `@requires` fields are only useful with `@lambda` or `@custom` on the same field.
- Directives with non-scalar args (`@auth`, `@custom`, `@generate`, `@cascade`, `@cacheControl`) are hidden from the federated SDL because of an Apollo gateway bug (comment in `gqlschema.go`).
- In progress: prerelease tag `v25.3.1-preview-federation-changes` (2026-03-20) and open PR #9663 "Exclude auxiliary types for @extends in Apollo Federation _service queries". No federation changes were released since v25.0.0.

## HTTP transport, responses and extensions

- `POST /graphql` with `application/json` (`query`, `variables`, `operationName`, `extensions`) or `application/graphql` (raw query). `GET /graphql?query=...&variables=...&operationName=...&extensions=...`. The GET handler in `graphql/admin/http.go` does not check the operation type. I think this means mutations over GET are accepted (CSRF risk). I did not run it.
- `Content-Encoding: gzip` requests and `Accept-Encoding: gzip` responses.
- Always HTTP 200, also for errors.
- Error objects: `message`, `locations`, `path`. Partial data with errors is returned.
- `extensions` in responses (on by default, `--graphql extensions=false` turns it off): `touched_uids` (number of nodes touched, a cost metric) and `tracing` in Apollo Tracing format (per resolver timings, plus `dgraph` sub-timings with labels `query`, `mutation`, `preMutationQuery`).
- Introspection on by default. `--graphql introspection=false` turns it off.
- `--graphql debug=true` shows auth errors and more detail.
- Multiple operations in a document need `operationName`. Query shorthand `{ ... }` works.
- `X-Dgraph-AccessToken` header for ACL. `X-Auth-Token` for the poor man's auth token. Header from `Dgraph.Authorization` for `@auth`.
- Since v25.5.0 (unreleased): `--security "anonymous=full|data|none"` controls what callers without a credential can do.
- Endpoints: `/graphql`, `/admin`, `/admin/schema`, `/admin/schema/validate`, `/probe/graphql` (health). Per-namespace GraphQL is selected by the ACL JWT namespace.
- No built-in GraphiQL or playground UI. The docs point to external IDEs (Postman, Insomnia, GraphiQL, VS Code). Dgraph's Ratel UI is for DQL.
- No `@defer`, `@stream`, `@oneOf`, batched (array) requests, file uploads (multipart), or SSE.

## Other code-level details

- GraphQL parsing uses Dgraph's forks `github.com/dgraph-io/gqlparser/v2 v2.2.2` and `github.com/dgraph-io/gqlgen v1.0.0`. Validation is done with gqlparser rules plus Dgraph rules in `graphql/schema/rules.go` and `validation_rules.go`.
- Security fix in v25.3.8: CVE-2026-63637 (GHSA-33p8-wc97-5qcj). The GraphQL `regexp` filter value was passed into DQL without validation. This allowed DQL injection without authentication in the default config. Now values that are not `/pattern/flags` literals are quoted.
- Open GraphQL PRs (2026-07 to 2026-10) are mostly auth fixes: #9761 "enforce update auth on existing nodes linked via @hasInverse", #9841 "replace full type-scan auth var with indexed seed traversal", #9846 "authorize similarity ById references and candidates", #9840 "keep the search vector in auth-protected similarity queries", #9702 "allow update mutations to set an @id field to its existing value", #9847 "normalize operation-root fragment selections". These suggest current gaps: `@hasInverse` linking can bypass update auth, and similarity queries have auth gaps.
- MCP server added to Dgraph core in v25.0.0 (#9389). It is for DQL and schema access by agents, not the GraphQL API.
- I think the GraphQL layer is in maintenance mode. Recent GraphQL changes are fixes and vector search. The last GraphQL features: `@default` (v24.0), vector similarity queries (v24.0), `ngram` search (v25.0), `ef` and `distance_threshold` (v25.2).

## Not supported (GraphQL API)

- Custom scalars (no JSON, Decimal, Date-only, Time, UUID, Upload scalars).
- Cursor or Relay pagination, `Node` interface, global object IDs.
- Filtering on related object fields. Ordering by related fields or aggregates.
- Group-by in the generated API (only via `@custom(dql:)`).
- Nested update or delete through relations.
- Field-level authorization. Code-level permission hooks. Input validators.
- Server-side resolver code in Go. Custom logic is only HTTP, DQL or the JS lambda server.
- Computed fields from DQL on stored types (only `@custom(http:)` or `@lambda` fields, not `@custom(dql:)` fields).
- Event or diff subscriptions. Subscriptions are live queries by polling.
- `graphql-transport-ws` protocol, SSE, `@defer`, `@stream`, file uploads.
- Federation v2. Schema stitching inside Dgraph (only remote calls via `@custom`).
- Query depth, complexity or cost limits. Rate limits.
- Data migrations on schema change.
- Optimistic concurrency control in GraphQL mutations (DQL has transactions, GraphQL mutations are one transaction each).

## Sources

- Repo: https://github.com/dgraph-io/dgraph (redirect from https://github.com/hypermodeinc/dgraph). Clone at `/tmp/dgraph-audit/dgraph`. Main files: `graphql/schema/gqlschema.go`, `graphql/schema/rules.go`, `graphql/schema/auth.go`, `graphql/schema/wrappers.go`, `graphql/resolve/resolver.go`, `graphql/resolve/mutation.go`, `graphql/resolve/mutation_rewriter.go`, `graphql/subscription/poller.go`, `edgraph/graphql.go`, `graphql/schema/testdata/schemagen/`.
- Changelog: https://github.com/dgraph-io/dgraph/blob/main/CHANGELOG.md
- Releases: https://github.com/dgraph-io/dgraph/releases
- Docs source: https://github.com/dgraph-io/dgraph-docs (`docusaurus-docs/docs-graphql/`). Clone at `/tmp/dgraph-audit/dgraph-io-docs`.
- Docs site: https://docs.dgraph.io/graphql/ (no `llms.txt`).
- Lambda server (archived): https://github.com/dgraph-io/dgraph-lambda
- WebSocket library: https://github.com/dgraph-io/graphql-transport-ws
- Ownership: https://www.istaridigital.com/resources/istari-acquires-dgraph and https://www.fenwick.com/insights/experience/fenwick-represents-hypermode-in-sale-of-dgraph-to-istari-digital. PRs https://github.com/dgraph-io/dgraph/pull/9522 and https://github.com/dgraph-io/dgraph/pull/9533.
