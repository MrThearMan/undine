# Netflix DGS findings

Versions checked: dgs-framework 12.1.0 (latest, GitHub release 2026-09-16). Repo `master` at `0f3f258` (last commit 2026-09-14). dgs-codegen 8.7.0 (2026-09-22), `master` at `bcbc9a7` (2026-09-30). Docs repo `Netflix/dgs` at `fc3d3e0` (2026-08-23).
DGS ("Domain Graph Service") is a Spring Boot framework for GraphQL servers in Java and Kotlin. Apache 2.0. Built on graphql-java (engine details are in `graphql-java.md`, not repeated here).
Schema style: schema-first only. SDL files plus annotated Spring beans (`@DgsComponent`, `@DgsData`). No code-first schema generation from classes. Codegen goes the other way (SDL to Java/Kotlin types).
Relation to Spring for GraphQL: since 8.5.0 (2024-03) DGS runs on top of Spring for GraphQL. Since 10.0.0 (2024-12) the old DGS web layer is gone. Spring for GraphQL owns HTTP, WebSocket, SSE, RSocket transports and execution (`ExecutionGraphQlService`). DGS builds the `GraphQLSchema` and adds its annotation model, data loader registry, codegen, client, metrics and testing on top. `DgsQueryExecutor` is now a proxy over `ExecutionGraphQlService`. Both programming models can be mixed, but the docs advise against it.

## Maintenance status

- Active. 3399 stars. Not archived. About 48 open issues plus PRs (GitHub search count). Maintained by Netflix (Paul Bakker, Jacob Jacobs, Kavitha Srinivasan, others).
- Last commit on `master` 2026-09-14. Repo push activity 2026-10-03 (branches and PRs).
- Release lines: 12.x (Spring Boot 4, Jackson 3 default), 11.x (Spring Boot 4, Jackson 2), 10.x (Spring Boot 3, still gets backports: 10.6.0 on 2026-04-27). JDK 17 toolchain.
- Major history: 6.0 Spring Boot 3 (2023-01). 7.0 graphql-java 20. 8.0 graphql-java 21. 8.5 Spring for GraphQL integration (2024-03). 10.0 legacy code removed (2024-12). 11.0 Spring Boot 4 (2025-12-05). 12.0 Jackson 3 (2026-04-27).
- No `CHANGELOG.md` in the framework repo. Changes are in GitHub release notes. dgs-codegen has an empty `CHANGELOG.md` and uses GitHub releases.
- Docs source is a separate repo: `Netflix/dgs` (MkDocs Material). About 6100 lines of Markdown. No versioned docs.
- https://netflix.github.io/dgs/llms.txt returns 404. `Accept: text/markdown` returns HTML.
- IntelliJ plugin "DGS" (JetBrains marketplace 17852): navigation between schema and code, hints, quick fixes.
- Community Maven codegen plugin: `deweyjose/graphqlcodegen` (same codegen core).

## Big changes between majors

- 10.0: removed modules `graphql-dgs-spring-boot-starter`, `graphql-dgs-spring-webmvc*`, `graphql-dgs-webflux-starter`, `graphql-dgs-mocking`, all `graphql-dgs-subscriptions-*` (websockets, SSE, graphql-sse). Removed `DgsAutoConfiguration`, `DefaultGraphQLClient`, `DefaultDgsQueryExecutor`, `DefaultDgsReactiveQueryExecutor`. New starter name `com.netflix.graphql.dgs:dgs-starter`. Subscriptions moved from `/subscriptions` to `/graphql`. SSE now uses the graphql-sse RFC protocol only.
- 10.1: `@Source` parameter annotation. Fallback global type resolver `@DgsDefaultTypeResolver`. JPMS `module-info`. `DgsDataFetchingEnvironment` allowed as first argument of `@DgsEntityFetcher`.
- 10.2: baseline Spring Boot 3.5 and spring-graphql 1.4. Scalar deserialization in `GraphQLResponse`. APQ autoconfig prefers a Caffeine cache with Micrometer metrics.
- 10.4: strict mode with `@DgsRuntimeWiring`. Data loader reload API for development (`DgsDataLoaderReloadController`).
- 11.0: Spring Boot 4 and spring-graphql 2. No new features.
- 12.0: Jackson 3 support. `DgsJsonMapper` abstraction (`graphql-dgs-json-api`). `Jackson3DgsJsonMapper` default. `dgs.graphql.preferred-json-mapper` (`jackson3` or `jackson2`). Opt-in `graphql-dgs-jackson2`. New Jackson-agnostic client classes `DgsGraphQLClient`, `DgsMonoGraphQLClient`, `DgsReactiveGraphQLClient`, `DgsWebClientGraphQLClient`, `DgsRestClientGraphQLClient`, `DgsGraphqlSSESubscriptionGraphQLClient`, `DgsGraphQLRequestOptions`. Old client classes deprecated. Spring Boot version check at startup. Flag to turn off the Apollo federation schema transform (`dgs.graphql.federation.enabled`).
- 12.1: graphql-java-extended-scalars 24.0 with new scalars registered. Data loader registry is closed in `SpringGraphQLDgsQueryExecutor`.

## Modules

- `dgs-starter` (alias `graphql-dgs-spring-graphql-starter`), `dgs-starter-test` (alias `graphql-dgs-spring-graphql-starter-test`).
- `graphql-dgs` (core annotations and schema provider), `graphql-dgs-spring-graphql` (autoconfig on Spring for GraphQL), `graphql-dgs-reactive` (`DgsReactiveQueryExecutor`, `DgsReactiveCustomContextBuilderWithRequest`).
- `graphql-dgs-client`, `graphql-dgs-subscription-types` (WebSocket protocol message types), `graphql-error-types` (`TypedGraphQLError`, `ErrorType`, `ErrorDetail`).
- `graphql-dgs-extended-scalars`, `graphql-dgs-extended-validation`, `graphql-dgs-pagination`, `graphql-dgs-spring-boot-micrometer`.
- `graphql-dgs-json-api` (`DgsJsonMapper`), `graphql-dgs-jackson2`.
- `graphql-dgs-platform` (BOM for DGS modules) and `graphql-dgs-platform-dependencies` (BOM that also pins Spring, Jackson, Kotlin, graphql-java).
- Spring Initializr has a "Netflix DGS" entry and a "GraphQL DGS Code Generation" entry.

## Schema definition

- SDL files loaded from `dgs.graphql.schema-locations` (default `classpath*:schema/**/*.graphql*`). Multiple locations allowed. Files are concatenated with `MultiSourceReader`.
- `@DgsTypeDefinitionRegistry` on a `@DgsComponent` method returns a graphql-java `TypeDefinitionRegistry`. Merged with the SDL files. Optional parameter gets the current registry. Lets you add schema parts from code.
- `@DgsCodeRegistry` method gets `GraphQLCodeRegistry.Builder` and `TypeDefinitionRegistry`, returns the builder. Programmatic data fetchers.
- `@DgsRuntimeWiring` method gets and returns `RuntimeWiring.Builder`. Raw access for scalars, directives, wiring.
- Spring for GraphQL `RuntimeWiringConfigurer` beans are also applied (`DgsRuntimeWiringConfigurerBridge`, source only).
- An existing `TypeDefinitionRegistry` bean is merged too (source only).
- Schema-to-code validation at startup (`dgs.graphql.schema-wiring-validation-enabled`, default true, not in docs): a `@DgsData` with an unknown parent type or field fails with `DataFetcherSchemaMismatchException`. An `@InputArgument` name that is not on the schema field fails with `DataFetcherInputArgumentSchemaMismatchException`. Duplicate data fetchers for one field fail with `InvalidDgsConfigurationException`.
- graphql-java `RuntimeWiring` strict mode is on by default (`dgs.graphql.strict-mode.enabled`, not in docs).
- `dgs.graphql.introspection.show-sdl-comments` (default true): `#` comments in SDL become descriptions. Legacy behavior.
- `ReloadSchemaIndicator` bean: rebuild the schema (rerun `@DgsTypeDefinitionRegistry` and `@DgsCodeRegistry`) when it returns true. Allows runtime schema changes from an external signal.
- Development mode reloads the schema on every request: `dgs.reload=true`, or the `laptop` Spring profile. `@ConditionalOnDgsReload` (source only). Designed for JRebel-style hot reload.
- Spring for GraphQL schema inspection report works for DGS data fetchers (unmapped fields, fetchers without schema fields).
- Schema printing: Spring for GraphQL `spring.graphql.schema.printer.enabled` serves SDL at `/graphql/schema`.

## Data fetchers

- `@DgsComponent` marks a Spring bean that holds DGS annotated methods. It is a Spring `@Component` with `@Qualifier("dgs")`.
- `@DgsData(parentType, field)` registers a method as the data fetcher for `Type.field`. `field` defaults to the method name. `@DgsData.List` (repeatable) binds one method to many fields. Also on interface parent types: registers on all implementations (source only).
- `@DgsData(trivial = true)` marks the fetcher as a graphql-java `TrivialDataFetcher` (not in docs). Affects instrumentation and virtual threads.
- Shorthands `@DgsQuery`, `@DgsMutation`, `@DgsSubscription` (fixed parent type). Not repeatable.
- Return types: plain value, `CompletableFuture`/`CompletionStage`, `DataFetcherResult<T>` (data, errors, `localContext`), Reactor `Mono` and `Flux` (via `MonoDataFetcherResultProcessor`, `FluxDataFetcherResultProcessor`), Kotlin `Flow` (`FlowDataFetcherResultProcessor`), Kotlin `suspend` functions (`ContinuationArgumentResolver`, coroutine dispatcher bean `dgsCoroutineDispatcher`, default `Dispatchers.Unconfined`). Most of these are source only.
- `DataFetcherResultProcessor` interface: plug in your own return type conversion (source only).
- Method parameters:
  - `@InputArgument` (optional `name`) converts a GraphQL argument into a Java/Kotlin type. Input objects map to POJOs (no-arg constructor plus field set) or Kotlin data classes (constructor). Lists and `Optional` work. Not Jackson based, so Jackson annotations are ignored.
  - Parameters without annotation are matched by parameter name (`FallbackEnvironmentArgumentResolver`, needs `-parameters` compiler flag).
  - `@Source` gets the parent object (10.1).
  - `DataFetchingEnvironment` or `DgsDataFetchingEnvironment`.
  - Spring MVC annotations `@RequestHeader`, `@RequestParam`, `@CookieValue`, plus map variants. `defaultValue`, `required`, `Optional`. Work on WebMVC and WebFlux (separate resolvers). A missing required value throws `DgsInvalidInputArgumentException` / `DgsMissingCookieException`.
- `InputObjectMapper` interface (`mapToJavaObject`, `mapToKotlinObject`) for custom input conversion (source only). `DefaultInputObjectMapper`.
- `DgsDataFetchingEnvironment` adds `getDgsContext()`, `getDataLoader(Class)` (type safe lookup by loader class) to graphql-java's environment.
- Child data fetchers on non-root types for expensive fields. `getSource()` for parent. `localContext` in `DataFetcherResult` to pass data down. `dfe.getSelectionSet().contains("field")` for look-ahead pre-loading. Fields on returned objects that are not in the schema are dropped.
- `DefaultDataFetcherFactory` bean overrides graphql-java's default property fetcher (source only).
- Custom `ExecutionStrategy` beans with qualifier `query` or `mutation` are used (source only).
- `QueryValueCustomizer` bean rewrites the incoming query string before execution (source only).
- Threading: data fetchers run on the request thread unless they return `CompletableFuture`. `dgs.graphql.virtualthreads.enabled=true` (JDK 21) runs each user-defined data fetcher in its own virtual thread. Turned on automatically when `spring.threads.virtual.enabled=true`. Executor bean `dgsAsyncTaskExecutor` for your own futures.
- Spring for GraphQL `@SchemaMapping`/`@QueryMapping` controllers can coexist. Some DGS features (scheduled dispatch, data loader metrics) do not apply to them.

## Context

- `DgsContext` holds `customContext` and `requestData`. `DgsContext.getCustomContext(dfe)` and `DgsContext.getCustomContext(batchLoaderEnvironment)`.
- `DgsCustomContextBuilder<T>` bean builds a per-request custom context. `DgsCustomContextBuilderWithRequest<T>` gets `extensions`, `HttpHeaders`, `WebRequest`. Reactive: `DgsReactiveCustomContextBuilderWithRequest`.
- `DgsRequestData` (headers, extensions). Cast to `DgsWebMvcRequestData` (`WebRequest`) or `DgsReactiveRequestData` (`ServerRequest`) to reach the raw request and response.
- `GraphQLContextContributor` bean: `contribute(GraphQLContext.Builder, extensions, DgsRequestData)`. Runs before other instrumentation. Puts values in graphql-java `GraphQLContext`.
- Data loaders get `GraphQLContext` as their context (since 6.0).
- `DgsQueryExecutorRequestCustomizer` adjusts the mock `WebRequest` used by `DgsQueryExecutor` in tests (source only).

## Arguments, input types, scalars

- `@DgsScalar(name)` on a class that implements graphql-java `Coercing`. Also accepts a `GraphQLScalarType` (source only).
- `graphql-dgs-extended-scalars` autoregisters graphql-java-extended-scalars: `DateTime`, `Date`, `Time`, `LocalTime`, `Object`, `Json`, `Url`, `Locale`, `UUID`, `CountryCode`, `Currency`, `Char`, numeric (`PositiveInt`, `NegativeInt`, `NonPositiveInt`, `NonNegativeInt`, float variants, `Long`, `Short`, `Byte`, `BigDecimal`, `BigInteger`), plus since 12.1 (not in docs) `HexColorCode`, `Year`, `YearMonth`, `SecondsSinceEpoch`, `AccurateDuration`, `NominalDuration`.
- Per group toggles `dgs.graphql.extensions.scalars.<group>.enabled` (`time-dates`, `objects`, `numbers`, `chars`, `ids`, `country`, `currency`, `colors`). Per scalar toggles `numbers.bigdecimal.enabled`, `numbers.biginteger.enabled` (source only). `dgs.graphql.extensions.scalars.strict-mode.enabled` (source only).
- `Upload` scalar: `UploadScalar` component maps to Spring `MultipartFile`. Multipart transport itself needs the third party `multipart-spring-graphql` library since the Spring for GraphQL move. I think `UploadScalar` is not auto-registered by any autoconfig (only declared as a `@DgsComponent` in core), not verified at runtime.
- `graphql-dgs-extended-validation` registers graphql-java-extended-validation schema directives (`@Size`, `@Range`, `@Pattern` and others). `ValidationRulesBuilderCustomizer` bean to customize `ValidationRules.Builder` (source only).
- `dgs.graphql.enable-entity-fetcher-custom-scalar-parsing` (default false): bug fix flag for custom scalars in federation representations.

## Interfaces and unions

- Automatic type resolution when Java class simple name equals the GraphQL type name.
- `@DgsTypeResolver(name = "Movie")` method returns the concrete type name as `String`.
- `@DgsDefaultTypeResolver` on a method: one global fallback resolver for all abstract types (10.1, not in docs).
- `checkUnregisteredTypeResolvers` fails at startup for abstract types without a resolver (I think, from the method name, not traced in detail).

## Mutations

- Same model as queries: `@DgsMutation` or `@DgsData(parentType = "Mutation")`. Input types via `@InputArgument`.
- Sparse updates are a codegen feature (`trackInputFieldSet`), see codegen.
- No built-in CRUD or ORM mutation generation.

## Subscriptions

- `@DgsSubscription` returns a Reactive Streams `Publisher` (Reactor `Flux`). Kotlin `Flow` also works (source only).
- Transports come from Spring for GraphQL: WebSocket `graphql-transport-ws` (needs `spring.graphql.websocket.path` or `dgs.graphql.websocket.path`, plus `spring-boot-starter-websocket` on MVC), SSE (graphql-sse RFC, `text/event-stream` on `/graphql`), RSocket.
- `dgs.graphql.websocket.connection-init-timeout` (default 10s) maps to the Spring property.
- Errors in the stream: implement Spring for GraphQL `SubscriptionExceptionResolver`.
- Unit testing via `DgsQueryExecutor.execute(...)` which returns `ExecutionResult` with a `Publisher<ExecutionResult>` as data. Reactor `StepVerifier` with virtual time.
- Federation subscription callback protocol is available via Spring for GraphQL and federation-jvm.
- The old DGS subscription modules (own WebSocket handler, legacy SSE) were removed in 10.0.

## Batching (data loaders)

- `@DgsDataLoader(name, caching = true, batching = true, maxBatchSize = 0)` on a class implementing `BatchLoader`, `MappedBatchLoader`, `BatchLoaderWithContext` or `MappedBatchLoaderWithContext` (java-dataloader). Also on a field holding a lambda, and on `@Bean` methods (source only).
- `name` can be omitted. A name is generated from the class (`DataLoaderNameUtil`, source only).
- Lookup: `dfe.getDataLoader("name")` or type safe `dgsDfe.getDataLoader(MyLoader.class)`.
- `Try<V>` results for partial failures per key.
- `@DgsDispatchPredicate` on a `DispatchPredicate` field: per loader scheduled dispatch (`ScheduledDataLoaderRegistry`). Example `DispatchPredicate.dispatchIfLongerThan(...)`.
- Ticker mode: `dgs.graphql.dataloader.ticker-mode-enabled`, `dgs.graphql.dataloader.schedule-duration` (default 10ms). Fixes chained loader calls that would hang without manual `dispatch()`. Executor bean `dgsScheduledExecutorService`.
- All loaders are wrapped to "with context" variants by default (`dgs.graphql.convert-all-data-loaders-to-with-context.enabled`, not in docs).
- Extension points (source only): `DgsDataLoaderCustomizer` (wrap or replace each loader), `DgsDataLoaderOptionsProvider` (java-dataloader `DataLoaderOptions` per loader), `DgsDataLoaderInstrumentation.onDispatch(name, keys, env)`, `DataLoaderInstrumentationExtensionProvider`, `DgsDataLoaderRegistryConsumer` (loader gets the whole `DataLoaderRegistry`).
- `DgsDataLoaderReloadController` (10.4): reload data loader beans at runtime in development, with stats (`getReloadStats`). Active only in reload mode. Programmatic API, no HTTP endpoint (source only).
- Data loaders are per request. `@DgsDataLoader` fields inside a `@Secured` class throw `UnsupportedSecuredDataLoaderException`.
- Docs warn about `ForkJoinPool` saturation and suggest a dedicated `Executor` per loader.

## Relay and pagination

- Spring for GraphQL `ConnectionTypeDefinitionConfigurer` is wired by default (`dgs.springgraphql.pagination.enabled`, default true, not in docs). It generates `XConnection`/`XEdge`/`PageInfo` for types named `*Connection` in the schema.
- `graphql-dgs-pagination` (older DGS feature): `@connection` directive on a type generates `XConnection`, `XEdge`, `PageInfo`. Directive is defined by the framework. Use graphql-java `graphql.relay.Connection`, `SimpleListConnection`.
- No built-in cursor or offset pagination logic, filtering or ordering. No ORM integration.
- No Relay `Node` interface or global ID helpers.

## Federation

- Federation is on by default via Apollo `federation-graphql-java-support` (`Federation.transform`). Turn off with `dgs.graphql.federation.enabled=false` (12.0, not in docs).
- `@DgsEntityFetcher(name = "Show")` method gets the representation `Map<String, Object>` and returns the entity, `CompletionStage`, or `Mono`. `Flux` not supported. Optional `DgsDataFetchingEnvironment` first argument (10.1).
- `DgsFederationResolver` interface. `DefaultDgsFederationResolver` with `typeMapping()` (`Map<Class<?>, String>`) when Java class names differ from GraphQL names. Custom `entitiesFetcher()` and `typeResolver()`.
- Errors: `MissingDgsEntityFetcherException`, `DuplicateEntityFetcherException`, `InvalidDgsEntityFetcher`, `MissingFederatedQueryArgument`.
- Docs examples use Federation 1 directives (`@key`, `@extends`, `@external`). Federation 2 support comes from federation-jvm (I think it works by `@link` in SDL, not verified).
- Federated tracing: `FederatedTracingInstrumentation` from federation-jvm as a bean. Docs show a `GraphQLContextContributor` that forwards the `apollo-federation-include-trace` header to stop tracing by default.
- Testing: `_entities` queries via `DgsQueryExecutor`. Codegen generates `EntitiesGraphQLQuery`, `<Type>Representation` classes and `EntitiesProjectionRoot` for type safe entity queries.
- Example repo: `Netflix/dgs-federation-example` with Apollo Gateway.

## Errors

- Default `DataFetcherExceptionHandler` is `DefaultDataFetcherExceptionHandler`. Any exception becomes a `TypedGraphQLError` with `errorType: INTERNAL` and message `"<ExceptionClass>: <message>"`. Spring Security `AccessDeniedException` becomes `PERMISSION_DENIED`. `DgsException` subclasses carry their own type and log level.
- `DgsException` subclasses: `DgsEntityNotFoundException` (`NOT_FOUND`), `DgsBadRequestException` (`BAD_REQUEST`), `DgsInvalidInputArgumentException`, others.
- Custom handling options: Spring for GraphQL `@ControllerAdvice` with `@GraphQlExceptionHandler` methods. Or a `DataFetcherExceptionHandler` bean that delegates to `DefaultDataFetcherExceptionHandler`. `logException` is overridable.
- `GraphQLJavaErrorInstrumentation` (on by default, `dgs.graphql.errors.classification.enabled`, not in docs): rewrites graphql-java validation, syntax, non-null, operation-not-supported and aborted errors to `BAD_REQUEST` typed errors. Adds `extensions.classification`.
- Netflix error spec (`graphql-error-types`): `extensions.errorType` enum `BAD_REQUEST`, `FAILED_PRECONDITION`, `INTERNAL`, `NOT_FOUND`, `PERMISSION_DENIED`, `UNAUTHENTICATED`, `UNAVAILABLE`, `UNKNOWN`. Each has a rough HTTP analog. Optional `errorDetail` (`ErrorDetail.Common`: `DEADLINE_EXCEEDED`, `ENHANCE_YOUR_CALM`, `TOO_MANY_REQUESTS`, `FIELD_NOT_FOUND`, `INVALID_ARGUMENT`, `INVALID_CURSOR`, `MISSING_RESOURCE`, `CONFLICT`, `SERIALIZATION_ERROR`, `SERVICE_ERROR`, `THROTTLED_CONCURRENCY`, `THROTTLED_CPU`, `UNIMPLEMENTED`), `origin`, `debugInfo`, `debugUri`.
- Builders: `TypedGraphQLError.newInternalErrorBuilder()`, `newBadRequestBuilder()`, `newPermissionDeniedBuilder()`, `newNotFoundBuilder()`, `newConflictBuilder()`, `newBuilder()`, with `.debugInfo(map)`, `.errorDetail(...)`, `.origin(...)`.
- SDL for the error types ships in the jar (`META-INF/schema/errortype.graphqls`, `errordetail.graphqls`). `apollo-error-code-mapping.json` maps Apollo codes (`GRAPHQL_PARSE_FAILED`, `BAD_USER_INPUT`, `PERSISTED_QUERY_NOT_FOUND` and others) to DGS types (source only).
- Docs describe "errors as data" (errors modeled in the schema) as a pattern. No framework support for it.

## HTTP layer and request handling

- Endpoint `dgs.graphql.path` (default `/graphql`) maps to `spring.graphql.http.path`. GraphiQL at `dgs.graphql.graphiql.path` (default `/graphiql`), `dgs.graphql.graphiql.enabled` (default true).
- WebMVC and WebFlux both supported (Spring for GraphQL). RSocket via Spring for GraphQL.
- `dgs.graphql.spring.webmvc.asyncdispatch.enabled` (default false in DGS, Spring default is async).
- Headers and response modification: Spring for GraphQL `WebGraphQlInterceptor`.
- `DgsExecutionResult` with `headers` and HTTP `status`, plus the `dgs-response-headers` extension key, still set response headers via a built-in interceptor (`dgs.graphql.dgs-response-headers.enabled`, default true). Kept for backward compatibility (source only).
- Introspection toggle `dgs.graphql.introspection.enabled` maps to `spring.graphql.schema.introspection.enabled`. Startup fails if both are set. When disabled, DGS also sets graphql-java `INTROSPECTION_DISABLED` in context.
- DGS turns off Spring Boot `GraphQlObservationAutoConfiguration` and `GraphQlWebMvcSecurityAutoConfiguration` unless `dgs.springgraphql.autoconfiguration.graphqlobservation.enabled` / `...graphqlwebmvcsecurity.enabled` is true (source only).
- Custom object mapper: customize Spring's Jackson builder. Does not affect scalar serialization.
- Logging: graphql-java `notprivacysafe` logger. Docs say turn it `OFF` to hide queries and errors from logs.

## Security

- Spring Security `@Secured("role")` on data fetcher methods. Access failures become `PERMISSION_DENIED`.
- No DGS-specific auth directives, field visibility per user, or permission classes. Community example uses a custom `@secured` schema directive.
- Introspection can be disabled. No built-in depth or complexity limits beyond graphql-java defaults.

## Directives

- `@DgsDirective(name)` on a class implementing graphql-java `SchemaDirectiveWiring` (for example wrap the data fetcher in `onField`).
- Built-in schema directives come from add-on modules: `@connection` (pagination), extended-validation directives.
- Codegen only directives: `@skipcodegen`, `@annotate`.

## Persisted queries and document caching

- `dgs.graphql.preparsed-document-provider.enabled` (default false): Caffeine backed `PreparsedDocumentProvider`. `maximum-cache-size` (2000), `cache-validity-duration` (PT1H). `DgsDefaultPreparsedDocumentProvider`.
- Any `PreparsedDocumentProvider` bean is used. Docs show a Caffeine example and warn to use variables.
- Automatic Persisted Queries (Apollo APQ): `dgs.graphql.apq.enabled` (default false). Default Caffeine cache `dgs.graphql.apq.default-cache.enabled`, `dgs.graphql.apq.default-cache.caffeine-spec` (default `maximumSize=100,expireAfterWrite=1h,recordStats`). Metered cache when Micrometer is present. Wraps any user `PreparsedDocumentProvider` (`DgsAPQPreparsedDocumentProviderWrapper`). Not in the docs at all (source and release notes only).
- No trusted-documents or allow-list mode in DGS itself.

## Observability

- Any graphql-java `Instrumentation` bean is added. Docs show a `SimplePerformantInstrumentation` timing example.
- Apollo tracing: `TracingInstrumentation` bean (graphql-java). Federated tracing via federation-jvm.
- `graphql-dgs-spring-boot-micrometer` (opt-in) meters: `gql.query` (timer), `gql.error` (counter), `gql.resolver` (per data fetcher timer), `gql.dataLoader` (batch timer), `gql.persistedQueryNotFound` (not in docs).
- Tags: `gql.operation`, `gql.operation.name`, `gql.query.complexity` (bucketed node count 5 to 1000), `gql.query.sig.hash` (SHA-256 of graphql-java `AstSignature`), `gql.errorCode`, `gql.errorDetail`, `gql.path`, `gql.field`, `gql.loaderName`, `gql.loaderBatchSize`, `outcome`. Also `gql.persistedQueryId`, `gql.persistedQueryType` (not in docs).
- Cardinality limiter on `gql.operation.name` and `gql.query.sig.hash`: `management.metrics.dgs-graphql.tags.limiter.limit` (100). `tags.limiter.kind` `FIRST`, `FREQUENCY`, `ROLLUP` (not in docs). `tags.complexity.enabled` (not in docs). Spectator limiter variant `SpectatorLimitedTagMetricResolver`.
- `QuerySignatureRepository`, `SimpleQuerySignatureRepository`, `CacheableQuerySignatureRepository` (`query-signature.enabled`, `query-signature.caching.enabled`).
- Tag customizer beans: `DgsContextualTagCustomizer`, `DgsExecutionTagCustomizer`, `DgsFieldFetchTagCustomizer`. `SimpleGqlOutcomeTagCustomizer`. `DgsGraphQLMetricsTagsProvider`, `DgsMeterRegistrySupplier`.
- `@DgsEnableDataFetcherInstrumentation(false)` removes one fetcher from `gql.resolver`.
- Toggles: `management.metrics.dgs-graphql.enabled`, `.instrumentation.enabled`, `.data-loader-instrumentation.enabled`, `.resolver.enabled`, `.query.enabled`, `.autotime.percentiles`, `.autotime.percentiles-histogram`.
- Internal timer `dgs.method.latency` (source only).
- Spring for GraphQL observation (Micrometer Observation) is turned off by default by DGS (see HTTP layer).

## Testing

- `@EnableDgsTest` test slice (no web stack) and `@EnableDgsMockMvcTest` (adds MockMvc for `@RequestHeader` and similar). Use with `@SpringBootTest(classes = {MyDataFetcher.class})`.
- `DgsQueryExecutor`: `execute(query[, variables, extensions, headers, operationName, servletRequest])`, `executeAndExtractJsonPath`, `executeAndExtractJsonPathAsObject` (with `Class` or `TypeRef`), `executeAndGetDocumentContext`. JsonPath based. Errors raise `QueryException` with all messages joined. `DgsReactiveQueryExecutor` for WebFlux.
- Spring for GraphQL `HttpGraphQlTester` with `@AutoConfigureHttpGraphQlTester`, `WebSocketGraphQlTester` for subscriptions.
- `GraphQLQueryRequest` plus codegen `*GraphQLQuery` and `*ProjectionRoot` for type safe test queries.
- Federation tests through `_entities` queries and `EntitiesGraphQLQuery`.
- Docs warn: with virtual threads on, `@Transactional` test rollback does not work because fetchers run on other threads.
- The old `graphql-dgs-mocking` module (automatic mock data) was removed in 10.0.

## Java GraphQL client (`graphql-dgs-client`)

- Blocking `GraphQLClient` / `DgsGraphQLClient`, reactive `MonoGraphQLClient` / `DgsMonoGraphQLClient`, streaming `ReactiveGraphQLClient` / `DgsReactiveGraphQLClient`.
- Implementations: `WebClientGraphQLClient` (`MonoGraphQLClient.createWithWebClient(webClient[, headersConsumer])`), `RestClientGraphQLClient`, `CustomGraphQLClient` (`GraphQLClient.createCustom(url, RequestExecutor)`), `CustomMonoGraphQLClient` (`createCustomReactive`). Dgs-prefixed variants since 12.0.
- Subscriptions: `WebSocketGraphQLClient`, `GraphqlSSESubscriptionGraphQLClient` (graphql-sse RFC), deprecated `SSESubscriptionGraphQLClient` (old protocol).
- `GraphQLResponse`: `getData`, `dataAsObject`, `extractValue(jsonPath)`, `extractValueAsObject(path, Class|TypeRef)`, `getRequestDetails` (Netflix gateway), `getParsed`/`getDocumentContext`, `errors` with typed `extensions.errorType`/`errorDetail`. Scalar-aware deserialization (10.2).
- `GraphQLRequestOptions` / `DgsGraphQLRequestOptions` (custom mapper, scalars).
- Works against any GraphQL server. Checks HTTP status and GraphQL `errors`. `GraphQLClientException`.

## DGS codegen (Netflix/dgs-codegen, brief)

- Gradle plugin `com.netflix.dgs.codegen`, task `generateJava` (generates Kotlin for Kotlin projects). Also a CLI (`CodeGenCli`: `--output-dir`, `--package-name`, `--language`, `--generate-client`, `--include-query`, `--include-mutation`, `--skip-entities`, `--type-mapping`, `--short-projection-names`, `--generate-docs` and others). Maven via community `graphqlcodegen`. Shared runtime `graphql-dgs-codegen-shared-core` (`GraphQLQueryRequest`, `BaseProjectionNode`).
- Generates: POJOs or Kotlin data classes for types, inputs, enums, interfaces, unions, with builders, all-args constructors, `equals`/`hashCode`/`toString`. `DgsConstants` class with type and field name constants (`DgsConstants.QUERY.Shows`). Client API (`<Field>GraphQLQuery`, `<Type>ProjectionRoot`, `EntitiesGraphQLQuery`, `<Type>Representation`). Interface fragments via `on<Type>()`.
- Example data fetcher stubs written to `examplesOutputDir` (default `generated-examples`) (source only, not in docs).
- `generateDocs` writes Markdown docs per Query field with example queries to `generatedDocsFolder` (`generated-docs`) (source only).
- Input options: `schemaPaths` (lazy file collections since 8.7), schemas from dependency jars via the `dgsCodegen` configuration, `META-INF/dgs.codegen.typemappings` exported by schema jars.
- `typeMapping` (GraphQL type to FQN class). Built-in mappings for scalars, `java.time`, `PageInfo` to `graphql.relay`.
- Data type flags: `generateDataTypes`, `generateInterfaces`, `generateInterfaceSetters`, `generateInterfaceMethodsForInterfaceFields`, `generateBoxedTypes`, `generateIsGetterForPrimitiveBooleanFields`, `javaGenerateAllConstructor`, `implementSerializable`, `trackInputFieldSet` (wraps input fields in `Optional`, adds `has<Field>()` for sparse updates), `generateJSpecifyAnnotations` (`@NullMarked`, `@Nullable`, `requireNonNull` in builders).
- Client flags: `generateClient`, `generateClientv2`, `includeQueries`, `includeMutations`, `includeSubscriptions`, `skipEntityQueries`, `shortProjectionNames`. Variable references `<arg>Reference(...)` and `<field>WithVariableReferences(...)`.
- Annotations: `addGeneratedAnnotation` (default true since 8.5), `generatedAnnotationType`, `disableDatesInGeneratedAnnotation`, `addDeprecatedAnnotation`, `generateCustomAnnotations` with SDL `@annotate(name, type, inputs, target)` and `includeImports`, `includeEnumImports`, `includeClassImports`.
- SDL directive `@skipcodegen` on types or fields.
- Kotlin: `generateKotlinNullableClasses` and `generateKotlinClosureProjections` (experimental "kotlin2" generator, fields as lazy suppliers that throw when not requested, DSL query builder `DgsClient`), `kotlinAllFieldsOptional`.
- Other: `snakeCaseConstantNames`, `subPackageNameClient`/`Types`/`Datafetchers`, `jacksonVersions` (`JACKSON_2`, `JACKSON_3`, since 8.6), `fileWriteParallelism` (source only).
- Codegen ignores `@connection`. Relay types need manual `typeMapping`.
- Open PRs (2026-08 to 2026-09): interface fragments, list-of-interface getters, `@annotate` `type_use` target, Gradle build cache fixes, kotlin2 `equals`/`hashCode`/`toString`.

## Not supported or not in scope

- Code-first schema (from Java classes or annotations). DGS is schema-first only.
- ORM or database integration: no auto filtering, ordering, projections, or query optimization. N+1 is solved only with data loaders or manual look-ahead.
- Auto CRUD mutation generation.
- Relay `Node`/global ID support.
- Auth beyond Spring Security `@Secured`. No per-field visibility API in DGS (graphql-java `GraphqlFieldVisibility` is wired internally, but I found no DGS hook for it).
- Query cost or complexity limits in DGS. Only a complexity metric tag.
- Built-in file upload transport (third party library needed).
- `@defer`/`@stream`: not mentioned in DGS docs or code (I think anything here would come from Spring for GraphQL).
- Schema change checks, schema registry, or breaking change detection.
- Mock data generation (removed in 10.0).
- Response caching or `@cacheControl`.

## Upcoming and unreleased work

- WIP PR (2026-09-24): Spring Boot 4.2, graphql-java 26, spring-graphql 2.1.
- POC PR (2026-08-27): migrate main sources from Kotlin to Java 17.
- Open PRs: bucket `gql.loaderBatchSize` tag, richer error info on `gql.resolver`, missing `DgsContext` in subscription callbacks, Spring request context propagation to virtual threads.
- Spring for GraphQL integration docs still promise SSE subscriptions "on the roadmap". This is now done (see disagreements).

## Docs and code disagree

- Docs say DGS requires Spring Boot 3 and JDK 17. Code: 11.x and 12.x require Spring Boot 4. Only 10.x is on Spring Boot 3. A startup version check enforces this.
- Docs (`configuration.md`) list `dgs.graphql.schema-json.enabled` (default true) and `dgs.graphql.schema-json.path`. Code has no such property any more. Spring's `spring.graphql.schema.printer.enabled` is the replacement.
- Docs (`spring-graphql-integration.md`) say response headers via `DGS_RESPONSE_HEADERS_KEY` are "no longer supported". Code still applies the `dgs-response-headers` extension and `DgsExecutionResult.headers` through a default-on interceptor.
- Docs say SSE subscriptions are a known gap. `subscriptions.md` and code say SSE works through Spring for GraphQL.
- Docs (`file-uploads.md`) say the "regular DGS starter" needs no extra dependency. That starter was removed in 10.0.
- Several pages (federation, scalars, relay pagination, subscriptions) use `@SpringBootTest(classes = {DgsAutoConfiguration.class, ...})`. `DgsAutoConfiguration` was deleted in 10.0. Code wants `@EnableDgsTest`.
- Docs say `@InputArgument(collectionType = ...)` is required for lists and `Optional` of input types. Code marks `collectionType` deprecated and infers the type from the parameter.
- Docs (`platform-bom.md`) use removed artifacts `graphql-dgs-spring-boot-starter` and `graphql-dgs-subscriptions-websockets-autoconfigure`.
- `java-client.md` names `SSESubscriptionGraphQLClient` with `/subscriptions` as the SSE client. Code deprecates it. The current client is `GraphqlSSESubscriptionGraphQLClient` on `/graphql`.
- Docs say data loader caching is off by default in "DGS 1". Code default is `caching = true`.
- Codegen docs describe `generateDocs` as "Generate JavaDoc from schema descriptions". I think code always adds JavaDoc from descriptions, and `generateDocs` gates Markdown doc files instead.
- APQ, strict mode, federation toggle, schema wiring validation, error classification, `@Source`, `@DgsDefaultTypeResolver`, `DgsDataLoaderReloadController` and Kotlin coroutine and `Flow` support are in code and release notes but not in the docs.

## Sources

- Docs site: https://netflix.github.io/dgs/ (source repo https://github.com/Netflix/dgs, cloned at `fc3d3e0`). All pages under `docs/` read, including `index.md`, `spring-graphql-integration.md`, `announcements.md`, `configuration.md`, `datafetching.md`, `mutations.md`, `data-loaders.md`, `error-handling.md`, `federation.md`, `scalars.md`, `query-execution-testing.md`, `generating-code-from-schema.md`, and all of `docs/advanced/`.
- Framework repo: https://github.com/Netflix/dgs-framework (shallow clone, `0f3f258`).
- Codegen repo: https://github.com/Netflix/dgs-codegen (shallow clone, `bcbc9a7`).
- Release notes: https://github.com/Netflix/dgs-framework/releases (10.0.0 to 12.1.0), https://github.com/Netflix/dgs-codegen/releases (8.5.0 to 8.7.0).
- Open PRs: https://github.com/Netflix/dgs-framework/pulls and https://github.com/Netflix/dgs-codegen/pulls.
- https://netflix.github.io/dgs/llms.txt (404).
