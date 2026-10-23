# GraphQL Yoga + Envelop findings

Versions checked: `graphql-yoga` 5.24.1 and `@envelop/core` 5.6.1. Repo `main` at `6b8d0b6` (2026-09-24).
Envelop moved into the Yoga monorepo. https://github.com/graphql-hive/envelop now only has a README that points to `packages/envelop` in https://github.com/graphql-hive/graphql-yoga. The old `dotansimha/graphql-yoga` and `n1ru4l/envelop` URLs redirect to `graphql-hive`.
Peer dependency `graphql` 15, 16 or 17 (graphql-js 17 support since Yoga 5.22.0 and core 5.6.0). Yoga 5 needs Node.js 18+ (5.0.0 dropped Node 16).
Yoga executes with `@graphql-tools/executor` (a graphql-js fork with abort signals and incremental delivery). See `graphql-js.md` for engine details. They are not repeated here.
Yoga is an HTTP server layer built on the WHATWG Fetch API (`@whatwg-node/server`). It is not a schema builder. It has no ORM, filtering, pagination or optimizer. Schema comes from `createSchema` (wraps `makeExecutableSchema` from `@graphql-tools/schema`), or any `GraphQLSchema` (Pothos, gqtx, graphql-js).
Envelop is a transport-agnostic plugin system that wraps `parse`, `validate`, `contextFactory`, `execute` and `subscribe`. Yoga is one Envelop consumer. Hive Gateway is another.

## Maintenance status

- Actively maintained by The Guild. Last commit on `main`: `6b8d0b6`, 2026-09-24.
- npm `latest`: `graphql-yoga` 5.24.1 (2026-09-17), `@envelop/core` 5.6.1 (2026-09-16), `@graphql-yoga/plugin-response-cache` 3.26.1 (2026-09-17).
- Prerelease tags: `graphql-yoga` `alpha` 5.24.2-alpha (2026-09-24 build), `@graphql-yoga/plugin-response-cache` `alpha` 4.0.0-alpha, `@envelop/core` `alpha` 6.0.0-alpha (2026-04-20 build). I did not check what the 6.0.0 and 4.0.0 alphas change.
- Changesets workflow. One pending changeset on `main`: `@envelop/opentelemetry` patch (end resolver spans on error).

## Envelop core (`@envelop/core`)

- `envelop({ plugins, enableInternalTracing? })` returns `getEnveloped(initialContext)`. That returns `{ parse, validate, contextFactory, execute, subscribe, schema }` bound to the plugin chain. The server calls these itself.
- `useEngine({ parse, validate, specifiedRules, execute, subscribe })`: pick the GraphQL engine (graphql-js, graphql-jit, a fork). Required in plain Envelop. Yoga sets it.
- `useSchema(schema)`: set the schema.
- `useSchemaByContext(ctx => schema)`: pick a schema per request (for example public vs private schema).
- `useValidationRule(rule)`: add a graphql-js `ValidationRule`.
- `useExtendContext(async ctx => ({...}))`: merge fields into the context.
- `useErrorHandler(fn)`: callback per error from any phase. Handles incremental execution errors since 5.5.0.
- `useMaskedErrors({ maskError?, errorMessage? })`: replace non-`GraphQLError` errors with `Unexpected error.`.
- `useLogger({ logFn(eventName, args) })`: log `execute-start`, `execute-end`, `subscribe-start`, `subscribe-end`.
- `usePayloadFormatter((result, executionArgs) => result | false)`: rewrite the result before it is returned.
- `useEnvelop(otherEnvelop)`: compose a shared base envelop (org-wide auth, tracing, logging) into another one.
- `enableInternalTracing: true`: the docs say it adds `extensions._envelopTracing` with ms per phase. The option is only declared in `create.ts` and is not used anywhere in the code (see "Docs and code disagree").
- Helpers: `handleStreamOrSingleExecutionResult`, `isAsyncIterable`, `mapAsyncIterator`, `errorAsyncIterator`, `finalAsyncIterator`, `makeExecute`, `makeSubscribe`, `isIntrospectionOperationString`, `documentStringMap` (5.4.0).
- `withState(getState => plugin)` (core 5.3.0, Yoga 5.14.0): per-scope plugin state kept in `WeakMap`s. Scopes `forOperation`, `forRequest` (Yoga), `forSubgraphExecution` (Hive Gateway). Replaces ad hoc `WeakMap` or context mutation.

## Envelop plugin hooks (`Plugin` in `@envelop/types`)

- Hooks run in plugin array order (FIFO). "Before" hooks return an optional "after" callback. Closures carry state between the two.
- `onPluginInit({ setSchema, plugins, addPlugin, registerContextErrorHandler })`: once at init. `addPlugin` inserts in place since core 5.0.0 (breaking change for order).
- `onEnveloped({ context, extendContext, setSchema })`: once per `getEnveloped` call (per request).
- `onSchemaChange({ schema, replaceSchema })`: fires when any plugin replaces the schema (gateways, `useDeferStream` adding directives). Not fired back to the plugin that replaced it.
- `onParse({ params, parseFn, setParseFn, setParsedDocument, context, extendContext })` then after `({ result, replaceParseResult })`. Used for parser caches, custom parsers (fragment arguments).
- `onValidate({ params, validateFn, setValidationFn, addValidationRule, setResult, context, extendContext })` then after `({ valid, result, setResult })`.
- `onContextBuilding({ context, extendContext, breakContextBuilding })` then after `({ context })`.
- `onExecute({ args, executeFn, setExecuteFn, setResultAndStopExecution, extendContext, context })` returns `{ onExecuteDone({ result, setResult }) }`. `result` may be an `AsyncIterable` (defer, stream, live queries).
- `onSubscribe({ args, subscribeFn, setSubscribeFn, setResultAndStopExecution, extendContext, context })` returns `{ onSubscribeResult, onSubscribeError }`.
- `context` field added to `onExecute` and `onSubscribe` payloads in core 5.1.0.
- No per-field resolver hook in core. Use `@envelop/on-resolve` (below).

## Instrumentation API (`@envelop/instrumentation`, core 5.2.0, Yoga 5.13.0)

- A plugin may have an `instrumentation` object. Each entry wraps one whole phase, including all plugin hooks for that phase. It sees no phase input or output. Meant for spans and timing.
- Envelop instruments: `init`, `parse`, `validate`, `context`, `execute`, `subscribe`. Sync for `init`, `parse`, `validate`, `context`. `execute` and `subscribe` may be async.
- Yoga adds: `request` (whole HTTP request incl. `onRequest`/`onResponse`), `requestParse`, `operation` (once per GraphQL operation, so per batch item), `resultProcess`.
- Signature `(payload, wrapped) => ...`. `wrapped()` must always be called.
- Default composition follows plugin order (first plugin is outermost). `composeInstrumentation([...])`, `chain`, `getInstrumentationAndPlugin` allow manual ordering.

## Yoga plugin hooks (HTTP layer, `Plugin` from `graphql-yoga`)

- Order: `onRequest` then `onRequestParse` then `onParams` then Envelop `onParse`, `onValidate`, `onContextBuilding`, `onExecute`/`onSubscribe` then `onExecutionResult` then `onResultProcess` then `onResponse`.
- `onYogaInit({ yoga })`: access the Yoga instance at init. `yoga.graphqlEndpoint` is writable after init (5.20.0).
- `onRequest({ request, url, serverContext, fetchAPI, endResponse })`: every HTTP request, GraphQL or not. `endResponse(response)` short-circuits. Errors are not caught (can crash `node:http`).
- `onRequestParse({ request, url, setRequestParser, endResponse })` returns `{ onRequestParseDone({ requestParserResult, setRequestParserResult }) }`. Custom request body formats. `endResponse` short-circuits since 5.21.0. A request parser may also return a `Response`.
- `onParams({ params, setParams, setResult, setParamsHandler, request, context, fetchAPI })`: after `GraphQLParams` extraction. `setResult` skips execution (response cache, persisted operations, APQ use this). `setResult` accepts an `AsyncIterable` since 5.2.0. `setParamsHandler` (5.11.0) replaces or wraps the whole pipeline (for example to run it in `AsyncLocalStorage`). Initial context injected since 5.9.0.
- `onExecutionResult({ result, setResult, request, context })` (5.7.0): once per operation. Batched requests call it per item.
- `onResultProcess({ request, result, setResult, resultProcessor, setResultProcessor, acceptableMediaTypes, serverContext })`: choose the response format per `Accept`. Once per HTTP request.
- `onResponse({ request, response, serverContext })`: after the response is built. Mutate headers here. Errors not caught.
- `onDispose()`: cleanup when the Yoga instance is disposed.
- Yoga is also a `@whatwg-node/server` adapter, so `@whatwg-node/server` plugins work (`useCookies` from `@whatwg-node/server-plugin-cookies`).

## `createYoga(options)`

- `schema`: `GraphQLSchema`, or a (async) factory `({ request, ...serverContext }) => schema` called per request (per-viewer schema).
- `context`: object, promise, or (async) function of the initial context. Merged into `YogaInitialContext` (`request`, `params`, `waitUntil`, plus server context such as `req`/`res` on Node or `FetchEvent` on Workers).
- `graphqlEndpoint` (default `/graphql`, a URL Pattern, so `/graphql/:document_id?` works). `healthCheckEndpoint` (default `/health`).
- `plugins`: Envelop and Yoga plugins mixed in one array.
- `maskedErrors`: `true` by default. `{ maskError(error, message, isDev), errorMessage, isDev }`. `isDev` defaults to `NODE_ENV=development`, which adds `extensions.originalError` with message and stack. `maskError` is exported for fallback.
- `logging`: `true`, `false`, a level (`debug`, `info`, `warn`, `error`) or a custom logger. `DEBUG=1` env enables debug. `createLogger` exported from `@graphql-yoga/logger`.
- `cors`: `{ origin, methods, allowedHeaders, exposedHeaders, credentials, maxAge }`, a per-request function, or `false`. Default is `Access-Control-Allow-Origin: *` on preflight.
- `graphiql`: `true`, `false`, options or `(request, serverContext) => options`. Default on (only for `GET` with `Accept: text/html`). Options include `defaultQuery`, `defaultTabs`, `headers`, `defaultHeaders`, `additionalHeaders`, `shouldPersistHeaders`, `subscriptionsProtocol` (`SSE`, `GRAPHQL_SSE`, `WS`, `LEGACY_WS`), `method`, `useGETForQueries`, `endpoint` (5.11.0), `title`, `logo`, `favicon` (5.15.0), `editorTheme`, `keyMap`, `timeout`, `retry`, `externalFragments`, `maxHistoryLength`.
- `renderGraphiQL`: swap the IDE. `@graphql-yoga/render-graphiql` bundles GraphiQL for offline use (default loads from unpkg CDN). `@graphql-yoga/render-apollo-sandbox` serves Apollo Sandbox.
- `landingPage`: `true`, `false`, or a renderer returning a `Response` (5.5.0). Shown on 404.
- `parserAndValidationCache`: on by default. `false` or `{ documentCache, errorCache, validationCache }` (any `get`/`set` store). Parse and validation results are cached by document string.
- `batching`: default off. `true` (limit 10) or `{ limit }`. Array body. Over the limit returns HTTP 413.
- `multipart`: file uploads on by default. `false` disables.
- `maxRequestBodySize` (5.24.0): default 25 MB. HTTP 413 on `Content-Length` or while streaming (covers chunked bodies). `false` disables. Malformed multipart now returns 400.
- `extraParamNames` (5.6.0): allow extra top-level body keys (for example Relay `doc_id`). Unknown keys are otherwise a 400.
- `allowedHeaders: { request, response }` (5.16.0): strip headers not in the list.
- `fetchAPI`: custom Fetch ponyfill. `createFetch({ formDataLimits: { fileSize, files, fieldSize, headerSize } })` from `@whatwg-node/fetch` sets upload limits (Node only).
- `disposeOnProcessTerminate`: dispose on process exit signals (Node).
- `id`, `version` property (5.8.0).

## Default plugin preset (built into `createYoga`)

- `useHealthCheck` (liveness `GET /health` returns 200). `useCORS`. `useGraphiQL`. `useUnhandledRoute` (landing page).
- Request parsers: `GET` query string, `POST` JSON, `POST` multipart (GraphQL multipart request spec), `POST application/graphql` string, `POST application/x-www-form-urlencoded`.
- `useResultProcessors`: picks `text/event-stream` (SSE), `multipart/mixed` (incremental delivery) or `application/graphql-response+json`/`application/json` from `Accept`.
- `useLimitRequestBodySize`, `useParserAndValidationCache`, `useLimitBatching`, `useCheckGraphQLQueryParams`, `useCheckMethodForGraphQL`, `usePreventMutationViaGET` (mutations over GET rejected), `useMaskedErrors`, `useHTTPValidationError`.
- GraphQL over HTTP spec compliant per the `graphql-http` audit (Apollo Server is not, per the Yoga docs).

## Yoga core extras (in `graphql-yoga`)

- `useReadinessCheck({ endpoint = '/ready', check })`: readiness probe. Throw or return `false` for 503.
- `useExecutionCancellation()` (5.3.0, experimental): abort resolver execution when the client disconnects. `context.request.signal` is an `AbortSignal` to pass to `fetch` or DB calls. Needs `handleNodeRequestAndResponse` in Fastify, Koa, Hapi.
- `useErrorCoordinate()` (5.17.0, experimental): sets `error.coordinate` (schema coordinate of the failing resolver, spec proposal PR 1200). Not serialized by default.
- `context.waitUntil(promise)`: background work that is awaited on dispose. Works outside Cloudflare too.
- `yoga.dispose()` and `await using yoga = createYoga(...)` (explicit resource management).
- `yoga.fetch(url, init)`: in-process request for tests. `yoga.handleNodeRequestAndResponse(req, res, ctx)` for Node frameworks.
- `extensions.http` on `GraphQLError`: `{ status, headers }` set the HTTP status and headers. Highest status wins. Stripped from the response body. Only for the first payload of streams.
- `extensions.code` set for Yoga's own HTTP and validation errors (5.12.0).

## Subscriptions

- Default transport: GraphQL over SSE "distinct connections mode" on the normal endpoint. Client sends `Accept: text/event-stream`. Works over `GET` and `POST`. Events `next` and `complete`. Keep-alive comment `:\n\n` sent at start and every 12 s.
- `useGraphQLSSE({ endpoint = '/graphql/stream' })` (`@graphql-yoga/plugin-graphql-sse`): adds "single connection mode" from the `graphql-sse` protocol. Uses all Envelop plugins.
- WebSocket: not built in. Wire `graphql-ws` `useServer` to `yoga.getEnveloped(...)` by hand (docs recipe). GraphiQL can then use `subscriptionsProtocol: 'WS'`.
- Resolvers use `subscribe` returning an `AsyncIterable` (async generators or `Repeater`).
- `createPubSub<Topics>({ eventTarget })` (`@graphql-yoga/subscription`, re-exported): typed topics as tuples. Topics with a dynamic ID (`pubSub.subscribe('user:followerCount', userId)`).
- Operators `pipe`, `map`, `filter`. `Repeater`, `Repeater.merge`, buffers (`FixedBuffer`, `SlidingBuffer`, `DroppingBuffer`) re-exported from `@repeaterjs/repeater`. Recipes for an initial value and for merging topics.
- Distributed: `createRedisEventTarget({ publishClient, subscribeClient, serializer })` (`@graphql-yoga/redis-event-target`, ioredis). Custom brokers implement `TypedEventTarget` (`@graphql-yoga/typed-event-target`). Payloads must be JSON.
- `useContextValuePerExecuteSubscriptionEvent(fn)` (`@envelop/execute-subscription-event`): new context (fresh DataLoaders) per subscription event, or `onEnd` callback per event.
- Live queries: `useLiveQuery({ liveQueryStore, applyLiveQueryPatchGenerator })` (`@envelop/live-query`). `@live` directive on a query. `InMemoryLiveQueryStore.invalidate('Query.greetings' | 'User:1')` re-runs affected queries and pushes results. Optional JSON diff patches (`@n1ru4l/graphql-live-query-patch-jsondiffpatch`).

## File uploads

- GraphQL multipart request spec, on by default. Declare `scalar File`. Resolvers get WHATWG `File`/`Blob` (`file.text()`, `file.arrayBuffer()`, `file.stream()`, `file.name`).
- Limits via `fetchAPI: createFetch({ formDataLimits })` (Node) and `maxRequestBodySize`.
- Not supported: resumable or chunked uploads, presigned-URL flows (docs show a manual S3 `PutObjectCommand` recipe only).

## Persisted operations and APQ

- `usePersistedOperations` (`@graphql-yoga/plugin-persisted-operations`): allowlist. Default id from APQ-style `extensions.persistedQuery.sha256Hash`.
- Options: `getPersistedOperation(key, request, context)` (sync or async, may return a string or a parsed `DocumentNode`), `extractPersistedOperationId(params, request, context)` (Relay `doc_id`, query param, header, or URL path recipes), `allowArbitraryOperations` (boolean or per-request function), `skipDocumentValidation` (trust build-time validation), `customErrors` (`notFound`, `keyNotFound`, `persistedQueryOnly` as string, `GraphQLError` options or factory).
- Errors: `PersistedOperationNotFound`, `PersistedOperationKeyNotFound`, `PersistedOperationOnly`.
- Multiple stores selected per request (for example by `client-name` header) inside `getPersistedOperation`.
- Recommended extraction: GraphQL Code Generator `client` preset (persisted documents) or `graphql-codegen-persisted-query-ids`.
- Envelop version `@envelop/persisted-operations`: `store` (instance or per-context function), `InMemoryStore`, `JsonFileStore` (`loadFromFile`, `loadFromFileSync`), `onlyPersisted`, `extractOperationId`, `onMissingMatch`. Id sent in `query`. Docs say to prefer the Yoga plugin.
- `useAPQ({ store, hash, responseConfig: { forceStatusCodeOk } })` (`@graphql-yoga/plugin-apq`): Apollo APQ protocol. Default store is LRU (`max` 1000, `ttl` 36000 ms, `createInMemoryAPQStore`). Async `get`/`set` stores (Redis via Keyv). Errors `PERSISTED_QUERY_NOT_FOUND` (404) and `PERSISTED_QUERY_MISMATCH` (400). Docs warn APQ gives no security.

## Response caching

- `useResponseCache` (`@graphql-yoga/plugin-response-cache`, wraps `@envelop/response-cache`). The Yoga variant short-circuits in `onParams`, before parse and validate.
- `session(request, context)` required: cache key per user. Return `null` for a global cache.
- `ttl` (global, ms), `ttlPerType`, `ttlPerSchemaCoordinate` (`'Query.lazy'`). Lowest TTL of all types in the result wins.
- `scopePerSchemaCoordinate` (`PUBLIC`/`PRIVATE`): private data is only cached with a session.
- `@cacheControl(maxAge, scope)` directive on types and fields. `cacheControlDirective` SDL export.
- `enabled(request, context)`, `shouldCacheResult`, `ignoredTypes`, `idFields` (default `id`), `buildResponseCacheKey`, `getDocumentString`, `onTtl` (change TTL per result), `includeExtensionMetadata` (`extensions.responseCache` with `hit`, `didCache`, `ttl`, `invalidatedEntities`).
- The plugin rewrites the document to add `__typename` and id fields (aliased `__responseCacheTypeName`, `__responseCacheId`) to track entities. They are stripped before sending.
- `invalidateViaMutation` (default `true`): mutation results auto-invalidate cached queries that contain the same `typename:id`.
- Manual invalidation: `cache.invalidate([{ typename: 'User', id: '1' }])` or by type only. Needs `createInMemoryCache()` passed in.
- Cache backends: in-memory LRU, `@envelop/response-cache-redis` (`createRedisCache({ redis })`, Node only), `@envelop/response-cache-cloudflare-kv` (`createKvCache`).
- HTTP caching: sends `ETag` and `Last-Modified`. Answers `If-None-Match` with 304.
- Introspection results can be cached with `ttlPerSchemaCoordinate`.

## Incremental delivery (`@defer`, `@stream`)

- `useDeferStream()` (`@graphql-yoga/plugin-defer-stream`). Marked experimental.
- Adds `@defer`/`@stream` directives to the schema if missing (via `onSchemaChange`). Adds validation rules `DeferStreamDirectiveLabelRule`, `DeferStreamDirectiveOnRootFieldRule`, `StreamDirectiveOnListFieldRule` and a replacement `OverlappingFieldsCanBeMergedRule`.
- Transport: `multipart/mixed` or SSE, chosen by `Accept`.
- Docs recommend `Repeater` over `async *` for stream resolvers to avoid leaked timers after client cancel.

## Security plugins

- `useDisableIntrospection({ isDisabled(request, context) })` (`@graphql-yoga/plugin-disable-introspection`). Envelop version `@envelop/disable-introspection` uses `disableIf({ context, params })` and graphql-js `NoSchemaIntrospectionCustomRule`.
- `useCSRFPrevention({ requestHeaders = ['x-graphql-yoga-csrf'] })` (`@graphql-yoga/plugin-csrf-prevention`): non-preflighted requests must carry one of the headers. 403 otherwise. Opt-in (Apollo Server has it on by default).
- `useJWT` (`@graphql-yoga/plugin-jwt`): `signingKeyProviders` (`createInlineSigningKeyProvider`, `createRemoteJwksSigningKeyProvider({ jwksUri })`), `tokenLookupLocations` (`extractFromHeader({ name, prefix })`, `extractFromCookie({ name })` with `useCookies`, `extractFromConnectionParams({ name })` for graphql-ws, or a custom function), `tokenVerification` (`issuer`, `audience`, `algorithms`), `reject: { missingToken, invalidToken }` (401), `extendContext` (default `context.jwt` with `payload` and `token`).
- Yoga docs recommend GraphQL Armor (Escape) for public APIs: `costLimitPlugin`, `maxTokensPlugin`, `maxDepthPlugin`, `maxDirectivesPlugin`, `maxAliasesPlugin`, `blockFieldSuggestionsPlugin`. Third-party, not part of the monorepo.
- Private APIs: docs recommend persisted operations only.

## Envelop plugin ecosystem (one line per plugin)

In the monorepo (`packages/envelop/plugins/`), published as `@envelop/<name>`:

- `useResponseCache` (`response-cache` 9.3.1): execution-level response cache. Same options as the Yoga plugin. `cache` may be a per-context function.
- `createRedisCache` (`response-cache-redis`): Redis backend. Supports invalidation by entity.
- `createKvCache` (`response-cache-cloudflare-kv`): Cloudflare KV backend.
- `useDepthLimit({ maxDepth, ignore })` (`depth-limit`): wraps `graphql-depth-limit` as a validation rule.
- `useRateLimiter({ identifyFn, configByField, rateLimitDirectiveName, transformError, onRateLimitError, interpolateMessage, store })` (`rate-limiter` 10.2.1): `@rateLimit(max, window, message, identityArgs, arrayLengthField, readOnly, uncountRejected)` directive per field. `configByField` sets limits without SDL and supports an `identifier: "{args.id}"` template (10.1.0). `InMemoryStore`, `RedisStore`. Message interpolation `{{ id }}`.
- `useResourceLimitations({ nodeCostLimit, paginationArgumentMaximum, paginationArgumentMinimum, paginationArgumentScalars, extensions })` (`resource-limitations`): GitHub-style node count cost limit on connections (`first`/`last` required and bounded).
- `useGenericAuth({ resolveUserFn, validateUser, mode, contextFieldName, authDirectiveName, extractScopes, fetchPolicies, rejectUnauthenticated })` (`generic-auth` 11.2.1): modes `protect-all` (with `@skipAuth`), `resolve-only` (`context.validateUser()`), `protect-granular` (with `@authenticated`). Also `@requiresScopes(scopes: [[String!]!]!)` (outer list OR, inner list AND) and `@policy` with async `fetchPolicies`. Works via directives or `extensions.directives`. Checks run on the selection set before execution. Error code `UNAUTHORIZED_FIELD_OR_TYPE`. Partial execution when rejection is off. The README calls the option `rejectUnauthorized` but the code uses `rejectUnauthenticated`.
- `useOperationFieldPermissions({ getPermissions(context) })` (`operation-field-permissions`): allowlist of schema coordinates (`'Query.greetings'`, `'Type.*'`) per viewer. Rejects the operation in validation with "Insufficient permissions for selecting 'Query.foo'".
- `useDisableIntrospection({ disableIf })` (`disable-introspection`): see above.
- `useImmediateIntrospection()` (`immediate-introspection`): skip context building for operations that only select introspection fields.
- `useFilterAllowedOperations(['query', ...])` (`filter-operation-type`): validation rule that allows only listed operation types.
- `useExtendedValidation({ rules, onValidationFailed, rejectOnErrors })` (`extended-validation`): validation rules that run at execute time with access to variables and context. Ships `OneOfInputObjectsRule` (`@oneOf` on inputs and on field argument sets).
- `usePersistedOperations` (`persisted-operations`): see above.
- `useParserCache({ documentCache, errorCache })` (`parser-cache`): LRU parse cache. Built into Yoga.
- `useValidationCache({ cache })` (`validation-cache`): LRU validation cache. Built into Yoga.
- `useGraphQlJit(compilerOptions, { enableIf, cache, onError })` (`graphql-jit`): replace `execute` with `graphql-jit` compiled queries.
- `useDataLoader(name, ctx => new DataLoader(...))` (`dataloader`): new DataLoader per context.
- `useOnResolve(fn, { skipDefaultResolvers })` (`on-resolve`): per-field hook with `replaceResolver` and an after callback with `setResult`. Base for tracing plugins.
- `useGraphQLMiddleware([middlewares])` (`graphql-middleware`): run `graphql-middleware` stacks such as `graphql-shield`.
- `useGraphQLModules(app)` (`graphql-modules`): GraphQL Modules DI integration.
- `useLiveQuery` (`live-query`): see Subscriptions.
- `useContextValuePerExecuteSubscriptionEvent` (`execute-subscription-event`): see Subscriptions.
- `useFragmentArguments()` (`fragment-arguments`): parser with fragment arguments (graphql-js PR 3152). README says not for production.
- `usePreloadAssets()` (`preload-assets`): `context.registerPreloadAsset(url)` adds URLs to `extensions.preloadAssets` for client preloading.
- `useOpenTelemetry(options, tracerProvider)` (`opentelemetry`): spans per phase and optional per resolver.
- `usePrometheus(options)` (`prometheus`): histograms and counters per phase, per resolver, errors, deprecated field usage, schema changes. Custom registry and labels.
- `useSentry(options)` (`sentry`): spans and error capture with operation data.
- `useStatsD(options)` (`statsd`): StatsD/DataDog metrics.
- `useNewRelic(options)` (`newrelic`): New Relic transaction naming and segments.
- `useApolloTracing()` (`apollo-tracing`): legacy `extensions.tracing` format.
- `useApolloFederation({ gateway })` (`apollo-federation`): run Apollo Gateway execution through Envelop.
- `useApolloDataSources(dataSources)` (`apollo-datasources`): Apollo Server style `dataSources` in context.
- `useApolloServerErrors()` (`apollo-server-errors`): Apollo Server error formatting.
- `useAuth0({ domain, audience, extractTokenFn, headerName, tokenType, preventUnauthenticatedAccess, extendContextField, jwksClientOptions, jwtVerifyOptions, onError })` (`auth0`): Auth0 JWT verification.

Listed on the Envelop plugin hub but outside the monorepo:

- `useHive` (`@graphql-hive/envelop`): Hive schema registry usage reporting.
- `maxAliasesPlugin`, `maxDepthPlugin`, `maxDirectivesPlugin`, `maxTokensPlugin`, `blockFieldSuggestions` (`@escape.tech/graphql-armor-*`): limits and suggestion blocking.
- `useInngest` (`envelop-plugin-inngest`): send operation events to Inngest.

## Yoga-only plugin packages (`packages/plugins/`)

- `@graphql-yoga/plugin-response-cache`, `plugin-persisted-operations`, `plugin-apq`, `plugin-defer-stream`, `plugin-graphql-sse`, `plugin-csrf-prevention`, `plugin-disable-introspection`, `plugin-jwt`: see above.
- `@graphql-yoga/plugin-prometheus` (6.19.1): Envelop Prometheus plus `graphql_yoga_http_duration` histogram, labels `method`, `statusCode`, `url`, and a `/metrics` `endpoint`.
- `@graphql-yoga/plugin-sofa` (`useSofa({ basePath, swaggerUI: { endpoint }, title, version })`): auto REST API plus OpenAPI and Swagger UI from the GraphQL schema via SOFA.
- `@graphql-yoga/plugin-apollo-inline-trace` (`useApolloInlineTrace`): federated tracing (`ftv1`) for subgraphs.
- `@graphql-yoga/plugin-apollo-usage-report`: report usage to Apollo GraphOS.
- `@graphql-yoga/apollo-managed-federation` (`useManagedFederation({ apiKey, graphRef, maxRetries, retryDelaySeconds, minDelaySeconds })`): pull the supergraph from GraphOS and poll.

## Federation

- Subgraph: pass `buildSubgraphSchema` from `@apollo/subgraph` as the schema. No Yoga plugin needed.
- Gateway: `getStitchedSchemaFromSupergraphSdl({ supergraphSdl })` from `@graphql-tools/federation`, with SDL from a file, Hive CDN (`createSupergraphSDLFetcher` from `@graphql-hive/yoga`) or GraphOS (`useManagedFederation`). Docs recommend Hive Gateway instead.

## Integrations and runtimes

- Runs on Fetch API runtimes: Node.js (`node:http`, Express, Fastify, Koa, Hapi, NestJS via `@graphql-yoga/nestjs` and `@graphql-yoga/nestjs-federation`, Next.js, SvelteKit), Bun, Deno, Cloudflare Workers, AWS Lambda, Azure Functions, Google Cloud Functions, uWebSockets.js.
- Client helpers: `YogaLink` (`@graphql-yoga/apollo-link`) and `yogaExchange` (`@graphql-yoga/urql-exchange`). Both wrap `buildHTTPExecutor` from `@graphql-tools/executor-http`, so I think they handle SSE and multipart responses.

## Testing

- `yoga.fetch(...)` for in-process HTTP tests. `buildHTTPExecutor({ fetch: yoga.fetch })` from `@graphql-tools/executor-http` parses SSE and multipart results into async iterables. Typed with GraphQL Code Generator documents.
- `@envelop/testing`: `createTestkit(pluginsOrEnveloped, schema)`, `testkit.execute(...)`, `testkit.modifyPlugins(...)`, `testkit.mockPhase({ phase, fn })`, `createSpiedPlugin()`, `assertSingleExecutionValue`, `assertStreamExecutionValue`.

## Documentation guides (not APIs)

- Envelop guides: one DB client per request via a plugin, wrap each request in a transaction, enforce read-only DB for queries, transactions over multiple databases, Auth0 setup, response cache, subscription DataLoader cache issue, monitoring setups, OneOf and fragment arguments.
- Yoga tutorial: basic (Prisma, filtering, pagination, codegen) and advanced (auth, subscriptions, sorting). Filtering and pagination are hand-written in resolvers.

## Not supported or not in scope

- No schema builder, ORM integration, filtering, ordering, pagination, optimizer or DataLoader integration beyond `useDataLoader`.
- No built-in WebSocket server. `graphql-ws` wiring is manual.
- No built-in query cost or complexity analysis in Yoga or Envelop core. Only `useResourceLimitations` (connection node count) and third-party GraphQL Armor `costLimitPlugin`.
- No built-in auth or permissions in Yoga core. All auth is plugins (`useJWT`, `useGenericAuth`, `useAuth0`, `useOperationFieldPermissions`).
- CSRF prevention is opt-in, not default.
- No field-level schema visibility per user. Only whole-schema switching (`schema` factory, `useSchemaByContext`).
- No persisted operation store management (registration API, admin UI). Stores are user-supplied.
- No resumable uploads.
- `@defer`/`@stream` still marked experimental.

## Upcoming and unreleased work

- Recent releases: request body size limit (5.24.0), graphql-js 17 (5.22.0), `onRequestParse` short-circuit (5.21.0), mutable `graphqlEndpoint` (5.20.0), `useErrorCoordinate` (5.17.0), `allowedHeaders` (5.16.0), GraphiQL logo and favicon (5.15.0), `withState` (5.14.0), Instrumentation API (5.13.0), rate limiter `configByField` identifier templates (rate-limiter 10.1.0).
- Unmerged branches on the remote with feature-like names (not inspected, so I only guess the content from the name): `feat-defer-stream-new-protocol`, `copilot/allow-multipart-uploads-as-streams`, `feat-pub-sub-buffer`, `feat-sse-single-connection`, `graphql-sse-single-connection`, `variable-batching`, `projection`, `disallow-reserved-context-keys`, `root-level-limit-with-validate`, `expose-parser-caches`, `feat-is-persisted-document-context-helper`, `better-operation-name-errors`, `copilot/optimize-execution-result-serialization`.

## Docs and code disagree

- `enableInternalTracing` (Envelop `tracing.mdx`): declared in `EnvelopOptions` but never read. I think `_envelopTracing` is no longer produced.
- Envelop lifecycle docs name the hook `onContext`. The code hook is `onContextBuilding`.
- Envelop `core.mdx` uses `EnvelopError`. It is no longer exported. Use `GraphQLError` (the `use-masked-errors.md` doc already does).
- Yoga JWT docs use `lookupLocations` in several examples. The code option is `tokenLookupLocations`.
- Yoga JWT docs show `useDisableIntrospection({ disableIf })`. The Yoga plugin option is `isDisabled(request, context)`. `disableIf` belongs to the Envelop plugin.
- Yoga health check docs mention `useReadinessPlugin`. The export is `useReadinessCheck`.
- Yoga response cache docs show `session: ({ context }) => ...`. The code signature is `session(request, context)`.
- `@envelop/generic-auth` README says `rejectUnauthorized`. The code option is `rejectUnauthenticated`.
- `@envelop/persisted-operations` README links to the Yoga v3 docs.

## Sources

Repos:
- https://github.com/graphql-hive/graphql-yoga (shallow clone at `/tmp/yoga`, `main` at `6b8d0b6`, 2026-09-24). Contains Envelop under `packages/envelop`.
- https://github.com/graphql-hive/envelop (shallow clone at `/tmp/envelop`). Only a README and a pointer `CHANGELOG.md`.

Docs read (repo source of the sites, all current `docs/` pages read):
- `website/content/docs/` is https://the-guild.dev/graphql/yoga-server/docs. Read: `index.mdx`, `comparison.mdx`, `prepare-for-production.mdx`, and all of `features/` (schema, context, error-masking, subscriptions, file-uploads, persisted-operations, automatic-persisted-queries, defer-stream, request-batching, parsing-and-validation-caching, introspection, csrf-prevention, cors, cookies, response-caching, jwt, health-check, graphiql, landing-page, logging-and-debugging, request-customization, execution-cancellation, explicit-resource-management, sofa-api, testing, apollo-federation, envelop-plugins). `features/monitoring.mdx` headings only. Integration pages not read (page list only).
- `envelop-website/content/docs/` is https://the-guild.dev/graphql/envelop/docs. Read: `index.mdx`, `core.mdx`, `plugins/lifecycle.mdx`, `plugins/custom-plugin.mdx`, `plugins/testing.mdx`, `composing-envelop.mdx`, `tracing.mdx`. Guides: `securing-your-graphql-api.mdx`, `using-graphql-features-from-the-future.mdx`, `integrating-with-databases.mdx`, `monitoring-and-tracing.mdx` (headings), `resolving-subscription-data-loader-caching-issues.mdx` (headings).
- `envelop-website/plugins.json` for the plugin hub list (https://the-guild.dev/graphql/envelop/plugins).
- Plugin READMEs under `packages/envelop/plugins/*/README.md` and `packages/envelop/core/docs/*.md`.
- https://the-guild.dev/graphql/yoga-server/llms.txt, https://the-guild.dev/graphql/envelop/llms.txt and https://the-guild.dev/llms.txt return 200 (index of `.md` page links). The Yoga index matches the repo docs. I used the repo source.

Changelogs:
- `packages/graphql-yoga/CHANGELOG.md` (5.x minor entries read in full, 3.x and 4.x headings)
- `packages/envelop/core/CHANGELOG.md` (4.x and 5.x minor and major entries)
- `packages/envelop/plugins/{generic-auth,response-cache,rate-limiter}/CHANGELOG.md` (minor entries skimmed)

Source files checked:
- `packages/graphql-yoga/src/server.ts` (options, default plugin list), `index.ts` (exports), `plugins/types.ts` (hooks), `plugins/use-graphiql.ts` (GraphiQL options), `plugins/use-result-processor.ts`, `plugins/result-processor/sse.ts`, `plugins/use-error-coordinate.ts`
- `packages/envelop/types/src/plugin.ts`, `packages/envelop/core/src/create.ts`
- `packages/plugins/{persisted-operations,apq,defer-stream,graphql-sse,csrf-prevention,disable-introspection,response-cache,prometheus}/src/index.ts`
- `packages/envelop/plugins/{response-cache/src/plugin.ts,rate-limiter/src/index.ts,generic-auth/src/index.ts}`
- `packages/subscription/src/index.ts`
