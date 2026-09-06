# GraphQL Mesh / Hive Gateway findings

Versions checked: GraphQL Mesh repo `ardatan/graphql-mesh` `master` at `70ed549` (2026-10-07). Hive Gateway repo `graphql-hive/gateway` `main` at `ce516e3` (2026-10-08).
GraphQL Mesh is still at `ardatan/graphql-mesh`. It did not move to the `graphql-hive` org. Hive Gateway, Yoga, Envelop and the Hive platform are in `graphql-hive`.
Stack: TypeScript, Node.js, Bun, Deno, serverless (Cloudflare Workers, AWS Lambda and so on). Built on `@graphql-tools/*` (stitching, delegation, executors), `@whatwg-node/*` (Fetch API) and Envelop/Yoga.
License: MIT for Mesh and Hive Gateway.
Product split since Mesh v1 (2024-09): Mesh Compose (`@graphql-mesh/compose-cli`) builds a supergraph SDL. Hive Gateway (`@graphql-hive/gateway`) serves it. Mesh v0 (`@graphql-mesh/cli`, `.meshrc.yml`) did both. v0 packages are still published.
Already covered elsewhere, not repeated here: Envelop/Yoga plugins and hooks (`graphql-yoga-envelop.md`), Federation spec and directives (`apollo-router-federation.md`), Cosmo (`wundergraph-cosmo.md`). Hive Gateway runs on Yoga, so every Yoga/Envelop plugin works in it.

## Maintenance status

- Mesh: very active in patch releases. Last commit 2026-10-07. Mostly fixes and dependency bumps. Few new features in 2026.
- Mesh npm `latest`: `@graphql-mesh/compose-cli` 1.8.2 (2026-08-24), `@graphql-mesh/fusion-composition` 0.11.2, `@omnigraph/openapi` and `@omnigraph/json-schema` 0.112.4, `@graphql-mesh/cli` (v0) 0.103.2 (2026-08-24). Daily `alpha` builds on npm (2026-10-09).
- Mesh GitHub releases: rolling "release-<id>" entries. Latest 2026-09-04.
- Hive Gateway: very active. `@graphql-hive/gateway` 2.15.2 (2026-10-08). `@graphql-hive/gateway-runtime` 2.12.2. `@graphql-hive/router-runtime` 1.6.5. `@graphql-hive/plugin-mcp` 0.2.1. Gateway 1.0.0 was 2024-09-10. 2.0.0 was 2025-09-04.
- Hive CLI `@graphql-hive/cli` 0.66.0 (2026-10-10).
- Changesets workflow in both repos.

## Mesh v1: how non-GraphQL sources become a schema

- Config file `mesh.config.ts` (also `.mts`, `.cts`, `.js`, `.mjs`, `.cjs`). Export `composeConfig = defineConfig({...})` for compose and `gatewayConfig` for Hive Gateway. One file can hold both.
- `composeConfig` keys (code, `compose-cli/src/types.ts`): `subgraphs`, `transforms`, `additionalTypeDefs`, `output`, `subgraph`, `fetch`, `cwd`.
- Each subgraph: `{ sourceHandler, transforms }`. A source handler returns `{ name, schema$: Promise<GraphQLSchema> }`. Custom handlers are plain functions with this shape.
- Loaders ("Omnigraph", `@omnigraph/*`) read the source spec at compose time and build a `GraphQLSchema` with `graphql-compose`. They annotate it with execution directives. Examples (code): `@transport`, `@httpOperation`, `@responseMetadata`, `@statusCodeTypeName`, `@discriminator`, `@flatten`, `@dictionary`, `@linkResolver`, `@pubsubOperation`, `@resolveRoot`, `@resolveRootField`, `@regexp`, `@length`, `@example`, `@oneOf`, `@typescript`, `@grpcMethod`, `@grpcConnectivityState`, `@soap`, `@mysqlSelect`, `@mysqlInsert`, `@mysqlUpdate`, `@mysqlDelete`, `@mysqlCount`, `@mysqlTableForeign`, `@entitySet`, `@navProp`, `@boundAction`, `@unboundFunction`, `@singleton`.
- The output SDL holds no code. At runtime, Hive Gateway reads `@transport(kind: ...)` and loads a transport package (`@graphql-mesh/transport-rest`, `-grpc`, `-soap`, `-mysql`, `-sqlite`, `-neo4j`, `-odata`, `-thrift`) that interprets the directives and builds resolvers. So the compose step is static and the gateway executes it.
- Mesh directives are namespaced with `@link(url: "https://the-guild.dev/graphql/mesh/spec/v1.0")`. Compose converts subgraphs to Federation v2 (`convertSubgraphToFederationv2`) and adds `@source` (original names after transforms) and `@merge` (type merging entry points).
- Composition engine: `composeServices` from `@theguild/federation-composition` (The Guild's own Federation composition, not Apollo's). Output is a supergraph SDL with extra Mesh annotations ("unified graph").
- CLI: `mesh-compose -o supergraph.graphql`, `--subgraph <name>` to output one subgraph only (to publish to a registry), `-c/--config-path` (`CONFIG_PATH` env). Output to `.graphql` or a JS module (`supergraph.js`).
- Dynamic values: string interpolation `{context.headers['x-token']}`, `{context.cookies.x}`, `{env.NAME}`, `{args.id}`, `{root.id}` in endpoints, headers, paths and metadata (`@graphql-mesh/string-interpolation`).
- `operationHeaders` (sent on each upstream call) and `schemaHeaders` (sent when fetching the source spec or introspecting) on most handlers.
- `ignoreSemanticConventions: true`: turn off automatic type merging by naming convention.
- Not supported: the docs say `composeConfig.transforms` (supergraph-level transforms) works. The code has that block commented out with `TODO`. Root transforms are silently ignored. The migration page says they are not supported.
- Not supported in v1: v0 `merger` choice (stitching, bare, federation). Composition is always Federation-style.

## Mesh v1: source handlers (one line each)

- GraphQL (`loadGraphQLHTTPSubgraph` in `@graphql-mesh/compose-cli`): introspect `endpoint`, or take SDL/introspection from `source` (URL or file) and execute against `endpoint`. `endpoint` may also be a local code-first schema file. Options `retry`, `timeout`, `strategy: 'fallback' | 'race'` with `sources: [...]` for several endpoints of one source. v0 also had `highestValue` strategy.
- OpenAPI 2/3 and Swagger (`loadOpenAPISubgraph`, `@omnigraph/openapi`): JSON or YAML, local or remote. Originated at IBM Research (openapi-to-graphql). GET to Query, others to Mutation. `selectQueryOrMutationField` overrides. Names from `operationId`. Unnamed types get path-based names like `query_getUsers_items_firstName`. OAS callbacks become Subscriptions via webhooks. Per-status-code responses become unions.
- OpenAPI options not in the docs (code): `jsonApi` (JSON:API sparse fieldsets: builds `fields[...]` query params from the GraphQL selection), `HATEOAS` (follows `rel`/`href` links, `linkNameIdentifier`, `linkPathIdentifier`), `fallbackFormat` (`json`, `yaml`, `js`, `ts`), OAS `links` and `x-links` become fields.
- JSON Schema or samples (`loadJSONSchemaSubgraph`, `@omnigraph/json-schema`): describe REST endpoints by hand. Per operation: `type`, `field`, `path` (with `{args.id}`), `method`, `responseSchema` (file or `$ref` path), `responseSample` (example JSON is turned into a schema), `responseTypeName`, `requestSchema`, `requestSample`, `requestTypeName`, `requestBaseBody`, `argTypeMap`, `requiredArgs`, `queryParamArgMap`, `queryParamsSample`, `queryStringOptionsByParam`, `headers`, `deprecated`, `responseByStatusCode`, `exposeResponseMetadata`, `links`. Handler level: `queryParams` (global args), `queryStringOptions` (qs library options, `jsonStringify`), `timeout`, `ignoreErrorResponses`, `errorMessage`, `bundle`, `getScalarForFormat` (map JSON Schema `format` to a scalar).
- JSON Schema file upload: operation with `binary: true` sends the raw `File` body. Multipart `FormData` built for `File` args (code, `transport-rest`).
- JSON Schema subscriptions: operation `type: Subscription` with `pubsubTopic`.
- RAML (`loadRAMLSubgraph`, `@omnigraph/raml`): RAML API specs. Not in the v1 docs nav. Package is published (0.112.4).
- gRPC / Protobuf (`loadGrpcSubgraph`, `@omnigraph/grpc`): `.proto` files (`source`, `load.includeDirs`) or server reflection when `source` is missing. `requestTimeout` (deadline), `useHTTPS`, `credentialsSsl` (`rootCA`, `certChain`, `privateKey`), `prefixQueryMethod` (default `list`, `get` become Query), `selectQueryOrMutationField` with `*` patterns, `metaData` (per-call metadata from context, for auth), `reflectionMetadata`, `channelOptions`. Server streaming RPCs become list fields by default (stream collected), or real Subscriptions when moved to `Subscription` with `selectQueryOrMutationField`. Client streaming RPCs take a `File` input. Connectivity state exposed through `@grpcConnectivityState` (code).
- SOAP / WSDL (`loadSOAPSubgraph`, `@omnigraph/soap`): WSDL from URL or file. `soapHeaders` (`alias`, `namespace`, `headers` with `{env.X}`), `bodyAlias`, `soapNamespace` (default detected for SOAP 1.1 or 1.2), `endpoint` override. XML via `fast-xml-parser`.
- OData / Microsoft Graph (`loadODataSubgraph`, `@omnigraph/odata`): reads `$metadata`. Entity sets, singletons, navigation properties, bound and unbound functions and actions, create/update/delete. `queryOptions` arg with `orderby`, `top`, `skip`, `filter`, `inlinecount`. `batch: 'none' | 'json' | 'multipart'` uses OData `$batch` through DataLoader. `expandNavProps` uses `$expand`. These two options are not in the v1 docs.
- Apache Thrift (`loadThriftSubgraph`, `@omnigraph/thrift`): `.thrift` IDL over HTTP. Code options are `source` (IDL file), `endpoint` (URL, `https:` switches TLS), `serviceName`, `operationHeaders`, `schemaHeaders`. The v1 docs show the v0 option names `idl`, `hostName`, `port`, `path`. Protocol is not configurable in v1 (I think it uses the thrift library default binary protocol).
- SQLite (`loadSQLiteSubgraph`, `@omnigraph/sqlite`): uses Tuql. `db` file or `infile` SQL dump loaded into memory.
- MySQL (`loadMySQLSubgraph`, `@omnigraph/mysql`): introspects tables. Per table: Query `<table>(limit, offset, where, orderBy)`, `count_<table>(where)`, Mutations `insert_<table>`, `update_<table>(where)`, `delete_<table>(where)`. Foreign keys become relation fields. `where` uses a string mini language: `">2010"`, `"100..200"`, `"<=3"`, `"*str?"` (LIKE), `"(1,2,4)"` (IN). Options `tables`, `tableFields` (limit what is exposed), `ssl`. Docs example uses `getProduct(where:)`. The code names the field after the table.
- Neo4j (`loadNeo4jSubgraph`, `@omnigraph/neo4j`): wraps `@neo4j/graphql` (see `neo4j-graphql.md`). Introspects the graph to build type defs. `endpoint`, `database`, `auth`, `driver`.
- PostgreSQL ("Coming soon" in v1 docs): docs say `npm i @omnigraph/postgresql` with `loadPostgreSQLSubgraph`. That package does not exist on npm (404) and is not in the repo. Only the v0 handler `@graphql-mesh/postgraphile` (PostGraphile v4, `appendPlugins` for many-to-many and PostGIS, `@graphile/federation`) exists.
- MongoDB ("Coming soon" in v1 docs): docs say `@omnigraph/mongoose` with `loadMongooseSubgraph`. Not on npm (404). Only v0 `@graphql-mesh/mongoose` (graphql-compose-mongoose) exists.
- Supergraph (v0 `@graphql-mesh/supergraph`): consume an existing Federation supergraph as a source. v1: give the SDL to Hive Gateway directly.
- Not supported as sources: Redis, Kafka (only via Hive Gateway pubsub), Elasticsearch, DynamoDB, generic SQL (Postgres only through v0 PostGraphile).

## Mesh v1: transforms

All transforms are "wrap" style. They emit directives (`@source` and so on) so the gateway can map renamed fields back to the original. Must be served by Hive Gateway or another gateway that reads them. Exported from `@graphql-mesh/compose-cli`.
- `createPrefixTransform({ value, includeRootOperations, includeTypes, ignore, force })`: prefix types and root fields. Builtin scalars never prefixed. `force` opts in custom scalars such as `DateTime`.
- `createRenameTransform({ typeRenamer, fieldRenamer, argRenamer })`: functions return the new name or `''` to keep it.
- `createNamingConventionTransform({ typeNames, enumValues, fieldNames, fieldArgumentNames })`: helpers `camelCase`, `pascalCase`, `upperCase` and so on. Response data is mapped back.
- `createFilterTransform({ rootFieldFilter, typeFilter, fieldFilter, argumentFilter })`: hide schema parts. v0 used glob strings like `Query.!user`.
- `createHoistFieldTransform({ mapping: [{ typeName, pathConfig, newFieldName, filterArgsInPath }] })`: lift a nested field to a parent (for example unwrap a paginated result). `filterArgs` drops args on the path.
- `createEncapsulateTransform({ applyTo: { query, mutation, subscription } })`: put the whole subgraph under one root field named after the subgraph.
- `createPruneTransform({ skipPruning })`: remove unused and empty types.
- `createFederationTransform({ [TypeName]: { key: { fields, resolveReference: { fieldName } }, extends: true, ... } })`: add Federation directives to a non-federated GraphQL source. `resolveReference` maps a root field as the entity resolver.
- `createExtendTransform(typeDefs)`, `createTypeReplaceTransform(...)` (code, `fusion/composition/src/transforms.ts`). Not in the v1 docs.
- Removed in v1 (v0 only): `typeMerging`, `cache` (now gateway response cache), `rateLimit` (now gateway plugin), `replaceField` (swap a field's type or resolver with another field's), `resolversComposition` (wrap resolvers with middleware by glob), `hive` transform.

## Mesh v1: composition features

- Automatic type merging by convention: same type name in several subgraphs plus a `<Type>By<Key>(<key>: <type>): <Type>` root field (also `<Types>ByIds`, pluralized). Compose adds `@merge` for you. Turn off with `ignoreSemanticConventions`.
- Federation directives in subgraphs work as normal (`@key`, `@shareable` and so on).
- `additionalTypeDefs` plus `@resolveTo` directive: add gateway-level fields that delegate to another subgraph. Args `sourceName`, `sourceTypeName`, `sourceFieldName`, `sourceArgs` (with `{root.x}`), `requiredSelectionSet`, `returnType`, `result` (path into the response), `filterBy`, `pubsubTopic`.
- Batch delegation in `@resolveTo`: `keyField` plus `keysArg` wraps calls in a DataLoader (per context, field, args and selection). Results matched by position. `valueKeyField` matches results by a field instead (for `WHERE id IN (...)` style sources that reorder or omit rows). Lists get `[]` for missing keys.
- `gatewayConfig.additionalResolvers`: code resolvers at gateway runtime. Typed with the in-context SDK.
- In-context SDK (`@graphql-mesh/incontext-sdk-codegen` GraphQL Codegen plugin): generates `MeshInContextSDK` so resolvers can call `context.<Source>.Query.<field>({ root, args, context, info, selectionSet })`. Also per-subgraph types.
- Operation SDK: GraphQL Codegen `typescript-generic-sdk` against the supergraph, then `getSdk(runtime.sdkRequester)` with `createGatewayRuntime`, or `getSdkRequesterForUnifiedGraph`. Queries, mutations and subscriptions (async iterators).
- Local execution without HTTP: `getExecutorForUnifiedGraph({ getUnifiedGraph })` from Hive Gateway runtime.
- Webhooks as Subscriptions: `@resolveTo(pubsubTopic: "webhook:post:/webhooks/todo_added", filterBy: "root.userId === args.userId", result: "data.x")`. Gateway option `webhooks: true` binds the HTTP path to the pubsub topic.
- Error mapping: non-2xx without mapping gives an error with `extensions.code: DOWNSTREAM_SERVICE_ERROR` and HTTP details. `responseByStatusCode` turns status codes into union members (`union BookResult = Book | BookNotFound | InternalError`).
- Auth directives: subgraphs can use Federation `@authenticated`, `@requiresScopes`, `@policy`. Mesh adds `@skipAuth` (from the Mesh spec link, needs `@composeDirective`) to open fields under "complete protection" mode.
- `@cacheControl(maxAge, scope, inheritMaxAge)` and `@rateLimit` in subgraphs are hints the gateway plugins read.
- Consume in other gateways (Apollo Router, Cosmo): they do not understand Mesh directives. Compose each non-GraphQL source with `--subgraph`, serve it with `hive-gateway subgraph <file>` as a real Federation subgraph, then compose it with the other tool.
- Omnigraph loaders also work outside Mesh: as GraphQL Config `loader:` entries (for Codegen, ESLint, VS Code), or called directly to get a `GraphQLSchema` (for example `loadGraphQLSchemaFromOpenAPI`) to serve with any server.

## Mesh v0 (legacy, still published)

- `.meshrc.yml` with `sources[].handler`, `transforms`, `additionalTypeDefs`, `additionalResolvers`, `merger` (`stitching`, `bare`, `federation`), `serve`, `plugins`, `cache`, `pubsub`, `documents`, `sdk`, `persistedOperations`, `codegen`.
- CLI `mesh dev`, `mesh build` (writes `.mesh/` with JS artifacts, `getBuiltMesh`, `execute`, `getMeshSDK`, `createBuiltMeshHTTPHandler`), `mesh start`, `mesh validate`, `mesh serve-source`.
- Transforms had `bare` (change schema in place) and `wrap` modes, and could run on the unified schema.
- v0 plugins (`packages/plugins`, still used by Hive Gateway where noted): `deduplicate-request`, `hive`, `http-cache`, `http-details-extensions` (upstream HTTP details in `extensions`), `jit` (graphql-jit), `live-query` (`@live` with `invalidations: [{ field: Mutation.addTodo, invalidate: [Query.todos] }]`), `mock`, `newrelic`, `operation-field-permissions`, `operation-headers`, `prometheus`, `rate-limit`, `response-cache`, `snapshot` (record upstream HTTP responses to files for offline dev), `statsd`.
- v0 guides: SOFA REST API generation (`@graphql-yoga/plugin-sofa`, GraphQL to REST plus Swagger UI), file uploads, persisted operations store, Auth0 guide.
- Caches (`packages/cache`, used by v0 and by Hive Gateway `cache`): `inmemory-lru`, `redis`, `upstash-redis`, `cfw-kv` (Cloudflare KV), `localforage`, `file`.
- Migration CLI `@graphql-mesh/migrate-config-cli` (`mesh-migrate-config`, `--dry-run`, `--force`). Experimental. Errors on root transforms, unknown handlers, `typeMerging`.

## Hive Gateway: shape and modes

- Runs on Yoga plus Envelop. All Yoga features and plugins apply (see `graphql-yoga-envelop.md`). This section lists only gateway additions or differences.
- Three CLI modes: `hive-gateway supergraph [path|url]` (Federation or Mesh supergraph), `hive-gateway subgraph [path]` (serve one Mesh-composed subgraph as a real Federation subgraph for Apollo Router, Cosmo and so on), `hive-gateway proxy [endpoint]` (put gateway features in front of any GraphQL API, `--schema` for a schema file or URL, else introspection).
- Distribution: npm package `@graphql-hive/gateway`, a standalone binary (`curl -sSL https://graphql-hive.com/install-gateway.sh | sh`), Docker image `ghcr.io/graphql-hive/gateway` (Node 26 since 2.8.0).
- Config file `gateway.config.ts` (`.mts`, `.cts`, `.js`, `.mjs`, `.cjs`) exporting `gatewayConfig = defineConfig({...})`. Or `mesh.config.ts` `gatewayConfig`. `defineConfig<TContext>()` is typed by context (2.0.0).
- Programmatic: `createGatewayRuntime(config)` returns a Fetch-API handler. Works with Express, Fastify, Hapi, Koa, Next.js, SvelteKit, uWebSockets.js, Bun, Deno, AWS Lambda, Azure Functions, Cloudflare Workers, Google Cloud. NestJS driver `@graphql-hive/nestjs`.
- Supergraph sources: file (watched for changes since 1.14.0), URL, function, Hive CDN (`--hive-cdn-endpoint`, `--hive-cdn-key`, several endpoints for main and mirror CDN, circuit breaker since runtime 2.4.0), Apollo GraphOS uplink (`--apollo-graph-ref`, `--apollo-key`, `--apollo-uplink`, `APOLLO_SCHEMA_CONFIG_DELIVERY_ENDPOINT`). `pollingInterval` (`--polling`, default 10s). On serverless with a cache, the remote supergraph is cached with `pollingInterval` as TTL.
- `dev` supergraph source (2.15.0, 2026-10): the gateway composes a supergraph itself from local subgraphs. `services: [{ name, url, source: 'federation' | 'graphql' | 'file', schema }]`, recomposes on change. `--dev-service name=url`, `--dev-service-source`, `--dev-service-schema`. `remote: true` (`--dev-remote`) sends local schemas to the Hive registry, which composes them with the rest of the published graph. Counterpart of `hive dev`. Code also has `unstable__forceLatest` (compose against a non-composable latest version) and a `circuitBreaker` option. Not in the docs.
- Subgraph polling (runtime 2.7.0): `subgraph` mode also polls.
- `gracefulSchemaReload: { drainTimeout, maxConcurrentGenerations }` (runtime 2.10.0): on schema reload, in-flight operations finish on the old schema generation. Default is off, which aborts them with `SCHEMA_RELOAD`. Only in code and changelog. Not in the docs.
- Subscriptions are closed on schema reload with `extensions.code: SUBSCRIPTION_SCHEMA_RELOAD`. Same as Apollo Router.
- Two query planners: the default JavaScript planner (graphql-tools stitching and delegation, `@graphql-tools/federation` turns the supergraph into stitched subschemas) and the Rust Query Planner from Hive Router (`@graphql-hive/router-runtime`, `--hive-router-runtime`, `HIVE_ROUTER_RUNTIME=true`, docs claim up to 3x faster per core). Rust planner does not support `additionalResolvers` and stitching hooks (`onDelegationPlan` and so on). `useQueryPlan` plugin exposes the plan. Rust runtime added `BatchFetch` plan nodes, EDFS, subscription entity resolution, remote cache (router-runtime 1.2 to 1.5).
- Supports Apollo Federation v1 and v2 supergraphs, including `@join__directive` (federation 4.4.0), progressive `@override(label:)`, `@provides`, `@interfaceObject`. I did not check every directive.
- Mesh features at runtime: `@transport` loads a transport per subgraph (`transports` option replaces the loader). `transportEntries` config per subgraph name, per kind (`*.http`) or `*`: `kind`, `location`, `headers` (with interpolation), `options` (`apq`, `useGETForHashedQueries`, `useContentTypeForGETRequests`, `subscriptions`).
- `additionalTypeDefs` and `additionalResolvers` at gateway level. `@resolveTo`, `@pubsubOperation(pubsubTopic, filterBy, result)` and `@pubsubPublish(pubsubTopic)` (publish a mutation result to a topic, 2.1.0) in the supergraph. `@pubsubPublish` and `@pubsubOperation` are only in the changelog, not the docs.
- Local execution and SDK: `runtime.sdkRequester` (2.9.0) for GraphQL Codegen `typescript-generic-sdk`, with automatic batching. `getExecutorForUnifiedGraph`, `getSdkRequesterForUnifiedGraph`.
- `unifiedGraphHandler` (experimental): replace the whole federation execution engine.
- White-label options (code): `productName`, `productDescription`, `productPackageName`, `productLogo`, `productLink`, `playgroundName`. Not documented.
- Landing page (`landingPage: false` to hide). GraphiQL is replaced by Hive Laboratory as the default editor (2.6.0). `--render-legacy-graphiql`. Offline GraphiQL by default (1.15.0).

## Hive Gateway: features (one line each)

Federation and routing:
- Progressive override: `progressiveOverride(label, context)` decides per request if an `@override(label:)` is active. Supports promises (2.3.0). Use with feature flags (LaunchDarkly example in e2e) or percentages.
- Automatic query batching to subgraphs: concurrent upstream calls to the same subgraph are merged into one request (graphql-tools `batch-execute`, aliased root fields). `__experimental__batchExecution`, `__experimental__batchDelegateOptions` tune it.
- Client request batching: `batching: true | { limit }` (GraphQL over HTTP batching RFC, array of operations). Default limit 10.
- Entity batching: `_entities` calls are batched by DataLoader per subgraph.

Subscriptions:
- Client side: SSE and `graphql-ws` WebSockets on the GraphQL endpoint. `disableWebsockets`. Yoga's incremental delivery over HTTP also applies.
- Upstream side, per subgraph with `transportEntries.<name>.options.subscriptions`: `http` with SSE, `ws` (`connectionParams` from context, `headers`), `http-callback` (Apollo HTTP callback protocol, needs a public gateway URL and `pubsub`). Mixed protocols per subgraph.
- Event-Driven Federated Subscriptions (EDFS): `@resolveTo(pubsubTopic: ...)` on a `Subscription` field. Events published to the broker by anyone. Payload only needs entity keys. The gateway fetches the other fields from subgraphs.
- PubSub (`@graphql-hive/pubsub`): `MemPubSub` (default), `NATSPubSub`, `NATSJetStreamPubSub` (replay with an opaque `cursor`, not in the docs), `RedisPubSub`. Custom `PubSub` interface with `publish`, `subscribe`, `subscribedTopics`, `dispose`. New interface in v2.
- Webhooks: `webhooks: true` binds `webhook:<method>:<path>` topics to HTTP routes so webhook calls feed subscriptions.

Auth and security:
- JWT (`jwt`, `@graphql-mesh/plugin-jwt-auth`, `useJWT`): `tokenLookupLocations` (`extractFromHeader`, `extractFromCookie`, custom function), `signingKeyProviders` (`createInlineSigningKeyProvider`, `createRemoteJwksSigningKeyProvider`), `tokenVerification` (`issuer`, `audience`, algorithms), `reject: { missingToken, invalidToken }`. Claims in `context.jwt`.
- JWT forwarding: `forward: { payload, token, extensionsFieldName }` puts the verified token or claims into the upstream request `extensions.jwt`. `useForwardedJWT` plugin on Yoga subgraphs reads it.
- Generic auth (`genericAuth`, from `@envelop/generic-auth`): modes `protect-all`, `protect-granular`, `resolve-only`. Federation directives `@authenticated`, `@requiresScopes` (also `@requiresScope` spelling in docs), `@policy` (policies resolved by a function, for example from a policy service). Mesh `@skipAuth` opens fields under `protect-all`. `extractScopes` customizes where scopes come from.
- HMAC upstream signature (`hmacSignature`, `@graphql-mesh/hmac-upstream-signature`): gateway signs each subgraph request with a shared secret. `useHmacSignatureValidation` plugin on the subgraph rejects unsigned or tampered requests.
- AWS SigV4 (`awsSigv4`, `@graphql-hive/plugin-aws-sigv4`): sign outgoing subgraph requests (for example to AWS Lambda or AppSync). Can also verify incoming SigV4 requests. Credentials from env or config, per subgraph.
- Armor built in (1.13.0): `maxTokens` (default 1000), `maxDepth` (default 6), `blockFieldSuggestions`, `maxAliases`, `maxDirectives`, character limit.
- Demand control (`demandControl`): IBM cost spec `@cost(weight)` and `@listSize(assumedSize, slicingArguments, sizedFields, requireOneSlicingArgument)` from subgraphs. `maxCost`, `listSize` (default list size), `operationTypeCost`, `fieldCost`, `typeCost`, `includeExtensionMetadata`. Cost is computed on the gateway query plan (per subgraph call). Error `COST_ESTIMATED_TOO_EXPENSIVE`. Directives are lost in `proxy` mode without a `schema`.
- Rate limiting (`rateLimiting`, `@rateLimit` directive in subgraphs): rules with `type`, `field`, `max`, `ttl` and one of `identifier` (template like `{context.headers.authorization}` or `{args.id}`), `identifyFn(ctx, args)` (2.10.0), `identityArgs`. Works with the Rust planner (2.3.0). Store via the gateway `cache`.
- CSRF prevention, CORS, `disableIntrospection` (with `disableIf`), HTTPS server (`sslCredentials`), custom HTTP agent for mTLS to subgraphs (`customAgent`), `maxHeaderSize`.
- Persisted documents: Hive App Deployments CDN (`type: 'hive'`, `endpoint`, `token`, layer 2 cache with `cacheTtlSeconds`, `cacheNotFoundTtlSeconds`, `cacheKeyPrefix`, since 2.4.0) or a custom `getPersistedOperation` store. `allowArbitraryDocuments` (boolean or function). APQ on client side and APQ toward subgraphs (`transportEntries` `options.apq`).
- Audit documents guide: `graphql-inspector audit` to find depth, alias and directive counts for armor limits.

Performance and resilience:
- Response caching (`responseCaching`): Yoga response cache plus gateway parts. Reads subgraph `Cache-Control` headers (for example from Apollo Server) or `@cacheControl` directives in the supergraph. Session-based and group-based caching, TTL per type or field, invalidation by mutation via entity identity. Works with the Rust planner.
- `cache` storage for all features: in-memory LRU (default), `RedisCacheStorage` (with AWS IAM auth, 2.11.0), `UpstashRedisCache`, `CloudflareKVCacheStorage`, `LocalForageCacheStorage`, file. `keyPrefix` on all backends (2.13.0).
- HTTP caching of upstream responses (`useHttpCache`): honors upstream `Cache-Control` and `ETag` for REST and GraphQL subgraphs.
- Deduplicate inflight requests: outbound (identical upstream requests share one response, on by default for queries in v2) and inbound (`inboundInflightRequestDeduplication`, identical client requests share one execution, runtime 2.8.0).
- Upstream retry (`upstreamRetry: { maxRetries, retryDelay, retryDelayFactor, shouldRetry }` or a per-subgraph function). Retries on 429, 5xx or `Retry-After`. Upstream timeout (`upstreamTimeout`, global or per subgraph). Error `TIMEOUT_ERROR`.
- Execution cancellation (`executionCancellation`) and upstream cancellation (`upstreamCancellation`) when the client disconnects.
- Request limits: `requestTimeout` (receive the request), `requestDeadline` (hard end-to-end limit, 2.7.0), `keepAliveTimeout`, `gracefulShutdownTimeout` (2.9.0).
- Compression (`contentEncoding`): gzip and deflate for client responses and subgraph traffic, both directions.
- Connection pooling via `customAgent` (`http.Agent` with `maxSockets`, keep-alive).
- Parse and validation caching (Yoga). `jit: true` (`--jit`) uses graphql-jit for execution.
- Concurrency: `fork` (`--fork`, `FORK`) runs Node cluster workers. Automatic forking was turned off in v2. Bun runs single process.
- `@defer` and `@stream` (`deferStream: true`) across subgraphs. File uploads (`multipart: true`, off by default in v2). Uploads are forwarded to subgraphs.

Headers and context:
- Header propagation: `propagateHeaders.fromClientToSubgraphs({ request, subgraphName })` and `fromSubgraphsToClient({ response, subgraphName })` (for example `set-cookie`).
- `requestId` (on by default): generates or forwards `x-request-id` and sends it upstream. Used by the logger.
- `cookies: true` adds `request.cookieStore`.
- `subgraphErrors`: control how subgraph errors show to clients. Error codes `DOWNSTREAM_SERVICE_ERROR`, `SCHEMA_RELOAD`, `SHUTTING_DOWN`, `UNAUTHENTICATED`, `PERSISTED_QUERY_NOT_FOUND`. `maskedErrors` on by default.

Observability:
- OpenTelemetry (`openTelemetry`, `@graphql-hive/plugin-opentelemetry`, `--opentelemetry [endpoint]`, `--opentelemetry-exporter-type otlp-http | otlp-grpc`): spans for HTTP, GraphQL operation, parse, validate, context, execute, subgraph execute, upstream fetch, cache hit/miss/write events. `spans` filter functions, `inheritContext`, `propagateContext`, custom spans and attributes, deterministic `samplingRate`, `ignoreRequest` API. Also usable in plain Yoga (subgraph traces). `@graphql-hive/gateway/opentelemetry/attributes` exports attribute names.
- Hive Tracing: OTEL traces to Hive Console (`--hive-trace-access-token`, `--hive-trace-endpoint`), with circuit breaker.
- Prometheus (`prometheus`): Envelop metrics plus `graphql_gateway_fetch_duration`, `graphql_gateway_subgraph_execute_duration`, `graphql_gateway_subgraph_execute_errors`. Grafana dashboard provided. StatsD, Sentry and New Relic via plugins.
- Health: `healthCheckEndpoint` (`/healthcheck`) and `readinessCheckEndpoint` (`/readiness`). I think readiness turns true once the schema is loaded.
- Hive Logger (`@graphql-hive/logger`, v2): levels, child loggers with attributes, JSON writer, redaction of sensitive fields, custom writers, Pino and Winston adapters, `LOG_LEVEL` env. `DEBUG=1` turns on debug plugins (`useFetchDebug`, `useSubgraphExecuteDebug`, `useDelegationPlanDebug`, `useCacheDebug` in code).
- Usage reporting (`reporting`): to Hive Console (`type: 'hive'`, `target`, token, client name and version from `graphql-client-name` or `x-graphql-client-name` headers) or Apollo GraphOS (`type: 'graphos'`). Experimental subgraph field-level metrics (count each schema coordinate in results).

Plugin API (gateway additions over Yoga and Envelop):
- `plugins: (ctx) => [...]` gets `{ fetch, log, cwd, pubsub, cache, openTelemetry }`.
- Hooks: `onFetch` (change URL, options, fetch function, response for every upstream HTTP call), `onSubgraphExecute` (change execution request or executor per subgraph), `onDelegationPlan`, `onDelegationStageExecute` (JS planner only), `onSchemaChange`, `onCacheGet`, `onCacheSet`, `onCacheDelete`, `onDispose`.
- `instrumentation` adds `subgraphExecute` and `fetch` wrappers on top of the Envelop/Yoga ones. `withState` scope `forSubgraphExecution`.
- `ExecutionRequest.subgraphName` (v2) for plugins.

MCP server (`@graphql-hive/plugin-mcp`, `useMCP`, 0.1.0 in 2026):
- Exposes chosen GraphQL operations as MCP tools at `/mcp` (Streamable HTTP). Methods `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`, `resources/templates/list`.
- Tool sources: inline query, named operations from `operationsPath` or `operationsStr`, per-request `loader`, Hive App Deployments persisted documents (0.2.0).
- Operation directives `@mcpTool(name, description, descriptionProvider, meta)`, `@mcpDescription(provider)`, `@mcpHeader(name)` (fill a variable from an HTTP header).
- Input overrides (alias, description, examples, default), output `path` extraction, output schema, `preprocess` and `postprocess` hooks, MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- Description providers: Langfuse prompts (by label or version) or custom. Change tool descriptions without a redeploy.
- Static resources and URI resource templates.

Testing and dev tooling:
- `@graphql-hive/gateway-testing` (`createGatewayTester`): in-process gateway with mocked subgraphs (typeDefs plus resolvers) or a proxy target. No network. Supports `await using`.
- Mocking (`useMock`, removed from built-ins in v2): mock fields and types, list lengths, stateful store (`MockStore`).
- Snapshot plugin (`useSnapshot`): record upstream HTTP responses to disk and replay them.

## Hive platform (brief)

- Hive Console (`graphql-hive/console`, MIT, self-hostable, also Hive Cloud SaaS): schema registry for single schema, schema stitching and Federation projects. Organization, project, target hierarchy.
- Hive CLI (`hive`): `schema:check`, `schema:publish`, `schema:delete`, `schema:fetch`, `schema:push` (immutable revision published later on deploy), `dev` (local composition, `--remote`), `app:create` and `app:publish` (App Deployments: persisted document sets per client version).
- Schema checks: breaking change detection with "conditional breaking changes" (a change is breaking only if usage data shows the field is used in a time window, with client filters). Schema policies (lint rules from graphql-eslint). GitHub integration for check status.
- Schema contracts: filtered public variants of a supergraph by `@tag`. External composition (bring your own composition service). CDN artifacts for supergraph, SDL, services, persisted documents. High-availability CDN with mirror.
- Usage insights per operation and client, schema explorer with field usage, unused and deprecated field lookup, metric alerts, Slack and webhook alerts, audit logs, SSO with OIDC, SCIM, roles and permissions, access tokens, GraphQL API for automation.
- Laboratory: GraphQL IDE with collections, history, environment variables, preflight scripts (OAuth token refresh). Default editor in Hive Gateway.
- `@meta(name, content)` via `@link(url: "https://specs.graphql-hive.com/hive/v1.0")`: ownership metadata shown in the explorer.
- Usage reporting clients: JS (`@graphql-hive/core`, Yoga, Envelop, Apollo Server, Apollo Router plugin), PHP (Lighthouse), Ruby (graphql-ruby), Rust, Go (gqlgen). Open usage report JSON spec. No Python client. A "Python Client for Graphene and Strawberry" is listed as a future integration (console issue #508). Python projects can still publish schemas with the CLI.
- Hive Router: separate Rust Federation router (MIT). Config for JWT, authorization (`@policy` with custom policies), demand control, persisted documents, coprocessors (external service called at request stages), a plugin system with hooks (I think plugins are written in Rust), header manipulation, dynamic subgraph routing, traffic shaping, subscriptions (SSE, multipart, incremental delivery, WebSockets, HTTP callback), OTEL. Competes with Apollo Router and Cosmo Router. Its query planner is also used by Hive Gateway's Rust planner.

## Upcoming and unreleased work

- Gateway open PRs (non-dependency): "Automatic Global Object Identification" (Relay `Node` across subgraphs, open since 2025-10), `@graphql-hive/semantic-introspection` (`__search` and `__definitions` schema additions for agents), MCP custom JSON-RPC methods, graceful reload for subscriptions and retry of subscriptions on schema reload, spread WebSocket closes over a shutdown window, `additionalTypeDefs` and `additionalResolvers` in Rust planner mode, dynamic `maxCost` function, tail-based sampling for Hive tracing, new `onQueryPlan` hook, schema coordinate on OTEL error events.
- Gateway `.changeset` has no pending entries at `ce516e3`.
- Mesh `.changeset`: dependency bumps and a Swagger body arg fix. An open PR reduces `website/` to the content served on the-guild.dev (v0 docs may go away from the repo).
- npm dist-tags `hive-router-query-planner` and `next` on gateway packages are older experiments.

## Not supported

- Mesh v1 does not serve anything. Hive Gateway is needed to run non-GraphQL sources. Other gateways need the `subgraph` workaround.
- Mesh v1 PostgreSQL and MongoDB handlers do not exist yet (only v0 PostGraphile and Mongoose handlers).
- Supergraph-level transforms in Mesh v1 (ignored in code, see below).
- Mesh v1 has no `merger` choice, no `bare` transforms, no `typeMerging`, `replaceField`, `resolversComposition`, `cache` or `rateLimit` transforms.
- Hive Gateway has no built-in coprocessor (Hive Router has one). Extensibility is via JS plugins.
- Rust planner mode: no `additionalResolvers`, limited schema extensions, no stitching hooks.
- No ORM or database layer, no schema builder. Hive Gateway is execution only.
- No Python client for Hive usage reporting.

## Docs and code disagree

- Mesh getting-started says top-level `composeConfig.transforms` transforms the supergraph. `compose-cli/src/getComposedSchemaFromConfig.ts` has that code commented out with `TODO`. The option is accepted and ignored. The migration page says root transforms are not supported.
- Mesh Thrift docs use `idl`, `hostName`, `port`, `path`. The v1 loader (`loaders/thrift/src/schema.ts`) takes `source`, `endpoint`, `serviceName`.
- Mesh PostgreSQL and MongoDB docs tell users to install `@omnigraph/postgresql` and `@omnigraph/mongoose`. Both are 404 on npm and missing from the repo.
- Mesh MySQL docs query `getProduct(where:)`. The code names the root field after the table (`product`), plus `count_<table>`, `insert_<table>`, `update_<table>`, `delete_<table>`.
- Mesh v1 docs do not list the RAML handler, OpenAPI `jsonApi`, `HATEOAS`, `fallbackFormat`, OData `batch` and `expandNavProps`, `createExtendTransform`, `createTypeReplaceTransform`. All exist in code.
- Hive Gateway CLI reference only shows the top-level `--help`. Subcommand flags `--hive-router-runtime`, `--apollo-uplink` (supergraph) and `--schema` (proxy) are missing from it. `--apollo-uplink` is not in any doc page.
- Hive Gateway config options in code but not in docs: `gracefulSchemaReload`, `unstable__forceLatest`, `__experimental__batchExecution`, `__experimental__batchDelegateOptions`, white-label `product*` options. `NATSJetStreamPubSub`, `@pubsubPublish`, `@pubsubOperation` are only in changelogs.
- Docs mention `@requiresScope` and `@requiresScopes`. The Federation directive is `@requiresScopes`. I think `@requiresScope` is a typo.

## Sources

- https://the-guild.dev/graphql/mesh/llms.txt and https://the-guild.dev/graphql/mesh/llms-full.txt (Mesh v1 docs, full text). Saved to `/tmp/mesh-hive-docs/`.
- https://the-guild.dev/graphql/hive/llms.txt and https://the-guild.dev/graphql/hive/llms-full.txt (Hive Console, Gateway, Router, Logger, Laboratory docs, full text). Saved to `/tmp/mesh-hive-docs/`.
- Pages used most: https://the-guild.dev/graphql/mesh/v1/getting-started, https://the-guild.dev/graphql/mesh/v1/source-handlers, https://the-guild.dev/graphql/mesh/v1/transforms, https://the-guild.dev/graphql/mesh/v1/schema-extensions, https://the-guild.dev/graphql/mesh/v1/type-merging, https://the-guild.dev/graphql/mesh/v1/migration-from-v0, https://the-guild.dev/graphql/hive/docs/gateway, https://the-guild.dev/graphql/hive/docs/api-reference/gateway-config, https://the-guild.dev/graphql/hive/docs/api-reference/gateway-cli, https://the-guild.dev/graphql/hive/docs/gateway/supergraph-proxy-source, https://the-guild.dev/graphql/hive/docs/gateway/subscriptions, https://the-guild.dev/graphql/hive/docs/gateway/other-features/custom-plugins, https://the-guild.dev/graphql/hive/docs/gateway/other-features/rust-query-planner, https://the-guild.dev/graphql/hive/docs/gateway/mcp
- Mesh v0 docs source: `website/src/content/docs/` in the Mesh repo.
- https://github.com/ardatan/graphql-mesh (shallow clone at `/tmp/graphql-mesh`, `master` at `70ed549`, 2026-10-07). Package CHANGELOGs.
- https://github.com/graphql-hive/gateway (shallow clone at `/tmp/hive-gateway`, `main` at `ce516e3`, 2026-10-08). Package CHANGELOGs, `e2e/` directory names.
- npm registry (`npm view`) for versions and dates. `gh release list` and `gh pr list` for releases and open PRs.
