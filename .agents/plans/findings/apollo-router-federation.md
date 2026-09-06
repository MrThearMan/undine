# Apollo Router / Federation findings

Version checked: Apollo Router `v2.18.0` (2026-09-30, latest stable). `v3.0.0-preview.0` (2026-10-03, prerelease, release notes empty). Router repo default branch is `dev`, last commit `ebcecb3` 2026-10-08. `apollo-router/Cargo.toml` on `dev` still says `2.17.0`. Unreleased changes are in `.changesets/`.
Router 2.x LTS line: `v2.16.4` (2026-09-24).
Federation JS repo (`apollographql/federation`): last commit `b95c124` 2026-08-18. `@apollo/subgraph` npm `latest` is `2.15.1` (2026-09-14). The repo `main` changelog stops at `2.14.4`. I think 2.15 was released from a branch.
Composition moved to Rust in Federation v2.15 (July 2026). The Rust code is the `apollo-federation` crate inside the router repo. The JS `composition-js`, `query-planner-js` and `gateway-js` still exist.
Latest federation spec in docs: `federation/v2.15`. The code also defines `federation/v2.16`. On the v3 branch, PR #10283 replaces the unreleased `v2.16` with `federation/v3.0`.
Router is Rust. It is licensed under Elastic License v2 (ELv2). Many features need a GraphOS plan or license ("GraphOS Router" vs free "Apollo Router Core").
Apollo Server is in `apollo-server.md`. It is not repeated here.

## Part 1: Federation spec, from the subgraph's side

### What a subgraph server must do (subgraph spec)

- Add schema definitions on startup: `union _Entity`, `scalar _Any`, `scalar FieldSet`, `scalar link__Import`, `scalar federation__ContextFieldValue`, `scalar federation__Scope`, `scalar federation__Policy`, `enum link__Purpose { SECURITY EXECUTION }`, `type _Service { sdl: String! }`, plus all federation directive definitions.
- `Query._service: _Service!`: "enhanced introspection". `sdl` returns the subgraph SDL as a string, including every federation directive use. Must work even when normal introspection is disabled. Not exposed in the supergraph.
- `sdl` for Federation 1 must omit the auto-added definitions. For Federation 2 only, it may include them.
- `Query._entities(representations: [_Any!]!): [_Entity]!`: router entry point to fetch entity fields. Must return results in the same order as the input. Entries may be `null` if not found.
- A representation (`_Any`) is a JSON object with `__typename` plus all fields of one `@key`. Also includes `@requires` fields when needed.
- Validation rules for each representation: must have `__typename`. Must contain all fields of a `@key` fieldset of that entity.
- `_Entity` union is generated: every type with `@key`, except types where every `@key` has `resolvable: false`. If no entities, do not add `_Entity` or `_entities`.
- The library must give developers a way to resolve an entity from its representation. Apollo calls it a "reference resolver" (`__resolveReference` in `@apollo/subgraph`). The spec does not fix the API shape.
- Must apply `@link(url: "https://specs.apollo.dev/federation/v2.x", import: [...])` to the `schema` type (Federation 2 opt-in).
- `@extends` is only needed for libraries that cannot emit the `extend` keyword (typical for code-first). Federation 2 does not require type extensions.
- `FieldSet` grammar: a selection set without the outer braces. Examples: `"upc"`, `"id countryCode"`, `"id organization { id }"`. Since v2.15 composition rejects non-string `FieldSet` values.
- Federated tracing (FTV1): when the router sends header `apollo-federation-include-trace: ftv1`, the subgraph returns `extensions.ftv1` (base64 protobuf trace). Optional. Tested by the compatibility suite.
- Entity interfaces: a subgraph that puts `@key` on an interface must resolve the interface reference to a concrete type (return `__typename`).
- Subscriptions in subgraphs: allowed since v2.4. The router talks to the subgraph over WebSocket (`graphql-ws` or legacy `subscriptions-transport-ws`) or HTTP callback protocol. See Part 2.
- `@defer` is not sent to subgraphs. The router splits the query plan itself. Subgraphs need no `@defer` support.
- Response caching reads the subgraph `Cache-Control` response header (`max-age`, `private`) for TTL. Apollo Server derives this header from `@cacheControl(maxAge:, scope: PUBLIC | PRIVATE)`. The docs say other servers need an equivalent. When one response has many entities, the subgraph sends the minimum TTL.
- Subgraphs can set cache tags at runtime in response `extensions`: `apolloEntityCacheTags` (array of arrays, one per `_entities` item) and `apolloCacheTags` (flat array for root fields).

### Directive imports and namespacing

- `@link(url: String!, as: String, for: link__Purpose, import: [link__Import]) repeatable on SCHEMA`: spec `https://specs.apollo.dev/link/v1.0`. `for: SECURITY | EXECUTION` marks specs a consumer must understand.
- `import: ["@key", "@shareable"]`: bring names in unprefixed.
- Rename on import: `import: [{ name: "@key", as: "@uniqueKey" }]`.
- Not imported directives are still usable with a namespace prefix: `@federation__shareable`. Custom prefix via `@link(as: "fed")` gives `@fed__shareable`.
- Since v2.14 composition validates name conflicts between linked specs and imports. Standalone `specs.apollo.dev/tag` and `specs.apollo.dev/inaccessible` links should be replaced by imports from the federation spec.
- Since v2.15 custom specs cannot use the `https://specs.apollo.dev` domain.

### Federation directives (with version added)

- `@key(fields: FieldSet!, resolvable: Boolean = true) repeatable on OBJECT | INTERFACE`: entity primary key. Fed 1.0. `resolvable` added in v2.0. Multiple keys, composite keys, nested keys allowed. On `INTERFACE` since v2.3 (entity interfaces).
- `@shareable on OBJECT | FIELD_DEFINITION`: field may be resolved by more than one subgraph. v2.0. `repeatable` since v2.2.
- `@external on FIELD_DEFINITION | OBJECT`: field is defined here but resolved elsewhere. Fed 1.0. `OBJECT` location in Fed 2. Since v2.15 merged directives on `@external` fields are an error.
- `@requires(fields: FieldSet!) on FIELD_DEFINITION`: field needs other `@external` fields. The router sends them in the representation. Fed 1.0. Fields with arguments allowed since v2.1.2 (`@requires(fields: "weight(units: \"KILOGRAMS\")")`).
- `@provides(fields: FieldSet!) on FIELD_DEFINITION`: this subgraph can return the listed `@external` fields at this path. Fed 1.0.
- `@extends on OBJECT | INTERFACE`: alternative to `extend type`. Fed 1.0.
- `@tag(name: String!) repeatable` on fields, objects, interfaces, unions, arguments, scalars, enums, enum values, input objects, input fields: metadata for contracts (schema variants filtered by tag). Fed 1.1. Since v2.15 tag validation runs in composition.
- `@inaccessible` on the same locations as `@tag`: element is in the supergraph but hidden from the API schema. v2.0.
- `@override(from: String!) on FIELD_DEFINITION`: migrate a field from another subgraph. v2.0. Works on entity fields and root fields. Only one subgraph can override a field.
- Progressive override: `@override(from: String!, label: String)`. v2.7. `label: "percent(x)"` sends x% of traffic to the new subgraph. Custom labels (regex: starts with a letter, then alphanumerics, `_-:./`) are resolved at runtime by a coprocessor or Rhai script via context keys `apollo_override::unresolved_labels` and `apollo_override::labels_to_override`. Each label doubles query plan cache entries.
- `@composeDirective(name: String!) repeatable on SCHEMA`: keep a custom type-system directive in the supergraph. v2.1. The directive must come from a `@link`ed custom spec. Not for executable directives.
- `@interfaceObject on OBJECT`: an object stands in for another subgraph's entity interface. Its fields are added to the interface and all implementations. v2.3.
- `@authenticated on FIELD_DEFINITION | OBJECT | INTERFACE | SCALAR | ENUM`: router requires an authenticated request. v2.5. Enforced by the router (GraphOS feature). Spec `authenticated/v0.1`.
- `@requiresScopes(scopes: [[federation__Scope!]!]!)`: same locations. JWT scopes. Outer list is OR, inner list is AND. v2.5.
- `@policy(policies: [[federation__Policy!]!]!)`: same locations. Policies resolved by a coprocessor or Rhai script. v2.6. Since v2.9 not allowed on interfaces (composition error). Docs location list still shows `INTERFACE`.
- `@context(name: String!) on OBJECT | INTERFACE | UNION`: name a context on a type. v2.8. Code defines it `repeatable`. The v2.8 version page shows it without `repeatable`.
- `@fromContext(field: ContextFieldValue) on ARGUMENT_DEFINITION`: argument value comes from an ancestor context, for example `"$userContext { prop }"`. v2.8. Argument must be nullable. No `@skip`/`@include` in the selection.
- `@cost(weight: Int!) on ARGUMENT_DEFINITION | ENUM | FIELD_DEFINITION | INPUT_FIELD_DEFINITION | OBJECT | SCALAR`: demand control weight. v2.9. Spec `cost/v0.1`. Default cost: scalars and enums 0, composite types 1. Licensed (GraphOS).
- `@listSize(assumedSize: Int, slicingArguments: [String!], sizedFields: [String!], requireOneSlicingArgument: Boolean = true) on FIELD_DEFINITION`: list size estimate for cost analysis. v2.9. `slicingArguments` takes the max of given args. `sizedFields` supports cursor/connection wrappers.
- `@cacheTag(format: String!) repeatable on FIELD_DEFINITION | OBJECT`: cache tag for router response cache invalidation. v2.12. Templates: `{$args.x}` on root fields, `{$key.x}` on entities. Values must be scalar or enum.
- Connectors `@connect` and `@source`: v2.10 (spec `connect/v0.1`). See Connectors in Part 2.
- `@oneOf` on input objects: composition merges it (PR #10124, v3 preview branch). Warning `INCONSISTENT_ONE_OF_INPUT_OBJECT` when subgraphs disagree.

### Federation version table (first release, minimum router)

- v1.0 / v1.1: `@key`, `@external`, `@requires`, `@provides`, `@extends`. v1.1 added `@tag`. Uses `_FieldSet` scalar.
- v2.0 (April 2022, router 1.0.0): `@link`, `@shareable`, `@inaccessible`, `@override`, `@key(resolvable:)`. Entities no longer have an "originating" subgraph. No `extend` needed. `@key` fields need no `@external`.
- v2.1 (August 2022, router 1.0.0): `@composeDirective`. `@requires` with field arguments (2.1.2).
- v2.2 (November 2022, router 1.6.0, not in GraphOS): `@shareable` repeatable.
- v2.3 (February 2023, router 1.10.2): `@interfaceObject`, `@key` on interfaces.
- v2.4 (March 2023, router 1.13.1): `Subscription` type allowed in subgraphs.
- v2.5 (July 2023, router 1.29.1): `@authenticated`, `@requiresScopes`, `Scope` scalar.
- v2.6 (November 2023, router 1.35.0): `@policy`, `Policy` scalar.
- v2.7 (February 2024, router 1.39.0): progressive `@override(label:)`.
- v2.8 (May 2024, router 1.48.0): `@context`, `@fromContext`.
- v2.9 (August 2024, router 1.53.0): `@cost`, `@listSize`.
- v2.10 (February 2025, router 2.0.0): Connectors `connect/v0.1`.
- v2.11 (June 2025, router 2.3.0): Connectors `connect/v0.2`.
- v2.12 LTS (November 2025, router 2.8.0): `@cacheTag`. Connectors `connect/v0.3`.
- v2.13 (January 2026, router 2.11.0): Connectors `connect/v0.4`.
- v2.14 (May 2026, router 2.14.0): `@interfaceObject` coexists with Fed 1 subgraphs unless a type name conflicts. `@composeDirective` no longer needs every subgraph to define every composed directive. Stricter `@link` validation.
- v2.15 LTS (July 2026, router 2.16.0): composition rewritten in Rust. No new directives. New errors: `INTERFACE_OBJECT_USAGE_ERROR`, `MERGED_DIRECTIVE_APPLICATION_ON_EXTERNAL`. Hints on failure. Default values normalized (`1` to `1.0` on `Float`). Errors have line numbers.
- v2.16: in code (`federation_spec_definition.rs`) but not in docs. Minimum for preview `connect/v0.5`.
- v3.0 (unreleased, `dev-v3.x` branch): replaces v2.16. Includes all v2 features. Adds a compat shim for GraphQL 2025 spec `@deprecated` changes (strips `@deprecated(reason: null)`, removes `@deprecated` on object fields whose interface field is not deprecated, with hints). Contract filtering ported to Rust.

### Docs vs code

- The subgraph spec page lists `@override(from: String!)` without `label`. The directive reference and code have `label: String`.
- The v2.15 version page says invalid `@override` labels that reference unknown subgraph names are "dropped". The Rust merger (`apollo-federation/src/merger/merger.rs`) raises `OverrideLabelInvalid` for labels that fail the label regex or `percent(0-100)`. I did not find code that drops labels by subgraph name.
- The subgraph spec page does not list `@cost`, `@listSize` or `@cacheTag` in the "schema additions" block. They are only needed when imported.
- `@policy` docs list `INTERFACE` as a location but say v2.9+ rejects it on interfaces.

### Subgraph compatibility tests

- Repo: https://github.com/apollographql/apollo-federation-subgraph-compatibility (last commit 2026-09-29). Implementers copy `implementations/_template_library_`, implement `products.graphql` (federation v2.3 schema), serve on port 4001 in Docker, and run `make test subgraph=<name>`.
- Supergraph also includes reference `inventory` and `users` subgraphs (`packages/subgraphs/`).
- Tests (`packages/compatibility/src/tests/`): `introspection` (`_service`), `@key` single, multiple, composite, repeatable, `@requires`, `@provides`, `ftv1`, `@link`, `@shareable`, `@tag`, `@override`, `@inaccessible`, `@composeDirective`, `@interfaceObject`.
- Fed 1 columns in the docs table: `_service`, `@key (single)`, `@key (multi)`, `@key (composite)`, `repeatable @key`, `@requires`, `@provides`, `federated tracing`. Fed 2 columns: `@link`, `@shareable`, `@tag`, `@override`, `@inaccessible`, `@composeDirective`, `@interfaceObject`.
- No tests exist for `@authenticated`, `@requiresScopes`, `@policy`, `@context`/`@fromContext`, `@cost`/`@listSize`, `@cacheTag`, progressive override, or subscriptions.
- Python libraries listed: Ariadne (all except FTV1 and `@composeDirective`), Graphene (no FTV1, `@composeDirective`, `@interfaceObject`), Strawberry (all except FTV1). Undine is not listed.
- Other listed libraries: Ballerina, GraphQL for .NET, Hot Chocolate, Absinthe, gqlgen, graphql-go fork, DGS, GraphQL Java Kickstart, graphql-kotlin, Spring GraphQL, Apollo Server, express-graphql, Yoga, Helix, Mercurius, NestJS, Pothos, Lighthouse, graphql-php, graphql-ruby, async-graphql, Caliban, Sangria, Graphiti (Swift), smallrye-graphql. Hosted: AppSync, Dgraph, Grafbase, GraphQL Mesh, Neo4j, StepZen.

### `@apollo/subgraph` (JS reference library)

- `buildSubgraphSchema(modules | { typeDefs, resolvers })`: adds `_service`, `_entities`, `_Entity`, `_Any` and directive definitions.
- `__resolveReference(representation, context, info)`: per-type reference resolver.
- `printSubgraphSchema(schema)`: SDL with federation directives, used for `_service.sdl`.
- Version tracks federation (2.15.1).

## Part 2: The Router

### Licensing and plans

- Two flavors of one binary. "Apollo Router Core" runs without GraphOS. "GraphOS Router" fetches a license from Apollo Uplink and unlocks licensed features.
- License gates (code `apollo-router/src/uplink/license_enforcement.rs`, `AllowedFeature`): `apq` Redis cache, `authentication.router` (JWT), `authorization.directives`, `batching`, `preview_entity_cache`, `response_cache`, `persisted_queries`, `subscription`, `coprocessor`, `supergraph.query_planning.cache.redis`, `demand_control`, `limits.router.max_depth`/`max_height`/`max_root_fields`/`max_aliases`, extended reference reporting, experimental features. Schemas using `specs.apollo.dev/authenticated` or `requiresScopes` also need a license.
- Docs mark these features as available on "Free, Developer, Standard, Enterprise" plans. Free has rate limits. Developer and Standard need router 2.6.0+.
- The v3 preview branch removes rate limiting from the license plugin (commit #10123).
- Offline license (Enterprise only, router 1.37+): `rover license fetch`, `--license`, `APOLLO_ROUTER_LICENSE_PATH`, `APOLLO_ROUTER_LICENSE`. Valid up to one year, 28-day grace period.
- Free features without license: query planning, in-memory caches, Rhai, native plugins, header propagation, CORS, CSRF, traffic shaping, telemetry/OTel, `@defer`, file uploads, connectors, introspection control, parser and HTTP limits, health checks.

### Request pipeline

- Services in order: Router service (HTTP, APQ, parse, validate), Supergraph service (query planning), Execution service (runs the plan), Subgraph service (one per subgraph, HTTP to subgraph). Connectors add a connector request service.
- Each service is a Tower service. Plugins wrap it. Request plugins run in order. Response plugins run in reverse order.
- A per-request `Context` (key-value map) is shared by all stages, plugins, Rhai and coprocessors. Documented context keys include `apollo::authentication::jwt_claims`, `apollo::authentication::jwt_status`, `apollo_override::unresolved_labels`, `apollo_override::labels_to_override`, and cost keys.
- Streaming design: no buffering before the end of the router service on the request path. No buffering on the response path.
- Fetches in a plan run in parallel or in sequence (`Parallel`, `Sequence`, `Flatten`, `Fetch`, `Defer`, `Condition` nodes).

### Customization

- YAML config (`router.yaml`) is the first choice. Env var expansion `${env.NAME:-default}`, also `${file.path}`. YAML aliases allowed. Hot reload of config and schema with `--hot-reload`.
- Rhai scripts (`rhai.scripts`, `rhai.main`): hooks `router_service`, `supergraph_service`, `execution_service`, `subgraph_service(service, subgraph)`. Use `service.map_request` / `map_response`. Helpers: logging, `throw` to end a request with status and body, `Router.APOLLO_SDL`, trace ID, url/json/base64 encode, sha256, Unix time, UUID, env vars. No network or disk access. Closures cannot read globals. Rhai 1.25 since router 2.18. No connector hook.
- External coprocessor (`coprocessor.url`): router POSTs JSON to any HTTP service at stages `router`, `supergraph`, `execution`, `subgraph`, `connector` (request and response). Choose which fields to send (`headers`, `body`, `context`, `sdl`, `path`, `method`, `status_code`). Reply with `control: "continue"` or `control: { break: <status> }` to end the request. Can modify `body`, `headers`, `context`. Per-stage URLs. `condition` per stage (not for execution). `response_validation`. `client` pool settings. `experimental_http2: http2only` for h2c. Handles deferred response chunks. Used to add auth claims, resolve `@policy`, resolve override labels.
- Native Rust plugins: `Plugin` trait with `new(PluginInit<Config>)`, `router_service`, `supergraph_service`, `execution_service`, `subgraph_service`, `web_endpoints` (custom HTTP endpoints). Register with `register_plugin!("group", "name", Struct)`. Configured under `plugins:`. Needs a custom router binary built from the `apollo-router` crate. `ServiceBuilderExt` helpers: `checkpoint`, `checkpoint_async`, `oneshot_checkpoint_async`, `buffered`, `instrument`, `map_request`, `map_response`. Private plugins also have `connector_request_service` and an HTTP client hook. Custom memory allocator choice for custom binaries.
- Docs say native plugins are for advanced cases. Apollo recommends Rhai or coprocessors first.

### Query planning

- Native Rust query planner (`apollo-federation` crate). Default since 1.59. Legacy JS (Deno/V8) planner removed in 2.x. Docs claim 10x median planning speedup.
- `supergraph.query_planning.cache.in_memory.limit` (default 512). `cache.redis` distributed plan cache (licensed). Redis URL schemes: `redis`, `rediss`, `redis-cluster`, `rediss-cluster`, `redis-sentinel`, `rediss-sentinel`.
- Cache warm-up on schema reload: `warmed_up_queries` (default 30% of cache). Prewarm from persisted query list (`persisted_queries.experimental_prewarm_query_plan_cache.on_startup` / `on_reload`). Warm-up metrics added in 2.18.
- Planner limits: `experimental_plans_limit`, `experimental_paths_limit`. `experimental_cooperative_cancellation` (`enabled`, `mode`, `timeout`, `memory_limit`). `experimental_reuse_query_plans`.
- `supergraph.generate_query_fragments`: auto-generate fragments in subgraph queries to shrink them.
- `experimental_type_conditioned_fetching`: split entity fetches by concrete type for abstract types.
- `Apollo-Expose-Query-Plan: true` header returns the plan in `extensions` (plugin `experimental.expose_query_plan`). Value `dry-run` plans without executing (used for cache warm-up).
- Plan nodes: `Fetch`, `Sequence`, `Parallel`, `Flatten`, `Defer`, `Condition` (for `@skip`/`@include` on `@defer`), subscription primary node.
- Progressive override: plans are cached per set of resolved labels. Plugin `progressive_override` resolves `percent(x)` labels at random per request.
- Upcoming (v3 preview branch): a new "incremental planner" (BULB search algorithm) with `@requires`, `@provides`, `@interfaceObject`, `@fromContext`, `@defer` support, native connector planning, and "fuel" metrics.

### Security

- Introspection: off by default (`supergraph.introspection: false`). `limits.router.introspection_max_depth`.
- `supergraph.redact_query_validation_errors`: replace validation error details with a generic message.
- `supergraph.strict_variable_validation`: variable validation modes.
- CSRF (`csrf`): on by default. Rejects "simple" requests unless a header like `apollo-require-preflight` or `x-apollo-operation-name` is present (`csrf.required_headers`). `unsafe_disabled` to turn off.
- CORS (`cors`): `policies` (per-origin list with `origins`, `match_origins` regex, `allow_credentials`, `allow_headers`, `expose_headers`, `methods`, `max_age`, private network access), `allow_any_origin`. Policy inheritance from global settings. Adds `Vary` header.
- TLS: `tls.supergraph` (server cert/key for HTTPS termination in router), `tls.subgraph` (custom CA, client cert mTLS per subgraph), `tls.connector`. TLS 1.2/1.3 only. Redis TLS.
- JWT authentication (`authentication.router.jwt`, licensed): `jwks` list (`url` or file, `issuers`, `audiences`, `algorithms`, `poll_interval`, `allow_missing_exp`, `headers`), `header_name` (default `Authorization`), `header_value_prefix` (default `Bearer`), `sources` (other headers or cookies), `ignore_other_prefixes`, `on_error` (`Error` or `Continue`, plus `RedactedError` since 2.18). Claims go to context `apollo::authentication::jwt_claims`. Custom JWKS (HS*, RS*, ES*, PS*, EdDSA). JWT forwarding to subgraphs via header rules. Claims to subgraphs via Rhai.
- Subgraph and connector authentication (`authentication.subgraph`, `authentication.connector`): AWS SigV4 request signing with static keys, default credential chain, or assume role.
- Authorization directives (`authorization.directives`, licensed): `@authenticated`, `@requiresScopes`, `@policy`. The router filters out unauthorized fields before planning. Response keeps the shape with `null` and `UNAUTHORIZED_FIELD_OR_TYPE` errors. Options: `enabled`, `reject_unauthorized` (reject the whole request instead), `errors.log`, `errors.response` (`errors`, `extensions`, `disabled`), `dry_run` (compute but do not filter).
- `authorization.require_authentication`: reject all unauthenticated requests.
- `@requiresScopes` reads `scope` claim (space-separated string). Rhai can reshape claims.
- `@policy`: the router puts required policies in context (`apollo::authorization::required_policies`). A coprocessor or Rhai script sets each to true or false.
- Authorization directives win over `@skip`/`@include`. Query deduplication groups by auth scope set. Authorization rules merge across subgraphs during composition (AND across subgraphs). Rules on `@key` fields and interfaces have special handling.
- Persisted queries (`persisted_queries`, licensed): fetch the persisted query list (PQL) from GraphOS. `safelist.enabled` rejects unknown operations. `safelist.require_id` accepts only IDs. `log_unknown`. `local_manifests` (JSON files with `format: "apollo-persisted-query-manifest"`, `version`, `operations[{id, body, name, type, clientName}]`). Per-client operation IDs. `hot_reload` for local manifests. Incremental adoption: audit mode, then safelist.
- APQ (`apq`): on by default. In-memory cache, optional Redis (licensed). `apq.subgraph` sends APQ hashes to subgraphs (off by default).
- Request limits (`limits.router`): `max_depth`, `max_height` (unique fields), `max_aliases`, `max_root_fields`, `max_recursive_selections`, `warn_only`. HTTP: `http_max_request_bytes` (default 2 MB), `http1_max_request_headers`, `http1_max_request_buf_size`, `http2_max_headers_list_bytes`. Parser: `parser_max_tokens`, `parser_max_recursion`. Subgraph and connector `http_max_response_size`.
- Demand control (`demand_control`, licensed): based on the IBM GraphQL Cost Directive spec. `mode: measure | enforce`. `strategy.static_estimated` with `list_size`, `max`, `actual_cost_mode` (`by_subgraph` default since 2.12, or `by_response_shape`). Per-subgraph limits `subgraph.all` / `subgraph.subgraphs.<name>` (2.12+): over-budget subgraph is skipped and treated as `null`. Defaults: mutation type cost 10, objects/interfaces/unions 1, scalars/enums 0. Uses `@cost` and `@listSize`. Context keys `APOLLO_COST_ESTIMATED_KEY`, `APOLLO_COST_ACTUAL_KEY`, `APOLLO_COST_STRATEGY_KEY`, `APOLLO_COST_RESULT_KEY`. Cost telemetry instruments `cost.estimated`, `cost.actual`, `cost.delta`.
- `forbid_mutations: true`: reject all mutations (read-only router).
- `include_subgraph_errors`: subgraph error details are redacted by default. Turn on per subgraph or all. Can allow or deny error extension keys.

### Caching

- Response caching (`response_cache`, licensed, GA in 2.10): Redis-backed cache of subgraph and connector responses. Root fields are cached as one unit. Each `_entities` item is cached as its own entry, so entities are reused across operations.
- TTL comes from the origin `Cache-Control` header (minimum across entities). Default TTL per subgraph or global if no header. `include_cache_control_header_on_router_response` (2.15) suppresses the computed `Cache-Control` on client responses.
- Private data: subgraph sends `Cache-Control: private`. `private_id` names a context key (for example the JWT `sub`) so data is cached per user. Without `private_id`, private data is not cached.
- Custom cache keys: context entry `apollo::response_cache::key` with `all`, `subgraphs`, `connectors`, or per-operation-name data. No merging between levels.
- Active invalidation: HTTP endpoint (default `/invalidation`, shared key in `Authorization` header). Body is a list of `{ kind: "subgraph" | "type" | "cache_tag" | "connector", ... }`. Returns the count of removed keys. Index-based, scales with invalidated entries. Per-subgraph `indexes` to choose which invalidation indexes are kept (2.16).
- Cache tags: `@cacheTag(format:)` in schema or `apolloEntityCacheTags` / `apolloCacheTags` in subgraph response extensions.
- CDN invalidation (2.17/2.18): router emits a `Cache-Tag` response header with `subgraph-{name}`, `type-{subgraph}-{type}` and `@cacheTag` values for Cloudflare/Fastly purging. Header size limits with truncation signal.
- Redis options: per-subgraph and per-connector-source Redis instances, cluster, sentinel, read replicas (2.10), TLS, timeouts, namespace prefix, `required_to_start`, pool size, TTL.
- Response cache works with authorization: cache keys include auth scope data. I did not check the exact key composition.
- Cache debugger in Apollo Sandbox for dev. Metrics for hits, misses, invalidation, Redis.
- `preview_entity_cache`: the older 2024 entity cache. Deprecated. Startup warning since 2.18. Docs say response caching is backward-compatible.
- Query plan cache: in-memory LRU plus optional Redis (see Query planning).
- APQ cache: in-memory, optional Redis.

### Operations and protocols

- HTTP: POST JSON, GET with query params. `supergraph.path` (default `/`), `supergraph.listen` (default `127.0.0.1:4000`). Unix domain socket listen (2.13). Trailing slash normalization (2.14).
- Persisted query protocol: `extensions.persistedQuery.sha256Hash` for both APQ and PQ IDs. Errors `PERSISTED_QUERY_NOT_FOUND`, `PERSISTED_QUERY_NOT_IN_LIST`, `PERSISTED_QUERY_ID_REQUIRED`, `CANNOT_SEND_PQ_ID_AND_BODY`.
- `@defer`: on by default (`supergraph.defer_support`). Client sends `Accept: multipart/mixed;deferSpec=20220824`. Format is the 2022-08-24 state of the RFC. Router plans deferred fragments into separate fetches, so subgraphs need no `@defer` support. Entity fields are deferrable. Non-deferrable fields are returned in the first chunk. Not supported with batching.
- `@stream`: not supported. I found no planner or execution support in the code.
- Subscriptions (`subscription`, licensed): clients use HTTP multipart only (`Accept: multipart/mixed;subscriptionSpec="1.0"`, heartbeats). The router does not accept client WebSocket connections.
- Subgraph subscription modes: `mode.passthrough` (WebSocket to subgraph with `path`, `heartbeat_interval`, `protocol`) and `mode.callback` (HTTP callback protocol: `public_url`, `listen`, `path`, `heartbeat_interval`, per-subgraph list). Modes can be mixed per subgraph.
- Passthrough `protocol` values: `graphql_ws` (default, the modern `graphql-ws` library, sends WebSocket subprotocol `graphql-transport-ws`) and `graphql_transport_ws` (legacy `subscriptions-transport-ws`, sends subprotocol `graphql-ws`). The config names are the reverse of the wire subprotocol names (`apollo-router/src/protocols/websocket.rs`).
- HTTP callback protocol: router POSTs the subscription with `extensions.subscription { callbackUrl, subscriptionId, verifier, heartbeatIntervalMs }`. The emitter (often the subgraph) POSTs `check`, `next`, `complete` messages to the callback URL. Apollo Server implements it via a plugin.
- Subscription options: `deduplication` (per subgraph, `ignored_headers`, `ignore_auth_context` 2.15), `max_opened_subscriptions`, `queue_capacity`, `max_lifetime` (2.15), termination on schema update, WebSocket auth via `connectionParams` from headers, reconnect on subgraph drop (`max_reconnect_attempts`, `reconnect_delay`, 2.18). Metrics for termination reasons.
- `@policy` with subscriptions: events re-enter at the execution service, so authorization is not re-planned per event.
- Docs have guides for running subscriptions behind AWS API Gateway, Azure APIM, Apigee, MuleSoft, Kong.
- File uploads (`preview_file_uploads`, preview): GraphQL multipart request spec. `protocols.multipart.mode: stream` only (no buffering, files must be in order and not nested). `limits.max_file_size`, `limits.max_files`. `operation_body_timeout` (2.15). Router forwards the multipart request to the subgraph. Not supported with `@defer`, subscriptions, or batching.
- Query batching (`batching`, licensed): client sends a JSON array (`mode: batch_http_link`). `maximum_size` (2.1). Subgraph batching (`batching.subgraph`) sends one batched HTTP request per subgraph. Not supported for `@defer` or subscriptions.
- Introspection: answered by the router itself. Off by default.
- Response validation: the router validates and coerces subgraph data to the schema. `supergraph.enable_result_coercion_errors` (2.8) reports coercion errors.
- `supergraph.early_cancel`: keep or stop subgraph work when the client disconnects. `connection_shutdown_timeout` for graceful shutdown.
- Error codes (`extensions.code`): `GRAPHQL_PARSE_FAILED`/`PARSING_ERROR`, `GRAPHQL_VALIDATION_FAILED`, `GRAPHQL_UNKNOWN_OPERATION_NAME`, `SUBREQUEST_HTTP_ERROR`, `GATEWAY_TIMEOUT`, `REQUEST_LIMIT_EXCEEDED`, `MAX_DEPTH_LIMIT`, `MAX_HEIGHT_LIMIT`, `MAX_ALIASES_LIMIT`, `MAX_ROOT_FIELDS_LIMIT`, `COST_ESTIMATED_TOO_EXPENSIVE`, `COST_ACTUAL_TOO_EXPENSIVE`, `SUBGRAPH_COST_ESTIMATED_TOO_EXPENSIVE`, `UNAUTHORIZED_FIELD_OR_TYPE`, `QUERY_NOT_IN_SAFELIST`, `RESPONSE_VALIDATION_FAILED`, `CONNECTOR_FETCH`, `HTTP_CLIENT_ERROR`, `VALIDATION_INVALID_TYPE_VARIABLE`.

### Traffic shaping and resilience

- `traffic_shaping.router`: `timeout` (default 30s), `global_rate_limit` (`capacity`, `interval`), `concurrency_limit` (none by default).
- `traffic_shaping.all` / `subgraphs.<name>` / `connector.all` / `connector.sources.<name>`: `timeout`, `global_rate_limit`, `compression` (`gzip`, `br`, `deflate`), `deduplicate_query` (merge identical in-flight subgraph queries, on by default), `experimental_http2` (`enable`, `disable`, `http2only`), HTTP/2 keep-alive pings, `pool_idle_timeout` (2.13), `dns_resolution_strategy`.
- Variable deduplication of `_entities` representations is always on. The `deduplicate_variables` option was removed on the v3 branch.
- Fixed execution order: prepare request, variable dedup, query dedup, rate limit, timeout, and so on.
- Circuit breaking: not built in for 2.x. Docs recommend a service mesh (Istio, Envoy). The v3 preview branch adds circuit breaking for subgraphs and connectors (PR #10300).
- No built-in retries for subgraph requests in the 2.x docs. I found none in the traffic shaping code.
- `headers` plugin: per subgraph or `all`, rules `propagate` (`named`, `matching` regex, `rename`, `default`), `remove`, `insert` (static `value`, `from_context`, `path` from request body). Fixed rule order. Response header propagation and subgraph-to-subgraph propagation need Rhai or coprocessor.
- `override_subgraph_url`: change subgraph URLs from config (for example per environment).
- Health check (`health_check`): `/health` on port 8088 by default. `?ready` and `?live` for Kubernetes. `readiness.allowed` and `interval` to mark unready on overload.
- Kubernetes Helm chart in repo (`helm/chart/router`). Docker images. Guides for AWS, Azure, GCP, Railway, Render.

### Telemetry and observability

- OpenTelemetry native. Traces, metrics, logs. Exporters: OTLP (gRPC and HTTP), Prometheus (metrics endpoint), Datadog, Zipkin, Jaeger (via OTLP), New Relic, Dynatrace guides. stdout logs with `text` or `json` format, `rate_limit`, `tty_format`.
- Trace propagation formats: W3C `trace_context`, `baggage`, `jaeger`, `zipkin`, `datadog`, AWS X-Ray, custom trace ID header. Datadog cannot mix with others (except baggage).
- `sampler` global and per exporter (2.16). `preview_datadog_agent_sampling`. `experimental_response_trace_id` returns the trace ID in a response header.
- Custom instrumentation in YAML: `instruments` (counters, histograms on any stage), `spans` (custom attributes, `mode`), `events` (custom log events on request, response, error), `conditions` (`eq`, `exists`, `all`, `any`, `not`). Selectors read headers, context, operation name, query, cost, response body, errors, cache status, `is_deferred`, and more.
- Standard instruments: `http.server.request.duration`, `http.server.active_requests`, `http.client.request.duration`, plus `apollo.router.*` (query planning duration, cache hit/miss/size, compute job queue, subscriptions, batching, coprocessor and Rhai durations, `apollo.router.overhead`, `apollo.router.graphql_error`, limit exceeded counters, uplink, OCI, Redis, memory).
- Metric cardinality controls: max cardinality per metric (2.16), rename metrics (2.8), header masking in telemetry and logs (2.16).
- GraphOS reporting: usage reporting (operation signatures, field usage), field-level traces from subgraph FTV1 (`field_level_instrumentation_sampler`), extended references (input and enum value usage), client awareness via `apollographql-client-name` / `apollographql-client-version` headers or client library name and version in request `extensions` (2.2, I did not check the exact key). `enhanced_client_awareness` plugin (2.11), `send_headers`, `send_variable_values`, error reporting with redaction, OTLP-based GraphOS tracing. Persisted query usage by ID.
- Client ID enforcement guide: reject requests without a client name via Rhai or coprocessor.
- `experimental_diagnostics`: web dashboard for heap profiling, config and schema dump, system info export.

### Configuration, deployment and lifecycle

- CLI: `--config`/`-c`, `--supergraph`/`-s`, `--hot-reload`/`--hr`, `--dev` (hot reload, introspection, sandbox, expose query plan, include subgraph errors), `--log`, `--listen`, `--license`, `--apollo-key-path`, `--apollo-uplink-endpoints`, `--apollo-uplink-timeout`, `--graph-artifact-reference`, `--anonymous-telemetry-disabled`. Subcommands `router config schema`, `router config upgrade`, `router config validate` (2.1).
- Env vars: `APOLLO_KEY`, `APOLLO_KEY_PATH`, `APOLLO_GRAPH_REF`, `APOLLO_ROUTER_CONFIG_PATH`, `APOLLO_ROUTER_SUPERGRAPH_PATH`, `APOLLO_ROUTER_SUPERGRAPH_URLS`, `APOLLO_ROUTER_HOT_RELOAD`, `APOLLO_ROUTER_LOG`, `APOLLO_ROUTER_LISTEN_ADDRESS`, `APOLLO_ROUTER_LICENSE(_PATH)`, `APOLLO_UPLINK_ENDPOINTS`, `APOLLO_UPLINK_TIMEOUT`, `APOLLO_GRAPH_ARTIFACT_REFERENCE`, `APOLLO_TELEMETRY_DISABLED`.
- Schema sources: local supergraph file (hot reload), URL list, Apollo Uplink (managed federation, polls GraphOS), OCI graph artifacts (2.x, reload on tag change since 2.11).
- The router does not compose. It needs a pre-composed supergraph SDL (from `rover supergraph compose` or GraphOS). Dynamic composition from `_service { sdl }` at runtime is not supported by the Router (it was a feature of `@apollo/gateway` `IntrospectAndCompose`).
- Config auto-migration on minor upgrades (2.2). JSON schema for config (`router config schema`) for IDE validation.
- `sandbox` (Apollo Sandbox UI) and `homepage` (landing page) settings. Sandbox needs introspection on.
- `fleet_detector`: private plugin that reports anonymous deployment info. `--anonymous-telemetry-disabled` turns off anonymous usage data.
- jemalloc allocator on Linux and macOS.
- Federation version support table: router 2.x supports Fed 1 and Fed 2 supergraphs.
- Migration guides: from `@apollo/gateway`, from router v0 and v1.

### Connectors (REST via `@connect` / `@source`)

- Declarative REST integration in a subgraph schema. No server code. The router calls the REST API directly. Spec `https://specs.apollo.dev/connect/v0.x`. Docs at https://www.apollographql.com/docs/graphos/connectors (not in the router repo).
- `@source(name:, http: { baseURL, headers }, errors:)` on the schema: shared base URL and headers.
- `@connect(source:, http: { GET | POST | PUT | PATCH | DELETE: "/path/{$args.id}", headers, body }, selection:, entity:, batch: { maxSize }, errors: { message, extensions }, isSuccess:)` on fields of `Query`, `Mutation`, or object types. `entity: true` makes a `Query` field an entity resolver. Since 0.2 `@connect` on types resolves entities.
- Selection mapping language (`JSONSelection`): field picking, aliasing, paths, literals, `->` methods. Public methods in code: `as`, `echo`, `map`, `match`, `first`, `last`, `slice`, `size`, `entries`, `jsonParse`, `jsonStringify`, `joinNotNull`, `filter`, `find`, `get`, `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`, `not`, `and`, `or`, `add`, `sub`, `mul`, `div`, `mod`, `toString`, `parseInt`, `keysToCamelCase`, `keysToCamelCaseDeep`, `split`, `trim`, `trimStart`, `trimEnd`, `withWarning`, `withError`. Non-public in code: `matchIf`, `typeof`, `has`, `keys`, `values`. Docs do not list `as`, `withWarning` or `withError` (`withError` added in .changesets).
- Variables: `$args`, `$this`, `$batch`, `$config`, `$context`, `$env` (0.3), `$request.headers`, `$response.headers`, `$status`, `$`, `@`. Nullish coalescing `??` and `?!` (0.3).
- Batching: `$batch` sends one request for many entities (repeated query params, comma lists, JSON body, composite keys). `batch.maxSize`.
- Error handling: default maps non-2xx to errors. Customize `errors.message`, `errors.extensions`, and `isSuccess` to decide success.
- Non-JSON responses supported (2.3). Abstract types (interfaces, unions) and `@interfaceObject` since `connect/v0.4`. Virtual connectors (`@connect` without `http`, 2.15) map literal or context data with no request.
- Router config `connectors.sources.<subgraph.source>`: override `$config`, base URL, headers, TLS, traffic shaping, auth (SigV4), `max_requests_per_operation_per_source`, `debug_extensions` (request and response debug info in `extensions`), `expose_sources_in_context`.
- Spec versions: `connect/v0.1` (Fed 2.10), `v0.2` (Fed 2.11), `v0.3` (Fed 2.12), `v0.4` (Fed 2.13, no longer preview in 2.18), `v0.5` preview (Fed 2.16/3.0, opt-in `preview_connect_v0_5`, validates response shape).
- Limitations: no subscriptions, no circular references, no `@context`/`@fromContext`, `@override` only from resolver subgraphs to connector subgraphs, no coprocessor or Rhai `subgraph` hook (coprocessor `connector` stage exists since 2.12). The limitations page still says no entity caching. The `.changesets` add response caching for connectors.
- Connector library examples: OpenAI, Anthropic, AWS DynamoDB, AWS Lambda, Stripe, Strapi, OData, gRPC via JSON transcoding.

### Undocumented or lightly documented features (found in source)

- `experimental_mock_subgraphs` (private plugin): return static mock responses and headers per subgraph from config.
- `experimental.record` plugin (`record_replay`): record requests and subgraph traffic to a directory for later replay.
- `experimental.expose_query_plan`: header `Apollo-Expose-Query-Plan: true | dry-run`. Documented only in passing.
- `experimental_hoist_orphan_errors`: move errors without a valid path up to a parent path.
- `experimental_chaos`: forced config and schema reload for testing. Removed on the v3 branch.
- `experimental_diagnostics`: memory profiling dashboard.
- `forbid_mutations`: one-line read-only switch. Only in the config reference.
- `experimental_log_on_broken_pipe`.

### Not supported

- Client-facing WebSocket subscriptions. Only multipart HTTP.
- `@stream`.
- Runtime composition from subgraph `_service` SDL. Composition is done ahead of time by Rover or GraphOS.
- Built-in circuit breaking in 2.x (coming in v3).
- `@defer`, subscriptions and file uploads inside a query batch.
- Federation 1 `@apollo/gateway` features like `IntrospectAndCompose` and `RemoteGraphQLDataSource`. They exist only in the JS gateway.

### Upcoming (v3.0.0-preview.0 and `.changesets`)

- Federation `v3.0` spec (replaces unreleased `v2.16`). GraphQL 2025 spec `@deprecated` compat shim. `@oneOf` merging in composition. Contract filtering in Rust.
- Incremental query planner (BULB search), native connector planning.
- Built-in circuit breaking for subgraphs and connectors.
- Plugin config declared with `apollo-configuration` crate. Unknown config keys rejected. `authentication.router.jwt.on_error` values become snake_case.
- Removals: `experimental_chaos`, `failfast` feature, `connectors.subgraphs` config, `traffic_shaping.deduplicate_variables`, legacy Apollo protobuf trace export path, license rate limiting.
- In `.changesets` for next 2.x: response caching for connectors, `->withError` mapping method, connectors public plugin, subgraph deduplication request metric, global condition resolver cache.

## Sources

Repos (shallow clones in `/tmp`):
- https://github.com/apollographql/router at `/tmp/apollo-router` (`dev`, `ebcecb3`, 2026-10-08). Read `CHANGELOG.md` (feature headings 2.1 to 2.17), `.changesets/`, `docs/source/routing/**` (171 pages, mostly headings plus key sections), `docs/shared/config/*`, `apollo-router/src/plugins/*` (plugin registry), `apollo-router/src/plugin/mod.rs`, `apollo-router/src/uplink/license_enforcement.rs`, `apollo-router/src/configuration/snapshots/apollo_router__configuration__tests__schema_generation.snap` (config key list), `apollo-router/src/services/layers/persisted_queries/manifest.rs`, `apollo-federation/src/link/*_spec_definition.rs`, `apollo-federation/src/merger/merger.rs`, `apollo-federation/src/connectors/spec/mod.rs`, `apollo-federation/src/connectors/json_selection/methods.rs`.
- https://github.com/apollographql/federation at `/tmp/apollo-federation` (`main`, `b95c124`, 2026-08-18). Read `docs/source/schema-design/federated-schemas/reference/subgraph-spec.mdx`, `directives.mdx`, `versions.mdx`, `compatible-subgraphs.mdx`, `subgraph-specific-fields.mdx`, `entities/migrate-fields.mdx` (progressive override), `query-plans.mdx` (condition nodes), `README.md`, `subgraph-js/`.
- https://github.com/apollographql/apollo-federation-subgraph-compatibility at `/tmp/apollo-federation-subgraph-compatibility` (`f9520a4`, 2026-09-29). Read `SUBGRAPH_GUIDE.md`, `packages/compatibility/src/tests/*`, `implementations/_template_library_/products.graphql`.

Docs:
- https://www.apollographql.com/docs/graphos/routing (source in router repo `docs/source/routing`).
- https://www.apollographql.com/docs/graphos/reference/federation/subgraph-spec, https://www.apollographql.com/docs/graphos/reference/federation/directives, https://www.apollographql.com/docs/graphos/reference/federation/versions, https://www.apollographql.com/docs/graphos/reference/federation/compatible-subgraphs (source in federation repo).
- llms.txt: https://www.apollographql.com/docs/graphos/routing/llms.txt (200, text/plain), https://www.apollographql.com/docs/graphos/llms.txt (200), https://www.apollographql.com/docs/graphos/connectors/llms.txt (200), https://www.apollographql.com/llms.txt (200). Adding `.md` to a docs URL returns markdown.
- Connectors docs fetched as markdown (not in any cloned repo): https://www.apollographql.com/docs/graphos/connectors/reference/directives.md, `reference/changelog.md`, `reference/limitations.md`, `reference/preview-features.md`, `mapping/methods.md`, `mapping/variables.md`, `mapping/virtual-connectors.md`, `requests/batching.md`, `requests/grpc-json-bridge.md`, `responses/error-handling.md`, `getting-started/version-requirements.md`. Saved in `/tmp/apollo-router-docs-dl`.

Releases:
- GitHub API releases for `apollographql/router` (`v2.18.0` 2026-09-30, `v3.0.0-preview.0` 2026-10-03, `v2.16.4` 2026-09-24) and the compare `v2.18.0...v3.0.0-preview.0` commit list. PR descriptions #10283, #10029, #10124.
- GitHub API releases for `apollographql/federation` (`@apollo/subgraph@2.14.4` 2026-08-18). npm registry `@apollo/subgraph` dist-tags (`latest` 2.15.1, 2026-09-14).
