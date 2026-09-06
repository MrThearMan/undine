# Apollo Server findings

Version checked: `@apollo/server` 5.5.1 (npm `latest`, 2026-05-05). Repo `main` at `0c22029` (2026-09-14). 5.0.0 shipped 2025-07-17.
Node.js 20+ (v24 recommended). Peer dependency `graphql` 16.11.0+. Built on graphql-js. See `graphql-js.md` for engine details. They are not repeated here.
Apollo Server 4 is end-of-life since 2026-01-26. Apollo Server 3 since 2024-10-22.
Schema input: `typeDefs` + `resolvers` (SDL-first via `@graphql-tools/schema`), or a prebuilt `schema` (`GraphQLSchema`, so any code-first builder works), or a `gateway`.
Apollo Server is an HTTP and request-pipeline layer. It is not a schema builder. It has no ORM integration, no filtering, no pagination, no dataloader.
Many features report to or depend on the proprietary Apollo GraphOS cloud (usage reporting, schema reporting, safelisting, operation limits).
Federation (`@apollo/subgraph`, `@apollo/gateway`) and the Router are out of scope for this file.

## Constructor (`new ApolloServer(options)`)

- `typeDefs`, `resolvers`, `schema`, `gateway`: schema source. Exactly one mode.
- `introspection`: default `true` unless `NODE_ENV=production`. When off, adds the `NoIntrospection` validation rule (error extension `validationErrorCode: INTROSPECTION_DISABLED`).
- `maxRecursiveSelections` (`boolean | number`, 4.12): validation rule that counts selections with named fragments inlined. `true` means limit 10,000,000. Runs before custom `validationRules`. Error code `MAX_RECURSIVE_SELECTIONS_EXCEEDED`.
- `hideSchemaDetailsFromClientErrors` (4.11): strips "Did you mean ...?" suggestions from validation errors. Same as installing `ApolloServerPluginDisableSuggestions()` (`@apollo/server/plugin/disableSuggestions`, a regex on the message).
- `validationRules`, `validationOptions` (`maxErrors`, 5.3), `parseOptions`, `executionOptions` (`maxCoercionErrors`, 5.3): passed to graphql-js.
- `dangerouslyDisableValidation` (4.10): skip validation entirely. For build-time validated operations.
- `fieldResolver`, `rootValue` (value or function of the parsed document): passed to graphql-js.
- `documentStore` (`KeyValueCache<DocumentNode> | null`): cache of parsed and validated documents keyed by query hash. Default `InMemoryLRUCache` about 30 MiB. A hit skips parse and validate. `null` disables it.
- `cache` (`KeyValueCache`): shared cache for APQ, response cache and plugins. Default bounded `InMemoryLRUCache` (about 30 MiB). Exposed as `server.cache`.
- `persistedQueries` (`{ cache, ttl } | false`): APQ settings. See below.
- `csrfPrevention` (`boolean | { requestHeaders }`): on by default. See below.
- `allowBatchedHttpRequests`: default `false`. Array body runs operations in parallel (`Promise.all`) and returns an array.
- `formatError(formattedError, error)`: rewrite each error before sending.
- `stringifyResult` (4.8, async since 4.10): custom JSON serializer for the response body.
- `includeStacktraceInErrorResponses`: default `true` unless `NODE_ENV` is `production` or `test`. Adds `extensions.stacktrace`.
- `status400ForVariableCoercionErrors`: default `true` in v5. Deprecated. Will be removed in v6.
- `logger` (`@apollo/utils.logger` `Logger` interface). Exposed as `server.logger` and on every plugin context.
- `stopOnTerminationSignals`: default on (not in `NODE_ENV=test` or serverless). Handles `SIGINT`/`SIGTERM` by calling `stop()` then re-sending the signal.
- `nodeEnv`: override `NODE_ENV` for the defaults above.
- `apollo` (`key`, `graphRef`, `graphId`, `graphVariant`) or env vars `APOLLO_KEY`, `APOLLO_GRAPH_REF`, `APOLLO_GRAPH_ID`, `APOLLO_GRAPH_VARIANT`: GraphOS link.
- `plugins`: array of plugin objects. `server.addPlugin()` adds more before `start()`. Factory functions are not accepted (v4 change).
- `legacyExperimentalExecuteIncrementally` (5.2): pass `legacyExecuteIncrementally` from `@yaacovcr/transform` to serve the old `deferSpec=20220824` format.
- Removed in v4: `dataSources`, `modules`, `mocks`/`mockEntireSchema`, `debug`, `formatResponse` (use `willSendResponse`), `executor`, `path`, built-in CORS and body parsing options, `gql` re-export, `ApolloError` and its subclasses.

## Server lifecycle and methods

- `server.start()`: runs `serverWillStart` hooks (and gateway schema load). Throws on failure so the process can crash before serving traffic.
- `startInBackgroundHandlingStartupErrorsByLoggingAndFailingAllRequests()`: sync start for serverless integrations. Startup errors fail all later requests with 500.
- `server.assertStarted(name)`: integrations call this to require `start()` first.
- `server.stop()`: runs `drainServer` hooks, then refuses new operations, then runs `serverWillStop` hooks (usage reporting flushes here).
- `server.executeOperation(request, { contextValue })`: run the full request pipeline without HTTP. For tests. Accepts `TypedQueryDocumentNode` for typed variables and data. Returns `{ http, body }` where `body.kind` is `'single'` or `'incremental'`.
- `server.executeHTTPGraphQLRequest({ httpGraphQLRequest, context })`: the entry point for web framework integrations.
- Serving a request before `start()` finishes, or during shutdown, returns 500.

## Plugin system (`ApolloServerPlugin<TContext>`)

- Plugins are plain objects with optional async hooks. Options come from a factory function you write (`myPlugin(options)`).
- Nested design: `serverWillStart` returns a `GraphQLServerListener`. `requestDidStart` returns a `GraphQLRequestListener`. `executionDidStart` returns a `GraphQLRequestExecutionListener`. State is shared through closures.
- End hooks: `parsingDidStart`, `validationDidStart`, `willResolveField` (and `executionDidStart` via `executionDidEnd`) may return a function called with the error (or errors, or result) when the phase ends.
- All hooks are async except `willResolveField` and `schemaDidLoadOrUpdate`. Since v4, `requestDidStart` hooks of different plugins run in parallel.
- Built-in plugins are auto-installed by condition. Installing a plugin yourself, or its `...Disabled()` twin from `@apollo/server/plugin/disabled`, stops the auto-install. A plugin and its disabled twin together is an error.
- Types for plugin authors: `GraphQLRequestContext` (`logger`, `cache`, `request`, `response`, `schema`, `contextValue`, `queryHash`, `document`, `source`, `operationName`, `operation`, `errors`, `metrics`, `overallCachePolicy`, `requestIsBatched`), `GraphQLServerContext` (`logger`, `cache`, `schema`, `apollo`, `startedInBackground`), `GraphQLSchemaContext` (`apiSchema`, `coreSupergraphSdl`).
- `requestContext.metrics` flags: `persistedQueryHit`, `persistedQueryRegister`, `responseCacheHit`, `captureTraces`, `startHrTime`, `forbiddenOperation`, `registeredOperation`, `queryPlanTrace`.
- Batched HTTP requests share one `requestContext.request.http` object across operations (4.1). `requestContext.requestIsBatched` tells plugins.

### Server lifecycle events

- `serverWillStart(serverContext)`: runs on `start()`. A throw fails startup. Returns listener with the next three.
- `drainServer()`: first step of `stop()`. Operations can still run. Used to close HTTP connections.
- `serverWillStop()`: after drain. New operations are refused. Flush telemetry here.
- `renderLandingPage()`: returns `{ html }` (string or async function called per request). At most one plugin may define it. Served for `GET` requests that prefer `text/html`.
- `schemaDidLoadOrUpdate({ apiSchema, coreSupergraphSdl })`: sync. Fires on load and on every gateway schema change.
- `startupDidFail({ error })`: top-level hook.
- `requestDidStart(requestContext)`: top-level hook. Returns the request listener.
- `unexpectedErrorProcessingRequest({ requestContext, error })`: top-level. For bugs or throwing plugins. The error is masked from the client.
- `contextCreationDidFail({ error })`: top-level. The user `context` function threw.
- `invalidRequestWasReceived({ error })` (4.11): top-level. Fires for HTTP-level bad requests, including CSRF blocks and malformed JSON or GET params. Not for malformed GraphQL.

### Request lifecycle events (in order)

- `didResolveSource`: the query string is known (from body or APQ cache). Not yet parsed.
- `parsingDidStart`: not called on a `documentStore` hit.
- `validationDidStart`: not called on a `documentStore` hit. Only valid documents are cached.
- `didResolveOperation`: operation and name are known. Resolvers have not run. Main place for extra checks with access to `contextValue`. A thrown `GraphQLError` becomes the response (default 500 unless `extensions.http.status` is set).
- `responseForOperation`: runs in series across plugins. The first non-null `GraphQLResponse` replaces execution. The response cache plugin uses this.
- `executionDidStart`: returns `{ executionDidEnd, willResolveField }`.
- `willResolveField({ source, args, contextValue, info })`: sync, per field. Returns an end hook with `(error, result)`. Not called in gateway mode.
- `didEncounterErrors`: errors from parse, validate or execute. With `@defer` only for the initial payload.
- `didEncounterSubsequentErrors(requestContext, errors)`: errors in later incremental payloads.
- `willSendResponse`: can mutate `response.body` and `response.http` (status, headers). Also called for error responses. Replaces v3 `formatResponse`.
- `willSendSubsequentPayload(requestContext, payload)`: per incremental payload. `payload.hasNext` is `false` on the last.

## Built-in plugins

- `ApolloServerPluginCacheControl({ defaultMaxAge, calculateHttpHeaders })` (`@apollo/server/plugin/cacheControl`): auto-installed. See caching.
- `ApolloServerPluginLandingPageLocalDefault(opts)` and `ApolloServerPluginLandingPageProductionDefault(opts)` (`@apollo/server/plugin/landingPage/default`): auto-installed by `NODE_ENV`.
- `ApolloServerPluginUsageReporting(opts)` (`@apollo/server/plugin/usageReporting`): auto-installed when `APOLLO_KEY` and `APOLLO_GRAPH_REF` are set and the schema is not a subgraph.
- `ApolloServerPluginSchemaReporting(opts)` (`@apollo/server/plugin/schemaReporting`): opt-in (`APOLLO_SCHEMA_REPORTING=true` or install).
- `ApolloServerPluginInlineTrace({ includeErrors })` (`@apollo/server/plugin/inlineTrace`): auto-installed in subgraphs (detected by `_Service.sdl`). Adds a protobuf trace in the `ftv1` response extension when the gateway sends `apollo-federation-include-trace: ftv1`.
- `ApolloServerPluginDrainHttpServer({ httpServer, stopGracePeriodMillis })` (`@apollo/server/plugin/drainHttpServer`): graceful shutdown for Node `http.Server`. Stops listening, closes idle connections, closes active ones when idle, force-closes after the grace period (default 10 s). `startStandaloneServer` does this itself.
- `ApolloServerPluginSubscriptionCallback({ logger, retry, fetcher })` (`@apollo/server/plugin/subscriptionCallback`, 4.9): Router callback protocol for federated subscriptions. Skips the normal request lifecycle. No metrics or tracing for these.
- `ApolloServerPluginDisableSuggestions()` (`@apollo/server/plugin/disableSuggestions`): removes "Did you mean" text.
- Disabled twins: `ApolloServerPluginCacheControlDisabled`, `ApolloServerPluginInlineTraceDisabled`, `ApolloServerPluginLandingPageDisabled`, `ApolloServerPluginSchemaReportingDisabled`, `ApolloServerPluginUsageReportingDisabled`.
- Separate packages: `@apollo/server-plugin-response-cache` (5.0.0), `@apollo/server-plugin-landing-page-graphql-playground` (unmaintained, Playground is retired).

## Error handling

- Errors are plain `GraphQLError` with `extensions.code`. v4 removed `ApolloError`, `AuthenticationError`, `ForbiddenError`, `UserInputError` and `error.extensions.exception`.
- `ApolloServerErrorCode` enum (`@apollo/server/errors`): `INTERNAL_SERVER_ERROR`, `GRAPHQL_PARSE_FAILED`, `GRAPHQL_VALIDATION_FAILED`, `PERSISTED_QUERY_NOT_FOUND`, `PERSISTED_QUERY_NOT_SUPPORTED`, `BAD_USER_INPUT`, `OPERATION_RESOLUTION_FAILURE`, `BAD_REQUEST`.
- `ApolloServerValidationErrorCode` enum: `INTROSPECTION_DISABLED`, `MAX_RECURSIVE_SELECTIONS_EXCEEDED`. Set as `extensions.validationErrorCode`, not as `code`.
- Any error without a code gets `code: INTERNAL_SERVER_ERROR`. Non-`GraphQLError` throws are wrapped.
- Docs recommend custom codes like `UNAUTHENTICATED` and `FORBIDDEN`. These are a convention only. They are not exported constants.
- `formatError(formattedError, error)`: mask or rewrite per error. `unwrapResolverError(error)` returns the original thrown error from a resolver-wrapped `GraphQLError`.
- `formatError` does not affect what goes to GraphOS. Usage reporting and inline trace mask errors by default (`<masked>` message, `maskedBy` extension). Options `sendErrors` / `includeErrors`: `{ masked: true }`, `{ unmodified: true }`, `{ transform(err) => err | null }`.
- HTTP status from errors: `new GraphQLError(msg, { extensions: { http: { status, headers: Map } } })` in a resolver or the `context` function. Plugins can also set `response.http.status` and headers. Conflicts between resolvers resolve arbitrarily.
- Status codes: 400 for parse, validation, variable coercion, CSRF block, batching disabled, bad body. 405 for mutation over GET or other methods. 415 for bad `Content-Type` on GET (5.5) or bad charset (standalone, 5.4). 500 for `context` throw, unexpected errors, not started or stopping. 200 otherwise, even with resolver errors.
- Stack traces in `extensions.stacktrace` by default in dev. When omitted, they are not available to the app either. Log in a plugin.

## HTTP transport

- `POST` with `application/json` body (`query`, `operationName`, `variables`, `extensions`). `GET` with URL params for queries only. Mutations over GET get 405.
- Non-string `operationName` or non-object `variables`/`extensions` in POST are rejected with 400 (4.2). Doubly-escaped JSON `variables` removed in v4.
- Response content type is negotiated from `Accept`: `application/json` (default), `application/graphql-response+json`, and `application/json; callback-spec` for the Router callback protocol. A code comment says the default may become `application/graphql-response+json`. It has not changed yet.
- The status code does not change with `application/graphql-response+json`. I think the graphql-over-http rule "4xx for request errors under the new media type" is met only because Apollo already uses 400 for those.
- Batching: `allowBatchedHttpRequests: true`. Not combinable with incremental delivery. Later operations win when two set the same header.
- No built-in body parsing or CORS in integrations since v4. The framework or its middleware does it. `startStandaloneServer` sets CORS and body parsing with no config options.
- No file uploads. `graphql-upload` (third party) works only if the client sends `Apollo-Require-Preflight`. Docs link a blog post that recommends signed URLs instead.
- No built-in health check since v4. Docs recommend `GET /graphql?query=%7B__typename%7D` with `apollo-require-preflight: true`, or a framework route.

## CSRF prevention

- `csrfPrevention` default `true` since v4 (added in 3.7).
- Rule: execute only if the request has a `Content-Type` that is not `text/plain`, `application/x-www-form-urlencoded` or `multipart/form-data`, or has a non-empty header from `requestHeaders`. Default headers: `x-apollo-operation-name`, `apollo-require-preflight`.
- `csrfPrevention: { requestHeaders: [...] }` replaces the header list. The `Content-Type` check stays.
- Blocked requests get 400 with a message that names the needed headers. Landing page requests are not checked.
- 5.5.0 security fix (GHSA-9q82-xgwf-vj6h): GET requests with a `Content-Type` other than `application/json` are rejected with 415. This covers a browser CORS bug that allowed XS-Search.
- Also blocks XS-Search timing attacks on GET queries, not only side effects.
- Integrations must reject POST bodies without `application/json`. Otherwise the CSRF guarantee does not hold (documented contract).

## Persisted queries

- Automatic persisted queries (APQ) only. On by default. Request shape: `extensions.persistedQuery = { version: 1, sha256Hash }`. Only version 1 is accepted.
- Hash miss returns `PERSISTED_QUERY_NOT_FOUND`. Client retries with query and hash. Server checks the hash equals SHA-256 of the query. With `persistedQueries: false`, returns `PERSISTED_QUERY_NOT_SUPPORTED`.
- Registration is written after validation and after plugins had a chance to throw. So only valid operations are stored.
- `persistedQueries.cache` (`KeyValueCache<string>`, default the server `cache`, key prefix `apq:`) and `persistedQueries.ttl` (seconds, `null` means no TTL, default none).
- Works over GET for CDN caching with Apollo Client `createPersistedQueryLink({ sha256, useGETForHashedQueries: true })`.
- Docs say APQ is a performance feature, not security. Trusted documents / safelisting ("persisted queries" in GraphOS) are a GraphOS plus Router feature. Apollo Server has no local safelist or allowlist mode.
- No build-time manifest loading in Apollo Server itself.

## Caching

### Cache control (`@cacheControl`)

- The user must add the SDL: `enum CacheControlScope { PUBLIC PRIVATE }` and `directive @cacheControl(maxAge: Int, scope: CacheControlScope, inheritMaxAge: Boolean) on FIELD_DEFINITION | OBJECT | INTERFACE | UNION`. Otherwise startup fails with an unknown directive error.
- Type-level hints apply to every field returning that type. Field-level hints override type-level ones.
- Dynamic hints: `cacheControlFromInfo(info)` from `@apollo/cache-control-types` returns `{ setCacheHint({ maxAge, scope }), cacheHint, cacheHintFromType(type) }`. `cacheHint.restrict()` can only tighten. `inheritMaxAge` is static only.
- Defaults: root fields and fields returning composite types get `maxAge: 0`. Non-root scalar fields inherit from the parent. `defaultMaxAge` changes the `0` default.
- Overall policy: lowest `maxAge` across fields, `PRIVATE` if any field is `PRIVATE`. Exposed as `requestContext.overallCachePolicy` (`CachePolicy` with `maxAge`, `scope`, `restrict`, `replace`, `policyIfCacheable()`).
- HTTP header: `Cache-Control: max-age=N, public|private` when cacheable. `Cache-Control: no-store` otherwise (since v4). Not cacheable if `maxAge` is 0, the response has errors, or it is incremental. Batches get one combined policy (4.1).
- `calculateHttpHeaders: false`: compute only. Docs show a custom plugin to emit `s-maxage` for CDNs.
- Works in subgraphs. `_entities` uses the concrete entity type hint. `__resolveReference` can set hints dynamically.

### Full response cache (`@apollo/server-plugin-response-cache`)

- `responseCachePlugin({ cache, sessionId, extraCacheKeyData, shouldReadFromCache, shouldWriteToCache, generateCacheKey })`.
- Uses `responseForOperation` to serve hits and `willSendResponse` to store. Caches queries only. Never caches responses with errors. Never caches incremental responses.
- TTL from the overall cache policy. `PRIVATE` responses are cached only when `sessionId` returns a value. With `sessionId`, public responses are stored twice: logged-in and logged-out.
- Default key: SHA-256 of JSON of `{ source, operationName, variables, extra, sessionMode, sessionId }`. Keys are prefixed `fqc:`.
- Sets the `Age` response header on hits. Sets `metrics.responseCacheHit`.
- No tag-based or entity-based invalidation. Docs (technote TN0010) show custom `generateCacheKey` prefixes plus Redis `SCAN` + `DEL` for manual eviction.

### Cache backends

- `KeyValueCache<V>` interface from `@apollo/utils.keyvaluecache` (`get`, `set(key, value, { ttl })`, `delete`).
- `InMemoryLRUCache` (wraps `lru-cache`). `PrefixingKeyValueCache` from the same package is used by Apollo Server to isolate feature keys. I think `ErrorsAreMissesCache` is also in that package (not verified).
- External stores via `keyv` and `KeyvAdapter` (`@apollo/utils.keyvadapter`). Docs cover Redis single, Sentinel, Cluster, and Memcached. Apollo no longer maintains its own Redis or Memcached backends.

## Landing pages

- `GET` with `Accept` that prefers `text/html` returns the landing page. `Accept: */*` still gets JSON.
- Local default: embedded Apollo Sandbox (IDE). Production default: a static page with a curl example, or an embedded Explorer when `graphRef` is given.
- Options: `version`, `footer`, `document`, `variables`, `headers`, `collectionId`/`operationId`, `includeCookies`, `embed` (`runTelemetry`, `initialState.pollForSchemaUpdates`, `initialState.sharedHeaders`, `endpointIsEditable`, `displayOptions.docsPanelState`, `showHeadersAndEnvVars`, `theme`, `persistExplorerState`).
- Assets load from Apollo CDNs (`embeddable-sandbox.cdn.apollographql.com`, `apollo-server-landing-page.cdn.apollographql.com`). A CSP header with a per-request nonce is set. There is no self-hosted IDE option. GraphiQL is not bundled.
- Custom landing page: any plugin with `renderLandingPage`. Disable with `ApolloServerPluginLandingPageDisabled()`.

## Usage reporting (GraphOS)

- Sends batched protobuf reports (`@apollo/usage-reporting-protobuf`) to GraphOS. Default interval about 1 minute. Operation signatures normalize the document. Per-field stats, duration histograms and traces.
- Options: `sendVariableValues` and `sendHeaders` (`{ none }` default, `{ all }`, `{ onlyNames }`, `{ exceptNames }`, `{ transform }` for variables), `sendErrors`, `sendTraces`, `fieldLevelInstrumentation` (sample rate number or async function returning an estimation multiplier), `includeRequest`, `generateClientInfo`, `overrideReportedSchema`, `sendUnexecutableOperationDocuments`, `sendReportsImmediately` (for Lambda), `fetcher`, `reportIntervalMs`, `maxUncompressedReportSize` (4 MB), `maxAttempts` (5), `minimumRetryDelayMs`, `requestTimeoutMs`, `logger`, `reportErrorFunction`, `endpointUrl`, `debugPrintReports`, `calculateSignature`.
- The values of `authorization`, `cookie` and `set-cookie` are never sent.
- Client awareness: `apollographql-client-name` and `apollographql-client-version` headers, or `generateClientInfo`.
- Parse and validation failures are grouped as "parse failure", "validation failure", "unknown operation name".
- Not for subgraphs. Subgraphs send inline traces to the Router instead.
- No local metrics exporter. No Prometheus. OpenTelemetry is only a link to the federation docs (I think it uses `@opentelemetry/instrumentation-graphql` from outside).

## Schema reporting (GraphOS)

- `ApolloServerPluginSchemaReporting({ initialDelayMaxMs, overrideReportedSchema, endpointUrl, fetcher })`. Needs `APOLLO_KEY`.
- Registers the schema on startup, then sends the schema hash as a heartbeat. A new version shows only when all instances report the same hash.
- Not supported for federation. Docs recommend the Rover CLI for CI publishing.

## Integrations

- `startStandaloneServer(server, { context, listen })` (`@apollo/server/standalone`): Node `http` server (not Express since v5). Fixed CORS and body parsing. Docs call it a getting-started tool.
- Official: `@as-integrations/express4` and `@as-integrations/express5` (`expressMiddleware(server, { context })`). Moved out of core in v5.
- Community (`@as-integrations/*`): AWS Lambda, Azure Functions, Cloudflare Workers, Google Cloud Functions, Fastify, Hapi, Koa, Next.js, h3/Nuxt, and more in the table.
- Integration contract: build an `HTTPGraphQLRequest` (`method`, `headers` as `HeaderMap`, `search`, `body`), call `executeHTTPGraphQLRequest`, write back `status`, headers and a body that is `{ kind: 'complete', string }` or `{ kind: 'chunked', asyncIterator }`.
- `ContextFunction<[Args], TContext>` type for typed per-integration context functions. Serverless function names should start with `start` (convention).
- `@apollo/server-integration-testsuite`: shared Jest test suite for integration authors.
- `context` function runs per request. Throwing a `GraphQLError` with `extensions.http` sets status and headers (default 500).

## Subscriptions

- Not handled by Apollo Server itself. No WebSocket, SSE, or multipart subscription transport in the package.
- Docs recipe: `graphql-ws` (`useServer({ schema, context })` from `graphql-ws/use/ws`) on a separate `ws` server, with `ApolloServerPluginDrainHttpServer` and a custom `drainServer` hook to close it.
- Subscriptions over `graphql-ws` bypass the Apollo plugin pipeline. So no plugin hooks, APQ, cache control or usage reporting for them.
- Pub/sub: `PubSub` and `withFilter` from `graphql-subscriptions` (in-memory, dev only). Production needs a `PubSubEngine` subclass (Redis, etc.).
- `subscriptions-transport-ws` is no longer documented.
- Federated subscriptions: only through the Router, via `ApolloServerPluginSubscriptionCallback` (HTTP callback protocol). Multipart HTTP subscriptions are a Router feature.

## Incremental delivery (`@defer`, `@stream`)

- Experimental. Works only with the exact pre-release `graphql@17.0.0-alpha.9` (5.1) or `17.0.0-alpha.2` (5.0 and earlier). Version is checked with string equality. With graphql 16 it is not available.
- graphql-js 17.0.0 final shipped 2026-06-15. Apollo Server 5.5.1 does not support it yet. The code only checks for `17.0.0-alpha.9`.
- The user must add `@defer` and `@stream` to the SDL (or pass `GraphQLDeferDirective`/`GraphQLStreamDirective`).
- Transport: `multipart/mixed` only. Client must send `Accept: multipart/mixed; incrementalSpec=v0.2`. Legacy `deferSpec=20220824` needs the `legacyExperimentalExecuteIncrementally` option (5.2). Without an accepted `multipart/mixed` type, an operation that uses `@defer` gets an error.
- Types: `...Alpha2` and `...Alpha9` suffixed types, for example `GraphQLExperimentalFormattedSubsequentIncrementalExecutionResultAlpha9`.
- Plugin hooks `willSendSubsequentPayload` and `didEncounterSubsequentErrors`. Not cacheable. Not combinable with batching. No SSE framing.

## Security and limits

- Introspection toggle (`introspection`). Suggestion hiding (`hideSchemaDetailsFromClientErrors`). Recursive selection limit (`maxRecursiveSelections`). Variable coercion error cap (`executionOptions.maxCoercionErrors`, graphql-js default 50). Validation error cap (`validationOptions.maxErrors`).
- No query depth limit, no cost or complexity analysis, no rate limiting, no token limit option of its own (only `parseOptions.maxTokens` from graphql-js). Docs point to GraphOS operation limits (Router) and the graphql-js production guide.
- No auth or permissions. Docs show context-based checks, resolver checks, model-level checks and custom directives via `@graphql-tools/utils` `mapSchema`.
- Standalone server: request body charset limited to UTF-8, UTF-16, UTF-32 (5.4 DoS fix).
- Proxy support for outgoing reporting requests: Node 24 `NODE_USE_ENV_PROXY=1`, or undici `EnvHttpProxyAgent` on Node 20/22, or a custom `fetcher`.

## Data, testing and tooling

- Data sources: no base class since v4. Put per-request clients in `context`. `RESTDataSource` (`@apollo/datasource-rest`) is the only Apollo-maintained one. It has request deduplication and HTTP caching. No dataloader in Apollo Server.
- Testing: `executeOperation` for pipeline tests without HTTP. End-to-end tests with `supertest` or similar are left to the user.
- Mocking: removed from core in v4. Use `addMocksToSchema` from `@graphql-tools/mock`.
- TypeScript types: GraphQL Code Generator (`@graphql-codegen/typescript-resolvers`) recipe. Not built in. `ApolloServer<TContext>` generic types `contextValue`.

## Not supported or not in scope

- No schema builder, ORM integration, filtering, ordering, pagination or optimizer.
- No built-in subscription transport. No SSE. No WebSocket server in the package.
- No file uploads (explicitly blocked by default via CSRF unless preflight header).
- No trusted documents / operation allowlist in Apollo Server. That is GraphOS plus Router.
- No depth limit, cost analysis or rate limiting.
- No auth, permissions or per-user schema visibility.
- No self-hosted GraphiQL or Sandbox assets. Landing pages load from Apollo CDNs.
- No built-in health check endpoint (removed in v4).
- No incremental delivery with graphql-js 17.0.0 final.
- No response cache invalidation API. No tag-based purge.
- No local metrics exporter. Usage reporting only targets GraphOS.
- No CORS or body parsing in integrations (delegated to the web framework).

## Sources

Repo: https://github.com/apollographql/apollo-server (shallow clone at `/tmp/apollo-server`, `main` at `0c22029`, 2026-09-14).

Docs read (repo `docs/source/` is the source of https://www.apollographql.com/docs/apollo-server):
- `api/apollo-server.mdx` (https://www.apollographql.com/docs/apollo-server/api/apollo-server)
- `integrations/plugins.mdx`, `integrations/plugins-event-reference.mdx` (https://www.apollographql.com/docs/apollo-server/integrations/plugins-event-reference)
- `builtin-plugins.md`, `api/plugin/cache-control.mdx`, `api/plugin/landing-pages.mdx`, `api/plugin/usage-reporting.mdx`, `api/plugin/schema-reporting.mdx`, `api/plugin/inline-trace.mdx`, `api/plugin/drain-http-server.mdx`, `api/plugin/subscription-callback.mdx`
- `data/errors.mdx` (https://www.apollographql.com/docs/apollo-server/data/errors), `data/subscriptions.mdx`, `data/fetching-data.mdx`, `data/context.mdx` (headings)
- `performance/apq.mdx` (https://www.apollographql.com/docs/apollo-server/performance/apq), `performance/caching.md` (https://www.apollographql.com/docs/apollo-server/performance/caching), `performance/cache-backends.mdx`, `performance/response-cache-eviction.mdx`
- `security/cors.mdx` (CSRF section, https://www.apollographql.com/docs/apollo-server/security/cors), `security/hardening-for-production.md`, `security/authentication.mdx` (headings)
- `workflow/requests.md` (https://www.apollographql.com/docs/apollo-server/workflow/requests), `workflow/build-run-queries.mdx` (headings)
- `integrations/integration-index.mdx`, `shared/integration-table.mdx`, `integrations/building-integrations.md`, `api/standalone.mdx`
- `monitoring/metrics.mdx`, `monitoring/health-checks.mdx`
- `migration.mdx` (v4 to v5), `migration-from-v3.mdx` (headings, removed options, removed features)
- `testing/testing.mdx`, `testing/mocking.mdx`, `schema/directives.md` (headings)
- `_sidebar.yaml` for the page list
- https://www.apollographql.com/docs/apollo-server/llms.txt returns 200 (an index of `.md` page links). https://www.apollographql.com/llms.txt returns 200. https://www.apollographql.com/docs/llms-full.txt returns 404. I used the repo source instead.

Changelog:
- `packages/server/CHANGELOG.md` (4.0 to 5.5.1, minor entries read in full for 5.x, skimmed for 4.x)
- `packages/plugin-response-cache/CHANGELOG.md` (headings)
- `CHANGELOG_historical.md` (v0 to v3, not read beyond the header)
- npm registry `@apollo/server` for dist-tags and release dates

Source files checked:
- `packages/server/src/index.ts`, `package.json` (exports map), `externalTypes/constructor.ts`, `externalTypes/plugins.ts`, `externalTypes/requestPipeline.ts`
- `packages/server/src/ApolloServer.ts` (introspection, media types, landing page negotiation), `requestPipeline.ts` (APQ), `runHttpQuery.ts`, `httpBatching.ts`, `incrementalDeliveryPolyfill.ts`
- `packages/server/src/errors/index.ts`, `validationRules/NoIntrospection.ts`, `plugin/disabled/index.ts`, `plugin/disableSuggestions/index.ts`, `plugin/landingPage/default/index.ts`, `plugin/usageReporting/options.ts`
- `packages/plugin-response-cache/src/ApolloServerPluginResponseCache.ts`
