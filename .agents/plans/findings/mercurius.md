# Mercurius findings

Versions checked: `mercurius` 16.10.1 (npm `latest`, 2026-09-26). Repo `master` at `4f635eb` (2026-10-02). npm `next` tag is the old 15.0.0. npm `eight` tag is 8.13.2.
Mercurius is a Fastify plugin that serves a GraphQL schema over HTTP and WebSocket. It is schema-first (SDL string plus a resolvers map) and also accepts any prebuilt `GraphQLSchema` (from `makeExecutableSchema`, Nexus, TypeGraphQL, GQLoom and others).
Execution is graphql-js. Optional JIT execution uses `graphql-jit` (Zalando). Batching uses `single-user-cache`. Pub/sub uses `mqemitter`.
Peer dep `graphql` `^16.0.0`. Fastify `5.x` only. Node `^20.9.0 || >=22.0.0`. CJS.
Official `mercurius-js` org packages: `mercurius-auth`, `mercurius-cache`, `mercurius-validation`, `mercurius-upload`, `@mercuriusjs/gateway`, `@mercuriusjs/federation`, `mercurius-codegen` (in `mercurius-typescript`), `mercurius-integration-testing`, `@mercuriusjs/subscription-client`. Each has a short section below.

## Maintenance status

- Active. Main maintainers are from the Fastify team (Matteo Collina and others). Last commit on `master`: `queryDepth: 0 disables the depth check instead of rejecting every query (#1271)`, 2026-10-02.
- GitHub `pushed_at` 2026-10-02. Not archived. 2489 stars. 68 open issues plus PRs.
- Releases: v16.10.1 (2026-09-26), v16.10.0 (2026-07-14), v16.8.0 (2026-03-06), v16.7.0 (2026-01-19), v16.6.0 (2025-11-13), v16.5.0 (2025-10-10), v16.4.0 (2025-10-31), v16.0.0 (2024-12-21). About one minor release every one to two months.
- No `CHANGELOG.md` in the repo. Release notes are on GitHub releases only.
- Branches: `master`, `next` (stale since 2022, 237 commits behind), `v8.x`, `support-http-query-method`, `fix-1227-apq-hash-verification`, `fix/350-subscription-context-types`, `maybe-improve-types`, `add-node-24`, `dep-updates`, `gh-pages`.
- Docs site https://mercurius.dev/ is docsify. It renders `docs/*.md` and `README.md` from the main repo. `/llms.txt` returns 404.

## Schema definition

- `schema` option: SDL `String`, `String[]` (joined with newlines), or a `GraphQLSchema` instance.
- No schema option at all gives an empty `Query` type. `defineMutation: true` also adds an empty `Mutation` type.
- `resolvers` map: `{ TypeName: { field: fn } }`. `Query`, `Mutation` and `Subscription` use the same shape.
- Top-level function entries in `resolvers` (`{ add: fn }`) go to the graphql-js `rootValue`. Used by `reply.graphql` docs example. Not explained in the docs.
- Scalar and enum resolvers: every key in `resolvers.MyScalar` is copied onto the `GraphQLScalarType` or `GraphQLEnumType` (`serialize`, `parseValue`, `parseLiteral`, enum values). Source only.
- Interface and union resolvers: `resolvers.MyInterface.resolveType`. Source only.
- `isTypeOf` on an object type resolver entry is moved onto the `GraphQLObjectType`. Source only.
- `__resolveReference` on an object type resolver is stored as `type.resolveReference` for federation.
- Unknown type or field in `resolvers` throws `MER_ERR_INVALID_OPTS` (`Cannot find field x of type Y`).
- Schema is validated with `validateSchema` on Fastify `onReady`. Errors throw `MER_ERR_GQL_INVALID_SCHEMA` with `.errors`.
- Modular schema: `app.graphql.extendSchema(sdl | DocumentNode)`, `app.graphql.defineResolvers(resolvers)`, `app.graphql.defineLoaders(loaders)` from any Fastify child plugin. Uses `extendSchema` from graphql-js, so SDL must use `extend type Query`.
- `app.graphql.replaceSchema(schema)` swaps the whole schema at runtime. It clears the parse/validate LRU and the JIT queue.
- `app.graphql.transformSchema(fn | fn[])` and the `schemaTransforms` option apply `(schema) => schema` functions. Calls `replaceSchema` under the hood.
- `app.graphql.schema` exposes the current `GraphQLSchema`.
- Custom schema directives: no built-in API. Docs use `@graphql-tools/utils` `mapSchema` and `getDirective` plus `schemaTransforms`.
- Schema per request header: docs show two Mercurius instances on constrained Fastify routes (find-my-way custom constraints, `routes: false`). No per-viewer schema API in core.
- Introspection: on by default. Disable with `validationRules: [NoSchemaIntrospectionCustomRule]` from graphql-js (FAQ).

## Execution API

- `app.graphql(source, context?, variables?, operationName?)`: server decorator. Runs the full pipeline (hooks, parse cache, validation, depth limit, JIT, error formatter). Adds `{ app }` to the context.
- `reply.graphql(source, context?, variables?, operationName?)`: reply decorator. Adds `{ app, reply }` to the context and creates the per-request loader instance. Loaders only work through `reply.graphql`. Calling a loader without `reply` throws `loaders only work via reply.graphql()`.
- `source` can be a query string or a pre-parsed `DocumentNode` (deep cloned with `structuredClone`). Source only.
- If `parse` fails, Mercurius tries `JSON.parse(source)` and uses the result as a document AST. So a JSON-serialized AST is accepted as the query string. Source only.
- Variables are checked with `buildExecutionContext` before execution. Variable errors become `MER_ERR_GQL_VALIDATION` (400).
- GET requests can only run `query` operations. Mutations over GET give `MER_ERR_METHOD_NOT_ALLOWED` (405).
- `graphql.parseOptions` and `graphql.validateOptions` pass options to graphql-js `parse` and `validate` (for example `maxTokens`, `maxErrors`).
- `validationRules`: `ValidationRule[]` or a function `({ source, variables, operationName }) => ValidationRule[]`. The function form throws at startup unless `cache: false`, because results are cached per query string.
- `cache` option: `boolean | number`. LRU (`quick-lru`) of parsed and validated documents, keyed by query string. Default 1024 entries. `false` disables it and also disables loader caching. A second LRU of the same size caches validation errors, so bad queries do not evict good ones (DoS protection). Not listed in `docs/api/options.md`. Only `cache: false` appears in `docs/loaders.md`.
- `queryDepth: number`: depth limit, based on `graphql-depth-limit`. Error `MER_ERR_GQL_QUERY_DEPTH`. Applied to HTTP and, since v16.8.0, to WebSocket subscriptions (CVE-2026-30241 was a bypass over WS).
- No query complexity or cost analysis in core. No alias or token count limit beyond graphql-js `maxTokens`.

## JIT compilation

- `jit: number`: synchronous JIT. When a cached query has been run `n` times, `graphql-jit` `compileQuery` compiles it on the triggering request. Later runs use `compiled.query(root, context, variables)`. Default `0` (off).
- `jit: { minCount, eluThreshold, maxCompilePerTick, maxQueueSize }`: adaptive background JIT (v16.10.0). Hot queries go into a popularity-sorted queue. Compilation happens in `setImmediate` ticks only while Node event loop utilization (`performance.eventLoopUtilization`) is below `eluThreshold`. Defaults `3`, `0.8`, `1`, `100`. Least popular entries are dropped when the queue is full.
- `compilerOptions`: passed to `graphql-jit` `compileQuery` (for example `customJSONSerializer`, `disableLeafSerialization`).
- JIT is skipped for a request when a `preExecution` hook returns a modified `schema` or `document`.
- JIT needs the query cache. With `cache: false` there is no JIT.

## Loaders (batching)

- `loaders` option or `app.graphql.defineLoaders(loaders)`: `{ Type: { field: async (queries, context) => results[] } }`. Each loader replaces the field resolver and batches all calls of that field in one tick.
- `queries` is `[{ obj, params }]` (`obj` is the parent, `params` the args). `info` is added only when cache is off.
- Per loader options: `{ loader, opts: { cache: false } }`. Cached loaders dedupe identical `{ obj, params }` within a request using `safe-stable-stringify` keys.
- Loaders are per request. Subscriptions get a separate loader factory with cache always off.
- `__resolveReference` can be defined as a loader for federation entity batching.
- No per-field DataLoader class or `load(key)` API. Loaders are always bound to a type field.

## HTTP transport

- `POST /graphql` with `application/json` body `{ query, operationName, variables, extensions, persisted }`. Body validated by Fastify JSON schema.
- `POST /graphql` with `Content-Type: application/graphql`. Body is the raw query. No variables.
- `GET /graphql?query=&operationName=&variables=&extensions=`. `variables` and `extensions` are JSON strings parsed with `secure-json-parse`.
- Response is serialized through a Fastify response JSON schema (fast-json-stringify).
- `path` (default `/graphql`), `prefix`, `routes: false` (no HTTP routes, use `app.graphql` or your own route).
- `additionalRouteOptions`: Fastify route options merged into the GraphQL routes (constraints, `bodyLimit`, extra hooks). `handler` and `wsHandler` are ignored.
- `context: (request, reply) => object | Promise<object>`: custom context. `reply` and `app` are always added. The resolver also gets `pubsub` and `__currentQuery` (the query string, undocumented).
- `allowBatchedQueries: true`: array request body, array response (Apollo `apollo-link-batch-http` style). Runs all operations in parallel. Errors are per operation. Each operation context gets `operationsCount` and `operationId` (in the TS types, not in the docs). Loaders are shared across the batch.
- HTTP status codes: 200 when `data` is present. 400 for parse and validation errors (`MER_ERR_GQL_VALIDATION`). 200 for execution errors with `data: null`, unless there is exactly one error with a numeric `statusCode`, then that code is used.
- `errorHandler: boolean | (error, request, reply) => any`: replaces the Fastify error handler for the GraphQL routes. Default formats with `errorFormatter`.
- `errorFormatter: (executionResult, context) => { statusCode, response }`: custom error shape and status code. `mercurius.defaultErrorFormatter` is exported for reuse. The default logs every error at `info` level.
- `ErrorWithProps(message, extensions, statusCode)`: error class that sets `extensions` and an HTTP status code. Exported as `mercurius.ErrorWithProps`.
- Error codes are `@fastify/error` codes: `MER_ERR_GQL_VALIDATION`, `MER_ERR_GQL_QUERY_DEPTH`, `MER_ERR_GQL_CSRF_PREVENTION`, `MER_ERR_GQL_PERSISTED_QUERY_NOT_FOUND`, `MER_ERR_GQL_PERSISTED_QUERY_NOT_SUPPORTED`, `MER_ERR_GQL_PERSISTED_QUERY_MISMATCH`, `MER_ERR_METHOD_NOT_ALLOWED`, `MER_ERR_INVALID_OPTS`, subscription and hook error codes.
- No error masking in production by default. Resolver error messages go to the client as-is.
- No `application/graphql-response+json` content negotiation. No `Accept` header handling. Responses are always `application/json`.
- No SSE transport. No `multipart/mixed`.
- No HTTP response caching headers (`Cache-Control`) and no `@cacheControl` directive.

## CSRF prevention

- `csrfPrevention: boolean | { allowedContentTypes, requiredHeaders }` (v16.4.0). Off by default.
- A request passes if its `Content-Type` is in `allowedContentTypes` (default `application/json`, `application/graphql`, parameters ignored) or it has one of `requiredHeaders` (default `x-mercurius-operation-name`, `mercurius-require-preflight`).
- Blocked requests get `MER_ERR_GQL_CSRF_PREVENTION` (400).
- `multipart/form-data` can be added to `allowedContentTypes` for uploads. Then a required header is still needed.
- Documented in `docs/security/csrf-prevention.md` but not listed in `docs/api/options.md`.

## Persisted queries

- `persistedQueries: { hash: query }`: map of prepared queries. Clients send `{ query: '<hash>', persisted: true }`.
- `onlyPersisted: true`: reject everything not in the map. Also turns off GraphiQL.
- `persistedQueryProvider`: pluggable provider with `isPersistedQuery`, `isPersistedQueryRetry`, `getHash`, `getQueryFromHash`, `getHashForQuery`, `saveQuery`, `notFoundError`, `notSupportedError`, `mismatchError`.
- `mercurius.persistedQueryDefaults.prepared(map)`, `.preparedOnly(map)`, `.automatic(maxSize = 1024)`.
- `automatic()` is Apollo APQ compatible (`extensions.persistedQuery.{ version: 1, sha256Hash }`). Uses a `tiny-lru` store. Error messages `PersistedQueryNotFound` and `PersistedQueryNotSupported`.
- Since v16.0.0, APQ only saves queries inside an APQ retry flow. Since v16.10.0, the hash is checked before the operation runs (a mutation no longer runs when the hash mismatches).
- Shared store (Redis) by spreading `automatic()` and overriding `getQueryFromHash` and `saveQuery` (docs example).
- Persisted queries are not supported over WebSocket subscriptions. A 2023 draft PR exists.

## Hooks (GraphQL lifecycle)

- `app.graphql.addHook(name, asyncFn)`. Async or promise only. Register after `await app.ready()` or inside a plugin after Mercurius.
- `preParsing(schema, source, context)`.
- `preValidation(schema, document, context)`. Not called for cached queries.
- `preExecution(schema, document, context, variables)`. May return `{ schema, document, variables, errors }` to replace them for this request. Returned `errors` are added to the response while the query still runs.
- `onResolution(execution, context)`. Runs after the error formatter.
- `preSubscriptionParsing(schema, source, context, id)`, `preSubscriptionExecution(schema, document, context, id)`, `onSubscriptionResolution(execution, context, id)`, `onSubscriptionEnd(context, id)`.
- `onSubscriptionConnectionClose(context, code, reason)` and `onSubscriptionConnectionError(context, error)` (v16.5.0).
- `onExtendSchema(schema, context)`: application hook, runs when `extendSchema` is called.
- Throwing in any request hook ends the request with a GraphQL error. Throwing in `onSubscriptionResolution` or `onSubscriptionEnd` closes the socket.
- Gateway adds `preGatewayExecution`, `preGatewaySubscriptionExecution` and `onGatewayReplaceSchema` (see gateway).
- No field-level middleware or resolver wrapping hook. Field middleware is done with schema transforms or `mercurius-auth` style directive wrapping.

## Subscriptions

- `subscription: true | { emitter, pubsub, verifyClient, context, onConnect, onDisconnect, keepAlive, fullWsTransport, wsDefaultSubprotocol, queueHighWaterMark }`.
- Transport is WebSocket on the same `path` (`@fastify/websocket`, `maxPayload` 1 MiB).
- Subprotocols: `graphql-transport-ws` (graphql-ws) and the legacy `graphql-ws` (Apollo `subscriptions-transport-ws`). Clients without a subprotocol are closed unless `wsDefaultSubprotocol` is set (v16.5.0).
- Resolver: `Subscription.field.subscribe(root, args, { pubsub })` returns `pubsub.subscribe(topic | topic[], ...customArgs)`. Publish with `context.pubsub.publish({ topic, payload })` or `app.graphql.pubsub.publish(...)`.
- `mercurius.withFilter(subscribeFn, filterFn)`: filter events per subscriber.
- Default pub/sub is in-memory `mqemitter`. Distributed with any mqemitter backend (`mqemitter-redis`, `mqemitter-mongodb`) through `emitter`.
- `pubsub`: custom class with `subscribe(topic, queue, ...customArgs)` and `publish(event, callback)`. Custom args come from the resolver (for example an offset).
- `queueHighWaterMark`: backpressure limit of the per-subscription Readable queue (v16.6.0).
- `verifyClient(info, next)`: accept or reject the WS upgrade. `onConnect({ payload })`: check `connection_init`. Returning an object extends the context. `onDisconnect(context)`.
- `connection_init` payload is copied into `request.headers` (or `payload.headers` if present) without overwriting existing headers.
- `subscription.context(connection, request)`: custom subscription context.
- `keepAlive`: interval in ms for keep-alive messages.
- `fullWsTransport: true`: queries and mutations can also run over the WebSocket.
- `connectionInit` WS message extension: lets a gateway forward a client `connection_init` payload to a service over an existing connection. Unknown extensions throw `MER_ERR_GQL_SUBSCRIPTION_UNKNOWN_EXTENSION`.
- Loaders work in subscriptions with caching off.
- I found no `validate()` call in the subscription path (`lib/subscription-connection.js`). Subscription documents over WS are parsed and passed to graphql-js `subscribe` without spec validation and without custom `validationRules`. The parse also ignores `graphql.parseOptions`.
- No SSE subscriptions. No `graphql-sse`. No subscription over HTTP multipart.

## GraphiQL

- `graphiql: true | 'graphiql' | { enabled, plugins }`. `ide` is an alias. Served at fixed `/graphiql` (plus `prefix`), not under `path`.
- GraphiQL 3.8.3 and React 18.3.1 load from unpkg. A service worker (`/graphiql/sw.js`) caches them.
- GraphiQL plugins: `plugins: [{ name, props, umdUrl, fetcherWrapper }]`. UMD plugins load at runtime. `fetcherWrapper` can read or change fetch responses. Example plugin in `examples/graphiql-plugin`.
- Not served when `routes: false` or `onlyPersisted: true`.
- Altair is a separate community plugin (`altair-fastify-plugin`).

## Incremental delivery

- No `@defer` or `@stream`. A draft PR "feat: @defer support" has been open since 2022-10-25.

## TypeScript

- Bundled `index.d.ts`. Types: `IResolvers`, `IFieldResolver`, `MercuriusContext` (extend with module augmentation), `MercuriusLoaders`, `PersistedQueryProvider`, `CustomPubSub`, `SubscriptionContext` (v16.10.0).
- Codegen is in `mercurius-codegen` (see below).

## Integrations (docs pages)

- NestJS (`@nestjs/mercurius`), Nexus, TypeGraphQL, GQLoom (Zod and Valibot), Prisma, OpenTelemetry (`@autotelic/fastify-opentelemetry` plus `@opentelemetry/instrumentation-graphql`), `mercurius-integration-testing`.
- Community plugins listed in docs: `altair-fastify-plugin`, `mercurius-apollo-registry` (schema reporting to Apollo Studio), `mercurius-apollo-tracing` (metrics to Apollo Studio), `mercurius-postgraphile`, `mercurius-logging` (structured GraphQL request logs), `mercurius-fetch` (REST calls from schema directives), `mercurius-hit-map` (count resolver executions).
- Core has no built-in tracing, metrics or Apollo `ftv1` support.

## mercurius-auth

- Version 6.0.0 (npm 2024-10-12). Last commit 2026-05-28.
- Directive mode (default): `authDirective: 'auth'` names an SDL directive on `OBJECT | FIELD_DEFINITION`. Each protected field runs `applyPolicy(policy, parent, args, context, info)`. Return `true` to allow, or `false` / an `Error` to deny.
- `authContext(context)`: runs in `preExecution` and sets `context.auth`.
- External policy mode (`mode: 'external'`, `policy: { Type: { field: any, __typePolicy: any } }`): no schema directives needed.
- Several auth plugins can be registered at once with different directives. Only the last `authContext` wins.
- `filterSchema: true`: introspection only shows fields and types the user may access. Policy runs once per type during introspection. Inputs with a protected `INPUT_FIELD_DEFINITION` are hidden entirely.
- Schema replacement: `outputPolicyErrors: { enabled: false, valueOverride: string | fn }` returns a replacement string (masking) instead of an error for denied `String` fields.
- Denied fields return `null` plus an error. Custom errors and status codes via thrown or returned errors.
- Works with the gateway. Re-registers on `onGatewayReplaceSchema`.

## mercurius-cache

- Version 8.0.0 (GitHub release 2026-02-10). Last commit 2026-08-10.
- Caches resolver results in process. Built on `async-cache-dedupe`.
- Options: `ttl` (number or function of the result), `stale` (stale-while-revalidate seconds), `all` (cache every resolver), `policy` (per `Type.field` config), `storage: { type: 'memory' | 'redis', options }`, `skip`, `onDedupe`, `onHit`, `onMiss`, `onSkip`, `onError`, `logInterval`, `logReport`.
- Policy options: `ttl`, `stale`, `storage`, `skip`, `key` (custom key serializer), `extendKey` (for example per-user cache), `references` (tag entries), `invalidate` (tags to invalidate after a mutation), `__options` (name conflict escape).
- Request deduplication: concurrent identical resolver calls run once.
- `app.graphql.cache.invalidate(references, storage?)`, `app.graphql.cache.clear()`. Redis garbage collection with `chunk` and `lazy` modes.
- Works with federation. Caveat in README: invalid resolver results are cached too.

## mercurius-validation

- Version 7.0.0 (2026-02-10). Last commit 2026-05-18.
- `mode: 'JSONSchema' | 'JTD'`. `schema: { Type: { field: { arg: schema }, __typeValidation } }` validates field arguments, input object fields and whole input objects with AJV.
- Function validation: `(metadata, value, parent, args, context, info) => void | throw`.
- `@constraint` directive (`directiveValidation`, default `true`) on `ARGUMENT_DEFINITION`, `INPUT_FIELD_DEFINITION`, `INPUT_OBJECT`. Args: `type`, `maxLength`, `minLength`, `format`, `pattern`, `maximum`, `minimum`, `exclusiveMaximum`, `exclusiveMinimum`, `multipleOf`, `maxProperties`, `minProperties`, `required`, `maxItems`, `minItems`, `uniqueItems`, plus `schema` (raw JSON Schema string).
- `mercuriusValidation.graphQLTypeDefs` (SDL for the directive) and `mercuriusValidation.graphQLDirective`.
- `customTypeInferenceFn` maps GraphQL types to JSON Schema types. Default maps `String`, `Int`, `Float` and others.
- Extra AJV options are passed through. Custom error messages through AJV.
- Works in gateway mode.

## mercurius-upload

- Version 8.0.0 (2024-11-12). Last commit 2024-11-12. Least active package.
- Fastify plugin that parses `multipart/form-data` (GraphQL multipart request spec) with `graphql-upload-minimal` `processRequest`. Options pass through (`maxFileSize`, `maxFiles`).
- User declares `scalar Upload` and uses `GraphQLUpload` from `graphql-upload-minimal`.

## @mercuriusjs/federation

- Version 5.1.1 (2026-03-27). Last commit 2026-05-01.
- `mercuriusFederationPlugin` (Mercurius with federation schema), `buildFederationSchema(sdl, { isGateway })`, `federationSchemaTransformer(transforms)` (keeps `resolveReference` through `mapSchema`).
- Adds `_Any`, `_FieldSet`, `_Service { sdl }`, `_entities(representations)`, `_Entity`, and directives `@key`, `@extends`, `@external`, `@requires`, `@provides`.
- Federation v1 only. I found no `@link`, `@shareable`, `@override`, `@inaccessible`, `@tag` or `@interfaceObject` in the federation or gateway code.

## @mercuriusjs/gateway

- Version 5.2.0 (2026-03-04). Last commit 2026-08-01.
- Mercurius as a federation gateway. Composes service SDLs (from `_service`) and plans queries itself. Not Apollo Router compatible beyond federation v1.
- `gateway.services`: array or async function. Per service: `name`, `url` (array for load balancing), `mandatory`, `useSecureParse`, `rewriteHeaders`, `setResponseHeaders`, `initHeaders`, `connections`, `agent` (undici), timeouts, `keepAlive`, `wsUrl`, `wsConnectionParams` (reconnect, init payload rewrite), `allowBatchedQueries`, `collectors` (`collectHeaders`, `collectStatutsCodes`, `collectExtensions`).
- `gateway.retryServicesCount`, `retryServicesInterval`, `pollingInterval` (schema refresh), `errorHandler` (downstream errors).
- `app.graphql.gateway.refresh()`, `serviceMap.<name>.setSchema(sdl)` for a schema registry flow.
- Subscriptions are proxied to services over WebSocket.
- Hooks: `preGatewayExecution` (can change the document per service), `preGatewaySubscriptionExecution`, `onGatewayReplaceSchema`.

## mercurius-codegen (mercurius-typescript repo)

- Version 6.0.1 (2025-01-29). Repo last commit 2026-05-06.
- `mercuriusCodegen(app, { targetPath, operationsGlob, disable, silent, codegenConfig, preImportCode, watchOptions, outputSchema })`. Runs GraphQL Code Generator on the live app schema and writes resolver, loader and context types. Watches in dev. Disabled when `NODE_ENV=production` by default.
- Also generates typed `DocumentNode`s for client operations from `operationsGlob`.
- `loadSchemaFiles(globs, { watchOptions, prebuild })`, fake `gql` tag, `LazyPromise`, `DeepPartial`.

## mercurius-integration-testing

- Version 9.0.1 (2024-12-26). Last commit 2026-01-13.
- `createMercuriusTestClient(app, { url, headers, cookies })` with `query`, `mutate`, `batchQueries`, `subscribe`, `setHeaders`, `setCookies`, `getFederatedEntity`. Accepts strings or `DocumentNode`s. Typed results with `TypedDocumentNode`.

## @mercuriusjs/subscription-client

- Version 2.0.0 (2024-09-09). Last commit 2024-09-09.
- Node WebSocket client `SubscriptionClient(uri, { protocols, reconnect, maxReconnectAttempts, connectionInitPayload, rewriteConnectionInitPayload, keepAlive, ... })` with `connect`, `close`, `createSubscription`, `unsubscribe`, `unsubscribeAll`. Used by the gateway.

## Other org repos

- `relay-pagination`: empty (README with a title only, 2024-01-04). No Relay connection helpers exist in the org.
- `mercurius-cache-example`, `website`, `graphics`, `registry` ("Go away, come back later", 2021): not libraries.

## Not supported or not in scope

- No code-first schema builder. Bring your own (Nexus, TypeGraphQL, GQLoom, Pothos).
- No ORM integration, filtering, ordering or pagination helpers. Prisma docs page is a manual example.
- No Relay helpers (global IDs, `Node`, connections).
- No `@defer`, `@stream`, SSE or `multipart/mixed` responses.
- No query complexity or cost limits. Only `queryDepth`.
- No built-in error masking.
- No per-viewer schema visibility in core (only `mercurius-auth` `filterSchema` for introspection).
- No `@oneOf` handling beyond what graphql-js 16 gives. graphql 17 is not supported yet (PR open).
- No HTTP caching headers, no response cache keyed on the whole operation (only resolver-level `mercurius-cache`).
- No built-in tracing, metrics or Apollo usage reporting.
- No Federation v2. No Apollo Router compatibility claim.
- No persisted queries over WebSocket.
- No rate limiting (use `@fastify/rate-limit` at the route level).
- Fastify only. No other HTTP frameworks.

## Upcoming and unreleased work

- On `master`, unreleased: `queryDepth: 0` now disables the depth check. In 16.10.1, `0` rejects every HTTP query (the WS path already treated `0` as off).
- Open PR (2026-10-03): serialize list indices in error `path` as integers.
- Open PR (2026-08-22): HTTP `QUERY` method (RFC 10008, graphql-over-http #411). Mutations over `QUERY` give 405. Feature-detected on Fastify >= 5.11.0.
- Open PR (2026-07-23): graphql 17 support with a CI matrix for 16 and 17. Widens the peer dep to `^16.8.0 || ^17.0.0`.
- Open PR (2026-07-16): WS `sendError` payload follows the subprotocol format.
- Older open PRs: `@defer` support (2022, draft), request in context by default (2024), persisted queries on subscriptions (2023, draft), base OpenTelemetry integration (2020), loader batching fix and GraphiQL upgrade (2025).

## Docs and code disagree

- Response JSON schema in `lib/routes.js` types error `path` items as `string`. So list indices in error paths are sent as strings (`"0"`), not integers as the GraphQL spec says. The open PR above fixes it.
- `docs/api/options.md` does not list the `cache` option or `csrfPrevention`. Both exist in code and in `index.d.ts`.
- `docs/plugins.md` says `mercurius-upload` implements `graphql-upload`. The code uses `graphql-upload-minimal`.
- `docs/hooks.md` says there are "five different hooks" for requests. It lists four (`preParsing`, `preValidation`, `preExecution`, `onResolution`).
- `docs/api/options.md` says `queryDepth` is the maximum depth. In 16.10.1, `queryDepth: 0` blocks all HTTP queries but not WS subscriptions. Fixed on `master`.
- `docs/subscriptions.md` does not say that WS subscription documents skip `validate()` and custom `validationRules`. HTTP requests run both.
- `package.json` lists `p-map` as a dependency. I found no use of it in `index.js` or `lib/`.

## Sources

Repos (shallow clones in `/tmp/mercurius-audit/`):
- https://github.com/mercurius-js/mercurius (`master` at `4f635eb`, 2026-10-02)
- https://github.com/mercurius-js/auth, https://github.com/mercurius-js/cache, https://github.com/mercurius-js/validation, https://github.com/mercurius-js/mercurius-upload, https://github.com/mercurius-js/mercurius-gateway, https://github.com/mercurius-js/mercurius-federation, https://github.com/mercurius-js/mercurius-typescript, https://github.com/mercurius-js/mercurius-integration-testing, https://github.com/mercurius-js/mercurius-subscription-client, https://github.com/mercurius-js/relay-pagination

Docs read (repo source of https://mercurius.dev/, all files read):
- `docs/api/options.md`, `hooks.md`, `lifecycle.md`, `loaders.md`, `context.md`, `batched-queries.md`, `http.md`, `persisted-queries.md`, `subscriptions.md`, `graphql-over-websocket.md`, `custom-directive.md`, `federation.md`, `plugins.md`, `faq.md`, `typescript.md`, `security/csrf-prevention.md`. Integration pages (`docs/integrations/*.md`) headings and setup only.
- Package READMEs and `docs/` folders of `auth` and `validation`. READMEs of the other org packages.
- https://mercurius.dev/llms.txt returns 404.

Changelogs:
- No changelog file. GitHub releases https://github.com/mercurius-js/mercurius/releases (v16.0.0 to v16.10.1 read). Unreleased commits via the GitHub compare API (`v16.10.1...master`). Open PR list via `gh pr list`.
- npm registry (`npm view`) for versions and dates of all packages.

Source files checked:
- `index.js` (options, execution pipeline, `defineResolvers`, `defineLoaders`, cache, JIT), `index.d.ts` (option types)
- `lib/routes.js`, `lib/errors.js`, `lib/csrf.js`, `lib/queryDepth.js`, `lib/persistedQueryDefaults.js`, `lib/adaptive-jit.js`, `lib/hooks.js`, `lib/subscription.js`, `lib/subscription-connection.js`, `lib/subscriber.js`
- `auth/index.js`, `auth/lib/validation.js`, `validation/lib/directive.js`, `mercurius-upload/index.ts`, `mercurius-federation/lib/federation.js`, `mercurius-gateway/lib/gateway/*`, `mercurius-typescript/packages/mercurius-codegen/src/index.ts`
