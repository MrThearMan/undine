# graphql-java findings

Versions checked: graphql-java 26.1 (latest, GitHub release 2026-08-24). Backport releases 25.1 and 24.4 (same day). 26.0 (2026-04-23). Repo `master` at `ba06366` (2026-10-02).
graphql-java is a GraphQL engine for the JVM (Java 11+). It has its own ANTLR parser, validator and async execution engine. MIT. It is a low-level engine only. It has no HTTP layer, no DI, no ORM, no auth. Spring for GraphQL and Netflix DGS build on it (covered in their own files).
Schema styles: SDL plus `RuntimeWiring` (recommended in docs), or programmatic builders (`GraphQLObjectType.newObject()` and others). No annotation or code-first class mapping in core.
Sister projects in the same GitHub org: `java-dataloader`, `graphql-java-extended-scalars`, `graphql-java-extended-validation` (brief groups below).

## Maintenance status

- Very active. Last commit on `master`: 2026-10-02. 6220 stars. 49 open issues plus PRs (GitHub count). Not archived. Main authors Brad Baker, Andreas Marek, Donna Zhou (Atlassian heavy contributor base).
- Release cadence: one major per six to twelve months, with betas. 24.3 (2025-09-23), 25.0 (2025-11-10, nine betas before), 26.0 (2026-04-23, two betas), 26.1 / 25.1 / 24.4 (2026-08-24).
- Release policy blog post (2023): only the latest major gets fixes, with security backports. 24.4 and 25.1 show backports in practice.
- No `CHANGELOG.md`. Changes are in GitHub release notes. 26.0 notes are a curated summary plus full PR list.
- Docs source is a separate repo: `graphql-java/graphql-java-page` (Docusaurus). Only one versioned set (`versioned_docs/version-v25`), identical to `documentation/` (master). No docs version for 26.x.
- https://www.graphql-java.com/llms.txt returns 404. `Accept: text/markdown` returns HTML.
- Repo has `AGENTS.md` and `CLAUDE.md`, a performance results dashboard subproject (`performance-results-page`) and an agentic "CI doctor" workflow. JSpecify nullability annotations are being added across the codebase (waves 1 to 5).

## Big changes between majors

- v22: stricter `parseValue` coercion for `String`, `Boolean`, `Float`, `Int` (no more string-to-int). `LegacyCoercingInputInterceptor` (`observeValues` / `migratesValues`) to monitor or revert. `InputInterceptor` added in v21.
- v25: DataLoader dispatch rewrite. New opt-in strategies "chained" and "exhausted". `GraphQL.unusualConfiguration()` / `GraphQLUnusualConfiguration` for rare settings. `ExecutionInput.profileExecution(true)` profiler. `ExecutionInput.cancel()`. `ResponseMapFactory` (custom map class for results). `QueryGenerator`. Subscriptions accept `java.util.concurrent.Flow.Publisher`. DataLoader dispatch inside `@defer` and inside subscriptions. java-dataloader 5.0. `InstrumentationFieldCompleteParameters#getFetchedObject` replaces `getFetchedValue` (breaking).
- v26: `QueryComplexityLimits` enforced by default in validation (`maxDepth` 100, `maxFieldsCount` 100,000, errors `MaxQueryDepthExceeded` / `MaxQueryFieldsExceeded`). All validation rules merged into one `OperationValidator` pass. Rule filter predicate is now `Predicate<OperationValidationRule>` (enum). `DirectiveInfo` removed for `Directives.BUILT_IN_DIRECTIVES`. `@oneOf` inhabitability check. `GraphQLSchema.FastBuilder` (about 5x faster). `QueryAppliedDirective` on operations and documents. Instrumentation hook after exception handling. `DataFetcherResult.newBuilder(T)`. Earlier start of `@defer` execution.

## Schema definition

- SDL path: `SchemaParser.parse(...)` gives `TypeDefinitionRegistry`. `RuntimeWiring.newRuntimeWiring()` with `.type(...)`, `.scalar(...)`, `.directive(...)`, `.wiringFactory(...)`, `.codeRegistry(...)`, `.fieldVisibility(...)`. `SchemaGenerator.makeExecutableSchema(registry, wiring)`.
- `TypeRuntimeWiring.newTypeWiring("Type").dataFetcher(...)`, `.typeResolver(...)`, `.enumValues(EnumValuesProvider)`, `.defaultDataFetcher(...)`.
- `WiringFactory` decides wiring dynamically by inspecting SDL definitions (directives and more). `CombinedWiringFactory`, `NoopWiringFactory`.
- `EchoingWiringFactory` and `MockedWiringFactory`: build a runnable schema from SDL with fake data (source only). `UnExecutableSchemaGenerator.makeUnExecutableSchema(registry)` builds a schema for tooling without wiring (source only).
- `TypeDefinitionRegistry.merge(...)` combines many SDL files. `ImmutableTypeDefinitionRegistry` (source only).
- SDL `extend type`, `extend schema` and other extensions are merged in order. Duplicate identical fields merge.
- Programmatic path: `GraphQLObjectType.newObject()`, `GraphQLFieldDefinition.newFieldDefinition()`, `GraphQLInterfaceType.newInterface()`, `GraphQLUnionType.newUnionType()`, `GraphQLInputObjectType.newInputObject()`, `GraphQLEnumType.newEnum()`, `GraphQLScalarType.newScalar()`, `GraphQLDirective.newDirective()`, `GraphQLArgument.newArgument()`.
- Code is separate from types: `GraphQLCodeRegistry.newCodeRegistry().dataFetcher(FieldCoordinates.coordinates("Type", "field"), fetcher)`, `.typeResolver(...)`, `.defaultDataFetcher(...)`, `.fieldVisibility(...)`.
- `GraphQLTypeReference.typeRef("Person")` for recursive types in code. SDL resolves recursion itself.
- `GraphQLSchema.newSchema().query(...).mutation(...).subscription(...).additionalType(...).additionalDirective(...).codeRegistry(...)`. `clearDirectives()` re-added in 26.0.
- `GraphQLSchema.FastBuilder` (26.0): restrictive, faster schema build for large schemas. `FastSchemaGenerator` in `schema.idl` (source only).
- Schema is immutable. `SchemaTransformer.transformSchema(schema, GraphQLTypeVisitor)` with commands `changeNode`, `insertAfter`, `insertBefore`, `deleteNode`. `GraphQLTypeVisitorStub`. `SchemaTraverser`. `schema.transform(builder -> ...)` and `type.transform(...)` on every element.
- `GraphQLAppliedDirective` (schema usages) vs `GraphQLDirective` (definitions). `IntrospectionWithDirectivesSupport` adds `appliedDirectives` fields to introspection types, filtered by predicate (source only).
- Schema validation on build (`SchemaValidator` rules): types implement interfaces, input/output types used correctly, default values valid, no default value circular refs, no unbroken input cycles, `@oneOf` rules, deprecated non-null args, applied directives valid. Throws `InvalidSchemaException`.
- `SchemaPrinter` with `SchemaPrinter.Options`: `includeIntrospectionTypes`, `includeScalarTypes`, `includeSchemaDefinition`, `includeDirectiveDefinitions`, `includeDirectives`, `useAstDefinitions`, `descriptionsAsHashComments`, `setComparators`, `includeAstDefinitionComments` (source only, not in docs).
- `GraphqlTypeComparatorRegistry` / `DefaultGraphqlTypeComparatorRegistry` controls element order (source only).
- `SchemaUsage` / `SchemaUsageSupport`: reference counts and finds types and directives not reachable from the roots (source only).
- `CyclicSchemaAnalyzer` (source only).

## Object types, fields and data fetching

- `DataFetcher<T>` is the resolver interface. `get(DataFetchingEnvironment)`.
- `PropertyDataFetcher` is the default. Reads POJO getters, public fields, records, and `Map` keys. `PropertyDataFetcher.fetching("desc")` renames. POJO methods can take `DataFetchingEnvironment` as a parameter.
- `LambdaFetchingSupport` builds getters via `LambdaMetafactory` for speed (source only). `unusualConfiguration().propertyDataFetching()`: `clearReflectionCache()`, `setUseSetAccessible`, `setUseNegativeCache`.
- `TrivialDataFetcher` marker interface (the profiler counts these separately).
- `StaticDataFetcher`, `AsyncDataFetcher.async(fetcher[, executor])`, `DataFetcherFactory`, `DataFetcherFactories.wrapDataFetcher(...)`.
- `DataFetchingEnvironment`: `getSource()`, `getRoot()`, `getArguments()`, `getArgument(name)`, `getArgumentOrDefault`, `getGraphQlContext()`, `getLocalContext()`, `getExecutionStepInfo()`, `getSelectionSet()`, `getQueryDirectives()`, `getExecutionId()`, `getDataLoader(name)`, `getDataLoaderRegistry()`, `getLocale()`, `getOperationDefinition()`, `getDocument()`, `getVariables()`, `getField()`, `getMergedField()`, `getFieldType()`, `getParentType()`, `getGraphQLSchema()`, `getFragmentsByName()`. `DelegatingDataFetchingEnvironment`.
- `DataFetcherResult` returns data plus errors plus `localContext` (passed down to child fields) plus `extensions` (merged into the response `extensions` via `ExtensionsBuilder` / `ExtensionsMerger`). `transform`, `map`, `newResult()`, `newBuilder(T)`.
- `ExecutionStepInfo`: `getPath()`, `getParent()`, `getUnwrappedNonNullType()`, argument values. `ResultPath`.
- `ValueUnboxer` / `DefaultValueUnboxer` unwraps `Optional`, `OptionalInt` and similar before completion. `GraphQL.Builder.valueUnboxer(...)`.
- Any `Iterable`, array or `Stream` completes as a list (I think, based on `FpKit` usage, not verified in detail).

## Arguments, input objects, enums

- Arguments arrive as `Map<String, Object>`. Input objects are ordered `LinkedHashMap`. No automatic mapping to POJOs in core.
- Enums: `GraphQLEnumType` values map a name to any JVM object. Default is the name `String`. Input can also be `java.lang.Enum`. `EnumValuesProvider`, `NaturalEnumValuesProvider` (Java enum), `MapEnumValuesProvider` for SDL.
- `@oneOf` input objects supported (`Directives.ONE_OF_DIRECTIVE_DEFINITION`, marked `@ExperimentalApi`). Errors `OneOfNullValueException`, `OneOfTooManyKeysException`. Inhabitability validation in 26.0. Not mentioned in the docs.
- `InputInterceptor` rewrites or observes input values during coercion. `LegacyCoercingInputInterceptor`.
- `InputMapDefinesTooManyFieldsException` on extra input keys. `NonNullableValueCoercedAsNullException`.

## Scalars

- Built-in: `Scalars.GraphQLString`, `GraphQLBoolean`, `GraphQLInt`, `GraphQLFloat`, `GraphQLID`.
- Custom: `GraphQLScalarType.newScalar().name(...).coercing(Coercing)`. `Coercing` methods `serialize`, `parseValue`, `parseLiteral`, `valueToLiteral`, each with `GraphQLContext` and `Locale` parameters (the old signatures are deprecated). Exceptions `CoercingSerializeException`, `CoercingParseValueException`, `CoercingParseLiteralException`.
- `@specifiedBy(url:)` supported.
- Long, Short, Byte, BigDecimal, BigInteger, Char live in graphql-java-extended-scalars, not in core.

## Interfaces and unions

- `TypeResolver.getType(TypeResolutionEnvironment)` per interface or union. `env.getObject()`, `env.getSchema()`, `env.getField()`, `env.getArguments()`, `env.getContext()`.
- Interfaces implementing interfaces supported.
- `UnresolvedTypeException` when a resolver returns nothing.

## Mutations

- No mutation helpers. A mutation field is a normal field with a `DataFetcher`. `AsyncSerialExecutionStrategy` runs root fields in order.
- Relay `Relay.mutationWithClientMutationId(...)` builds a classic Relay mutation field (see Relay group).

## Subscriptions

- `SubscriptionExecutionStrategy`. The subscription field `DataFetcher` returns a Reactive Streams `Publisher` or (25.0) a JDK `Flow.Publisher`. The result `getData()` is a `Publisher<ExecutionResult>`.
- Each event runs the selection set. Event ordering is kept (`CompletionStageMappingOrderedPublisher`).
- DataLoader dispatching works inside subscription events (25.0).
- No transport. No WebSocket, SSE or pub/sub broker in core. Docs point to an example repo (`graphql-java-subscription-example`).
- Instrumentation hooks: `beginReactiveResults`, `beginSubscribedFieldEvent`.

## Execution

- `GraphQL.newGraphQL(schema)` builder: `queryExecutionStrategy`, `mutationExecutionStrategy`, `subscriptionExecutionStrategy`, `defaultDataFetcherExceptionHandler`, `instrumentation`, `preparsedDocumentProvider`, `executionIdProvider`, `doNotAutomaticallyDispatchDataLoader()`, `valueUnboxer`.
- `ExecutionInput.newExecutionInput()`: `query`, `operationName`, `variables`, `extensions`, `root`, `graphQLContext(...)`, `localContext`, `locale`, `executionId`, `dataLoaderRegistry`, `profileExecution`. `context(Object)` is deprecated in favor of `GraphQLContext`.
- `graphQL.execute(...)` (blocks) and `executeAsync(...)` (returns `CompletableFuture`). Fully async engine. Data fetchers can return `CompletionStage`.
- Strategies: `AsyncExecutionStrategy` (queries, parallel dispatch), `AsyncSerialExecutionStrategy` (mutations), `SubscriptionExecutionStrategy`. Custom `ExecutionStrategy` subclasses possible.
- `ExecutionInput.cancel()` / `isCancelled()` (25.0) cancels a running execution. `EngineRunningObserver` sees engine running and not-running states, plus cancellation (source only).
- `ResponseMapFactory` / `DefaultResponseMapFactory` picks the `Map` class for results (25.0).
- `ConditionalNodes` / `ConditionalNodeDecision` lets custom code decide field inclusion beyond `@skip` / `@include` (source only).
- `ExecutionResult.toSpecification()` produces a spec-shaped map. JSON encoding is left to the user.
- i18n: error messages come from resource bundles (`Execution`, `Parsing`, `Scalars`, `Validation`, `General`) in English, German and Dutch, picked by `ExecutionInput.locale` (source only).
- `ParseAndValidate.parseAndValidate(...)` and `Validator.validateDocument(...)` for standalone use. Rule filter by `OperationValidationRule` enum to disable rules.
- No public API to add custom operation validation rules to `Validator` (I think, based on the enum-based `OperationValidator`). Custom checks go through `Instrumentation.beginValidation` or `FieldValidationInstrumentation`.

## Query analysis and normalized operations

- `QueryTraverser` with `QueryVisitor` / `QueryVisitorStub` walks an operation with type info. `QueryReducer` folds over fields. `QueryTransformer` rewrites the AST.
- `ExecutableNormalizedOperationFactory.createExecutableNormalizedOperation(...)` builds an `ExecutableNormalizedOperation` tree of `ExecutableNormalizedField` (fields merged, fragments resolved, per possible object type). Used by `DataFetchingFieldSelectionSet`. Not in the docs.
- `ExecutableNormalizedOperationToAstCompiler` turns a normalized tree back into a query document with variables (useful for gateways). Source only.
- `DataFetchingFieldSelectionSet`: `contains("a/b*")`, `containsAnyOf`, `containsAllOf`, `getFields(glob)`, `getImmediateFields()`, `getFieldsGroupedByResultKey()`. Glob syntax uses `java.nio` path matching (`*`, `**`, `?`).
- `QueryGenerator` (25.0) generates a query string that selects all fields under a path, with `QueryGeneratorOptions` (filters, max fields). Source only.
- `Anonymizer` turns schemas and queries into anonymized ones for bug reports. Source only.

## Batching (DataLoader integration)

- `DataLoaderRegistry` passed in `ExecutionInput.dataLoaderRegistry(...)`. `env.getDataLoader("name")`.
- The engine dispatches DataLoaders automatically. `GraphQL.Builder.doNotAutomaticallyDispatchDataLoader()` turns it off.
- Default strategy: per-level dispatch (`PerLevelDataLoaderDispatchStrategy`). Works only with `AsyncExecutionStrategy`.
- Opt-in chained DataLoaders (25.0): `GraphQL.unusualConfiguration(graphQLContext).dataloaderConfig().enableDataLoaderChaining(true)`. Handles a DataLoader that depends on another DataLoader, and "delayed" DataLoaders after async work. `DelayedDataLoaderDispatcherExecutorFactory`.
- Opt-in exhausted dispatching (25.0): `enableDataLoaderExhaustedDispatching(true)` (`ExhaustedDataLoaderDispatchStrategy`). Dispatches when the engine is idle, like the JS dataloader. Only in release notes and source, not in docs.
- DataLoaders work inside `@defer` and subscriptions.
- Docs warn that calling `load()` from another thread inside a data fetcher hangs. Async work must go in the batch loader.

## Relay

- "Very basic" support in `graphql.relay.Relay`: `nodeInterface`, `nodeField`, `getConnectionFieldArguments`, `getForwardPaginationConnectionFieldArguments`, `getBackwardPaginationConnectionFieldArguments`, `edgeType`, `connectionType`, `pageInfoType`, `mutationWithClientMutationId`, `toGlobalId`, `fromGlobalId` (base64 `Type:id`).
- `SimpleListConnection` builds a connection from an in-memory list. `Connection`, `Edge`, `PageInfo`, `ConnectionCursor` and default implementations. `InvalidCursorException`, `InvalidPageSizeException`.
- No database pagination. Docs state pagination is an application concern.

## Authorization and visibility

- No authorization feature. Docs say to put it in business logic or a `SchemaDirectiveWiring` (`@auth` example).
- `GraphqlFieldVisibility` hides fields per request at runtime (set on `GraphQLCodeRegistry` or `RuntimeWiring`). `BlockedFields.newBlock().addPattern(regex)`. `DefaultGraphqlFieldVisibility`.
- `NoIntrospectionGraphqlFieldVisibility` is deprecated (2024-03-16). Use `Introspection.enabledJvmWide(false)` or the `Introspection.INTROSPECTION_DISABLED` context key (error `IntrospectionDisabledError`).
- `FieldVisibilitySchemaTransformation` builds a new schema with fields and interface implementations removed by predicate, and removes types that become unreachable (source only). Many fixes in 26.0.
- `ExecutableNormalizedField` respects field visibility since 26.0.

## Security and limits

- Parser limits in `ParserOptions`: `maxCharacters` (1 MB), `maxTokens` (15,000), `maxWhitespaceTokens` (200,000), `maxRuleDepth` (500), `maxNumericLiteralCharacters` (100, not in docs), `redactTokenParserErrorMessages`, `captureIgnoredChars`, `captureSourceLocation`, `captureLineComments`, `parsingListener`. Separate defaults for operations and SDL (`setDefaultOperationParserOptions`, `setDefaultSdlParserOptions`).
- `QueryComplexityLimits` (26.0) enforced in validation by default: `maxDepth` 100, `maxFieldsCount` 100,000. Set per request via `GraphQLContext` key `QueryComplexityLimits.KEY`. `QueryComplexityLimits.NONE` disables. `setDefaultLimits(...)` changes JVM default.
- `GoodFaithIntrospection` (on by default, `GOOD_FAITH_INTROSPECTION` validation rule): caps introspection queries at 500 fields and depth 20. Disable per request with `GOOD_FAITH_INTROSPECTION_DISABLED` key or JVM-wide via `unusualConfiguration().goodFaithIntrospection().enabledJvmWide(false)`.
- `MaxQueryComplexityInstrumentation(max, FieldComplexityCalculator)` aborts above a score. Default counts one per field. `MaxQueryDepthInstrumentation(max)`. Both take an optional callback with `QueryComplexityInfo` / `QueryDepthInfo`.
- `FieldValidationInstrumentation` with `FieldValidation` or `SimpleFieldValidation.addRule(ResultPath, BiFunction)` checks fields and arguments before execution.
- No rate limiting. No cost directives (`@cost`, `@listSize`) in core.
- The project is a CVE Numbering Authority (blog 2024-12) and has `SECURITY.md`.

## Persisted queries and document caching

- `PreparsedDocumentProvider` caches parsed and validated documents. `NoOpPreparsedDocumentProvider` is the default (no cache). Docs show a Caffeine-backed example. Open PR #4121 "Caching parse and validate by default".
- Apollo Automatic Persisted Queries: `ApolloPersistedQuerySupport` reads `extensions.persistedQuery.sha256Hash`. `PersistedQueryCache` interface, `InMemoryPersistedQueryCache` (with known queries preloaded). Errors `PersistedQueryNotFound`, `PersistedQueryIdInvalid`. `PersistedQuerySupport` base for custom id schemes. Not in the docs (source only).
- No trusted documents allow-list mode built in (I think. The cache can be made read-only by the user).

## Errors

- `GraphQLError` interface with `getMessage`, `getLocations`, `getPath`, `getExtensions`, `getErrorType` (`ErrorClassification`). `GraphqlErrorBuilder.newError(env)`. `GraphqlErrorException` (throwable that is also a `GraphQLError`).
- `DataFetcherExceptionHandler` (async `handleException`). `SimpleDataFetcherExceptionHandler` makes `ExceptionWhileDataFetching`. Exceptions that implement `GraphQLError` keep their message and extensions. Set with `GraphQL.Builder.defaultDataFetcherExceptionHandler(...)` or per strategy.
- `AbortExecutionException` stops execution and becomes errors.
- `NonNullableFieldWasNullError` for null in non-null fields.
- `@experimental_disableErrorPropagation` on operations (marked `@ExperimentalApi`) turns off null bubbling. Not in docs. Open PRs #4378 "Add `onError` request parameter" and #4401 "Add support for `@semanticNonNull`".
- Runtime exceptions thrown out of `execute`: `CoercingSerializeException`, `CoercingParseValueException`, `UnresolvedTypeException`, `NonNullableValueCoercedAsNullException`, `InputMapDefinesTooManyFieldsException`, `InvalidSchemaException`, `UnknownOperationException`, `GraphQLException`, `AssertException`.

## Directives

- Built-ins: `@deprecated` (fields, enum values, arguments, input fields), `@include`, `@skip`, `@specifiedBy`, `@oneOf`, `@defer`, `@experimental_disableErrorPropagation`. `Directives.BUILT_IN_DIRECTIVES` (26.0).
- Schema directives: `SchemaDirectiveWiring` with `onField`, `onObject`, `onArgument`, `onInterface`, `onUnion`, `onEnum`, `onEnumValue`, `onScalar`, `onInputObjectType`, `onInputObjectField`. Registered per name with `RuntimeWiring.directive("name", wiring)` or for all with `directiveWiring(...)`. Wirings chain in SDL order and can wrap data fetchers or add arguments (docs `@dateFormat` example).
- Operation directives: `env.getQueryDirectives()` gives `QueryDirectives` with `getImmediateAppliedDirective(name)` (`QueryAppliedDirective`, `QueryAppliedDirectiveArgument`). 26.0 adds directives on operations and documents (`OperationDirectivesResolver`).

## Incremental delivery

- `@defer` supported but experimental and off by default. Enable per request with `GraphQLContext` key `ExperimentalApi.ENABLE_INCREMENTAL_SUPPORT` or `unusualConfiguration(ctx).incrementalSupport().enableIncrementalSupport(true)`. `enableEarlyIncrementalFieldExecution(...)` (26.0).
- Result is `IncrementalExecutionResult` with `getIncrementalItemPublisher()` emitting `DelayedIncrementalPartialResult` (`DeferPayload`). Transport (multipart) is left to the user.
- Validation rules `DEFER_DIRECTIVE_LABEL`, `DEFER_DIRECTIVE_ON_ROOT_LEVEL`, `DEFER_DIRECTIVE_ON_VALID_OPERATION`. Instrumentation `beginDeferredField`.
- `@stream`: not supported. `StreamPayload` and `StreamedCall` classes exist but no `@stream` directive is defined.
- None of this is in the docs.

## Introspection

- Standard introspection. `IntrospectionQuery`, `IntrospectionQueryBuilder.Options` (`descriptions`, `specifiedByUrl`, `isOneOf`, `directiveIsRepeatable`, `schemaDescription`, `inputValueDeprecation`, `directiveDeprecation`, `typeRefFragmentDepth`). `IntrospectionResultToSchema` turns an introspection result back into SDL / a `Document`.
- Disable via `Introspection.enabledJvmWide(false)` or per request key `INTROSPECTION_DISABLED`.

## Schema evolution

- `SchemaDiff` / `DiffSet` / `SchemaDiffSet` compares two schemas (from introspection or `GraphQLSchema`) and reports `DiffEvent`s by `DiffLevel` (`INFO`, `DANGEROUS`, `BREAKING`) and `DiffCategory`. Reporters in `schema.diff.reporting` (for example `CapturingReporter`, `PrintStreamReporter`, `ChainedReporter`). Not in docs.
- `SchemaDiffing` (`schema.diffing`) computes a graph edit distance between schemas with the Hungarian algorithm, plus `ana` package for edit analysis. Source only.

## Observability

- `Instrumentation` interface with `createState(Async)` and hooks: `beginExecution`, `beginParse`, `beginValidation`, `beginExecuteOperation`, `beginExecutionStrategy`, `beginExecuteObject`, `beginDeferredField`, `beginSubscribedFieldEvent`, `beginFieldExecution`, `beginFieldFetching`, `beginFieldCompletion`, `beginFieldListCompletion`, `beginReactiveResults`. Rewrite hooks: `instrumentExecutionInput`, `instrumentDocumentAndVariables`, `instrumentSchema`, `instrumentExecutionContext`, `instrumentDataFetcher`, `instrumentExecutionResult`. 26.0 adds a hook after exception handling.
- `SimplePerformantInstrumentation` base. `ChainedInstrumentation`. `NoContextChainedInstrumentation`.
- `TracingInstrumentation` writes Apollo Tracing format to `extensions`.
- Profiler (25.0): `ExecutionInput.profileExecution(true)`. `ProfilerResult` under `ProfilerResult.PROFILER_CONTEXT_KEY`. `shortSummaryMap()` gives timings, data fetcher counts (custom vs trivial), DataLoader load counts and dispatch events, instrumentation classes, result types (`COMPLETABLE_FUTURE_COMPLETED`, `COMPLETABLE_FUTURE_NOT_COMPLETED`, `MATERIALIZED`).
- `ExecutionIdProvider` / `ExecutionId` per request.
- No OpenTelemetry or Micrometer integration in core.

## java-dataloader (brief)

- Latest 6.0.0 (2025-11-05). Last commit 2026-08-21. Port of the JS dataloader with manual dispatch (`dispatch()`, `dispatchAndJoin()`).
- Loaders: `BatchLoader`, `BatchLoaderWithContext`, `MappedBatchLoader` (returns `Map`), `BatchPublisher` and `MappedBatchPublisher` (stream results as they arrive, Reactive Streams), each with a `WithContext` variant. `DataLoaderFactory.newDataLoader(...)`.
- `BatchLoaderEnvironment`: overall context (`BatchLoaderContextProvider`) plus per-key context via `load(key, keyContext)`.
- `DataLoaderOptions`: `setBatchingEnabled`, `setCachingEnabled`, `setCachingExceptionsEnabled`, `setCacheKeyFunction`, `setCacheMap`, `setValueCache` (external caches like Redis, `ValueCacheOptions`), `setMaxBatchSize`, `setBatchLoaderScheduler`, `setStatisticsCollector`, `setInstrumentation`.
- `prime`, `clear`, `clearAll`, `loadMany`. `Try` type for per-key failures.
- `ScheduledDataLoaderRegistry` with `DispatchPredicate` (by depth or time), ticker mode. `BatchLoaderScheduler` to delay batch calls.
- `DataLoaderInstrumentation` / `ChainedDataLoaderInstrumentation`. Statistics: `SimpleStatisticsCollector`, `ThreadLocalStatisticsCollector`.

## graphql-java-extended-scalars (brief)

- Latest 24.0 (2025-07-06). Last commit 2026-02-15. No release for graphql-java 25 or 26 yet.
- `ExtendedScalars`: `DateTime`, `Date`, `Time`, `LocalTime`, `YearMonth`, `Year`, `AccurateDuration`, `NominalDuration`, `SecondsSinceEpoch`, `Object`, `Json`, `Url`, `Uri`, `Locale`, `Currency`, `CountryCode`, `HexColorCode`, `UUID`, `PositiveInt`, `NegativeInt`, `NonPositiveInt`, `NonNegativeInt`, the four float variants, `GraphQLLong`, `GraphQLShort`, `GraphQLByte`, `GraphQLBigDecimal`, `GraphQLBigInteger`, `GraphQLChar`.
- Factories: `ExtendedScalars.newAliasedScalar(...)` (rename an existing scalar), `ExtendedScalars.newRegexScalar(...)` (pattern-validated string).

## graphql-java-extended-validation (brief)

- Latest 24.0 (2025-07-07). Last commit 2025-10-07. Low activity.
- SDL constraint directives on arguments and input fields, like Bean Validation: `@AssertFalse`, `@AssertTrue`, `@DecimalMax`, `@DecimalMin`, `@Digits`, `@Expression` (Java EL), `@Max`, `@Min`, `@Negative`, `@NegativeOrZero`, `@NotBlank`, `@NotEmpty`, `@ContainerNotEmpty`, `@Pattern`, `@Positive`, `@PositiveOrZero`, `@Range`, `@Size`, `@ContainerSize`.
- Wiring: `ValidationSchemaWiring` (a `SchemaDirectiveWiring`) with `ValidationRules` / `DirectiveConstraints`. Direct use in data fetchers via `TargetedValidationRules`. Custom `ValidationRule`.
- Message interpolation with Hibernate-Validator-style templates and i18n resource bundles by `Locale`.

## Not supported or not in scope

- HTTP server, GraphQL-over-HTTP, multipart uploads, WebSockets, SSE. All left to the user or to Spring for GraphQL / DGS.
- JSON encoding (`toSpecification()` only).
- Database access, ORM integration, filtering, ordering, pagination beyond `SimpleListConnection`.
- Authorization and authentication.
- Dependency injection and annotation or class-based schema definition.
- Federation (separate `federation-jvm` project by Apollo, not in this org).
- Response caching and cache-control hints.
- `@stream`.
- Cost directives (`@cost`, `@listSize`).
- Code generation (DGS and others provide it).
- Schema stitching or gateway features (only building blocks like `ExecutableNormalizedOperationToAstCompiler`).

## Upcoming and unreleased work

- Merged on `master` after 26.1: `CancellationConfig.capturePartialResultsOnCancel(...)` (keep partial results on `cancel()`, PR #4398), description parsing speedups, AST printer triple-quote escaping, float exponent syntax errors.
- Open PRs: `onError` request parameter (#4378), `@semanticNonNull` (#4401), caching parse and validate by default (#4121), forbid `@skip`/`@include` on subscription root (#4396), directive definition cycle validation (#4365, #4202, #4459), "schema universe" (#4422), property-based generators `graphql-java-arbitrary` (#4421), instrumentation of `createExecutableNormalizedOperation` (#4045), known queries take precedence in `InMemoryPersistedQueryCache` (#4489), subscription events keep `DataFetcherResult` extensions (#4476), JSpecify waves 4 and 5.

## Docs and code disagree

- Docs are versioned v25 and getting started says 25.0. Latest is 26.1. 26.0 features (`QueryComplexityLimits` on by default, `FastBuilder`, enum rule filter) are not documented. `limits.md` lists only the two instrumentations, not the default validation limits.
- `batching.md` uses `DataLoaderDispatcherInstrumentation` and `DataLoaderDispatcherInstrumentationOptions` and says it is added automatically. These classes do not exist in the code (they existed in v21). Dispatching is now built into the engine through `DataLoaderDispatchStrategy`.
- `batching.md` names `ExecutorServiceExecutionStrategy` as an alternative strategy. The class does not exist in the code.
- `schema.md` lists `GraphQLLong`, `GraphQLShort`, `GraphQLByte`, `GraphQLBigDecimal`, `GraphQLBigInteger` as "Extended graphql-java scalars" next to the built-ins. They are only in graphql-java-extended-scalars. `scalars.md` gets this right.
- `field-visibility.md` presents `NoIntrospectionGraphqlFieldVisibility` as the way to block introspection. The class is deprecated since 2024-03-16 in favor of `Introspection.enabledJvmWide(false)`.
- `profiler.md` calls DataLoader chaining "experimental" in the summary table, while `batching.md` calls it a 25.0 feature. The code keeps it opt-in.
- `profiler.md` says the profiler "will also be included in the forthcoming official v25.0 release". 25.0 shipped 2025-11-10.
- `limits.md` lists four parser limits. The code also has `maxNumericLiteralCharacters` (100).
- Not documented at all: `@defer` and incremental support, `@oneOf`, `@experimental_disableErrorPropagation`, Apollo persisted queries, `ExecutionInput.cancel()`, exhausted DataLoader dispatching, `SchemaPrinter`, `SchemaDiff`, `SchemaUsage`, `FieldVisibilitySchemaTransformation`, `IntrospectionWithDirectivesSupport`, `ExecutableNormalizedOperation`, `QueryTraverser`, `QueryGenerator`, `Anonymizer`, `ResponseMapFactory`, `ValueUnboxer`, `InputInterceptor` (only in upgrade notes), `EchoingWiringFactory` / `MockedWiringFactory`, `ConditionalNodeDecision`, i18n of error messages.

## Sources

Repos (shallow clones in `/tmp/gj-audit/`):
- https://github.com/graphql-java/graphql-java (`master` at `ba06366`, 2026-10-02)
- https://github.com/graphql-java/graphql-java-page (docs source, `dd2282c`, 2026-05-22)
- https://github.com/graphql-java/java-dataloader (`747a7de`, 2026-08-21)
- https://github.com/graphql-java/graphql-java-extended-scalars (`545cf7f`, 2026-02-15)
- https://github.com/graphql-java/graphql-java-extended-validation (`47efeca`, 2025-10-07)

Docs read (repo source of https://www.graphql-java.com/documentation/getting-started, all pages in `documentation/`):
- getting-started, schema, data-fetching, execution, batching, data-mapping, directives, concerns, exceptions, field-selection, field-visibility, instrumentation, limits, profiler, relay, scalars, subscriptions, upgrade-notes.
- READMEs of java-dataloader, extended-scalars and extended-validation (headings and feature lists).
- https://www.graphql-java.com/llms.txt (404). `Accept: text/markdown` returns HTML.

Changelog and status:
- GitHub releases API (v25.0, v25.1, v26.0, v26.1 notes, release list). GitHub repo API (stars, issues, push date). `gh pr list` (open PRs). Commits on `master` since 2026-08-24.
- `ExecutionInput.java` at tags v24.3, v25.0, v26.1 (cancel API). `execution/instrumentation/dataloader/` at v21.0 (old dispatcher classes).

Source checked:
- `src/main/java/graphql/` package layout, `GraphQL.java`, `ExecutionInput.java`, `GraphQLUnusualConfiguration.java`, `Directives.java`, `ExperimentalApi.java`, `execution/instrumentation/Instrumentation.java`, `validation/OperationValidationRule.java`, `validation/QueryComplexityLimits.java`, `introspection/GoodFaithIntrospection.java`, `introspection/Introspection.java`, `parser/ParserOptions.java`, `relay/Relay.java`, `execution/DataFetcherResult.java`, `schema/idl/` file list, `schema/idl/SchemaPrinter.java`, `schema/visibility/*`, javadoc heads of `SchemaUsage`, `Anonymizer`, `QueryGenerator`, `IntrospectionWithDirectivesSupport`, `FieldVisibilitySchemaTransformation`, `ConditionalNodeDecision`, `ResponseMapFactory`, `EngineRunningObserver`, `ApolloPersistedQuerySupport`. `src/main/resources/i18n/`.
- java-dataloader `DataLoaderOptions.java` and package layout. extended-scalars `ExtendedScalars.java`. extended-validation constraint list.
