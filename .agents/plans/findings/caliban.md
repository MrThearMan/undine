# Caliban findings

Versions checked: `caliban 3.2.0` (latest GitHub release, 2026-09-30). Repo default branch `series/3.x` at `027e353` (last commit 2026-10-09). Docs source is in the repo under `vuepress/docs/` (about 4600 lines). All doc pages read in full, including the new gateway pages and the FAQ. Core, federation, adapters, interop, stitching, client and codegen source spot-checked. Release notes read from 3.2.0 back to 3.0.0, plus the feature lists of 2.7.0 to 2.11.0. Unmerged branches and open PRs checked through the GitHub API.
Caliban is a Scala GraphQL library for servers and clients. Apache-2.0. Scala 2.13 and 3, with Scala.js for the client. Code-first. The schema is derived at compile time from case classes and sealed traits through the `Schema` and `ArgBuilder` type classes. No reflection. Built on ZIO. Batching uses ZQuery. Cats Effect, Monix and `Future` work through interop modules.

## Maintenance status

- Very active. Main maintainer `ghostdogpr`, with `kyri-petrou` and `paulpdaniels` as frequent contributors. 993 stars. 27 open issues plus PRs. Not archived.
- Recent releases: 3.2.0 (2026-09-30), 3.1.5 (2026-07-08), 3.1.4 (2026-07-03), 3.1.3 (2026-07-01), 3.1.2 (2026-05-28), 3.1.1 (2026-05-24), 3.1.0 (2026-05-07), 3.0.0 (2026-01-11), 2.11.2 (2025-12-27).
- No `CHANGELOG.md`. Release notes are only on GitHub releases.
- `series/3.x` is 18 commits ahead of 3.2.0 (unreleased): interface objects in supergraphs, recursive `@oneOf` input fix, `@defer` multipart flush fix, fewer fibers per gateway request.
- https://ghostdogpr.github.io/caliban/llms.txt returns 404. `Accept: text/markdown` returns HTML.
- The repo has an `AGENTS.md`. The 3.1.5 release notes say an agent reviewed the whole codebase for spec compliance.

## Big changes in recent releases

- 2.7.0 (2024-05-29): schema transformations (`Transformer`). Scala 3 union type derivation. `@semanticNonNull` support.
- 2.8.0 (2024-06-28): `@oneOf` inputs for server and client. `@GQLFieldsFromMethods` (Scala 3). `ExcludeDirectives` transformer. zio-http adapter merged into `QuickAdapter`. `GraphQL#interpreter` returns `Exit`.
- 2.9.0 (2024-09-24): `@stream` directive. Deprecated arguments in introspection and client codegen. GraphiQL endpoints for tapir adapters. `GraphQLRequest` flag for GET requests.
- 2.11.0 (2025-07-08): `java.time` encoders and decoders in the client.
- 3.0.0 (2026-01-11): sttp 4 in the client. `tools` split into `codegen`, `stitching` and `tools`. Relay global identifier support. SSE subscription heartbeats. Fragments and operation directives in the client. All deprecated code removed.
- 3.1.0 (2026-05-07): Federation 2.12 (`@cacheTag`). Built-in `ArgBuilder` for enums. Covariant interface field narrowing.
- 3.1.1: security fix. `WebSocketHooks.beforeInit` was skipped when the client sent no payload, which could bypass auth.
- 3.1.5 (2026-07-08): large spec-compliance pass over parsing, validation, variable coercion, rendering, `@stream`, codegen and adapters.
- 3.2.0 (2026-09-30): Caliban Gateway (`caliban-gateway`, `caliban-gateway-tracing`). `QuickAdapter#configureHttp` with body size limits (new 1 MB default request limit). `RemoteSchema` moved from `tools` to core. Up to 2.6x faster fragment field-merging validation.

## Schema definition (derivation)

- `graphQL(RootResolver(queries, mutations, subscriptions))` builds a `GraphQL[R]`. Only queries are required. `R` is the ZIO environment the resolvers need.
- `Schema[R, A]` type class maps Scala types to output types. `ArgBuilder[A]` maps input values to Scala types.
- Auto derivation: `import caliban.schema.Schema.auto._` and `import caliban.schema.ArgBuilder.auto._`. Docs recommend semi-auto for non-trivial schemas.
- Semi-auto: `Schema.gen`, `ArgBuilder.gen`. Scala 3: `derives Schema.SemiAuto, ArgBuilder`, `Schema.Auto`. `Schema.genDebug` prints generated code.
- Custom environment: `GenericSchema[R]` (Scala 2), `SchemaDerivation[R]` (Scala 3 `derives customSchema.SemiAuto`).
- `DerivationConfig` on a custom `SchemaDerivation` object toggles disabled-by-default features. Example: `enableSemanticNonNull`.
- Type mapping: `UUID` to `ID`. Custom scalars `Unit`, `Long`, `BigInt`, `BigDecimal`, `Instant`, `LocalDate`, `LocalTime`, `LocalDateTime`, `OffsetDateTime`, `ZonedDateTime`. `Option` is nullable. `List`/`Set`/`Seq`/`Vector`/`Chunk` are lists. `Map[A, B]` is a list of `{key, value}` objects. `Either[A, B]` is an object with `left` and `right`. Tuples are objects with `_1`, `_2`.
- Non-null is the default. `ZIO[R, Throwable, A]` and `Future[A]` become nullable, because they can fail. `ZIO[R, Nothing, A]` stays non-null.
- Circe, play-json and zio-json `Json` as a `Json` scalar (`caliban.interop.circe.json._` and similar). Jsoniter is also supported for the wire format.
- Case class is an object type. Fields that are functions `Args => B` get arguments from the `Args` case class.
- Sealed trait of case objects is an enum. Sealed trait of case classes is a union. Mixed traits give a union, and case objects get a fake `_: Boolean` field.
- `@GQLInterface` turns a sealed trait into an interface with the common fields. `@GQLInterface(excludedFields*)` drops listed fields from the interface (not in docs).
- `@GQLUnion` forces a union even for case objects only.
- Scala 3 union types (`A | B`) derive a GraphQL union through `TypeUnionDerivation` (2.7.0). Not in the docs.
- `@GQLValueType(isScalar)`: unwrap a single-field wrapper, or make it a named scalar. Also used to share a type between unions.
- Value classes are unwrapped in Scala 2. Scala 3 derivation does not support value classes or opaque types.
- `@GQLField` (Scala 3): expose a case class method as a field. `@GQLFieldsFromMethods`: expose all public methods. Methods cannot take arguments. Not compatible with GraalVM native image.
- Annotations: `@GQLName`, `@GQLInputName` (default adds `Input` suffix), `@GQLDescription`, `@GQLDeprecated` (fields, enum values, arguments), `@GQLExcluded`, `@GQLDirective(directive)`, `@GQLDefault("graphql literal")`, `@GQLOneOfInput`, `@GQLNullable`, `@GQLNonNullable`. `@GQLNonNullable` is not in the docs.
- `@oneOf` input: sealed trait or Scala 3 enum annotated `@GQLOneOfInput`. Each case has exactly one non-null field.
- `@semanticNonNull` (RFC) for fallible effects, behind `enableSemanticNonNull`. `Schema.nullable` and `Schema.canFail` decide it for custom schemas.
- Manual schemas: `Schema.obj` (Scala 2), `Schema.customObj` (Scala 3), `Schema.field`, `Schema.fieldLazy`, `Schema.fieldWithArgs`, `Schema.objectSchema`, `Schema.enumSchema`, `Schema.enumValue`, `Schema.scalarSchema`. Needed for co-recursive types.
- `Schema#contramap` and `Schema#rename` reuse an existing schema. `ArgBuilder#map` and `ArgBuilder#||` (fallback) on input side.
- `ArgBuilder.enumString`, `ArgBuilder.enumJava`, and `*WithFormatter` builders for `java.time` types (custom `DateTimeFormatter`, `instantEpoch`).
- `Field => A` resolver parameter: gives the selected sub-fields (look-ahead). Hidden from the schema. Combinable with arguments: `Field => (Args => A)`.
- `Extended[A]` wrapper adds response metadata to a field value (used by Federation cache tags).
- Subscriptions: all fields must return `ZStream` (or `Args => ZStream`). fs2 `Stream` and Monix `Observable` through interop.
- `GraphQL#render`, `renderCompact`, `renderWith(renderer)`, `toDocument`. SDL export of the schema.
- `GraphQL#combine` / `|+|` merges two APIs into one schema.
- `GraphQL#withAdditionalTypes`, `withSchemaDirectives`, `withAdditionalDirectives`, `rename(...)` (root type names).
- `caliban.Macros.gqldoc("...")`: compile-time syntax check of a GraphQL document (FAQ only).
- Built-in Java enum schema is explained in the FAQ. Case classes over 22 fields are allowed (FAQ).

## Schema transformations

- `GraphQL#transform(Transformer)`: `RenameType`, `RenameField`, `RenameArgument`, `ExcludeField`, `ExcludeInputField`, `ExcludeArgument`, `ExcludeDirectives` (by `GQLDirective` or `Directive => Boolean`).
- Docs use `ExcludeDirectives` to serve a beta API and a v1 API from the same schema. This is static schema variants, not per-request visibility.
- Custom transformers by extending `Transformer`.

## Execution and interpreter

- `api.interpreter` returns `Exit[ValidationError, GraphQLInterpreter[R, CalibanError]]`. Schema validation happens here. `interpreterUnsafe` throws.
- `GraphQLInterpreter#execute(query, operationName, variables, extensions)`, `executeRequest(GraphQLRequest)`, `check(query)` (validate only).
- `GraphQLInterpreter#mapError`, `provide`/`provideLayer`, `wrapExecutionWith`.
- `QueryExecution.Parallel` (default), `Sequential`, `Batched`, `Mixed` (batched, but top-level fields always in parallel). Docs recommend `Batched` when all effects use `ZQuery.fromRequest`. `Sequential` and `Mixed` are not in the docs.
- `Configurator.ExecutionConfiguration(skipValidation, enableIntrospection, allowMutationsOverGetRequests, queryExecution, validations, queryCache)`. Set per request through a fiber ref, or app-wide with `toLayer`.
- `Configurator.setSkipValidation`, `setEnableIntrospection`, `setQueryExecution`, `setValidations`, `setAllowMutationsOverGetRequests`, `setQueryCache`. Only the first three are in the docs.
- `Configurator.setValidations(List[QueryValidation])`: replace or extend the validation rule list (`Validator.AllValidations`). Custom validation rules this way are not documented.
- `setQueryCache`: custom ZQuery `Cache` per execution.
- Mutation root fields run in order. Pure fields are not forked.
- Errors: `CalibanError` with `ParsingError`, `ValidationError`, `ExecutionError(msg, path, locationInfo, innerThrowable, extensions)`. Error `extensions` set through `mapError`. Domain errors must extend `Throwable` to get a message.
- `GraphQLResponse.withExtension` adds response extensions.

## Wrappers (middleware)

- Wrapper types: `OverallWrapper`, `ParsingWrapper`, `ValidationWrapper`, `ExecutionWrapper`, `FieldWrapper` (`wrapPureValues` flag), `IntrospectionWrapper`. Plus `EffectfulWrapper`, `CombinedWrapper`, `Wrapper.empty`, `Wrapper.suspend`.
- Attach with `GraphQL#withWrapper` or `@@`. Combine with `|+|`.
- `GraphQLAspect`: transforms the whole `GraphQL` (schema plus wrappers). Used by federation, incremental delivery and caching.
- `Wrappers.maxDepth(n)`, `maxFields(n)`, `timeout(duration)`, `printErrors`, `printSlowQueries(duration)`, `logSlowQueries(duration)` (ZIO logging), `onSlowQueries(duration)(fn)`.
- `Wrappers.metrics(...)` (`FieldMetrics`): per-field ZIO metrics, count and duration histogram.
- `Wrappers.checkDirectives(check, excludePureFields)`: field wrapper that reads the field's schema directives and can fail. A building block for directive-based auth. Not in the docs.
- `CostEstimation`: `@GQLCost(weight, multipliers)` on types and fields (`@cost` directive). `multipliers` names numeric arguments that multiply the cost. `queryCost`, `queryCostWith`, `queryCostZIO`, `queryCostZIOWith` add the cost to response extensions. `maxCost(n)(costDirective)`, `maxCostOrError`, `maxCostZIO` reject queries over a limit.
- `ApolloTracing.apolloTracing()`: Apollo Tracing format in `extensions`.
- `Caching.extension(CacheSettings)`: Apollo-style cache control. `@GQLCacheControl(maxAge, scope)` annotation (`@cacheControl` directive), `CacheScope.Public`/`Private`, `CacheSettings.withMaxAge`/`withScope`, runtime `Caching.setCacheHint(hint)` and `Caching.disableCaching`. Adapters turn the policy into a `Cache-Control` header. Docs only give one line.
- `ApolloPersistedQueries.wrapper`: Apollo APQ (sha256 hash in `extensions.persistedQuery`). `ApolloPersistence` service for a custom store. The default store is an unbounded `ConcurrentHashMap`.
- `IncrementalDelivery.defer`, `.stream`, `.all`: opt-in `@defer` and `@stream`. Only allowed on query operations. Docs only describe `@defer` and call it experimental. `@stream` is not in the docs.
- `caliban-tracing`: `TracingWrapper.traced` (`SchemaTracer` plus `FieldTracer`). OpenTelemetry spans per effect through zio-telemetry.
- `caliban-federation`: `ApolloFederatedTracing.wrapper()` (ftv1), turned on by the `apollo-federation-include-trace` header or `request.withFederatedTracing`.

## Batching and optimization (ZQuery)

- `ZQuery[R, E, A]` (zio-query): fields returning `ZQuery` are merged into one query per execution. Automatic batching, deduplication and per-request caching.
- `DataSource[R, A]` / `DataSource.Batched` with `identifier` and `run(Chunk[Req]): CompletedRequestMap`. Requests extend `Request[E, A]`.
- `ZQuery.fromRequest`, `succeed`, `fromZIO`, `foreachPar`, `collectAllPar`, `foreach`, `collectAll`. `run`, `runCache` (replay with a prepared cache), `runLog` (result plus request log).
- Docs example: naive version makes 47 requests, ZQuery version makes 8.
- `Field` metadata in resolvers for projection (select columns or joins). No ORM integration.

## Relay

- `caliban.relay`: `Connection[E]`, `Edge[C, N]`, `PageInfo`, `PaginationArgs[C]`, `Pagination(args)` (validates and decodes args), `Connection.fromList`, `Base64Cursor` (offset cursor), `Cursor[A]` type class for custom cursors.
- `RelaySupport.globalIdentifiers` / `withGlobalIdentifiers[ID](NodeResolver...)`: adds the `Node` interface and `node(id:)` root field. `NodeResolver.from`, `fromMetadata`, `fromOption`, `fromEither`, `fromZIO`. `TypeResolver[ID]` maps an ID to a type name. Added in 3.0.0. Not in the docs.

## HTTP adapters (brief)

- `caliban-quick` `QuickAdapter` (zio-http, no tapir): fastest option. `api.unsafe.runServer(port, apiPath, graphiqlPath, uploadPath, webSocketPath)`, `api.handlers`, `QuickAdapter(interpreter).routes(...)`.
- `QuickAdapter#configure`, `configureWebSocket(WebSocketConfig)`, `configureSse(SseConfig)` (heartbeat), `configureHttp(HttpConfig)` (1 MB JSON request, 16 MB upload and response by default).
- `GraphiQLHandler.handler(apiPath, wsPath)`: GraphiQL from a CDN.
- Tapir-based adapters: `Http4sAdapter`, `AkkaHttpAdapter`, `PekkoHttpAdapter`, `PlayHttpAdapter`. Methods `makeHttpService`, `makeHttpUploadService`, `makeWebSocketService`. Tapir also gives GraphiQL endpoints (2.9.0).
- Interpreters: `HttpInterpreter` (GET and POST), `HttpUploadInterpreter` (GraphQL multipart request spec), `WebSocketInterpreter(keepAliveInterval, webSocketHooks)`.
- `configure(Configurator)` per request. `intercept(ZLayer[ServerRequest, TapirResponse, R])` reads the request (for example an auth token) and provides part of the environment. This is the documented auth pattern.
- `WebSocketHooks`: `beforeInit`, `afterInit`, `onMessage`, `onPing`, `onPong`, `onAck`. Combine with `++`.
- Protocols: `graphql-transport-ws` and legacy `graphql-ws`. SSE subscriptions over POST when `Accept: text/event-stream`. `application/graphql-response+json` content negotiation. `@defer`/`@stream` parts as `multipart/mixed` over HTTP, or `next` messages over WebSocket.
- Mutations over GET are rejected unless `allowMutationsOverGetRequests` is on.
- Custom adapter: `TapirAdapter.makeHttpService` returns tapir `ServerEndpoint`s for any tapir server. `convertHttpEndpointToFuture`, `Http4sAdapter.convertHttpEndpointToF`.
- File uploads: `Upload` type in the schema, `Uploads` service. Only through `HttpUploadInterpreter` or the quick upload path.

## Effect and JSON interop

- `caliban-cats`: `interpreterF[F]`, `executeAsync`, `checkAsync`. `Schema` for any `F[_]: Async` with a `Dispatcher`. `ToEffect`, `FromEffect`, `CatsInterop.contextual` to share a context (for example `Kleisli`) between cats-effect and ZIO. `InjectEnv`. fs2 `Stream` for subscriptions.
- `caliban-monix`: `interpreterMonix`, `executeAsync`, `checkAsync`. Monix `Task` and `Observable` schemas. Only with cats-effect 2.
- `Future` fields are supported in core.
- JSON codecs: circe, jsoniter, play-json, zio-json.
- Third-party: `kyo-caliban` (Kyo effect), `caliban-extras` / `caliban-refined` (refined types).

## Tapir interop

- `caliban-tapir`: `import caliban.interop.tapir._` adds `toGraphQL` to tapir `Endpoint` and `ServerEndpoint`.
- `GET` endpoints become queries. `PUT`, `POST`, `DELETE` become mutations.
- Field names come from fixed path segments (`/book/add` gives `bookAdd`). Override with `endpoint.name("...")`.
- Query params, headers, cookies and body become GraphQL arguments. Needs `Schema` and `ArgBuilder` for the types.
- The same `ServerEndpoint` can serve REST (`toRoutes`) and GraphQL. Combine APIs with `|+|`.

## Federation

- `caliban-federation`. `schema @@ federated(entityResolvers*)` adds `_service`, `_entities`, `_Any`, `_Entity`, `_FieldSet`.
- v1: `caliban.federation.v1._`. `@GQLKey`, `@GQLExtend`, `@GQLExternal`, `@GQLProvides`, `@GQLRequires`.
- v2: import `caliban.federation.v2_x._` to pick the spec version. Packages exist for v2.0, 2.1, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12.
- v2 annotations: `@GQLShareable`, `@GQLInaccessible`, `@GQLOverride`, `@GQLProgressiveOverride` (label, 2.7), `@GQLTag`, `ComposeDirective`, `@GQLInterfaceObject` (2.3), `@GQLCost` and `@GQLListSize` (2.9), `@GQLCacheTag` (2.12). `@GQLKey(fields, resolvable)`.
- v2 annotations not in the docs: `@GQLAuthenticated`, `@GQLRequiresScopes` (2.5), `@GQLPolicy` (2.6), `@GQLContext`/`@GQLFromContext` (2.8), `@GQLConnect`/`@GQLSource` (Apollo Connectors, 2.10 and 2.11, with `connect` helpers for HTTP method, headers, batch settings and JSON selection).
- `EntityResolver[R, Args, T](args => ZQuery)`, `EntityResolver.from`, `fromMetadata` (look-ahead), `fromEither`, `fromOption`, `fromZIO`, `fromQuery`. Cached variants `fromCachedOption`, `fromCachedEither`, `fromCachedZIO`, `fromCachedQuery` return cache tags.
- Cache tags: `cacheField(value)(tags)` returns `Extended[A]`. Tags go to `extensions.apolloEntityCacheTags`.
- `FederationV2(Link(...) :: ComposeDirective(...) :: ...)`: custom federation object with own `@link` imports and composed directives.
- `CacheInvalidator` (in `caliban-stitching`, package `caliban.federation.subgraph`): Apollo cache invalidation by subgraph, type or tag through a shared-secret POST.

## Gateway (new in 3.2.0)

- `caliban-gateway`: router alternative to Apollo Router, Hive Router and Cosmo. Passes all 199 cases of the Federation Gateway Audit, which runs in CI (`gateway-audit/`). Release notes call it "very fresh".
- `Gateway.compose(subgraphs*)` or `Gateway.fromSupergraph(source)`. `gateway.interpreter`, `gateway.reloadable` (hot schema reload with polling and jitter, draining old interpreter).
- `Subgraph.graphql(name, url | GraphQL[R], sdl?)` for plain GraphQL services. `Subgraph.federation(...)` for Federation subgraphs. Local in-process Caliban APIs can be subgraphs.
- `Lookup.single` / `Lookup.list` with `Lookup.Argument.key`, `obj`, `batch`: join objects across plain (non-federated) services. Compile-time checks on lookup shape.
- `Supergraph.file`, `http`, `sdl`, `parsed`, `uplink` (Apollo GraphOS), `hive` (Hive CDN). `withSubgraphConfig`, `withSubgraphEndpoint`.
- `SchemaTransformation.renameField`, `hideField`, and type and argument renames before composition.
- `interpreter.explain(query)`: shows the query plan. Operation and plan cache (`withMaxOperationCacheWeight`).
- `RemoteGraphQLConfig`: timeouts, retries for queries only, in-flight query deduplication, static, effectful and forwarded headers, body size limits, redirect rules.
- `GatewayConfig`: request timeout, drain timeout, planning limits and timeout, `withMaxOperationCost` (demand control from `@cost`/`@listSize`), `withRemoteErrorMessages` (hidden by default, only `code` passes through).
- `PhaseHooks`: `operation`, `preparation`, `resolution`, `overrideLabels`, `cacheAccess`, `authorization`, `execution`, `subgraphCall`, `attempt`, `completion`, and subscription hooks. `PhaseHandler.incoming`, `incomingDiscard`, `outgoing`, `scoped`.
- `PhaseHooks.trustedDocuments(map)(idExtractor)` and `PhaseHooks.resolution(...)`: persisted and trusted documents. Error codes `TRUSTED_DOCUMENT_ID_INVALID`, `TRUSTED_DOCUMENT_NOT_FOUND`.
- `PhaseHooks.fromClaims(...)`: enforces `@authenticated` and `@requiresScopes`. `@policy` always denies. `PhaseHooks.authorization` for custom checks with `PhaseHooks.Denial`.
- Progressive `@override` with `percent(n)` labels or custom labels.
- Subscriptions from local and remote subgraphs (WebSocket or SSE upstream). Limits on active subscriptions and buffers. No upstream reconnect.
- `GatewayMetrics.hooks` (ZIO metrics). `GatewayTracing.hooks` in `caliban-gateway-tracing` (OpenTelemetry).
- No `@defer`/`@stream` from subgraphs. No Federation 1 supergraphs. No breaking-change check on reload.

## Stitching

- `caliban-stitching`: `SchemaLoader.fromIntrospection`, `RemoteSchema.parseRemoteSchema`, `RemoteSchemaResolver.fromSchema(...).remoteResolver(typeName)(...)`.
- `RemoteResolver` composable steps with `>>>`: `fromFunction`, `fromFunctionM`, `toQuery`, `request(url)`, `execute`, `unwrap`, `fromUrl`.
- Docs now point new users to the gateway. No type renaming or conflict resolution in stitching.

## Client and codegen

- `caliban-client` (JVM and Scala.js), on sttp 4. `SelectionBuilder[Origin, A]` built from generated code. Combine with `~`, map with `mapN`. Fragments (`fragment(on)`), field and operation directives (`withDirective`). `toRequest(uri, useVariables, queryName, dropNullInputValues)`, `toRequestWith`.
- Client sends queries and mutations only. Subscriptions only through `caliban-client-laminext` (`toEventStream`, `toSubscription` over `graphql-ws`).
- `caliban-codegen-sbt` `CalibanPlugin`: generates client code from `src/main/graphql` on compile, or from a URL through introspection. Manual `calibanGenClient`.
- Client codegen settings: `packageName`, `clientName`, `scalafmtPath`, `genView`, `scalarMappings`, `imports`, `splitFiles`, `enableFmt`, `extensibleEnums`, `excludeDeprecated`, `headers`.
- `CompileTimeCalibanPlugin` (`CompileTimeCalibanServerPlugin` plus `CompileTimeCalibanClientPlugin`): generates a client straight from the server's `GraphQL[R]` value in another sbt module.
- Server codegen (schema-first): `genType(Codegen.GenType.Schema)` or `calibanGenSchema`. Options `effect`, `abstractEffectType`, `preserveInputNames`, `addDerives`, `envForDerives`, `scalarMappings`.
- Codegen directives: `@lazy` (field becomes an effect), `@newtype(name)` (value-class IDs).
- `caliban-codegen` runs the generators without sbt (`caliban.codegen.Codegen`).
- Codegen does not support type extensions.

## Tools and reporting

- `caliban-tools`: `IntrospectionClient`, `SchemaLoader` (`fromCaliban`, `fromFile`, `fromString`, `fromIntrospection`), `SchemaComparison.compare` returning `SchemaComparisonChange` with a `breaking` flag.
- `caliban-reporting`: Apollo schema reporting protocol. `SchemaReporter.fromDefaultConfig` (`APOLLO_KEY`), `SchemaReportingRef.make`/`fromRef`, `ReportingDaemon.register`.

## Not supported or not in scope

- No ORM or database integration. No auto filtering, ordering or pagination from models. `Field` metadata only gives the selection.
- No built-in auth or permission system in the server library. Docs point to ZIO environment plus adapter `intercept`. `checkDirectives` is a building block only. The gateway has `@authenticated`/`@requiresScopes` enforcement.
- No per-request schema visibility. Transformers make static schema variants.
- No input validation framework beyond `ArgBuilder` errors and `@oneOf`.
- No rate limiting.
- No trusted-documents or persisted-query allowlist in the server library. Only Apollo APQ (cache, not allowlist). The gateway has trusted documents.
- No schema-first SDL loading for servers at runtime. Schema-first is only through code generation.
- Scala 3 derivation does not support value classes or opaque types.
- Client cannot send subscriptions over sttp.
- Monix only with cats-effect 2.

## Upcoming and unreleased work

- `series/3.x` after 3.2.0: gateway support for interface objects in supergraphs, recursive `@oneOf` fix, `@defer` multipart flush fix, gateway performance.
- PR #3152 (2026-10-09): `caliban-hive` and `caliban-gateway-hive` modules. Report operation usage to GraphQL Hive (`HiveUsage.wrapper`, `GatewayHive.hooks`).
- PR #3088: progressive override support. PR #2980: cross-compile core to Scala Native. PR #2866: `TypeVisitor` loops through arguments.
- Branch `gateway-composite-schemas` (2026-10-05): gateway support for the GraphQL Composite Schemas spec (`@lookup`-style resolution, `FieldSelectionMap`, `@require`).
- Branch `native` (2026-05-29): Scala Native support.
- Stale branches: `codegen-from-graphql-queries` (2024, codegen from query files), `schema-tags-poc` and `schema-tags-transformer` (2024, exclude fields by tags), `hearth-derivation` (2026-04, WIP derivation rewrite).

## Docs and code disagree

- Federation docs say "Caliban provides support for v2.0, v2.1 and v2.3". The code ships `v2_0` to `v2_12`, and the same page documents 2.7, 2.9 and 2.12.
- The federation directive table omits `@authenticated`, `@requiresScopes`, `@policy`, `@context`, `@fromContext`, `@connect` and `@source`. The code has annotations for all of them.
- Middleware docs describe only `@defer` as "experimental". The code also has `@stream` (`IncrementalDelivery.stream`, since 2.9.0).
- Relay docs cover only connections. The code has global identifiers and the `node` field (`RelaySupport`, since 3.0.0).
- Adapter docs list only three `Configurator` setters. The code also has `setValidations`, `setAllowMutationsOverGetRequests` and `setQueryCache`.
- Middleware docs name `ApolloPersistedQueries.apolloPersistedQueries`. That method does not exist. The code has `ApolloPersistedQueries.wrapper` and `wrapper(cache)`.
- Interop docs say cats and monix add `interpreterAsync`. That method does not exist. The code has `interpreterF[F]` (cats, used in the docs example) and `interpreterMonix` (monix).
- Docs snippets use version `3.1.5`. The gateway pages describe 3.2.0 features.
- `CacheInvalidator` is documented on the stitching page and ships in `caliban-stitching`, but lives in package `caliban.federation.subgraph`.
- Getting Started lists ZIO HTTP as a supported server. There is no separate zio-http adapter since 2.8.0. It is the `QuickAdapter`.
- Stitching example code uses old ZIO 1 APIs (`Has`, `Task.effect`, `toLayer`). I think it does not compile on current versions.

## Sources

- https://ghostdogpr.github.io/caliban/ (source: https://github.com/ghostdogpr/caliban/tree/series/3.x/vuepress/docs)
- https://ghostdogpr.github.io/caliban/docs/schema.html
- https://ghostdogpr.github.io/caliban/docs/middleware.html
- https://ghostdogpr.github.io/caliban/docs/optimization.html
- https://ghostdogpr.github.io/caliban/docs/adapters.html
- https://ghostdogpr.github.io/caliban/docs/interop.html
- https://ghostdogpr.github.io/caliban/docs/federation.html
- https://ghostdogpr.github.io/caliban/docs/gateway.html (plus `gateway/configuration`, `hooks`, `planning`, `subgraphs`, `subscriptions`)
- https://ghostdogpr.github.io/caliban/docs/client.html, `client-codegen.html`, `server-codegen.html`, `laminext.html`
- https://ghostdogpr.github.io/caliban/docs/relay-connections.html, `stitching.html`, `schema-comparison.html`, `schema-reporting.html`, `tools.html`
- https://ghostdogpr.github.io/caliban/faq/
- https://github.com/ghostdogpr/caliban (source in `core`, `federation`, `adapters`, `interop`, `stitching`, `client`, `codegen`, `gateway`)
- https://github.com/ghostdogpr/caliban/releases
- https://github.com/ghostdogpr/caliban/pulls
- https://github.com/ghostdogpr/caliban/branches
- https://ghostdogpr.github.io/caliban/llms.txt (404)
