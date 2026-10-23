# WunderGraph Cosmo findings

Version checked: monorepo `wundergraph/cosmo` `main` at `1473af4` (2026-10-09). Releases are per component, not one version.
Latest releases: `router@0.357.0` (2026-10-07), `controlplane@0.253.2` (2026-10-07), `wgc@0.132.3` (2026-10-06), `studio@0.183.0` (2026-10-06), `router-plugin@0.9.1` (2026-10-06), `@wundergraph/protographic@0.24.17` (2026-10-06), `graphqlmetrics@0.43.1` (2026-10-06), `helm-cosmo@0.21.0` (2026-10-06), `aws-lambda-router@0.43.0` (2026-09-25), `cdn@0.22.0` (2026-09-25). `@wundergraph/composition` package is `0.65.2`.
Very active. Several releases each week. Router is still `0.x`.
Stack: Router is Go (engine is `graphql-go-tools`). Control plane, CLI (`wgc`), composition and Studio are TypeScript.
License: Apache 2.0 for the whole repo, router included. Paid features are enforced by the control plane (Cosmo Cloud) plan, not by a router license key. Compare Apollo: router under ELv2 with license-gated features.
Apollo Router / Federation is in `apollo-router-federation.md`. This file records only where Cosmo differs from it or adds to it.

## Product parts

- `router`: Go federation gateway. Loads an execution config from the CDN, a file, S3 or the control plane. Runs without the control plane after it has a config.
- `controlplane`: Platform API (for `wgc` and Studio) and Node API (for routers). Connect RPC (protobuf) APIs. Stores graphs, schemas, checks, compositions.
- `cdn-server`: serves signed router configs and persisted operations. Router only depends on this at runtime.
- `graphqlmetrics`: Go collector for schema field usage. Feeds ClickHouse. Used by traffic-based breaking change checks.
- `otelcollector`: OTEL collector for router traces and metrics into ClickHouse.
- `studio`: Next.js web UI.
- `cli` (`wgc`): CLI for everything in the control plane, plus local tooling (compose, plugin build, router download).
- `composition`: TypeScript composition library (`@wundergraph/composition`). Open source replacement for Apollo composition. Used by control plane and `wgc router compose`.
- `protographic`: converts GraphQL SDL to protobuf and back. Used by gRPC subgraphs and Connect RPC.
- `router-plugin`: Go library for gRPC router plugins.
- `aws-lambda-router`: router build for AWS Lambda.
- `admission-server`: example webhook for router config validation and signing.
- `keycloak`: auth for the control plane and Studio. SSO and SCIM go through it.
- `helm`, `docker-compose*.yml`, `infrastructure`: full self-hosting.
- Stores: PostgreSQL (records), Redis (queues, cron, cache), ClickHouse (analytics), S3 or compatible (blob storage, persisted operations, configs).
- "Monograph": a single non-federated GraphQL API managed by Cosmo (schema checks, analytics, router as proxy). Supported in `wgc monograph *`.

## Plans and paid features

Pricing page (https://wundergraph.com/pricing) lists plans `Developer` (free), `Launch` ($499/month), `Scale` (custom), `Enterprise` (custom). All plans use a self-hosted router.
- Limits per plan: users, federated graphs or monographs (1 / 2 / 5 / custom), subgraphs (10 / 20 / ...), requests per month (10M / 250M / 1B), data retention (7 / 14 / 30 days), breaking change detection window, feature flags (1 on Developer and Launch), plugins (3 / 10).
- Not in Developer or Launch: Rate Limiting, Persisted Operations, Runtime Health Metrics, Multi OTEL Exporter, Cache warming, SSO, SCIM, RBAC, Subgraph Check Extensions, email or Slack support, SLAs.
- In every plan: Federation v1 and v2, JWT/JWKS, federated subscriptions, Prometheus, OTEL tracing, Advanced Request Tracing (ART), EDFS, request deduplication ("Ludicrous Mode: Singleflight"), Cost Control.
- Control plane feature IDs (code, `controlplane/src/types/index.ts`): limits `users`, `federated-graphs`, `analytics-retention`, `tracing-retention`, `changelog-retention`, `breaking-change-retention`, `trace-sampling-rate`, `requests`, `feature-flags`, `persisted-operations`. Boolean `ai`, `cache-warmer`, `composition-ignore-external-keys`, `field-pruning-grace-period`, `login-method-restrictions`, `oidc`, `plugins`, `proposals`, `rbac`, `scim`, `security`, `sso`, `subgraph-check-extensions`, `support`, `split-config-loading`, `prompt-to-query`.
- Docs mark these as plan features: Groups and RBAC (Scale plan and up), login method restrictions for organization and namespace (Enterprise), cache warmer (Enterprise), schema usage check period for graph pruning (Enterprise).
- The router code does not check a license. Rate limiting, persisted operations safelist and so on run in an OSS self-hosted setup without a plan. I think the pricing table refers to Cosmo Cloud features (for example uploading persisted operations to the CDN). Not verified against a live account.
- Router features gated by graph token claims (code, `router/internal/jwt/claims.go`): `prompt-to-query` (MCP `generate_query` tool). `split-config-loading` changes how the control plane builds configs.
- Cosmo Dedicated Cloud (Enterprise): isolated single-tenant Cosmo Cloud on AWS, GCP or Azure. Air-gapped option. Custom release cycles.
- Cosmo AI (Cosmo Cloud only, `ai` feature): LLM-generated documentation and other non-production helpers in Studio.

## Router: configuration and lifecycle

- Config: one YAML file (`config.yaml`), JSON schema in `router/pkg/config/config.schema.json` for IDE completion. Most keys also have an env var (for example `RATE_LIMIT_SIMPLE_RATE`). YAML wins over env vars.
- Multiple config files merged in order: `--config base.yaml --config dev.yaml` or `CONFIG_PATH=a.yaml,b.yaml`. Last wins. Lists are replaced, not merged. Each file and the merged result are schema-validated. Since 0.221.0.
- `${ENV}` interpolation inside YAML. `.env` file plus `OVERRIDE_ENV` file.
- `watch_config` (`enabled`, `interval`, `startup_delay`): hot reload of the router config files. `.env` changes need a restart.
- Execution config (the composed supergraph plus subgraph URLs, JSON, protobuf-shaped `RouterConfig`) sources: Cosmo CDN polling (default, `poll_interval` 15s with `poll_jitter`), control plane, S3 storage provider, or local file (`execution_config.file.path`, `watch`, `watch_interval`). Compressed config files supported.
- `execution_config.split_config_poller`: split router config (one file per feature flag) for big graphs. Needs plan feature `split-config-loading` in the graph token. `skip_missing_feature_flags`, `ignored_feature_flags`. `wgc router compose --split-configs-enabled` does the same locally.
- Config hot swap: on new execution config the router builds a new graph server and drains the old one. All subscriptions are closed on swap. Plan cache starts empty (see cache warmer).
- `graph.token` (`GRAPH_API_TOKEN`): JWT from `wgc router token create`. Router self-registers with the control plane on start (key exchange for ART).
- Config signing: `graph.sign_key`. Control plane calls an admission webhook (`--admission-webhook-url`, `--admission-webhook-secret` on the federated graph) at `/validate-config` after each composition. The webhook fetches the config from `privateConfigUrl`, validates it and returns an HMAC-SHA256 signature. Router rejects configs whose hash does not match. Example server in `admission-server/` (Hono). Since 0.74.0.
- `overrides.subgraphs.<name>` (`routing_url`, `subscription_url`, `subscription_protocol` `ws`/`sse`/`sse_post`, `subscription_websocket_subprotocol`): override subgraph config per router. Old `override_routing_url` is deprecated.
- `dev_mode: true`: pretty logs, ART without signed token, subgraph status codes in errors. Not for production.
- `demo_mode`: router serves a built-in demo graph without a token.
- Health: `health_check_path` (`/health`), `liveness_check_path` (`/health/live`), `readiness_check_path` (`/health/ready`). `shutdown_delay`, `grace_period` for graceful shutdown.
- `localhost_fallback_inside_docker`: rewrites `localhost` subgraph URLs inside Docker.
- `tls.server` (TLS and HTTP/2, mTLS client auth with `client_auth`), `tls.client` (mTLS to HTTP subgraphs, global and per subgraph), `tls.client_grpc` (TLS/mTLS to gRPC subgraphs).
- `cors` with `allow_origins`, `match_origins` (regex), custom URL schemes, `allow_credentials`, `max_age`.
- `graphql_path`, `playground` (`enabled`, `path`): built-in GraphiQL-based playground. `introspection.enabled` and `introspection.secret`.
- `concurrency_limit`, `engine.max_concurrent_resolvers`: global request concurrency.
- `cluster.name`, `instance_id`: identify router fleet in Studio.
- `client_header.name` and `client_header.version`: custom headers for client identification. Default headers are `graphql-client-name` and `graphql-client-version`. Apollo headers `apollographql-client-name`/`-version` also read.
- `query_plans_enabled`: allow `X-WG-Include-Query-Plan` header. `X-WG-Skip-Loader` returns the plan without calling subgraphs. `X-WG-Disable-Tracing` skips tracing.
- `./router query-plan` CLI (since 0.185.0): batch-generate query plans for a folder of operations against an execution config. `-print-report`, `-fail-on-error`, `-print-format json`, `-enable-multi-fetch`, `-enable-schedule-fetches`. Used by `check_query_planner` in CI.
- Engine flags of note: `enable_single_flight` (subgraph request dedup), `enable_inbound_request_deduplication` (dedup identical client requests), `enable_multi_fetch` (merge entity fetches to the same subgraph in one wave into one aliased `_entities` request), `enable_schedule_fetches` (dependency-aware fetch scheduler instead of waves), `minify_subgraph_operations`, `enable_subgraph_fetch_operation_name`, `disable_variables_remapping`, `execution_plan_cache_size`, `normalization_cache_size`, `validation_cache_size`, `operation_hash_cache_size`, `enable_defer`, `allow_string_literals_for_enums`, `relax_subgraph_operation_field_selection_merging_nullability`, `validate_required_external_fields`, `enable_require_fetch_reasons`, `enable_grpc_wire_encoding`, `enable_net_poll` (epoll WebSocket server).
- `engine.debug`: print query plans, planning paths, `always_include_query_plan`, `enable_cache_response_headers` (`X-WG-Execution-Plan-Cache`, `X-WG-Normalization-Cache`, `X-WG-Persisted-Operation-Cache`, `X-WG-Variables-Normalization-Cache`, `X-WG-Variables-Remapping-Cache` hit/miss headers).
- `allow_string_literals_for_enums`: opt-in spec deviation. Accepts `"VALUE"` where an enum literal is expected.
- `relax_subgraph_operation_field_selection_merging_nullability`: allow same-named fields with different nullability across non-overlapping union members.
- `apollo_compatibility_flags` (`enable_all`, `value_completion`, `truncate_floats`, `suppress_fetch_errors`, `replace_undefined_op_field_errors`, `replace_invalid_var_errors`, `replace_validation_error_status`, `subscription_multipart_print_boundary`, `use_graphql_validation_failed_status`) and `apollo_router_compatibility_flags` (`replace_invalid_var_errors`, `subrequest_http_error`, `skip_null_variables_error`): match Apollo Gateway or Apollo Router error shapes and status codes for migration.
- Distribution: binaries per release, Docker image (also nonroot image), Helm chart, AWS Lambda build (`aws-lambda-router`), custom builds with Go modules.
- Profiling: `PPROF_ADDR` pprof server. Continuous profiling with Grafana Pyroscope (`pyroscope` block). Flight recorder custom module example (trace on slow requests).

## Router: template expressions

- Language: expr-lang (`github.com/expr-lang/expr`). Read-only, compiled and type-checked at startup.
- Used in: `security.block_*.condition`, header rules (`expression`), router response headers, access log fields, telemetry and metric attributes, rate limit `key_suffix_expression`, retry `expression`, response cache `private_id`, feature flag selection, MCP and others. Not a general concept. Only some keys accept expressions.
- Context: `request.method`, `request.url.*`, `request.header.Get()`, `request.body.raw` (lazy), `request.trace.sampled`, `request.error`, `request.client.name/version`, `request.auth.isAuthenticated/type/claims/scopes`.
- `request.operation.*`: `name`, `type`, `hash`, `queryPlanHash`, `sha256Hash`, `persistedId`, parse/normalize/validate/plan timings, `resolverAcquireDuration`, cache hit flags (`planCacheHit`, `normalizationCacheHit`, `persistedOperationCacheHit`, ...), `queryDepth`, `queryTotalFields`, `queryRootFields`, `queryRootFieldAliases`, `variables` (lazy JSON).
- `subgraph.*` (in subgraph-scoped expressions): `id`, `name`, `request.error`, `request.startTime`, `request.clientTrace.*` (DNS, TCP, TLS, time to first/last byte), `response.header.Get()`, `response.body.raw`, `response.cache.status/storeDecision/lookupDuration/entityType`.
- `response.body.raw`, `response.cache.status` in router access logs.

## Router: customization

- Custom modules: Go code compiled into a custom router binary. Register with `core.RegisterModule(&MyModule{})` and `core.ModuleInfo{ID, Priority, New}`. Config from YAML `modules.<id>` via `mapstructure` tags.
- Hooks (interfaces in `router/core/modules.go`):
  - `core.RouterOnRequestHandler` (`RouterOnRequest`): runs before tracing and auth. Since 0.188.0.
  - `core.RouterMiddlewareHandler` (`Middleware`): after auth and operation parsing, before execution.
  - `core.EnginePreOriginHandler` (`OnOriginRequest`): before each subgraph request. Can return a mock `*http.Response` to short-circuit. Runs concurrently per fetch.
  - `core.EnginePostOriginHandler` (`OnOriginResponse`): after each subgraph response.
  - `core.Provisioner` (`Provision(*ModuleContext)`) and `core.Cleaner` (`Cleanup`): lifecycle.
  - `core.TracePropagationProvider` (`TracePropagators()`): add custom OTEL propagators. Not in the custom modules doc page.
  - `core.SpanNameFormatterProvider` (`WrapSpanNameFormatter`): customize span names, chained by priority. Since 0.316. Not in the custom modules doc page.
  - Cosmo Streams hooks: `SubscriptionOnStartHandler`, `SubscriptionOnCreateHandler`, `StreamReceiveEventHandler`, `StreamPublishEventHandler`, `StreamBeforeEventsDispatchHandler`. See EDFS section.
  - Cache warmer: `CacheWarmupSource`, `CacheWarmupProcessor` interfaces.
- `core.RequestContext` API: `Operation()` (`Name`, `Type`, `Hash`, `Content`, `Sha256Hash`, `Variables`, `QueryPlanStats()` with `SubgraphFetches` and `SubgraphFieldsFetches`, `Timings()`, cost values), `SetForceSha256Compute()`, `ActiveSubgraph(req)`, `Authentication()` (`Claims()`, `SetScopes()`), `SetAuthenticationScopes()`, `Set/Get` shared values, `Logger()`, `Error()`, `ResponseWriter()`.
- `core.WriteResponseError(ctx, err)`: GraphQL-shaped error with tracing and metrics.
- Custom value renderer via module: rewrite field values in the response (data masking, "Advanced Data Privacy").
- Custom response writers must implement `http.Flusher` for subscriptions.
- Examples: `router/cmd/custom`, `router/cmd/custom-jwt`, repo `wundergraph/router-examples`.
- ADR `adr/custom-modules-v1.md` (accepted, not yet built): planned "module system v1" with `RouterRequestHook`, `RouterResponseHook`, `SubgraphRequestHook`, `SubgraphResponseHook`, `ApplicationStartHook`, `GraphServerStartHook`, `AuthenticationHook`, `AuthorizationHook`, telemetry hooks. Docs say it comes in the next major router release.
- No scripting language (no Rhai, no external coprocessor). Compare Apollo: Rhai scripts and HTTP coprocessors. Cosmo uses Go modules or gRPC plugins.

## Router: security

- Authentication: `authentication.jwt.jwks[]` with `url`, `secret` (symmetric), `algorithms`, `refresh_interval`, `audiences`, OIDC discovery (`.well-known/openid-configuration`), `refresh_unknown_kid` (`burst`, `interval`, `max_wait`). `header_sources` (header name plus `value_prefixes`, multiple sources). `scope_claim` for custom scope claim names (`scp`, `roles`). Symmetric keys and empty `alg` in JWKS allowed.
- `authentication.jwt.on_error: reject | continue`. `continue` ignores invalid tokens for modules or subgraphs to validate. Since 0.354.
- `authentication.ignore_introspection` plus `introspection.secret`: bypass auth for introspection, optional shared secret.
- `authorization.require_authentication`, `reject_operation_if_unauthorized` (default nulls unauthorized fields and adds `missingScopes` extension), `enable_pre_fetch_field_authorization` (check all `@authenticated`/`@requiresScopes` fields before any fetch).
- Authorization directives: only `@authenticated` and `@requiresScopes`. `@policy` is supported in composition but I found no router enforcement (no policy hook). Scopes can be set from a module.
- WebSocket auth: from upgrade headers, or from `connection_init` payload (`websocket.authentication.from_initial_payload` with `key`, `export_token`). `websocket.client_info_from_initial_payload`.
- `security.block_mutations`, `block_subscriptions`, `block_non_persisted_operations`, `block_persisted_operations`: each with `enabled` and expression `condition`.
- `security.complexity_limits`: `depth`, `total_fields`, `root_fields`, `root_field_aliases`, each `enabled`, `limit`, `ignore_persisted_operations`. `mode: measure | enforce`. `ignore_introspection`. `complexity_calculation_cache`. `depth_limit` is deprecated. Since recent release a limit of `0` enforces 0 (breaking change).
- `security.parser_limits`: `approximate_depth_limit`, `total_fields_limit` (checked while parsing, before normalization).
- `security.operation_name_length_limit`.
- Cost control: `security.cost_control` (`enabled`, `mode: measure | enforce`, `max_estimated_limit`, `estimated_list_size`, `expose_headers`, `ignore_implementing_type_weights`). Implements the IBM cost spec with `@cost(weight: Int!)` (on types, fields, arguments, input fields, directive arguments) and `@listSize(assumedSize, slicingArguments, sizedFields, requireOneSlicingArgument)`. Dot paths in `slicingArguments` (`input.pagination.first`). Estimated cost from the query plan (counts entity and `@requires` fetches). Actual cost after execution from real list sizes. Headers `X-WG-Cost-Estimated`, `X-WG-Cost-Actual`. Metrics `router.graphql.operation.cost.estimated/actual`. Weights per subgraph. Since router 0.294.0, composition 0.54.0. Differences from IBM spec: integer weights, list size multiplies the type weight too.
- `engine.validate_inline_arguments`: detect literal argument values (not variables). Modes `permissive` (warn log, optional `extensions.inlineArguments`) and `strict` (reject). `include_persisted_operations`. Since 0.333.
- Rate limiting: `rate_limit` with Redis GCRA (`strategy: simple`, `rate`, `burst`, `period`). Applies to outgoing subgraph requests, not to client requests. `key_suffix_expression` (per claim or header), `simple_strategy.overrides[]` with regex `matching` per key, `exclude_subscriptions`, `error_extension_code`, `reject_exceeding_requests`, `hide_stats_from_response_extension`. Pricing page lists it as paid. The code does not gate it.
- Persisted operations, see Operations section.
- `compliance.anonymize_ip` (`enabled`, `method: redact | hash`). On by default.
- `headers.cookie_whitelist`: only forward listed cookies.
- File uploads on by default (`file_upload.enabled`, `max_file_size`, `max_files`).
- Config signing and admission webhook, see configuration section.
- Hardening guide lists: disable introspection, no dev mode, disable uploads, config signing, rate limiting, CORS, subgraph URL overrides, persisted operations, block unused operation types, TLS, log level.

## Router: caching

- Query plan cache (`execution_plan_cache_size`, TinyLFU), normalization, variables normalization, variables remapping, validation, operation hash, persisted operation and complexity caches. Hit or miss visible in expressions and in debug headers.
- Slow plan cache (`slow_plan_cache_size` 300, `slow_plan_cache_threshold` 100ms): keeps plans that were slow to build, protects them from eviction, and re-warms them after config reloads. Since 0.300.
- Cache warmer (`cache_warmup`: `enabled`, `source` (`cdn` or `filesystem`), `workers`, `items_per_second`, `item_delay`, `timeout`, `in_memory_fallback`): pre-plans operations before the router serves traffic. CDN source is built by Cosmo Cloud from P90 planning latency telemetry plus manual operations (`wgc router cache push`). Studio can recompute. CDN warmer is an Enterprise feature. In-memory fallback (slow plan cache) is free. Manifest of persisted operations also warms caches.
- Response cache (`response_cache`), labelled experimental and alpha. Since 0.343 (2026). Caches subgraph entity fetches (per entity and selection set) and root query fetches (whole answer keyed by operation and variables). Storage `redis` (Redis 7+, shared, `key_prefix`) or `memory` (`max_entries`, per replica).
  - Driven by subgraph `Cache-Control` response header: `no-store`, `no-cache`, `private`, `s-maxage`, `max-age`. `fallback_ttl` for headers with `public` etc. but no lifetime. Responses with GraphQL errors never cached.
  - Client request `Cache-Control: no-cache` (bypass read) and `no-store` (no write) are honored. Cannot be disabled.
  - `private_id` expression (for example `request.auth.claims.sub`) gives per-user or per-tenant cache partitions for `private` responses. SHA-256 hashed.
  - `Vary` response header support (one variant per header value set, up to 100 headers).
  - Per-subgraph config under `subgraphs.<name>` replaces `all` fully.
  - Cache tags: subgraph returns `extensions.apolloEntityCacheTags` (array per entity) or `extensions.apolloCacheTags` (flat). Same extension names as Apollo Router. Removed before the client sees the response.
  - Invalidation HTTP endpoint on a separate port (`invalidation.endpoint`, `listen_addr` default `localhost:5027`, `path` `/invalidation`, `shared_key` of 32+ chars). `POST` a JSON array of `{kind: subgraph | type | cache_tag}`. Returns `202 {"count": n}`. Indexes per `cache_tag`, `subgraph`, `type` can be switched off.
  - `cache_tag_header` (`Cache-Tag` or `Surrogate-Key`, delimiter, `max_bytes`): emits tags for CDN purging (Cloudflare, Fastly). Tags `subgraph-{name}`, `type-{subgraph}-{type}` and declared tags.
  - Limitations: a batch is a hit only if every entity is cached. Merged multi-fetches drop declared tags. Race: an entry written during invalidation can survive it.
  - Metrics `router.response_cache.*` and expression fields `subgraph.response.cache.*`.
- Entity cache directives (composition only, not documented): `@openfed__entityCache(maxAge: Int!, negativeCacheTTL: Int = 0, includeHeaders: Boolean = false, partialCacheLoad: Boolean = false, shadowMode: Boolean = false) on OBJECT`, `@openfed__cacheInvalidate on FIELD_DEFINITION` (evict returned entity after a mutation or subscription), `@openfed__cachePopulate(maxAge: Int) on FIELD_DEFINITION` (write returned entity into the cache), `@cacheTag(format: String!) repeatable on FIELD_DEFINITION | OBJECT`. Composition writes them to `EntityCachingConfiguration` in the router config proto (since composition release for router 0.326). The router Go code does not read `EntityCachingConfiguration` yet. I think this is the next step of the response cache. A proto comment also mentions an `@openfed__requestScoped` directive that does not exist yet.
- `cache_control_policy` (`enabled`, `value`, per subgraph): computes the most restrictive `Cache-Control` and `Expires` across all subgraph responses and sends it to the client. Errors force `no-store, no-cache, must-revalidate`. Response header rule algorithm `most_restrictive_cache_control` exists in code (`config.ResponseHeaderRuleAlgorithmMostRestrictiveCacheControl`) and the response cache doc names it. The JSON schema enum for `algorithm` lists only `first_write`, `last_write`, `append`. I think schema validation rejects it in YAML, so only `cache_control_policy` can enable it.
- APQ: `automatic_persisted_queries` (`enabled`, `cache.size`, `cache.ttl`, `storage` Redis `provider_id`, `object_prefix`). Apollo APQ protocol (`extensions.persistedQuery.sha256Hash`).
- Valkey works as a Redis replacement everywhere. Redis URLs accept pool and replica options (`read_from_replicas` style query params). Redis cluster supported.

## Router: operations and protocols

- GraphQL over HTTP: POST JSON, GET. `@oneOf` input objects (since 0.262). Operation and variable descriptions (September 2025 spec) used by MCP. `@deprecated` on arguments in introspection.
- Persisted operations ("trusted documents"): pushed with `wgc operations push` per federated graph and per client name (`graphql-client-name`). Manifest formats: Apollo persisted query manifest, Relay query map (array or object), plain `.graphql` files. Stored in the Cosmo CDN or a custom S3 storage provider. Router fetches single operations on demand and caches them.
  - Custom IDs (since 0.355): any 1 to 250 printable ASCII chars (no slashes). A 64-char lowercase hex ID must equal the SHA-256 of the body.
  - PQL manifest (`persisted_operations.manifest`, since 0.300): router loads all operations at start and polls for updates (also from S3). The manifest is authoritative. Unknown hashes rejected without CDN lookup. Warms caches.
  - Modes: allow all (default), `persisted_operations.log_unknown`, `persisted_operations.safelist.enabled` (match a full query body to a persisted hash), `security.block_non_persisted_operations` (with optional expression `condition`). Also `block_persisted_operations` and `persisted_operations.disabled`.
  - Delete operations in Studio (Clients page). Studio warns when the operation still gets traffic.
  - Pricing page lists Persisted Operations as a paid feature (`persisted-operations` limit in control plane). I think this limits pushing operations to Cosmo Cloud, not the router feature.
- Query batching (`batching`: `enabled`, `max_concurrency`, `max_entries_per_batch`, `omit_extensions`): JSON array of operations. Off by default and not recommended. Feature flag applies to the whole batch. Span attributes `wg.operation.batching.*`.
- File upload: GraphQL multipart request spec. Nested uploads and any variable name. Files are buffered to temp files by the router. I think the engine forwards them as multipart to the subgraph.
- `@defer` (`engine.enable_defer`, off by default, since 0.329 in 2026): Incremental Delivery spec draft (graphql-spec PR 1110), `multipart/mixed;incrementalSpec=v0.2`. Supports labels, `if`, nested and sibling fragments, lists, deferred entity fields from other subgraphs, `@requires` inside deferred fragments. `@stream` is not supported. Apollo Client 4.1 `GraphQL17Alpha9Handler` works.
- Subscriptions, client side: `graphql-ws` (`graphql-transport-ws`), legacy `subscriptions-transport-ws`, Absinthe (Phoenix) protocol with `websocket.absinthe_protocol` endpoint, SSE (GET and POST), multipart HTTP (Apollo style). `websocket.default_subprotocol` for clients without a protocol header.
- Subscriptions, subgraph side: `ws` (subprotocol `auto`, `graphql-ws`, `graphql-transport-ws`), `sse`, `sse_post`. Set per subgraph with `wgc subgraph create/update --subscription-protocol --websocket-subprotocol --subscription-url`. No HTTP callback protocol (Apollo has it).
- Subscription multiplexing: one upstream WebSocket per unique set of forwarded headers. Epoll/kqueue event loop. Router 0.313.0 "subscriptions overhaul": upstream error ends only that subscription, `complete` no longer sent after `error`, WebSocket option renames (`websocket_server_*` vs `websocket_client_*`).
- `websocket.forward_upgrade_headers`, `forward_upgrade_query_params`, `forward_initial_payload`: pass WebSocket upgrade data to subgraphs. Client `extensions` in subscribe payload forwarded to subgraph.
- All subscriptions closed on config hot reload. Clients must reconnect.
- Feature flags at request time: header `X-Feature-Flag: <name>` or cookie. The router keeps one graph per flag and switches per request. Local router compose also supports `feature_flags`/`feature_graphs`.
- Request deduplication: subgraph level (`enable_single_flight`, key: subgraph, request body, forwarded header hash) and inbound (`enable_inbound_request_deduplication`, identical client requests share one execution). Since 0.278.0 dedup moved to the engine layer. Headers set in `OnOriginRequest` are no longer in the dedup key.
- Header rules (`headers.all` / `headers.subgraphs.<name>`): request ops `propagate` (`named`, `matching` regex, `negate_match`, `rename`, `default`), `set` (`value`, `expression`, `from_file` with `refresh_interval`). Response ops `propagate` with `algorithm: first_write | last_write | append`, `set`. Router-level response headers with expressions (`headers.router.response`). Headers become gRPC metadata for Connect subgraphs.
- Client extensions forwarded: `extensions` in the request JSON go to subgraphs.
- Subgraph error propagation (`subgraph_error_propagation`): `mode: wrapped` (default, one generic error with subgraph errors under `extensions.errors`) or `pass-through`. `rewrite_paths`, `attach_service_name`, `default_extension_code` (`DOWNSTREAM_SERVICE_ERROR`), `allowed_extension_fields`, `allow_all_extension_fields`, `allowed_fields`, `omit_locations`, `omit_extensions`, `propagate_status_codes`. Fallback errors from non-JSON subgraph responses use the status code.
- Subgraph extension propagation (`subgraph_extension_propagation`: `enabled`, `allowed_extension_fields`, `algorithm: first_write | last_write`). Since 0.316.
- `@openfed__requireFetchReasons`: router sends `extensions.fetch_reasons` to the subgraph, telling it which client fields caused the fetch (`engine.enable_require_fetch_reasons`). Lets a subgraph know if a field was requested by the client or only by the router for `@requires`/keys.
- `@semanticNonNull(levels: [Int!]! = [0])`: accepted and composed.

## Router: traffic shaping and resilience

- `traffic_shaping.all` and `traffic_shaping.subgraphs.<name>`: `request_timeout`, `dial_timeout`, `response_header_timeout`, `expect_continue_timeout`, `tls_handshake_timeout`, `keep_alive_idle_timeout`, `keep_alive_probe_interval`, connection pool (`max_conns_per_host`, `max_idle_conns`). Subgraph config inherits from `all`.
- `traffic_shaping.router`: `max_request_body_size`, `max_header_bytes`, `decompression_enabled`, response compression min size.
- Retry (`retry`): `enabled`, `algorithm: backoff_jitter`, `max_attempts`, `interval`, `max_duration`, `expression` (retry context: `statusCode`, `error`, `IsTimeout()`, `IsHttpReadTimeout()`, `IsConnectionRefused()`, `IsConnectionReset()`, `IsConnectionError()`, `IsRetryableStatusCode()`). Only queries are retried. `Retry-After` honored on 429 when 429 retry is enabled.
- Circuit breaker (since 0.262 in 2025): per unique subgraph URL. Time-based sliding window (`num_buckets`, `rolling_duration`), `request_threshold`, `error_threshold_percentage`, `sleep_window`, `half_open_attempts`, `required_successful`, `execution_timeout`, `max_concurrent_requests`. HTTP 4xx/5xx do not count as failures. Metrics `router.circuit_breaker.state`, `.short_circuits`. Apollo Router 2.x has none (planned for v3).
- Subgraph rate limiting (see Security).

## Router: telemetry

- OpenTelemetry traces and metrics. Default exporter is Cosmo Cloud (`DEFAULT_TELEMETRY_EXPORTER`). Add more exporters (`http` or `grpc`) per signal. Multiple exporters is a paid feature in Cosmo Cloud pricing, not gated in code.
- Tracing: `sampling_rate`, `parent_based_sampler`, propagation (`trace_context`, `jaeger`, `b3`, `baggage`, `datadog`), `export_graphql_variables` (opt-in), `response_trace_id` header, `sanitize_utf8`, `with_new_root` options. Plan cache, normalize, validate, plan, fetch spans. Span error status rules documented. Unauthenticated request tracing option (0.316).
- Metrics: OTLP and Prometheus (`telemetry.metrics.prometheus`, own `listen_addr`, `exclude_metrics`, `exclude_metric_labels`, `exclude_scope_info`). Metrics log exporter prints metrics to logs (debug). Cardinality limit. Exemplars with trace IDs (`exemplar_filter`).
- Metric families: `router.http.requests`, `router.http.request.duration_milliseconds`, `router.http.requests.in_flight`, `router.http.requests.error`, request/response content length, `router.graphql.operation.planning_time`, cache stats (`router_graphql_cache_*`), engine (`router.engine.connections`, `.subscriptions`, `.triggers`, `.messages.sent`, `.resolvers.inflight`), `router.graphql.resolver.acquire_duration`, connection metrics (`router.http.client.*` DNS, TCP, TLS, first/last byte), `router.streams.received/sent.messages`, `router.response_cache.*`, `router.circuit_breaker.*`, cost metrics, `router_info` gauge with version, Go runtime metrics.
- Custom attributes (`telemetry.attributes`): `value_from.request_header`, `context_field` (`operation_sha256`, `operation_name`, `persisted_operation_sha256`, timings, ...), `expression`, static `default`. Applied to spans and metrics.
- Schema usage export: router sends field and argument usage per operation to `graphqlmetrics` (`graphql_metrics.enabled`, `collector_endpoint`). Also a Prometheus "schema usage lite" sink (`telemetry.metrics.prometheus.schema_usage`).
- Access logs (`access_logs`): stdout or file (`file.path`, `mode`), `buffer`, `level`, `add_stacktrace`, router and subgraph access logs (`subgraphs.enabled`), custom `fields` with `request_header`, `response_header`, `context_field`, `expression`. Redact query params. Log response payload via expression.
- `log_level`, `json_log`, `log_service_name`.
- Advanced Request Tracing (ART): header `X-WG-Trace: true` or `?wg_trace=true` returns a full execution trace (plan, fetches, inputs, outputs, timings) in `extensions.trace`. Options `exclude_output`, `exclude_input`, `exclude_planner_stats`, `exclude_load_stats`, `enable_predictable_debug_timings`. In production it needs a signed token issued by Studio (key exchanged at self-registration). `engine.debug.force_unauthenticated_request_tracing` bypasses it. Studio playground shows ART trees.
- Grafana dashboards and Docker compose example for Prometheus plus Grafana. Dynatrace and Prometheus OTLP ingestion guides. OTEL collector setup guide.
- PostHog usage telemetry in the router (added 0.262). I did not check how to opt out.

## Cosmo Streams (EDFS)

- Event-Driven Federated Subscriptions, renamed "Cosmo Streams". Router connects directly to NATS (incl. JetStream), Kafka or Redis Pub/Sub. Subgraphs stay stateless. No subgraph WebSocket.
- Event-Driven Graph (EDG): an abstract subgraph with no resolvers, created with `wgc subgraph create --edg` (alias `--event-driven-graph`). Only root fields with event directives plus entity stubs with `@key(..., resolvable: false)`. Other subgraphs resolve the rest of the entity.
- Directives (all have `providerId: String! = "default"` matching `events.providers.<kind>[].id`):
  - NATS: `@edfs__natsRequest(subject:)` on Query (request/reply), `@edfs__natsPublish(subject:)` on Mutation, `@edfs__natsSubscribe(subjects:, streamConfiguration: edfs__NatsStreamConfiguration)` on Subscription (`consumerName`, `streamName`, `consumerInactiveThreshold`).
  - Kafka: `@edfs__kafkaPublish(topic:)`, `@edfs__kafkaSubscribe(topics:)`.
  - Redis: `@edfs__redisPublish(channel:)`, `@edfs__redisSubscribe(channels:)`.
  - Publish mutations must return `edfs__PublishResult!` (`success: Boolean!`). Subscribe and request fields return a non-null entity.
- Argument templates in subjects/topics/channels: `employeeUpdated.{{ args.id }}`.
- `@openfed__subscriptionFilter(condition: openfed__SubscriptionFilterCondition!)`: filter events per subscriber with `AND`/`OR`/`NOT`/`IN` conditions on `fieldPath` and `values`, values may use `{{ args.x }}`. Needs `engine.disable_variables_remapping` for variables.
- Triggers are shared between subscribers of the same topic (dedup).
- Provider config: NATS (`url`, auth token or user/password, TLS since 0.311), Kafka (`brokers`, SASL plain and SCRAM, TLS, topic templates), Redis (`urls`, cluster). `events.skip_unavailable_providers`. Remove NATS consumers on shutdown option.
- Stream hooks (custom modules): `SubscriptionOnCreateHandler` (experimental, change event config before register), `SubscriptionOnStartHandler` (auth checks, initial event), `StreamReceiveEventHandler` (per subscriber, filter or change events), `StreamBeforeEventsDispatchHandler` (once per batch, since 0.337), `StreamPublishEventHandler` (change outgoing events). Configurable via `events.handlers.on_receive_events` (concurrency, timeouts).
- Metrics `router.streams.received.messages`, `router.streams.sent.messages`.
- RFC and ADR `cosmo-streams-v1.md` in repo.

## Cosmo Connect (gRPC subgraphs and router plugins)

- Federate gRPC services without a GraphQL server. Schema first: write a GraphQL subgraph SDL, run `wgc grpc-service generate` to get a `.proto`, a mapping file and a `proto.lock` (stable field numbers). The router translates GraphQL to gRPC using the mapping (`protographic` library).
- Two deployment models:
  - gRPC services: remote, any language. `wgc grpc-service init --template golang-connect-rpc | typescript-connect-rpc-fastify`, `wgc grpc-service list-templates`, `wgc grpc-service create`, `wgc grpc-service publish` (schema plus proto). TLS/mTLS (since 0.321).
  - Router plugins: local processes managed by the router via HashiCorp `go-plugin` over gRPC. Go (`router-plugin` package) or TypeScript on Bun. `plugins.enabled`, `plugins.path`, `plugins.registry`. Fault isolated from the router. Logging, OTEL tracing and an HTTP client helper in the Go plugin SDK. Debugging guide.
  - `wgc router plugin init | generate | build | test | publish | create | delete`. Publish pushes the plugin image to the Cosmo Cloud plugin registry, so routers pull it without redeploy. Plugin count is limited per plan (3 / 10 / ...).
- Supported: queries, mutations, entity lookups (single, multiple, compound keys), `@requires` (generates `Require{Type}{Field}By{Key}` RPCs, batched, since 0.300), interfaces, unions (protobuf `oneof`), recursive types, nested lists, enums, nullable scalars (wrapper types).
- `@connect__fieldResolver(context: openfed__FieldSet!) on FIELD_DEFINITION`: turn a field into a batched RPC with parent context fields and field args. Since 0.264.
- Not supported: subscriptions, nested key lookups, nullable list items, custom scalar mapping (string only), `@requires` on abstract types, grouping several field resolvers into one call.
- Request encoding: direct protobuf wire encoding (`engine.enable_grpc_wire_encoding`), custom codec option (0.357).
- Headers forwarded as gRPC metadata. Span per gRPC call.

## Cosmo ConnectRPC (GraphQL to REST/gRPC for consumers)

- `connect_rpc` router server (`enabled`, `server.listen_addr`, `storage.provider_id`, `graphql_endpoint`). Since 0.284.
- Define named GraphQL operations ("trusted documents") in `.graphql` files, one per file, PascalCase name. `wgc grpc-service generate` with operations produces a proto service: one RPC per operation. Queries get `idempotency_level = NO_SIDE_EFFECTS` so HTTP GET works.
- Consumers call the router with Connect protocol (JSON over HTTP, REST style), gRPC, or gRPC-Web. Generate TypeScript and Go SDKs and an OpenAPI spec with Buf plugins. The router runs the GraphQL operation and returns protobuf/JSON.
- Only predefined operations can run. No GraphQL exposed to consumers.

## MCP Gateway (router)

- `mcp` block. The router runs an MCP server (Streamable HTTP, separate `listen_addr`). Since 0.262 (2025).
- Tools come from `.graphql` files in a `file_system` storage provider. One operation per file. Tool name `execute_operation_<snake_name>` (or without prefix with `omit_tool_name_prefix`). Operation and variable descriptions become tool and parameter descriptions. Root field description is the fallback.
- Built-in tools: `get_operation_info`, `get_schema` (`expose_schema`), `execute_graphql` (`enable_arbitrary_operations`), `generate_query` (Cosmo Cloud "Prompt to Query", needs graph token feature `prompt-to-query`, since 0.356).
- `exclude_mutations`, `session.stateless`, `router_url`, `graph_name`, `output_schema.enabled` (structured output per MCP 2025-06-18), `server/discover` method (MCP 2026-07-28) with `title`, `description`, `version`.
- OAuth 2.1 for MCP (`mcp.oauth`, since 0.311): JWKS validation, RFC 9728 protected resource metadata at `/.well-known/oauth-protected-resource/mcp`, multiple authorization servers, scopes per tool and per operation, scopes taken from `@requiresScopes` in the used fields, step-up via `WWW-Authenticate` `insufficient_scope`.
- Header forwarding from MCP clients. CORS shared with router.
- Subscriptions are not exposed as tools.

## Composition ("Open Federation") vs Apollo

- Own TypeScript implementation `@wundergraph/composition` (`federateSubgraphs({ subgraphs, options })`, `federateSubgraphsWithContracts`). Not Apollo code. Brand name "Open Federation". Claims compatibility with Apollo Federation v1 and v2. Compatibility matrix lists v1 directives, v2.0, 2.1, 2.3 and 2.5 as supported.
- Pipeline: normalize each subgraph, batch normalize, federate (merge), resolvability validation (can every field be reached from root via keys). Errors and warnings are separate. 194 error builders and 17 warning builders in the code.
- Composition options (`CompositionOptions`): `disableResolvabilityValidation` (`--disable-resolvability-validation` on `wgc router compose`, `subgraph fix`, `subgraph delete` and others), `ignoreExternalKeys` (`--ignore-external-keys`, plan feature `composition-ignore-external-keys` in Cosmo Cloud).
- Router compatibility versions: a new version only when the composition output and router contract break. Configs are stored per version in the CDN. `wgc router compatibility-version list`. Move a graph to a new version with `wgc federated-graph version get|set` (also `wgc monograph version`).
- Federation v1 and v2 subgraphs can be mixed. v1 subgraphs need no `@link`. `@extends` and `extend type` supported.
- Supported Apollo directives: `@key` (incl. `resolvable`, on interfaces), `@external`, `@requires` (fields with arguments), `@provides`, `@shareable`, `@inaccessible`, `@override(from:)`, `@tag`, `@extends`, `@link`, `@composeDirective`, `@interfaceObject`, `@authenticated`, `@requiresScopes`.
- Apollo directives accepted but unsupported (composition warning, ignored): `@override(label:)` (progressive override, warning says use Feature Flags instead), `@policy`, `@context`, `@fromContext`, `@cacheTag`. `@context`/`@fromContext` are partly built: composition validates them and strips context arguments from the client schema, but the router config has no context mapping. I think runtime support is not there yet.
- Apollo Connectors (`@connect`, `@source`) are not supported. Cosmo answers with Cosmo Connect (gRPC) and `@connect__fieldResolver`.
- No Apollo Federation 2.6+ features beyond `@authenticated`/`@requiresScopes` in the matrix. `@cost` and `@listSize` are supported for cost control (Apollo 2.9 directives, same names).
- Cosmo-only directives:
  - `@openfed__configureDescription(propagate: Boolean! = true, descriptionOverride: String)` and `@openfed__configureChildDescriptions(propagate: Boolean! = true)` (on enums, input objects, interfaces, objects): choose which subgraph description wins, hide or override descriptions. Only one subgraph may propagate per coordinate.
  - `@openfed__subscriptionFilter`, `@edfs__*` (EDFS), `@connect__fieldResolver` (gRPC).
  - `@openfed__requireFetchReasons repeatable on FIELD_DEFINITION | INTERFACE | OBJECT`: router adds `extensions.fetch_reasons` to subgraph requests (why a field was fetched: by user, by key, by requires).
  - `@openfed__entityCache`, `@openfed__cacheInvalidate`, `@openfed__cachePopulate`: entity cache, composition only (see Caching).
  - Scalars `openfed__FieldSet`, `openfed__Scope`.
- Also supported: `@oneOf` (merged), `@semanticNonNull(levels:)`, `@specifiedBy`, `@deprecated` (longest reason wins across subgraphs), `@defer` (operation directive).
- Merge rules differing from or adding to Apollo:
  - `@requiresScopes` across subgraphs: scope sets combined as a cross product (AND of both subgraphs' OR-lists).
  - Enum used as both input and output must be identical in all subgraphs. Docs give a migration recipe with `@inaccessible`.
  - Custom executable directives are kept in the supergraph when their definitions are compatible in all subgraphs (locations intersected, arguments merged, repeatable compatible). No `@composeDirective` needed for executable directives.
  - Non-entity shared object types must be resolvable on every path ("shared root type fields" rule).
  - Shareable on an object applies only to fields defined in that block, not to extensions.
- Contracts: `@tag` include or exclude filters (`wgc contract create --include/--exclude`). Built in composition. Apollo puts contracts behind GraphOS Enterprise. In Cosmo they are part of all plans.
- Composition is versioned with the control plane. Composition history and diffs in Studio ("Compositions" page).

## Control plane, schema registry and CLI (`wgc`)

- Model: organization > namespaces (for example `production`, `staging`) > federated graphs, monographs, subgraphs, feature subgraphs, feature flags, contracts. A federated graph selects subgraphs by label matchers (`--label-matcher team=A,team=B`), not by an explicit list. Subgraphs carry labels (`--label`).
- Platform API (Connect RPC, `proto/wg/cosmo/platform/v1/platform.proto`, about 200 RPCs). Used by `wgc` and Studio. API keys with group-scoped permissions for CI.
- Node API for routers: router config, persisted operations, self-registration. CDN serves signed configs.
- `wgc` commands (TypeScript, `npx wgc`):
  - `auth login | logout | whoami`, API key via `COSMO_API_KEY`.
  - `namespace create | delete | list | rename`.
  - `federated-graph create | update | delete | list | fetch | fetch-schema | check | move | changelog | version get | version set`. `--admission-webhook-url`, `--admission-webhook-secret`, `--readme`. `fetch -a, --apollo-compatibility` writes an Apollo-style supergraph for Apollo Router/Gateway. `fetch-schema --client-schema`.
  - `monograph create | update | delete | list | fetch | publish | check | move | migrate | changelog | version get | set`. `migrate` turns a monograph into a federated graph.
  - `subgraph create | update | delete | list | fetch | publish | batch-publish | check | fix | introspect | link | unlink | move`. Options include `--routing-url`, `--label`, `--subscription-url`, `--subscription-protocol ws|sse|sse_post`, `--websocket-subprotocol auto|graphql-ws|graphql-transport-ws`, `--edg`, `--readme`, `--fail-on-composition-error`, `--fail-on-admission-webhook-error`, `--suppress-warnings`, `--disable-resolvability-validation`.
  - `subgraph check --schema | --delete | --skip-traffic-check`: composition, breaking changes, operation (traffic) checks, lint, graph pruning, proposals, check extensions. Also works for a new subgraph not yet in the graph.
  - `subgraph batch-publish --config batch.yaml`: publish many subgraph schemas in one composition.
  - `subgraph link -t <namespace>/<subgraph>`: use traffic of another namespace (for example production) when checking a dev subgraph.
  - `subgraph fix`: uses OpenAI to fix composition errors in a schema (Cosmo AI).
  - `subgraph introspect --routing-url`: get SDL from a running subgraph via `_service { sdl }`. `--use-raw-introspection` uses standard introspection instead. `--header` for auth.
  - `feature-subgraph create | publish | update | delete` (`--subgraph <base>`), `feature-flag create | update | delete | enable | disable | list | recompose` (`--fs, --feature-subgraphs`, `--label`, `-e, --enabled`).
  - `contract create | update` (`--source`, `--include`, `--exclude` tags), contracts also listed, fetched and deleted with federated-graph commands.
  - `proposal create | update | update-status` (approve, close).
  - `operations push <graph> -c <client> -f manifest.json [--format json] [--allow-conflicts] [-q]`.
  - `clients list | delete`.
  - `router token create | list | delete`, `router fetch` (download execution config), `router compose -i graph.yaml -o config.json` (local composition from SDL files or introspection, with `feature_flags`, `--include/--exclude` contracts, `--split-configs-enabled`, `--disable-base-contract`, `--contract-feature-flag-names`), `router download-binary`, `router cache push` (cache warmer operations), `router compatibility-version list`, `router plugin init | generate | build | test | publish | create | delete`.
  - `grpc-service init | list-templates | generate | create | publish | delete`.
  - `demo`: guided onboarding. Builds demo plugins with Docker Buildx, creates a token and starts a local router.
  - `mcp`: local stdio MCP server for AI tools (beta). Tools: list subgraphs, introspect subgraph, verify schema changes, schema change proposal workflow, verify query against local or remote schema, verify router config, supergraph changelog, search docs, "dream query" workflow, federated graph tools.
- CI: `wgc` detects GitHub env and reports check status. GitHub App integration (`IsGitHubAppInstalled`) lets users force a failed check to pass from Studio (`ForceCheckSuccess`). GitHub Action `wundergraph/cosmo-previews` creates per-PR feature flags as supergraph previews.
- Terraform provider `wundergraph/cosmo` for Cosmo Cloud resources. Terraform module for the router on AWS Fargate. Helm charts for the full platform and the router.
- Webhooks (organization): events in proto `OrganizationEventName`: `FEDERATED_GRAPH_SCHEMA_UPDATED`, `MONOGRAPH_SCHEMA_UPDATED`, `VALIDATE_CONFIG`, `PROPOSAL_STATE_UPDATED`. Delivery history and redelivery in Studio. HMAC signature. Slack integration for the same events.
- Platform webhooks (self-hosted control plane config): `USER_REGISTER_SUCCESS`, `APOLLO_MIGRATE_INIT`, `APOLLO_MIGRATE_SUCCESS`.
- Migrate from Apollo GraphOS: one click import with a GraphOS API key (`MigrateFromApollo`). Tutorial for running Apollo Router or Gateway on the Cosmo registry via webhook plus `fetch --apollo-compatibility`.
- Readmes on graphs and subgraphs (`--readme`, `AddReadme`).

## Schema checks and governance

- Check kinds: composition errors, breaking change detection, operation checks against real traffic (schema usage from `graphqlmetrics` in ClickHouse, configurable window, default per plan 7/14/30 days), lint checks, graph pruning checks, proposal match, subgraph check extensions.
- Directive usage is not tracked. Changing or deleting directives is always non-breaking in checks.
- Operation check overrides: per operation, ignore specific breaking changes or ignore all. Namespace-wide. List of all overrides.
- Feature-flag aware: checks run against base and feature flag compositions.
- Lint policy per namespace with severity `error | warning`. Rules: `FIELD_NAMES_SHOULD_BE_CAMEL_CASE`, `TYPE_NAMES_SHOULD_BE_PASCAL_CASE`, `SHOULD_NOT_HAVE_TYPE_PREFIX`, `SHOULD_NOT_HAVE_TYPE_SUFFIX`, `SHOULD_NOT_HAVE_INPUT_PREFIX`, `SHOULD_HAVE_INPUT_SUFFIX`, `SHOULD_NOT_HAVE_ENUM_PREFIX`, `SHOULD_NOT_HAVE_ENUM_SUFFIX`, `SHOULD_NOT_HAVE_INTERFACE_PREFIX`, `SHOULD_NOT_HAVE_INTERFACE_SUFFIX`, `ENUM_VALUES_SHOULD_BE_UPPER_CASE`, `ORDER_FIELDS`, `ORDER_ENUM_VALUES`, `ORDER_DEFINITIONS`, `ALL_TYPES_REQUIRE_DESCRIPTION`, `DISALLOW_CASE_INSENSITIVE_ENUM_VALUES`, `NO_TYPENAME_PREFIX_IN_TYPE_FIELDS`, `REQUIRE_DEPRECATION_REASON`, `REQUIRE_DEPRECATION_DATE`.
- Graph pruning (traffic-based linter): `UNUSED_FIELDS`, `DEPRECATED_FIELDS` (deprecated but unused, can be removed), `REQUIRE_DEPRECATION_BEFORE_DELETION`. Grace period for new fields (plan feature `field-pruning-grace-period`). Usage check period configurable only on Enterprise.
- Proposals (plan feature `proposals`): a set of subgraph schema changes reviewed in Studio (diff view, checks). States Draft, Approved, Published, Closed. Namespace config sets check and publish severity when a schema does not match an approved proposal. Webhook on state change.
- Subgraph Check Extensions (paid, `subgraph-check-extensions`): control plane POSTs check data (SDLs, lint and pruning issues, schema changes, affected operations) to your endpoint per namespace. HMAC `X-Cosmo-Signature-256`. Your response can fail the check.
- Admission webhook for router configs (see router configuration).
- Changelog per federated graph (additions and deletions per composition).
- Persisted operation traffic check before delete (`CheckPersistedOperationTraffic`).

## Studio

- Next.js web app. Hosted at `cosmo.wundergraph.com` or self-hosted.
- Graph overview: subgraphs, label matchers, composition status, router URL, graph visualization, request and error stats.
- Schema registry view (current SDL of graph and subgraphs, download), Schema Explorer (navigate types, field usage per client and operation, deprecated fields, `@authenticated` markers), Compositions history with inputs, errors and diffs, Changelog.
- Checks pages (see above) with affected operations and clients.
- Playground: GraphiQL with ART trace view and query plan view. Pre-flight scripts and pre/post-operation scripts (JS, for example fetch tokens). Shared playground state via URL (operation, variables, headers optional). Default headers per graph and per user. Feature flag selection.
- Analytics: metrics dashboard (request rate, P95 latency, error rate), traces list with filters and grouping (operation, client, error), distributed trace view (router plus subgraph spans), field usage, client identification (`graphql-client-name`/`-version`), Operations page (per operation metrics, deprecated field usage, clients), subgraph metrics.
- Clients page with persisted operations per client, delete operations.
- Router cluster management: list of running routers (service name, instance ID, version, cluster, uptime, CPU and memory).
- Cache warmer config and manual operations.
- Feature flags overview.
- Organization: members, invitations, groups and group rules (RBAC, Scale plan), roles at organization, namespace, graph and subgraph level, API keys with resource scopes, audit log, sessions, SSO via OIDC (Okta, Auth0, Keycloak, Microsoft Entra), IdP mappers to groups, SCIM provisioning (Okta, also Okta OIN app), login method restrictions per organization and per namespace (Enterprise), webhooks, Slack, billing.
- Cosmo AI (open beta, Cosmo Cloud): generate subgraph documentation, help with composition errors. Prompt to Query (natural language to operation) for MCP.

## Upcoming and unreleased work

- `main` at `1473af4` (2026-10-09) is after `router@0.357.0`. It adds response cache health metrics and fetch counts by type (#3294). Not yet in a router release.
- Response cache work in progress (open PRs): `@cacheTag` on root fields in composition (#3131), cacheTag configs on entities (#3341, #3342), fix for invalidation races that leave dangling entries (#3322). The `@openfed__entityCache` family is in composition but not documented yet.
- Cosmo Streams: basic cursor support for Kafka (#3263) and an RFC for at-least-once delivery with cursors (#3259). I think delivery is at-most-once today.
- Subscriptions: subscription operation hooks for custom modules (#3283, draft), observe delivery failures (#3173, draft), idle WebSocket read fix (#3336), per-message-deflate WebSocket compression (#3096).
- MCP: MCP operation manifests (#3320, draft), MCP resources and skills (#3195, POC), schema discovery for search and query generation (#3156, draft), typed custom scalars in tool schemas with `scalar_mappings` (#3147, draft), `code_mode_run_js` per server (#2840, draft).
- Router engine: dataflow execution and plan scheduling flags (#2961, draft), `@defer` with defer-aware ART playground (#3074, draft), `drain_period` for keep-alive connections before shutdown (#3316), parser limits before normalization with skip for persisted operations (#3310, draft), `SetWildcardScope` to bypass `@requiresScopes` from a module (#2534).
- Composition: 2.2x and 3.9x speedups (#2962, #2967, drafts), clearer error for inconsistent input/output enums (#3313).
- Control plane and CLI: `split-config-loading` on by default for new organizations (#3288), mTLS client certificates in `wgc` (#3314), `proposal status` command (#3164), stricter persisted operation ID rules (#3327, #3330), custom headers for Studio webhooks (#2038), feature subgraphs in playground dropdowns (#3196).
- Custom modules v1 (`adr/custom-modules-v1.md`, accepted 2024-08-11): new hook set (see Router: customization). Not built yet.
- RFC `rfc/graph-feature-flags-v2.md`: changes feature flag composition to avoid the cost of composing every flag combination.
- gRPC roadmap in docs (`router/gRPC/graphql-support.mdx`): nested key entity lookups, subscriptions, event-driven updates, retry and timeout config, custom and JSON scalar mappings, lazy loading. Plugin languages beyond Go and TypeScript "coming soon".
- RBAC roadmap in docs (`studio/rbac.mdx`): limit subgraph access per federated graph, groups need at least one rule.
- Pricing: open PR changes the Scale plan price to "custom" (#3323).

## Not supported

- Scripting in the router. No Rhai, no external HTTP coprocessor. Only compiled Go custom modules and gRPC router plugins.
- `@policy` enforcement. Composition accepts it with a warning. The router has no policy hook.
- `@context` / `@fromContext` (Federation 2.8). Accepted with a warning and ignored.
- `@override(label:)` progressive override. Warning says to use feature flags.
- Apollo Connectors (`@connect`, `@source`). Cosmo Connect (gRPC) is the alternative.
- `@cacheTag` (Apollo directive). Ignored with a warning today. PRs are open.
- `@stream`. Only `@defer` (opt-in, `engine.enable_defer`).
- HTTP callback protocol for subgraph subscriptions. Only `ws`, `sse` and `sse_post`.
- Subscriptions survive config reloads. All subscriptions are closed on a config swap.
- Rate limiting of client requests by the router. `rate_limit` limits outgoing subgraph requests only.
- Cosmo Streams: at-least-once or ordered delivery, replay from a cursor. Providers are only NATS, Kafka and Redis.
- gRPC subgraphs and plugins: subscriptions, nested key lookups, nullable list items, custom scalar mapping (string only), `@requires` on abstract types, grouping several field resolvers into one call, plugin languages other than Go and TypeScript (Bun).
- MCP: subscriptions as tools.
- Code-first subgraph framework. Cosmo is a gateway and platform. Subgraphs are built with any third-party GraphQL server.
- Router license-gated features. There is no license check in the router code.

## Docs and code disagree

- Router config defaults in `router/configuration.mdx` differ from `router/pkg/config/config.go` (`envDefault`). The code values win:
  - `ENGINE_MAX_CONCURRENT_RESOLVERS`: docs 32, code 1024.
  - `ENGINE_MINIFY_SUBGRAPH_OPERATIONS`: docs false, code true.
  - `ENGINE_PARSEKIT_POOL_SIZE`: docs 8, code 16. The JSON schema also says 8.
  - `FILE_UPLOAD_MAX_FILES`: docs 2, code 10.
  - `EXECUTION_CONFIG_FILE_WATCH`: docs true, code false.
- gRPC support page (`router/gRPC/graphql-support.mdx`): the feature table says union types are supported. The linting table on the same page says unions are an "Error" and not supported. The protographic validator (`protographic/src/sdl-validation-visitor.ts`) has no union error. The code maps unions to protobuf `oneof`.
- Federation compatibility matrix (`federation/federation-compatibility-matrix.mdx`) stops at Federation 2.5. It does not list `@cost` and `@listSize` (2.9), which composition and cost control support. It also does not list the unsupported 2.6+ directives (`@policy`, `@context`, `@fromContext`, `@override(label:)`).
- `@openfed__entityCache`, `@openfed__cacheInvalidate` and `@openfed__cachePopulate` are in composition but not in the docs or the directive index.
- Custom modules page does not list `core.TracePropagationProvider` and `core.SpanNameFormatterProvider`. Both are in `router/core/modules.go`.
- Pricing page lists rate limiting, persisted operations and multiple OTEL exporters as paid features. The router code has no check for them. I think the limits apply only to Cosmo Cloud services.
- The ADR `adr/custom-modules-v1.md` says "Accepted" (2024). The new hook names are not in the code.

## Sources

Repos:
- https://github.com/wundergraph/cosmo (clone at `/tmp/cosmo`, `main` at `1473af4`, 2026-10-09, shallow). Paths used: `router/pkg/config/config.go`, `router/pkg/config/config.schema.json`, `router/core/modules.go`, `router/internal/jwt/claims.go`, `router/CHANGELOG.md`, `composition/src/v1/` (constants, normalization, warnings, errors), `protographic/src/sdl-validation-visitor.ts`, `protographic/src/sdl-to-proto-visitor.ts`, `controlplane/src/types/index.ts`, `proto/wg/cosmo/platform/v1/platform.proto`, `cli/src/commands/`, `adr/`, `rfc/`, component `CHANGELOG.md` files.
- Docs source in the same repo: `docs-website/` (343 `.mdx` files, Mintlify).
- GitHub releases and open PRs via `gh`: https://github.com/wundergraph/cosmo/releases, https://github.com/wundergraph/cosmo/pulls.
- https://github.com/wundergraph/router-examples (named for custom module examples, not cloned).

Docs (https://cosmo-docs.wundergraph.com/, read from `docs-website/`):
- https://cosmo-docs.wundergraph.com/router/configuration
- https://cosmo-docs.wundergraph.com/router/configuration/template-expressions
- https://cosmo-docs.wundergraph.com/router/custom-modules
- https://cosmo-docs.wundergraph.com/router/security/hardening-guide
- https://cosmo-docs.wundergraph.com/router/security/cost-control
- https://cosmo-docs.wundergraph.com/router/response-cache
- https://cosmo-docs.wundergraph.com/concepts/cache-warmer
- https://cosmo-docs.wundergraph.com/router/persisted-queries/persisted-operations
- https://cosmo-docs.wundergraph.com/router/persisted-queries/automatic-persisted-queries-apq
- https://cosmo-docs.wundergraph.com/router/query-batching
- https://cosmo-docs.wundergraph.com/router/file-upload
- https://cosmo-docs.wundergraph.com/router/defer/usage
- https://cosmo-docs.wundergraph.com/router/access-logs
- https://cosmo-docs.wundergraph.com/router/metrics-and-monitoring
- https://cosmo-docs.wundergraph.com/router/cosmo-streams
- https://cosmo-docs.wundergraph.com/router/gRPC/concepts
- https://cosmo-docs.wundergraph.com/router/gRPC/graphql-support
- https://cosmo-docs.wundergraph.com/router/gRPC/field-resolvers
- https://cosmo-docs.wundergraph.com/router/gRPC/requires
- https://cosmo-docs.wundergraph.com/router/mcp/tools
- https://cosmo-docs.wundergraph.com/federation/federation-compatibility-matrix
- https://cosmo-docs.wundergraph.com/federation/directives
- https://cosmo-docs.wundergraph.com/federation/composition-errors
- https://cosmo-docs.wundergraph.com/concepts/feature-flags
- https://cosmo-docs.wundergraph.com/studio/rbac
- https://cosmo-docs.wundergraph.com/tutorial/using-apollo-router-gateway-with-cosmo-oss-schema-registry
- Other pages used by the earlier sections: `cli/`, `control-plane/`, `studio/`, `connect/`, `connect-rpc/`, `deployments-and-hosting/`, `concepts/`, `router/`.
- Pricing: https://wundergraph.com/pricing
