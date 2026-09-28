# graphql-kotlin findings

Versions checked: 10.2.2 (latest stable, GitHub release 2026-08-21) and 11.0.0-alpha.3 (pre-release, 2026-09-24). Repo `master` at `d1d8979` (last commit 2026-10-01, version `11.0.0-SNAPSHOT`). Docs source is in the repo (`website/`, Docusaurus, about 9000 lines of Markdown in `website/docs/` plus versioned copies). All `website/docs/` pages read. Code of server, generator, federation and dataloader modules spot-checked.
graphql-kotlin is the Expedia Group set of Kotlin libraries on top of graphql-java. Apache 2.0. Engine details are in `graphql-java.md`.
Schema style: code-first by reflection. Public Kotlin classes, properties and functions become the schema (`toSchema`). No SDL-first mode. No annotation needed to expose a field.
Stack: Kotlin 2.3, JVM 17, graphql-java 26.1 (on `master`), Spring Boot 4.0 / Spring 7, Ktor 3.4, Jackson 3.

## Maintenance status

- Active. 1805 stars. Not archived. 86 open issues plus PRs. Main maintainers in recent releases: samuelAndalon, JordanJLopez, Samjin.
- Many parallel release lines get fixes. On 2026-06-18 releases 10.0.1, 9.2.1, 8.9.1, 7.4.1 and 6.11.1 shipped together. 9.3.1 and 10.2.2 shipped together on 2026-08-21.
- Majors: 1.0.0 (2019-10), 2.0 (2020-03), 3.0 (2020-06), 4.0 (2021-04), 5.0 (2021-09), 6.0 (2022-07), 7.0 (2023-09), 8.0 (2024-08), 9.0 (2026-02-25), 10.0 (2026-06-01).
- No `CHANGELOG.md`. Changes are in GitHub release notes only.
- Published docs default to `10.x.x` (first entry in `website/versions.json`). `website/docs/` is the unreleased "next" (11.x) version. Versioned docs exist for 3.x to 10.x.
- https://opensource.expediagroup.com/graphql-kotlin/llms.txt and https://opensource.expediagroup.com/llms.txt return 404. `Accept: text/markdown` returns HTML.
- Branches per major (`1.x.x` to `10.x.x`). Unmerged feature branches: `spring-boot-4.1.0` (PR #2194), `jordlopez-argument-coercing` (last commit 2026-04-24).

## Big changes between versions

- 6.0 (2022-07): automatic coroutine context propagation through the `GraphQLContext` map. `GraphQLContext` Kotlin extension functions. Data loader registry removed from the context. I think the custom context object deprecation also dates from here.
- 7.0 (2023-09): Ktor server plugin (`graphql-kotlin-ktor-server`). `graphql-transport-ws` subscriptions on Ktor and Spring. GraalVM native image support (build plugins generate metadata).
- 8.0 (2024-08): graphql-java 22. Federation v1 support dropped (Federation 2 only). Batch dataloader instrumentation fixes. Ktor errors moved to `StatusPages`. Client and test client Gradle tasks made cacheable.
- 9.0 (2026-02-25): graphql-java 23. Persisted queries over GET with only the SHA-256 hash. `SingletonPropertyDataFetcher` (one fetcher per property, not per call). Federation 2.7. Java toolchain for SDL generation.
- 9.1 / 9.2: dependency upgrades. Stop validating `@requires` field set content.
- 10.0 (2026-06-01): Kotlin 2.3, Spring 7 / Spring Boot 4, Jackson 3 (breaking), graphql-java 25. Ktor server skips its own `ContentNegotiation` install when one is already present. `subscriptionConcurrency` (flatMapMerge concurrency) for WebSocket subscriptions.
- 10.1.1: `@oneOf` input support (`@GraphQLOneOf`). 10.1.2: deprecated input fields in client introspection query. Configurable JVM args for `graphqlGenerateSDL`.
- 10.2.0: `SynchronizedDataLoader` wraps loaders that have batching off and caching on. 10.2.1: `useSharedResponseTypes` in client plugins. 10.2.2: fix dropped fields with multiple fragment selections in client generator.
- 11.0.0-alpha.1 to alpha.3 (2026-08-31 to 2026-09-24): graphql-java 26. Federation 2.15 support was added, then the default was lowered to 2.13 (`FEDERATION_SPEC_LATEST_VERSION = "2.13"` in code).

## Modules

- Generator: `graphql-kotlin-schema-generator` (`toSchema`), `graphql-kotlin-federation` (`toFederatedSchema`).
- Server: `graphql-kotlin-server` (framework-neutral core), `graphql-kotlin-spring-server` (Spring Boot WebFlux auto-config), `graphql-kotlin-ktor-server` (Ktor plugin).
- Execution: `graphql-kotlin-dataloader`, `graphql-kotlin-dataloader-instrumentation`, `graphql-kotlin-automatic-persisted-queries`.
- Client: `graphql-kotlin-client` (interface), `graphql-kotlin-ktor-client`, `graphql-kotlin-spring-client`, `graphql-kotlin-client-jackson`, `graphql-kotlin-client-serialization`.
- Build plugins: `graphql-kotlin-gradle-plugin`, `graphql-kotlin-maven-plugin`, plus libraries `graphql-kotlin-client-generator`, `graphql-kotlin-sdl-generator`, `graphql-kotlin-hooks-provider`, `graphql-kotlin-federated-hooks-provider`, `graphql-kotlin-graalvm-metadata-generator`.
- No BOM (added and reverted in 8.0).
- Examples in repo: Spring server, Ktor server, Gradle and Maven clients, federation (products and reviews subgraphs with Apollo Router `docker-compose`).

## Schema generation

- `toSchema(config, queries, mutations, subscriptions, schemaObject)`. Roots are lists of `TopLevelObject`. Returns graphql-java `GraphQLSchema`.
- `TopLevelObject(obj, kClass)`: pass the reflection class separately for Spring AOP proxies.
- `SchemaGenerator(config).generateSchema(queries, ..., additionalTypes = setOf(KType), additionalInputTypes = setOf(KType))`: add types not reachable from roots. `SchemaGenerator` is `Closeable` (closes the classpath scanner).
- `SchemaGenerator.addAdditionalTypesWithAnnotation` (protected): add all classes with a given annotation. Federation uses it for `@key` types.
- `SchemaGeneratorConfig`: `supportedPackages` (required, limits reflection scope), `topLevelNames` (`TopLevelNames` to rename `Query`/`Mutation`/`Subscription`), `hooks`, `dataFetcherFactoryProvider`, `introspectionEnabled`, `additionalTypes` (prebuilt `GraphQLNamedType`s), `typeResolver`.
- `typeResolver`: `GraphQLTypeResolver` finds implementations of interfaces and unions. Default `ClasspathTypeResolver(ClassScanner(...))` scans the classpath with ClassGraph. `SimpleTypeResolver(Map<KClass, List<KClass>>)` is the explicit map for GraalVM. Not in the generator docs.
- Schema object: `schemaObject = TopLevelObject(MySchema())` carries schema-level description and directives. Throws if it has properties or functions.
- Fields: every public property and function with a valid GraphQL name and supported type. Data class methods (`componentN`, `copy`, `equals`, `hashCode`, `toString`) are filtered out.
- Function arguments become GraphQL arguments. `DataFetchingEnvironment` parameters are injected and hidden.
- Properties resolve with `PropertyDataFetcher`. Functions resolve with `FunctionDataFetcher`. Docs advise functions for expensive fields so they only run when selected.
- Nullability from Kotlin types (`Int?` vs `Int`).
- Lists: only `kotlin.collections.List`. `Set`, `Map` and arrays are not supported. `Set` can be mapped to list through `willResolveMonad`.
- Function types (lambdas) as property types are not supported.
- Exclusion: non-public visibility or `@GraphQLIgnore` (fields, arguments, superclasses, interfaces).
- Renaming: `@GraphQLName` on classes, fields, arguments, enum values.
- Descriptions: `@GraphQLDescription` on any element. Markdown allowed. KDoc is not used.
- Deprecation: `@kotlin.Deprecated` (message plus `ReplaceWith` become the reason) or `@GraphQLDeprecated` (schema only). Fields, input fields and enum values. Argument deprecation is not supported.
- `@GraphQLType("Name")`: change a field return type to a type reference. Pair with `additionalTypes`. For types from libraries you cannot edit.
- `@GraphQLValidObjectLocations([Locations.OBJECT | INPUT_OBJECT])`: restrict a class to output or input. Throws on misuse.
- `@GraphQLSkipInputSuffix` on a class: no `Input` suffix on the input type. Not in docs.
- Print SDL: `GraphQLSchema.print(includeIntrospectionTypes, includeScalarTypes, includeDefaultSchemaDefinition, includeDirectives, includeDirectivesFilter, includeDirectiveDefinitions)`. Always hides `@defer`.
- Generation-time exceptions with specific names, for example `TypeNotSupportedException`, `ConflictingTypesException`, `InvalidGraphQLNameException`, `EmptyQueryTypeException`, `InvalidInputFieldTypeException`, `PrimaryConstructorNotFound`, `MultipleConstructorsFound`.

## Schema generator hooks

- `SchemaGeneratorHooks` interface. Set on `SchemaGeneratorConfig.hooks`. Default `NoopSchemaGeneratorHooks`.
- Type creation: `willGenerateGraphQLType(KType)` (custom scalars, override any type), `didGenerateGraphQLType`, `willAddGraphQLTypeToSchema`.
- Monads: `willResolveMonad(KType)` (unwrap return wrappers such as `Mono`, `Optional`), `willResolveInputMonad(KType)` (unwrap input wrappers, not in docs).
- Filters: `isValidSuperclass`, `isValidProperty`, `isValidFunction`, `isValidSubscriptionReturnType`, `isValidAdditionalType`.
- Directives: `willGenerateDirective`, `didGenerateDirective`, `willApplyDirective`, `didApplyDirective`, `wiringFactory` (`KotlinDirectiveWiringFactory`).
- Roots: `didGenerateQueryField`, `didGenerateMutationField`, `didGenerateSubscriptionField`, `didGenerateQueryObject`, `didGenerateMutationObject`, `didGenerateSubscriptionObject`, `didGenerateSubscriptionType` (docs name).
- Schema: `willBuildSchema`, `didBuildSchema(GraphQLSchema.Builder)`.
- Runtime rewire: `onRewireGraphQLType(element, coordinates, codeRegistry)`.

## Types

- Scalars: `String`, `Boolean`, `Int`, `Double` and `Float` (both to `Float`). `Long`, dates, `UUID`, `BigDecimal` need custom scalars or graphql-java-extended-scalars through hooks.
- `ID`: `com.expediagroup.graphql.generator.scalars.ID` value class. String-backed only. Needs `IDValueUnboxer` on the `GraphQL` instance (auto in both servers).
- Custom scalars: return a `GraphQLScalarType` from `willGenerateGraphQLType`.
- Kotlin inline value classes: three modes. As the underlying scalar (hook plus custom `IDValueUnboxer` subclass), as a custom scalar, or as a wrapper object type (default).
- Enums: Kotlin enums map directly. Java enums outside `supportedPackages` can be mapped through a hook.
- Interfaces: Kotlin interfaces with at least one field, abstract classes and sealed classes become GraphQL interfaces. Interfaces can implement interfaces. Implementations found by classpath scan.
- Unions: marker interfaces (no fields) become unions. `@GraphQLUnion(name, possibleTypes, description)` on a function returning `Any` for types you cannot edit. `@GraphQLUnion` also works as a meta-annotation to attach directives.
- Interfaces and unions as inputs throw at generation time.
- Input types: classes used as arguments. Suffix `Input` added unless the class name ends with `Input`. Only primary constructor properties become input fields.
- Input conversion: own reflection code (`convertArgumentValue`), not Jackson. Calls the primary constructor. Uses `@GraphQLName` names.
- `@oneOf` inputs (10.1.1): `@GraphQLOneOf` on a sealed interface. Each subclass needs `@GraphQLOneOfField(fieldName, type = WRAPPED | UNWRAPPED)`. `UNWRAPPED` uses the single constructor property type directly. Nesting works. Exceptions: `InvalidGraphQLOneOfTargetException`, `NoGraphQLOneOfImplementationsException`, `MissingOneOfInputFieldAnnotationException`, `DuplicateOneOfInputFieldException`, `InvalidGraphQLOneOfUnwrappedFieldException`.

## Arguments

- Optional argument: nullable plus a Kotlin default value.
- Kotlin default values are applied at runtime, but they do not show in the schema (Kotlin reflection limit, issue #53). No `defaultValue` in generated SDL.
- `OptionalInput<T>` sealed class (`OptionalInput.Undefined`, `OptionalInput.Defined(value)`): tells missing from explicit `null`. Always nullable in schema.
- `DataFetchingEnvironment.containsArgument(name)` as the other way to detect missing arguments.
- Parent arguments through `environment.executionStepInfo.parent`.
- Shared state to child resolvers by passing it into non-public constructor fields of the returned object.
- Spring: `@Autowired` (plus optional `@Qualifier`) function parameters are injected from the Spring context by `SpringDataFetcher`. Must also be `@GraphQLIgnore`.

## Directives

- Only type system (schema) directives can be defined. Executable directive definitions are not supported. `@skip`, `@include`, `@deprecated` built in.
- Custom directive: annotation class marked `@GraphQLDirective(name, description, locations)`. Annotation parameters become directive arguments. Name defaults to the decapitalized annotation name.
- Repeatable: Kotlin `@Repeatable` on the annotation.
- Hide a directive argument: `@get:GraphQLIgnore` on the annotation parameter.
- Runtime behavior: `KotlinSchemaDirectiveWiring` (`onField`, `onObject` and so on) through `KotlinDirectiveWiringFactory(manualWiring = mapOf(...))` or `getSchemaDirectiveWiring`. Manual wiring wins over factory (opposite of graphql-java).
- Directives apply in annotation declaration order.
- Limit: directive arguments can only be Kotlin annotation parameter types (primitives, strings, enums, annotations, arrays). Input objects need hooks.

## Execution and async

- Default: blocking functions run on the calling thread.
- `suspend` functions: run in the `CoroutineScope` from `GraphQLContext` (`CoroutineScope::class` key), returned as `CompletableFuture`. Servers set a `SupervisorJob` scope per request. Extra coroutine context through the `CoroutineContext::class` context key.
- `CompletableFuture<T>` return types unwrapped automatically.
- Reactor `Mono`, RxJava `Single`: need a `willResolveMonad` hook plus a custom `FunctionDataFetcher` and `KotlinDataFetcherFactoryProvider`.
- `KotlinDataFetcherFactoryProvider`: `functionDataFetcherFactory(target, kClass, kFunction)`, `propertyDataFetcherFactory(kClass, kProperty)`. Implementations `SimpleKotlinDataFetcherFactoryProvider`, `SimpleSingletonKotlinDataFetcherFactoryProvider` (caches getters in a `ConcurrentHashMap`), `SpringKotlinDataFetcherFactoryProvider`.
- `FunctionDataFetcher` open methods: `getParameters`, `mapParameterToValue`, `runSuspendingFunction`, `runBlockingFunction`.
- Partial data: return graphql-java `DataFetcherResult` with data and errors. Thrown exceptions become `GraphQLError`s.
- Context: graphql-java `GraphQLContext` map only. Kotlin helpers `GraphQLContext.get<T>()`, `getOrDefault`, `getOrElse`, `getOrThrow`, `plus`, `Map.toGraphQLContext()`, `DataFetchingEnvironment.getFromContext<T>()` and `getFromContextOrDefault/OrElse/OrThrow` (not in docs).
- Selection info via `DataFetchingEnvironment.selectionSet` (docs suggest SQL column pruning by hand). No built-in projection or ORM integration.
- Introspection off: `SchemaGeneratorConfig.introspectionEnabled = false` (`graphql.introspection.enabled` in Spring, `engine.introspection.enabled` in Ktor).

## Subscriptions

- Root functions that return `org.reactivestreams.Publisher<T>` (for example `Flux`).
- Kotlin `Flow`: `FlowSubscriptionSchemaGeneratorHooks` plus `FlowSubscriptionExecutionStrategy`. Both servers configure them automatically.
- Transport: WebSocket only. `graphql-transport-ws` (default) on both servers. Spring also has the deprecated Apollo `subscriptions-transport-ws` (`graphql.subscriptions.protocol=APOLLO_SUBSCRIPTIONS_WS`).
- Generic base: `GraphQLWebSocketServer<Session, Message>` in the core server module.
- Hooks: `GraphQLSubscriptionHooks` / `SpringGraphQLSubscriptionHooks` / `KtorGraphQLSubscriptionHooks`: `onConnect` (validate `connectionParams`, return context), `onOperation`, `onOperationComplete`, `onDisconnect`. Apollo protocol: `ApolloSubscriptionHooks` with `onConnectWithContext`, `onOperationWithContext`.
- Spring settings: `graphql.subscriptions.endpoint`, `connectionInitTimeout` (60 s), `keepAliveInterval` (deprecated), `subscriptionConcurrency` (not in docs table).
- No SSE subscription transport (open issue #2105). No multipart subscriptions.

## Data loaders and batching

- `KotlinDataLoader<K, V>`: `dataLoaderName` plus `getDataLoader(graphQLContext)`. Wraps java-dataloader `DataLoader`.
- `KotlinDataLoaderRegistryFactory(dataLoaders)`: new `DataLoaderRegistry` per request. Stores it in `GraphQLContext` under `DataLoaderRegistry::class`.
- `SynchronizedDataLoader` (10.2.0, internal): wraps a loader with batching off and caching on, so concurrent misses call the loader once.
- `DataFetchingEnvironment.getValueFromDataLoader(name, key)` and `getValuesFromDataLoader(name, keys)` (second one not in docs).
- Data loaders must return `CompletableFuture`. No native coroutine data loader. Docs show `coroutineScope.future { ... }` with the scope from the context.
- Cross-operation batching: `graphql-kotlin-dataloader-instrumentation` with `GraphQLSyncExecutionExhaustedDataLoaderDispatcher`. Dispatches all loaders when every synchronous path in all operations of an HTTP batch request is exhausted. One shared registry for the whole batch. Enable with `graphql.batching.enabled=true` (`strategy=SYNC_EXHAUSTION`, the only value).
- `CompletableFuture.dispatchIfNeeded(environment)`: chain several data loaders in one resolver and still batch.
- Federation `FederatedTypePromiseResolver` works with data loaders for `_entities` batching.

## Federation

- `toFederatedSchema(config: FederatedSchemaGeneratorConfig, queries, ...)`. `FederatedSchemaGeneratorHooks(resolvers)` is required. Federation 2 only (v1 dropped in 8.0).
- Default `@link` URL `https://specs.apollo.dev/federation/v2.13` on `master`. Override per schema with `@LinkDirective`.
- Auto-added `_service { sdl }`, `_entities(representations)`, `_Any`, `_Entity`, `FieldSet`.
- Entity resolvers: `FederatedTypeSuspendResolver` (suspend) and `FederatedTypePromiseResolver` (`CompletableFuture`, works with data loaders). `typeName` matches `__typename`. Spring picks up resolver beans automatically.
- Directive annotations: `@KeyDirective(FieldSet, resolvable)`, `@ExternalDirective`, `@RequiresDirective`, `@ProvidesDirective`, `@ShareableDirective`, `@InaccessibleDirective`, `@OverrideDirective(from, label)`, `@TagDirective`, `@InterfaceObjectDirective`, `@ComposeDirective`, `@LinkDirective` with `LinkImport`, `@LinkedSpec`, `@ContactDirective`, `@AuthenticatedDirective`, `@RequiresScopesDirective`, `@PolicyDirective`, `@ContextDirective`, `@FromContextDirective(ContextFieldValue)`, `@CostDirective`, `@ListSizeDirective`, `@CacheTagDirective` (Fed 2.12), `@ExtendsDirective` (deprecated).
- `@OverrideDirective.label` for progressive override (`percent(n)`, Fed 2.7+). Validated at generation. Not in docs.
- Generation-time validation of `@key`, `@requires`, `@provides` field sets (`FederatedSchemaValidator`). `@requires` content no longer validated since 9.2.
- Tracing: `FederatedTracingInstrumentation` from `federation-jvm`. Reads `apollo-federation-include-trace` from the context. `DefaultSpringGraphQLContextFactory` and `DefaultKtorGraphQLContextFactory` fill it.
- No gateway. No subgraph composition checks.

## HTTP server core (`graphql-kotlin-server`)

- `GraphQLServer<Request>(requestParser, contextFactory, requestHandler)`. Response sending is left to the framework.
- `GraphQLRequestParser<Request>`: returns `GraphQLServerRequest` or `null` (bad request).
- `GraphQLContextFactory<Request>`: `suspend fun generateContext(request)`. Context keys and values must be non-null.
- `GraphQLRequestHandler(graphQL, dataLoaderRegistryFactory)`: `executeRequest`, `executeSubscription`. Open for extension.
- Batch requests: JSON array body becomes `GraphQLBatchRequest`. One context for all. Runs concurrently, or sequentially when any query string contains `"mutation "` (plain substring check).
- `@defer` and incremental delivery are switched off on purpose (`ExperimentalApi.ENABLE_INCREMENTAL_SUPPORT = false`, "pending http implementation").
- Types: `GraphQLRequest(query, operationName, variables, extensions)`, `GraphQLResponse(data, errors, extensions)`, `GraphQLServerError`, `GraphQLBatchResponse`.
- Execution errors in the request handler become a single error in a 200 response. Parse failures in the parser become HTTP 400.
- Mutation strategy is `AsyncSerialExecutionStrategy` in both servers.

## Spring server (`graphql-kotlin-spring-server`)

- Spring Boot auto-config on WebFlux only. Spring MVC (servlet) is not supported.
- Schema from beans that implement marker interfaces `Query`, `Mutation`, `Subscription` (and a schema bean). `graphql.packages` required.
- Routes: `/graphql` (POST and GET), `/subscriptions`, `/sdl`, `/graphiql`. Prisma `/playground` opt-in.
- POST with `application/json` or `application/graphql` body. GET with `query`, `operationName`, `variables`, `extensions` params.
- GET does not block mutations in the Spring parser (code read). Ktor blocks them.
- Response content type `application/graphql-response+json` when the `Accept` header asks for it. Status stays 200 for GraphQL errors.
- Properties (`GraphQLConfigurationProperties`): `graphql.endpoint`, `packages`, `printSchema`, `serializationLibrary` (`JACKSON` or `FASTJSON`), `federation.enabled`, `federation.tracing.enabled/debug`, `introspection.enabled`, `playground.*`, `graphiql.*`, `sdl.*`, `subscriptions.*`, `batching.enabled/strategy`, `automaticPersistedQueries.enabled`.
- Overridable beans: `DataFetcherExceptionHandler`, `KotlinDataFetcherFactoryProvider`, `KotlinDataLoader`s, `KotlinDataLoaderRegistryFactory`, `SchemaGeneratorConfig`, `SchemaGeneratorHooks`, `TopLevelNames`, `GraphQLTypeResolver`, `FederatedTypeResolver`s, `Instrumentation`s (ordered by `Ordered`), `ExecutionIdProvider`, `PreparsedDocumentProvider`, `GraphQLRequestHandler`, `SpringGraphQLContextFactory`, `SpringGraphQLRequestParser`, `IDValueUnboxer`.
- HTTP request/response access through Spring `WebFilter`. Jackson config from Spring Boot (`spring.jackson.*`, `JsonMapperBuilderCustomizer`).
- GraalVM native image support.

## Ktor server (`graphql-kotlin-ktor-server`)

- `install(GraphQL)` with `schema { }`, `engine { }` and `server { }` blocks. Also from `application.conf` (HOCON) or YAML for simple values.
- `schema`: `packages`, `queries`, `mutations`, `subscriptions`, `schemaObject`, `hooks`, `topLevelNames`, `federation.enabled`, `federation.tracing.enabled/debug`, `typeHierarchy` (for GraalVM).
- `engine`: `automaticPersistedQueries.enabled`, `batching.enabled/strategy`, `introspection.enabled`, `dataFetcherFactoryProvider`, `dataLoaderRegistryFactory`, `exceptionHandler`, `executionIdProvider`, `idValueUnboxer`, `instrumentations`, `preparsedDocumentProvider`.
- `server`: `contextFactory` (`DefaultKtorGraphQLContextFactory`), `jacksonConfiguration`, `requestParser`.
- No routes by default. Route extensions: `graphQLPostRoute(endpoint, streamingResponse)`, `graphQLGetRoute(...)` (queries only, 405 on mutation or subscription), `graphQLSubscriptionsRoute(endpoint, protocol, handlerOverride)`, `graphQLSDLRoute`, `graphiQLRoute`. Routes can be wrapped in Ktor `authenticate { }`.
- Responses use chunked (streaming) encoding by default.
- Errors through Ktor `StatusPages` (`defaultGraphQLStatusPages()`: `UnsupportedOperationException` to 405, other to 400).
- Jackson only. `kotlinx.serialization` not supported on the server.

## Persisted queries and document caching

- `graphql-kotlin-automatic-persisted-queries`: `AutomaticPersistedQueriesProvider(cache)` is a graphql-java `PreparsedDocumentProvider`. Apollo APQ protocol (`extensions.persistedQuery.sha256Hash`).
- `AutomaticPersistedQueriesCache` interface. `DefaultAutomaticPersistedQueriesCache` is in-memory. Redis or Caffeine through your own implementation.
- Errors `PersistedQueryNotFound` and `PersistedQueryIdInvalid`.
- GET with hash only supported since 9.0.
- No trusted documents or operation allow list.

## Security

- No authentication or authorization module. Docs point to directives (`KotlinSchemaDirectiveWiring`), context factories and framework security (Spring `WebFilter`, Ktor `Authentication`).
- No query depth or complexity limits of its own. Use graphql-java instrumentations as beans or `engine.instrumentations`.
- No rate limiting (open issue #2118).

## Observability

- Only federation tracing (`FederatedTracingInstrumentation`). Any graphql-java `Instrumentation` can be added. No Micrometer or OpenTelemetry integration of its own.

## Developer tools

- GraphiQL route (default on in Spring). Prisma Playground (opt-in, Spring only).
- SDL route. `graphql.printSchema` logs the SDL at startup.

## Kotlin GraphQL client (brief)

- `GraphQLClient<RequestCustomizer>` interface: `suspend execute(request)` and `suspend execute(listOf(requests))` (batch).
- `GraphQLKtorClient` (Ktor `HttpClient`, default `kotlinx.serialization`) and `GraphQLWebClient` (Spring `WebClient`, default Jackson). Global and per-request customization.
- Queries and mutations only. No subscriptions in the client.
- Serializers through `ServiceLoader`: `GraphQLClientJacksonSerializer`, `GraphQLClientKotlinxSerializer` (explicit polymorphic fallbacks needed).
- Client APQ: `AutomaticPersistedQueriesSettings(enabled, httpMethod = GET | POST)` on both clients. Not in docs.
- Client `OptionalInput` for three-state inputs (`useOptionalInputWrapper`).
- `ScalarConverter<T>` for custom scalars.
- No blocking client (issue #2144). No Kotlin Multiplatform (issue #2046).

## Build plugins (brief)

- Gradle tasks: `graphqlDownloadSDL`, `graphqlIntrospectSchema`, `graphqlGenerateClient`, `graphqlGenerateTestClient`, `graphqlGenerateSDL`, `graphqlGraalVmMetadata`. Maven goals: `download-sdl`, `introspect-schema`, `generate-client`, `generate-test-client`, `generate-sdl`, `generate-graalvm-metadata`.
- Client codegen: one `.graphql` file with one operation gives one Kotlin class implementing `GraphQLClientRequest`. Operations validated against the schema. Schema from introspection, SDL endpoint, file or classpath.
- Codegen options: `packageName`, `queryFiles` / `queryFileDirectory`, `schemaFile`, `serializer` (`JACKSON` / `KOTLINX`), `customScalars`, `allowDeprecatedFields` (default false, generation fails on deprecated fields), `useOptionalInputWrapper`, `useSharedResponseTypes` (10.2.1), `parserOptions`.
- Generated code: KDoc from schema descriptions, `@Generated`, `__UNKNOWN_VALUE` added to every enum, sealed classes for interfaces and unions.
- SDL generation from code (`graphqlGenerateSDL`): scans `Query`/`Mutation`/`Subscription` beans. Custom or federated hooks through `SchemaGeneratorHooksProvider` SPI (`META-INF/services`). Fails if more than one provider is found. Worker `jvmArguments`.
- GraalVM metadata: generates reflection metadata from the schema so the app can build as a native image without classpath scanning.

## Not supported or not in scope

- SDL-first schemas.
- Relay: no `Node` interface, global IDs or connection types. No pagination helpers.
- Filtering, ordering, ORM or database integration, projections, query optimizer.
- File uploads (no multipart support anywhere in the repo).
- `@defer` / `@stream` (explicitly disabled in the request handler).
- SSE and multipart subscription transports. HTTP `QUERY` method.
- Spring MVC (servlet) stack.
- Query depth, complexity or cost limits (beyond federation `@cost` / `@listSize` metadata for the router).
- Authorization framework. Rate limiting.
- Default argument values in the generated schema.
- `Set`, `Map`, arrays, lambdas as field types without hooks. `ID` backed by non-String types.
- Executable (query) directive definitions.
- Argument deprecation.
- Kotlin Multiplatform client. Client subscriptions.
- Schema testing utilities (no tester like Spring `GraphQlTester`).
- Mutation input validation (no Bean Validation or similar).

## Upcoming and unreleased work

- 11.0.0 on `master` (alpha.3): graphql-java 26.1, Federation default 2.13.
- PR #2194: Spring Boot 4.1.0 upgrade.
- PR #2173: priority override when several `SchemaGeneratorHooksProvider`s are on the classpath (issue #2150).
- PR #2215: fix for `SYNC_EXHAUSTION` that stops dispatching after a cache hit on a completed future (10.x).
- PR #2116: respect custom coroutine scope for blocking functions.
- Branch `jordlopez-argument-coercing`: `DataFetchingEnvironment.getArgumentsAs<T>()` extension and public `convertInputMap` for typed argument coercion. Not merged.
- Open enhancements: SSE subscriptions (#2105), cacheable queries (#2068), rate limits (#2118), blocking client (#2144), KMP client (#2046), annotations in separate module (#2060), input/output split in `willGenerateGraphQLType` (#2120), custom scalars from polymorphic types (#1994).

## Docs and code disagree

- Docs (`renaming-fields.md`) say renamed input fields and enum values also need Jackson `@JsonProperty` (issue #493). The generator has no Jackson dependency. Input conversion uses `@GraphQLName` directly (`convertArgumentValue.kt`). I think the warning is stale.
- Docs (`nested-arguments.md`) still show a custom context object injected as a function parameter (marked deprecated). `FunctionDataFetcher.mapParameterToValue` only injects `DataFetchingEnvironment`. The custom context object path is gone.
- Docs (`async-models.md`) show `FunctionDataFetcher(target, fn, objectMapper)` and `SimpleKotlinDataFetcherFactoryProvider(objectMapper)`. The code constructor is `FunctionDataFetcher(target, fn)` and the factory method has an extra `kClass` parameter.
- Docs (`ktor-configuration.md`) HOCON example uses `batching.strategy = LEVEL_DISPATCHED`. The only enum value in code is `SYNC_EXHAUSTION`.
- Docs (`data-loader-instrumentation.mdx`) link to a "dispatching by level" section that no longer exists. Level-dispatch instrumentation was removed.
- Docs (`spring-properties.md`) omit `graphql.subscriptions.subscriptionConcurrency` and `graphql.automaticPersistedQueries.enabled` (the APQ page documents the second one).
- Docs (`graphql-server.md`) list only the Spring server as a reference implementation. A Ktor server module exists.
- Docs (`spring-beans.md` "Fixed Beans") call `ApolloSubscriptionProtocolHandler` the `graphql-ws` handler. The default protocol is `graphql-transport-ws` through `SubscriptionWebSocketHandler`.
- Docs (`spring-properties.md`) describe `graphql.graphiql.endpoint` as "Prisma Labs Playground GraphQL IDE endpoint". It is the GraphiQL endpoint.
- Features in code but not in docs: `@GraphQLSkipInputSuffix`, `willResolveInputMonad`, `SimpleTypeResolver` / `ClasspathTypeResolver` in generator docs, `getValuesFromDataLoader`, `getFromContext*` extensions, `@OverrideDirective.label`, client `AutomaticPersistedQueriesSettings`, `@defer` being disabled.

## Sources

- Docs site: https://opensource.expediagroup.com/graphql-kotlin/docs/ (default 10.x.x). Source in repo `website/docs/`: `schema-generator/` (writing-schemas, customizing-schemas, execution, federation), `server/` (core, spring-server, ktor-server, data-loader, automatic-persisted-queries), `client/`, `plugins/`, `framework-comparison.md`.
- Repo: https://github.com/ExpediaGroup/graphql-kotlin (shallow clone, `d1d8979`). Source read in `generator/`, `servers/`, `executions/`, `clients/`, `plugins/`.
- Release notes: https://github.com/ExpediaGroup/graphql-kotlin/releases (1.0.0 to 11.0.0-alpha.3).
- Open issues and PRs: https://github.com/ExpediaGroup/graphql-kotlin/issues and https://github.com/ExpediaGroup/graphql-kotlin/pulls
- Branch compare: https://github.com/ExpediaGroup/graphql-kotlin/compare/master...jordlopez-argument-coercing
- https://opensource.expediagroup.com/graphql-kotlin/llms.txt (404). https://opensource.expediagroup.com/llms.txt (404).
