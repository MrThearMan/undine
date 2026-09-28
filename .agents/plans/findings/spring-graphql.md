# Spring for GraphQL findings

Versions checked: 2.0.5 (latest GA, GitHub release 2026-08-20) and 2.1.0-M1 (milestone, 2026-09-24). Repo `main` at `397b7c0` (last commit 2026-09-25, version `2.1.0-SNAPSHOT`). Docs source is in the repo (`spring-graphql-docs/`, Antora, about 4300 lines of AsciiDoc). All pages read.
Spring for GraphQL is the official Spring integration for graphql-java. Joint project of the graphql-java team and Spring. Successor of `graphql-java-spring`. Apache 2.0. Engine details are in `graphql-java.md`. Netflix DGS runs on top of this project since DGS 8.5 (see `netflix-dgs.md`).
Schema style: schema-first. SDL files plus annotated `@Controller` methods. Also accepts a prebuilt `GraphQLSchema` (`GraphQlSource.builder(GraphQLSchema)`, not in docs), so graphql-java programmatic schemas work. No code-first schema generation from Java classes.

## Maintenance status

- Active. 1596 stars. Not archived. 32 open issues plus PRs. Maintained by the Spring team (Brian Clozel, Rossen Stoyanchev).
- Release lines: 2.1.x (Spring Framework 7.1, graphql-java 26, Spring Boot 4.2, GA planned Nov 2026), 2.0.x (Framework 7.0, graphql-java 25, Boot 4.0 to 4.1), 1.4.x (graphql-java 24, Boot 3.5, still gets fixes: 1.4.6 on 2026-06-10).
- Release cadence: one generation every six months (May and November), aligned with Spring Boot.
- 2.0.4 and 1.4.6 (2026-06-10) fixed 3 high CVEs: CVE-2026-41699 (unsafe deserialization), CVE-2026-41700 (cross-site WebSocket hijacking), CVE-2026-41856 (annotation detection).
- No `CHANGELOG.md`. Changes are in GitHub release notes and in wiki pages "Spring for GraphQL 1.3/1.4/2.0/2.1" (https://github.com/spring-projects/spring-graphql/wiki).
- https://docs.spring.io/spring-graphql/reference/llms.txt and https://docs.spring.io/llms.txt return 404. `Accept: text/markdown` returns HTML. Published docs default to 2.0.5. Versioned docs exist (`/reference/1.4/`, `/reference/2.1-SNAPSHOT/`).
- Samples are in a separate repo `spring-projects/spring-graphql-examples`. Older samples are on the `1.0.x` branch.

## Big changes between versions

- 1.0 (2022-05): first release. Boot 2.7.
- 1.2: `@Argument Map` returns the raw argument value. `@Arguments` added for the full map. Pagination (`ConnectionTypeDefinitionConfigurer`, `ConnectionAdapter`, `CursorStrategy`, `ScrollSubrange`, `Sort`). `@GraphQlExceptionHandler`. Schema mapping inspection.
- 1.3 (2024-05): virtual threads via `Executor` on `AnnotatedControllerConfigurer`. `HttpSyncGraphQlClient` (RestClient). `DgsGraphQlClient`. SSE transport. Apollo Federation (`FederationSchemaFactory`, `@EntityMapping`). Interface field mapping. Schema inspection of unions, interfaces and arguments. `AuthenticationWebSocketInterceptor`. WebSocket keep-alive. Separate JSON codec for the GraphQL endpoint. Kotlin `Flow` return values.
- 1.4 (2025-05): full GraphQL over HTTP alignment (4xx on parse and validation errors for `application/graphql-response+json`). SSE keep-alive. `TimeoutWebGraphQlInterceptor`. Client disconnect propagates cancellation to data fetchers. `DataLoader` arguments on `@EntityMapping`. Inspection reports federated entities without `@EntityMapping`. `graphql.dataloader` observation.
- 2.0 (2025-11-18): Spring Framework 7, graphql-java 25, Jackson 3 default with Jackson 2 fallback. JSpecify nullness on the whole API. Schema inspection checks nullness (schema `!` vs JSpecify or Kotlin nullness). `GraphQlArgumentBinder.Options.nameResolver`. `ArgumentValue` on the client via `GraphQlJacksonModule`. Multiple queries in one `DgsGraphQlClient` request. Kotlin reified extensions for client and tester.
- 2.0.x patches: `@EntityMapping` on interface types (2.0.0-RC2) and on types with many interfaces (2.0.2). Enum and number values in `JsonKeysetCursorStrategy` (2.0.2). Kotlin extensions for `ClientResponseField` (2.0.1). `GraphQlTester.EntityList.singleElement()` (2.0.3). SSE keep-alive switched to empty comments (2.0.3).
- 2.1.0-M1 (2026-09-24): HTTP GET support. HTTP `QUERY` method support (RFC 10008). Operation type restrictions per transport. `maxSubscriptionsPerSession` on `GraphQlWebSocketHandler`. Unsupported HTTP methods rejected at configuration time. graphql-java 26.1.

## Modules

- `spring-graphql` (server, client, data integration, observation). `spring-graphql-test` (`GraphQlTester` family). `platform` (BOM).
- Spring Boot starter `spring-boot-starter-graphql` (in Spring Boot, not in this repo). Boot 4 module `spring-boot-graphql`. Testing slice `@GraphQlTest` in Boot.
- Spring Initializr entry "Spring for GraphQL". Initializr can add the DGS codegen plugin.

## Schema definition

- SDL files loaded through `GraphQlSource.schemaResourceBuilder().schemaResources(Resource...)`. Any Spring `Resource` (classpath, file, remote, memory).
- Boot default: `classpath:graphql/**/`, extensions `.graphqls` and `.gqls`. `classpath*:` finds files across modules.
- `GraphQlSource.builder(GraphQLSchema)`: use an external, prebuilt schema (`ExternalSchemaGraphQlSourceBuilder`). Not in docs.
- `configureTypeDefinitions(TypeDefinitionConfigurer)`: change the `TypeDefinitionRegistry` before schema creation (for example `ConnectionTypeDefinitionConfigurer`).
- `configureRuntimeWiring(RuntimeWiringConfigurer)`: scalars, directive wiring, direct `DataFetcher` registration. Alternative `configure(RuntimeWiring.Builder, List<WiringFactory>)` adds `WiringFactory` instances. Boot picks up all `RuntimeWiringConfigurer` beans.
- `schemaFactory((registry, wiring) -> GraphQLSchema)`: replace graphql-java `SchemaGenerator`. Used for federation.
- `typeVisitors(...)`: traverse the schema after creation. Can change the `GraphQLCodeRegistry` but not the schema.
- `typeVisitorsToTransformSchema(...)`: transform the schema with `GraphQLTypeVisitor`. More expensive.
- `defaultTypeResolver(TypeResolver)`. Default is `ClassNameTypeResolver`: matches the simple class name, then walks superclasses and interfaces. `setClassNameExtractor` and explicit `Class` to type name mappings.
- `graphQlSourceFactory(Factory)`: custom `GraphQlSource` creation (not in docs).
- `configureGraphQl(Consumer<GraphQL.Builder>)`: raw engine access (execution strategy, `PreparsedDocumentProvider`, `ExecutionIdProvider`).
- `instrumentation(List<Instrumentation>)`, `exceptionResolvers(...)`, `subscriptionExceptionResolvers(...)`.
- Boot `GraphQlSourceBuilderCustomizer` bean: customize the builder.
- No code-first. Jackson annotations on Java types do not apply to GraphQL output. Custom scalars are the docs' answer.

## Schema mapping inspection

- `inspectSchemaMappings(Consumer<SchemaReport>)` checks at startup that the schema and the code match. Boot enables it by default and logs at INFO (`spring.graphql.schema.inspection.enabled`).
- Report sections: unmapped fields (no `DataFetcher` and no Java property), unmapped registrations (fetcher for a field that does not exist), unmapped arguments (`@Argument` not in schema), field nullness errors, argument nullness errors, skipped types.
- Nullness checks need Kotlin or JSpecify or Spring null-safety annotations. Schema `Book!` vs `@Nullable` getter is an error. The opposite is allowed.
- Unions and interfaces: finds Java classes by simple name in the same package as the controller return type, from other schema uses, or from `ClassNameTypeResolver` mappings. Customizable with `initializer.classMapping("Author", Author.class)` and a class name function.
- `SelfDescribingDataFetcher`: a `DataFetcher` can describe its return type and arguments for the inspection. Controller, Querydsl and QBE fetchers implement it.
- Reports federated entity types with no `@EntityMapping` (1.4).
- Open issue #970: inspection does not cover Querydsl and QBE auto-registrations yet.

## Annotated controllers

- `@Controller` beans detected by `AnnotatedControllerConfigurer` (a `RuntimeWiringConfigurer`). Registered as `DataFetcher`s.
- `@SchemaMapping(typeName, field)`. Field defaults to the method name. Type defaults to the simple class name of the source parameter. Class-level `@SchemaMapping(typeName=...)` sets a default type.
- `@QueryMapping`, `@MutationMapping`, `@SubscriptionMapping`: shortcuts with the type preset.
- Interface schema mappings: a method mapped to an interface field registers on every implementing type. A method for one subtype overrides that subtype.
- `@BatchMapping`: method takes `List<K>` of parents and returns `Mono<Map<K,V>>`, `Flux<V>` (same order), `Map<K,V>`, `Collection<V>`, `Callable<...>`, Kotlin coroutine or `Flow`. Registers a batch loader and a field fetcher in one step. Works on interface fields too. Parent type must implement `equals` and `hashCode`.
- `@BatchMapping(maxBatchSize = n)`: limit batch size. Not in docs.
- `@GraphQlExceptionHandler` in a controller or in `@ControllerAdvice`. Returns `GraphQLError`, `Collection<GraphQLError>`, `void`, `Object` or `Mono<T>`. Inject graphql-java `GraphqlErrorBuilder` prepared from the environment (docs spell it `GraphQlErrorBuilder`). Works for `@EntityMapping` too. For non-controller fetchers, get the resolver with `AnnotatedControllerConfigurer.getExceptionResolver()` and register it.
- Controller method arguments: `@Argument` (named argument bound to a typed object), `@Argument Map` (raw value), `ArgumentValue<T>` (omitted vs `null`), `@Arguments` (all arguments bound to one object), `@Arguments Map`, `@ProjectedPayload` interface, source/parent object, `Subrange` and `ScrollSubrange`, `Sort`, `DataLoader<K,V>`, `@ContextValue` (with `required`), `@LocalContextValue`, `GraphQLContext`, `Principal`, `@AuthenticationPrincipal`, `DataFetchingFieldSelectionSet`, `Locale`, `DataFetchingEnvironment`. Kotlin `Continuation` is handled.
- Return values: `T`, `Mono`/`Flux`, Kotlin `suspend` and `Flow`, `Callable<T>` (needs an `Executor`), `CompletableFuture`, `DataFetcherResult<P>` (extensions, local context, partial errors).
- Blocking methods on virtual threads: with an `Executor` on `AnnotatedControllerConfigurer`, non-async methods run on it. Boot sets this when `spring.threads.virtual.enabled=true`. `setBlockingMethodPredicate` decides which methods count as blocking.
- Local context: return `DataFetcherResult` with `localContext` to pass data to child fields only.
- Namespacing pattern (`music { album }`): documented as a recipe. Wrapper fields return an empty map.
- `AnnotatedControllerConfigurer` options (some not in docs): `setExecutor`, `setBlockingMethodPredicate`, `setControllerPredicate` (which beans count as controllers), `addCustomArgumentResolver(HandlerMethodArgumentResolver)` (custom parameter types), `addFormatterRegistrar` (type conversion for arguments), `setBinderOptions` / `configureBinder`, `setFallBackOnDirectFieldAccess`.

## Arguments, input binding, validation

- `GraphQlArgumentBinder` binds argument maps to objects. Uses the primary constructor first (recursive for nested types, records work). Falls back to default constructor plus setters. Optional direct field access.
- `GraphQlArgumentBinder.Options`: `nameResolver` (map schema names like `project_slug` to Java names, 2.0), `fallBackOnDirectFieldAccess`, `conversionService`.
- Binding errors raise `BindException` with one field error per argument path.
- `@Argument` has no `required` flag and no default value. The schema handles both.
- `ArgumentValue<T>`: tri-state input (value, explicit `null`, omitted). Works as a top-level parameter and as a field at any depth in input objects. `ArgumentValueValueExtractor` lets Bean Validation see inside it (registered through `ServiceLoader`, not in docs).
- `@ProjectedPayload` interfaces: argument access through Spring Data interface projections. Supports SpEL with `@Value("#{target.a + ' ' + target.b}")`.
- Bean Validation: when a `Validator` bean exists, `@Valid` and `@Validated` (groups) on controller parameters are checked before the call. Failure raises `ConstraintViolationException`. Hibernate Validator does not work with Kotlin coroutine methods.
- No built-in input validation directives. Docs point to `graphql-java-extended-validation`.

## Interfaces and unions

- `ClassNameTypeResolver` is the default type resolver for all interfaces and unions.
- Interface field mappings expand to implementing types (see controllers).

## Spring Data integration

- `QuerydslDataFetcher.builder(QuerydslPredicateExecutor).single() / many() / scrollable()`. Builds a Querydsl `Predicate` from GraphQL arguments. Default binding is "equals" per property. JPA, MongoDB, Neo4j, LDAP. Reactive variant from `ReactiveQuerydslPredicateExecutor` returns `Mono`/`Flux`.
- `QueryByExampleDataFetcher.builder(QueryByExampleExecutor)` with the same methods. Builds an example object from arguments. JPA, MongoDB, Neo4j, Redis. Reactive variant also for R2DBC.
- A single input-type argument is unwrapped one level for both fetchers.
- Builder options: `projectAs(Class)` (interface or DTO projection), `customizer(QuerydslBinderCustomizer)` (Querydsl only), `sortBy(Sort)`, `cursorStrategy(...)`, `defaultScrollSubrange(count, position)`, `maximumScrollCount(int)`. The last four are not in docs.
- `@GraphQlRepository(typeName = ...)`: auto-registers the repository for any `Query` field with no fetcher whose return type matches the domain type name. Works for single, list and `XConnection` fields. Auto-registration pagination is offset-based, 20 items per page.
- A repository that implements `QuerydslBinderCustomizer`, `QuerydslBuilderCustomizer`, `QueryByExampleBuilderCustomizer` (or reactive variants) is customized during auto-registration.
- Selection set to property paths: the fetchers turn the GraphQL selection into Spring Data property path hints (`PropertySelection`) so the store can limit loaded properties. Docs mention this only in one sentence.
- Docs position: the library is not a data gateway. It does not translate GraphQL to SQL. Spring Data projections are presented as the tool to shape data.
- Only top-level `Query` fields are auto-registered. Nested relation fields need controller methods or batch loading.
- No filter or order input grammar. Filtering is equality on arguments (Querydsl binder customization can change operators per property).
- Transactions: docs recommend `@Transactional` on mutation controller methods. Request-wide transactions need a custom `Instrumentation` or a serial `ExecutionStrategy` (`AsyncSerialExecutionStrategy`). No built-in transaction support (open issue #448).
- Spring Data projections as `@SchemaMapping` return values: not supported (open issue #657).

## Pagination

- `ConnectionTypeDefinitionConfigurer`: generates `XConnection`, `XEdge` and `PageInfo` types for any field returning `XConnection` that is not declared. Boot registers it by default.
- `first`/`after` win over `last`/`before` when both are given.
- `ConnectionAdapter` turns a container into a graphql-java `Connection`. Applied by `ConnectionFieldTypeVisitor`. Built-in `WindowConnectionAdapter` and `SliceConnectionAdapter` for Spring Data `Window` and `Slice`. `CompositeConnectionAdapter`, `ConnectionAdapterSupport` for custom adapters.
- `CursorStrategy` encodes and decodes cursors. `CursorEncoder` makes them opaque: `Base64CursorEncoder`, `NoOpCursorEncoder`. `EncodingCursorStrategy` combines both.
- `ScrollPositionCursorStrategy` for Spring Data `ScrollPosition` (offset or keyset). `JsonKeysetCursorStrategy` writes keyset maps as JSON with Jackson default typing for `Date`, `Calendar`, `UUID`, enums, `Number`, `java.time` types.
- `Subrange<P>` and `ScrollSubrange` controller arguments carry decoded pagination input.
- `SortStrategy` and `AbstractSortStrategy` build Spring Data `Sort` from arguments. A bean is needed to enable `Sort` parameters. No standard sort input shape.
- Boot registers `CursorStrategy<ScrollPosition>` with Base64 and the Window/Slice adapters when Spring Data is present.
- No Relay `Node` interface or global ID support.

## Batching (data loaders)

- `BatchLoaderRegistry`: one central registry. `forTypePair(K, V).registerBatchLoader(...)` (returns `Flux<V>`) or `.registerMappedBatchLoader(...)` (returns `Mono<Map<K,V>>`). Also `forName(...)`. `withName`, `withOptions(DataLoaderOptions)`.
- Default loader name is the value class name. `DataLoader<K,V>` parameters resolve by generic type, then by parameter name.
- `DefaultBatchLoaderRegistry(Supplier<DataLoaderOptions>)` sets global default options.
- Batch loaders get the same `GraphQLContext` and context propagation as fetchers. `BatchLoaderEnvironment.keyContexts` holds the local context of each `load()` call.
- `DataLoaderRegistrar` and `DefaultExecutionGraphQlService.addDataLoaderRegistrar`: plug in other loader sources per request.
- Docs give recipes for filtered loading (load all then filter, or composite keys) and a unit test pattern (`registerDataLoaders` then `dispatchAndJoin`).

## Context and threading

- Context propagation from Spring MVC `ThreadLocal` and WebFlux Reactor `Context` to fetchers, using Micrometer `context-propagation`. Register `ThreadLocalAccessor` via `ContextRegistry` or `ServiceLoader`. `SecurityContextThreadLocalAccessor` ships built in.
- `GraphQlContextAccessor` bridges `GraphQLContext` and Reactor context (source only).
- Reactive fetchers: `Mono` and `Flux` adapted to `CompletableFuture`. `Flux` collected into a list except for subscriptions.
- Spring MVC uses async request handling unless the result is already complete.
- Client disconnect or timeout cancels reactive fetchers in flight (1.4, graphql-java 25 cancellation).
- Subscription event order: opt in with `SubscriptionExecutionStrategy.KEEP_SUBSCRIPTION_EVENTS_ORDERED` in the context.

## Errors

- `DataFetcherExceptionResolver` chain. `DataFetcherExceptionResolverAdapter` with `resolveToSingleError` / `resolveToMultipleErrors`. Boot detects beans.
- `ErrorType` classification: `BAD_REQUEST`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `INTERNAL_ERROR`.
- Unresolved exceptions become `INTERNAL_ERROR` with an opaque message that includes the `executionId`. Logged at ERROR with the id. Resolved ones are logged at DEBUG.
- graphql-java `GraphqlErrorBuilder.newError(env)` builds errors. `GraphqlErrorBuilder` is also an injectable argument in `@GraphQlExceptionHandler` methods.
- Request-level errors (parse, validation) cannot use resolvers. Change them in a `WebGraphQlInterceptor` by transforming the `ExecutionResult`.
- `SubscriptionExceptionResolver` and `SubscriptionExceptionResolverAdapter` for errors from a subscription `Publisher`.
- `SecurityDataFetcherExceptionResolver` and `ReactiveSecurityDataFetcherExceptionResolver`: map Spring Security `AuthenticationException` to `UNAUTHORIZED` and `AccessDeniedException` to `UNAUTHORIZED` or `FORBIDDEN` depending on anonymous state.
- `ResponseError` and `ResponseField` give typed access to errors and fields on the client and tester side.

## Server transports

- HTTP: `GraphQlHttpHandler` (Spring MVC and WebFlux variants). POST with JSON by default. Default response type `application/graphql-response+json` with GraphQL over HTTP status codes (4xx on parse and validation errors). `application/json` keeps legacy 200 behavior.
- `isHttpOkOnValidationErrors()` exists on `GraphQlHttpHandler`. The field is always `false` and has no setter. I think only a subclass override can turn it on.
- Custom JSON codec for GraphQL payloads only: `GraphQlHttpHandler.builder(...).messageConverter(...)` (MVC) or codec configurer (WebFlux). Separate from the app's HTTP JSON config.
- HTTP GET (2.1): `GraphQlHttpHandler.builder(handler).httpMethods(GET, POST)` plus `GraphQlRequestPredicates.graphQlHttp(path, methods)`. `variables` and `extensions` are JSON strings in the query string. Mutations over GET get 405 with an `Allow` header.
- HTTP `QUERY` method (2.1, RFC 10008): body like POST. Mutations get 422.
- Operation type restrictions (2.1): the transport sets allowed operations on `ExecutionGraphQlRequest.allowedOperations(...)`. `OperationTypeInstrumentation` enforces it and raises `OperationNotAllowedException` (graphql-java `ErrorType.OperationNotSupported`). POST rejects subscriptions.
- SSE: `GraphQlSseHandler`, GraphQL over SSE "distinct connections mode" only. Subscriptions only. Builder options `timeout`, `keepAliveDuration` (empty SSE comments), `httpMethods` (GET for `EventSource`).
- WebSocket: `GraphQlWebSocketHandler` with the `graphql-ws` (`graphql-transport-ws`) protocol only. Legacy `subscriptions-transport-ws` not supported. Queries and mutations also allowed. Builder options: connection init timeout, `keepAliveDuration` (ping), `corsConfiguration` (allowed origins, added after CVE-2026-41700), `maxSubscriptionsPerSession` (2.1, closes the session when exceeded).
- RSocket: `GraphQlRSocketHandler`. Request-response for queries and mutations, request-stream for subscriptions. Mapped from an `@Controller` `@MessageMapping` route.
- File upload: not supported. Docs point to third-party `multipart-spring-graphql`.
- Batched requests (array of operations in one HTTP request): not supported. I did not find any code for it.
- Request timeout: `TimeoutWebGraphQlInterceptor` (1.4). Cancels reactive fetchers and returns a transport-specific status.

## Interception

- `WebGraphQlInterceptor` chain for HTTP, SSE and WebSocket. Can read HTTP details, change `ExecutionInput` (`request.configureExecutionInput(...)`), add response headers (`WebGraphQlResponse.getResponseHeaders()`), transform the `ExecutionResult` (`response.transform(...)`).
- `HttpRequestHeaderInterceptor.builder().mapHeader(...)`, `mapHeaderToKey`, `mapMultiValueHeader`, `mapMultiValueHeaderToKey`: copy HTTP headers into `GraphQLContext`.
- `WebSocketGraphQlInterceptor`: adds `handleConnectionInitialization` (return the `connection_ack` payload), `handleCancelledSubscription`, `handleConnectionClosed`. At most one per chain.
- `AuthenticationWebSocketInterceptor` (MVC and WebFlux): authenticates from the `connection_init` payload and keeps the `SecurityContext` for the session. `AuthenticationExtractor` contract. `BearerTokenAuthenticationExtractor` reads `Authorization` from the payload (not in docs by name).
- `RSocketGraphQlInterceptor` for RSocket.
- `WebGraphQlHandler.builder(service).interceptors(...)` builds the chain. Boot detects interceptor beans.

## Security

- Endpoint-level: Spring Security URL rules on the HTTP path.
- Field-level: method security (`@PreAuthorize`, `@Secured`) on services or controllers. Works because of context propagation.
- `Principal` and `@AuthenticationPrincipal` controller arguments.
- WebSocket auth through `connection_init` (see Interception).
- Boot: `GraphQlWebMvcSecurityAutoConfiguration` and `GraphQlWebFluxSecurityAutoConfiguration` register the security exception resolvers.
- No per-field visibility API, no schema directives for auth, no query depth or cost limits in this library. Those come from graphql-java instrumentation (`MaxQueryDepthInstrumentation`, `MaxQueryComplexityInstrumentation`) registered as beans.
- Introspection off: Boot `spring.graphql.schema.introspection.enabled=false` calls `Introspection.enabledJvmWide(false)`. This is JVM-wide, not per schema.

## Federation

- Apollo Federation subgraph through `federation-jvm`. `FederationSchemaFactory` bean plugged in with `builder.schemaFactory(factory::createGraphQLSchema)`. Optional `setTypeResolver`.
- `@EntityMapping(name)`: loads entities for the `_entities` query. Arguments: `@Argument` (value from the representation), `Map<String,Object>` (full representation), `List<Map<...>>` (batch), `DataLoader<I,E>`, plus the usual context, principal and environment arguments.
- Batch form: method takes `@Argument List<Integer> idList` and returns `List` or `Flux`.
- Returns `Mono`, `CompletableFuture`, `Callable` or the entity.
- `@EntityMapping` works on interface types (2.0). `@GraphQlExceptionHandler` applies.
- `RepresentationException`, `RepresentationNotResolvedException` for bad or unresolved representations (source only).
- Docs do not cover `@link` / Federation v2 directives specifically. That is up to `federation-jvm`.

## Directives

- Schema directives through graphql-java `SchemaDirectiveWiring`, registered with a `RuntimeWiringConfigurer`. No built-in directives.

## Persisted queries and document caching

- No built-in persisted queries. Docs show graphql-java `ApolloPersistedQuerySupport` with `InMemoryPersistedQueryCache` through `configureGraphQl(b -> b.preparsedDocumentProvider(...))`.
- Parsed document caching also through `PreparsedDocumentProvider`. Not configured by default.

## Observability

- Micrometer Observation via `GraphQlObservationInstrumentation`. Boot auto-configures it (`GraphQlObservationAutoConfiguration`).
- `graphql.request` observation: low cardinality `graphql.operation.type`, `graphql.outcome` (`SUCCESS`, `REQUEST_ERROR`, `INTERNAL_ERROR`). High cardinality `graphql.execution.id`, `graphql.operation.name`. GraphQL errors recorded as observation events.
- `graphql.datafetcher` observation for non-trivial fetchers only: `graphql.error.type`, `graphql.field.name`, `graphql.outcome`, high cardinality `graphql.field.path`.
- `graphql.dataloader` observation (1.4): `graphql.loader.name`, `graphql.error.type`, `graphql.outcome`, high cardinality `graphql.loader.size`.
- Custom conventions: `ExecutionRequestObservationConvention`, `DataFetcherObservationConvention`, `DataLoaderObservationConvention`. Contribute as beans in Boot.
- Parent observation is read from the `"micrometer.observation"` context key. Trace propagation is left to the transport.
- No metrics for subscriptions or WebSocket sessions (open issue #944).
- No Apollo tracing or usage reporting.

## Developer tools

- GraphiQL: stock `index.html` from the esm.sh CDN (GraphiQL 5.2, explorer plugin, subscriptions over the WebSocket path, sends `X-XSRF-TOKEN` from the `XSRF-TOKEN` cookie). `GraphiQlHandler(graphQlPath, wsPath, resource)`. Boot `spring.graphql.graphiql.enabled`, `.path` (default `/graphiql`). Docs warn it is for development only.
- Schema printer: `SchemaHandler` serves SDL. Boot `spring.graphql.schema.printer.enabled` at `{http.path}/schema`.
- GraalVM native images: `SchemaMappingBeanFactoryInitializationAotProcessor` registers reflection hints for controller types at build time. Manual fetchers need `@RegisterReflectionForBinding`. Client reachability metadata ships in the jar.
- Code generation: none in this project. Docs point to DGS codegen.
- IDE: docs mention the IntelliJ "JS GraphQL" plugin for document files.
- Incremental delivery (`@defer`/`@stream`): no support in Spring for GraphQL. The 1.3 wiki points to an external experiment (`felipe-gdr/spring-graphql-defer`).

## Java GraphQL client

- `GraphQlClient` with one API for all transports: `HttpSyncGraphQlClient` (RestClient, blocking), `HttpGraphQlClient` (WebClient, also SSE subscriptions), `WebSocketGraphQlClient` (multiplexed shared connection, `start()`/`stop()`, `keepAlive`), `RSocketGraphQlClient`.
- Requests: `document(...)` or `documentName(...)` (files in `graphql-documents/` with `.graphql`/`.gql`), `variable`, `operationName`, `extension`.
- `retrieve(path).toEntity(...)` / `toEntityList(...)`, sync variant `retrieveSync`. Dot paths with indexes (`project.releases[0].version`). `FieldAccessException` if the field is missing or `null` with an error.
- `execute()` / `executeSync()` for the full `ClientGraphQlResponse`.
- Subscriptions: `retrieveSubscription`, `executeSubscription` return `Flux`. `SubscriptionErrorException`, `WebSocketDisconnectedException`.
- Interceptors: `GraphQlClientInterceptor`, `SyncGraphQlClientInterceptor`, `WebSocketGraphQlClientInterceptor` (`connectionInitPayload`, `handleConnectionAck`).
- `ArgumentValue<T>` in client input types through `GraphQlJacksonModule` (Jackson 3) or `GraphQlJackson2Module`.
- `DgsGraphQlClient`: wraps any `GraphQlClient` to send DGS codegen request objects. Many queries per request (2.0).
- Kotlin extensions with reified types (`toEntity<Project>()`).

## Testing (`spring-graphql-test`)

- `GraphQlTester` with one API for all transports. Client side: `HttpGraphQlTester` (WebTestClient, MockMvc or live server), `WebSocketGraphQlTester` (supports interceptors), `RSocketGraphQlTester`. Server side: `ExecutionGraphQlServiceTester` (directly on the service, can customize `ExecutionInput`), `WebGraphQlTester` (runs the interceptor chain with mock HTTP details).
- Builder: `errorFilter`, `documentSource` (default `graphql-test/` on the classpath), `responseTimeout`.
- Request: `document`, `documentName`, `fragment`, `fragmentName` (append fragments from separate files), `variable`, `variables`, `operationName`, `extension`.
- Response: `path(...)` with JsonPath, nested `path(path, consumer)`, `entity(...)`, `entityList(...)` (`contains`, `containsExactly`, `hasSize`, `singleElement`), `hasValue`, `valueIsNull`, `pathDoesNotExist`, `matchesJson`, `matchesJsonStrictly`, `returnResponse()`.
- Errors: `errors().filter(...)`, `expect(...)`, `verify()`, `satisfy(...)`. `executeAndVerify()` checks no errors.
- Subscriptions: `executeSubscription().toFlux()` with Reactor `StepVerifier`.
- Boot: `@GraphQlTest` slice (controllers, `RuntimeWiringConfigurer`, exception resolvers, interceptors) and `@AutoConfigureHttpGraphQlTester`.
- Kotlin extensions for the tester.

## Spring Boot auto-configuration and properties (brief)

- Auto-config classes: `GraphQlAutoConfiguration` (builds `GraphQlSource`, `BatchLoaderRegistry`, `ExecutionGraphQlService`, `AnnotatedControllerConfigurer`, cursor strategy and connection adapters), `GraphQlWebMvcAutoConfiguration`, `GraphQlWebFluxAutoConfiguration`, `GraphQlRSocketAutoConfiguration`, `RSocketGraphQlClientAutoConfiguration`, `GraphQlQuerydslAutoConfiguration`, `GraphQlQueryByExampleAutoConfiguration` (plus reactive variants), `GraphQlObservationAutoConfiguration`, `GraphQlWebMvcSecurityAutoConfiguration`, `GraphQlWebFluxSecurityAutoConfiguration`. `@ConditionalOnGraphQlSchema` backs off when no schema files exist.
- Boot detects beans of type `RuntimeWiringConfigurer`, `Instrumentation`, `DataFetcherExceptionResolver`, `SubscriptionExceptionResolver`, `WebGraphQlInterceptor`, `TypeDefinitionConfigurer`, `GraphQlSourceBuilderCustomizer`, and `@GraphQlRepository` repositories.
- `AnnotatedControllerConfigurer` gets the application task executor (virtual threads when enabled).
- Properties `spring.graphql.*`: `http.path` (default `/graphql`), `http.methods` (default POST, new for 2.1), `http.sse.keep-alive`, `http.sse.timeout`, `http.sse.methods`, `schema.locations` (default `classpath:graphql/**/`), `schema.file-extensions` (`.graphqls`, `.gqls`), `schema.additional-files`, `schema.inspection.enabled` (default true), `schema.introspection.enabled` (default true), `schema.printer.enabled`, `graphiql.enabled`, `graphiql.path`, `websocket.path` (unset means no WebSocket endpoint), `websocket.connection-init-timeout` (60s), `websocket.keep-alive`, `rsocket.mapping`, `cors.*` (`allowed-origins`, `allowed-origin-patterns`, `allowed-methods`, `allowed-headers`, `exposed-headers`, `allow-credentials`, `max-age`).
- I did not find a Boot property for `maxSubscriptionsPerSession` on Boot `main`. I think it needs a custom handler bean for now.

## Not supported or not in scope

- Code-first schema from Java classes. Schema-first only (or a prebuilt graphql-java `GraphQLSchema`).
- GraphQL to SQL translation, ORM-aware query optimization, or `select_related`-style projections from the selection set. Only Spring Data property path hints in the Querydsl and QBE fetchers.
- Filter or ordering input grammar. Auto CRUD mutations. Auto-registration covers only `Query` fields.
- Relay `Node` and global IDs.
- File uploads (multipart spec).
- Batched HTTP requests.
- `@defer`/`@stream`.
- Built-in persisted queries or trusted documents. Only through graphql-java `PreparsedDocumentProvider`.
- Query depth, complexity or cost limits as library features (only graphql-java instrumentation).
- Per-field visibility or schema hiding. Introspection can only be turned off JVM-wide.
- Legacy `subscriptions-transport-ws` protocol. SSE "single connection mode".
- Response caching, `@cacheControl`, Apollo tracing.
- Request-wide transaction management (only recipes).
- Code generation (delegated to DGS codegen).

## Upcoming and unreleased work

- 2.1.0 GA planned for November 2026 with Spring Boot 4.2. `2.1.0-RC1` milestone exists.
- Already on `main` (2.1.0-M1): HTTP GET, HTTP `QUERY`, operation type restrictions, `maxSubscriptionsPerSession`, configuration-time check of HTTP methods.
- Open on the 2.1.x milestone: #1314 "Use HTTP 294 status for partial responses", #1297 "Improve metrics for `_entities` and fields".
- Other open enhancements: #1514 default exception handling for federation requests (2.0.6), #970 schema inspection for Querydsl/QBE auto-registration, #944 subscription and WebSocket session metrics, #657 Spring Data projections as `@SchemaMapping` return values, #448 `@Transactional` support, #1508 proposal for an Argo binary wire format.

## Docs and code disagree

- Docs (`request-execution.adoc` pagination and `data.adoc` scroll) call `GraphQlSource.schemaResourceBuilder().typeDefinitionConfigurer(...)`. The code has no such method. The real method is `configureTypeDefinitions(TypeDefinitionConfigurer)`.
- Docs (`controllers.adoc` HTTP Headers) say headers are available "as `@GraphQlContext` arguments". No `@GraphQlContext` annotation exists. The annotation is `@ContextValue`.
- Docs (`controllers.adoc` exception handler) say to inject `GraphQlErrorBuilder`. The real type is graphql-java `GraphqlErrorBuilder`. No Spring class with that name exists.
- Docs (`controllers.adoc` Validation) say `javax.validation.Validator`. The code uses `jakarta.validation`.
- Docs (`testing.adoc`) say tester documents live in `graphql-test/`, but the fragment examples show files in `src/main/resources/graphql-documents/`. The tester default in code is `graphql-test/`. `graphql-documents/` is the client default.
- Docs (`testing.adoc`) say subscriptions are supported only with `WebSocketGraphQlTester` and the server-side testers. I think `RSocketGraphQlTester` also streams subscriptions, since `RSocketGraphQlClient` supports them. I did not verify this in a test.
- `isHttpOkOnValidationErrors()` is documented in Javadoc as an option, but there is no public way to set it.
- Features in code but not in docs: `GraphQlSource.builder(GraphQLSchema)`, `graphQlSourceFactory`, `@BatchMapping(maxBatchSize)`, `@ContextValue(required)`, `AnnotatedControllerConfigurer.setControllerPredicate` / `addCustomArgumentResolver` / `addFormatterRegistrar`, Querydsl/QBE builder `sortBy` / `maximumScrollCount` / `defaultScrollSubrange` / `cursorStrategy`, `DataLoaderRegistrar`, `BearerTokenAuthenticationExtractor`, `ArgumentValueValueExtractor`, `GraphQlWebSocketHandler.Builder.corsConfiguration`, GraphiQL XSRF header support.

## Sources

- Docs site: https://docs.spring.io/spring-graphql/reference/ (2.0.5). Source in repo `spring-graphql-docs/modules/ROOT/pages/`: `index`, `transports`, `request-execution`, `data`, `controllers`, `security`, `observability`, `graalvm-native`, `federation`, `client`, `codegen`, `graphiql`, `testing`, `boot-starter`, `standalone-setup`, `samples`. All read.
- Repo: https://github.com/spring-projects/spring-graphql (shallow clone, `397b7c0`).
- Wiki: https://github.com/spring-projects/spring-graphql/wiki (cloned). Pages "Spring-for-GraphQL-Versions", "Spring-for-GraphQL-1.3", "1.4", "2.0", "2.1".
- Release notes: https://github.com/spring-projects/spring-graphql/releases (2.0.0 to 2.1.0-M1, 1.4.4 to 1.4.6).
- Open issues and milestones: https://github.com/spring-projects/spring-graphql/issues
- Spring Boot properties and auto-config: https://github.com/spring-projects/spring-boot/tree/main/module/spring-boot-graphql (`GraphQlProperties.java`, `GraphQlCorsProperties.java`, `GraphQlAutoConfiguration.java`, `GraphQlWebMvcAutoConfiguration.java`).
- https://docs.spring.io/spring-graphql/reference/llms.txt (404). https://docs.spring.io/llms.txt (404).
