# Candidates batch 4

Findings files: hot-chocolate, graphql-java, netflix-dgs, spring-graphql, graphql-kotlin, sangria, caliban.

## 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Dynamic schema hot swap | Rebuilds and swaps the schema at runtime without a restart. | hot-chocolate: `ITypeModule.TypesChanged`, `AddTypeModule<T>()` | missing | low | Django apps normally restart on deploy. |
| Multiple named schemas | Serves more than one schema from one project on different paths. | hot-chocolate: `AddGraphQL("Name")`, `MapGraphQL(path, schemaName)` | missing | medium | I think `SCHEMA` is a single setting and the view reads it. A public and an admin API is a real use case. |
| Remove unreachable types | Drops types that no root field reaches. | hot-chocolate: `RemoveUnreachableTypes`, `RemoveUnusedTypeSystemDirectives` | partial: Undine adds declared directives even if unused | low | Undine builds types from references, so unreachable types are rare. |
| Warmup at startup | Builds the schema and warms caches before the first request. | hot-chocolate: eager initialization, `AddWarmupTask`, `IRequestExecutorWarmupTask` | missing | low | I think the schema is built on first import of `SCHEMA`. A warmup of parse and validation caches is a small gain. |
| Schema export downgrade | Exports SDL without newer spec features for old tools. | hot-chocolate: `schema export --spec-version`, `?spec-version=` | missing | low | Niche. |
| Semantic non-null schema variant | Serves a second schema view where `@semanticNonNull` fields are rewritten. | hot-chocolate: `MapGraphQLSemanticNonNullSchema()`, `RewriteToSemanticNonNull` | partial: `@semanticNonNull` directive | low | Depends on client adoption. |
| SDL endpoint | Serves the schema SDL over HTTP (for example `?sdl` or `/schema.graphql`). | hot-chocolate: `MapGraphQLSchema`, `EnableSchemaRequests`, `?sdl`. spring-graphql: `SchemaHandler`, `spring.graphql.schema.printer.enabled`. graphql-kotlin: `graphQLSDLRoute`, `/sdl` | missing | medium | Undine has `print_schema` command only. Useful when introspection is off. |
| Schema-first (SDL-first) definition | Builds the schema from SDL files and wires resolvers by type and field name. | graphql-java: `SchemaParser`, `RuntimeWiring`, `SchemaGenerator.makeExecutableSchema`. hot-chocolate: `AddDocumentFromString`, `AddResolver` | missing | low | Inventory says code-first only. Model-centric design does not need it. |
| Schema transformation visitor | Rewrites a built schema with a visitor (change, insert, delete nodes). | graphql-java: `SchemaTransformer.transformSchema`, `GraphQLTypeVisitor`. hot-chocolate: `TypeInterceptor` | missing | low | Converters cover most needs. |
| Mocked schema execution | Runs a schema with fake data for front-end work and tests. | graphql-java: `MockedWiringFactory`, `EchoingWiringFactory`. netflix-dgs: `graphql-dgs-mocking` (removed in 10.0) | missing | medium | Useful for front-end teams before resolvers exist. |
| Printer options | Prints SDL with options like no descriptions or no directive definitions. | graphql-java: `SchemaPrinter.Options` | partial: `SDL_PRINTER` setting for a custom printer | low | |
| Unused type report | Lists types and directives not reachable from the roots. | graphql-java: `SchemaUsageSupport` | missing | low | |
| Static schema variants | Builds a second schema from the first by removing or renaming parts (for example a beta and a v1 API). | caliban: `GraphQL#transform`, `ExcludeDirectives`, `RenameType`, `ExcludeField` | partial: visibility hides parts per request | low | Visibility covers most use cases. |
| Merge APIs | Combines two separately built APIs into one schema. | caliban: `GraphQL#combine`, `|+|` | partial: one `RootType` collects entrypoints | low | |

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Selection check in resolver | Injects whether a sub field is selected into a resolver argument. | hot-chocolate: `[IsSelected("address")]`. graphql-java: `DataFetchingFieldSelectionSet.contains("a/b*")`, `getFields(glob)`. caliban: `Field => A` resolver parameter | partial: `GQLInfo` gives the raw AST | medium | A helper like `is_selected(info, "path")` would be simple. I did not find one in `undine/utils/graphql/utils.py`. |
| Declare parent columns for a resolver | Tells the optimizer which model columns a custom resolver needs. | hot-chocolate: `[Parent(requires: nameof(User.Id))]`, `[BindMember]`, `[IsProjected]` | partial: `@<field>.optimize` hook | low | Hook covers it with more code. |
| Default resolvers on interfaces | Interface fields with a resolver are inherited by all implementing types. | hot-chocolate: `[InterfaceType<IMessage>] static partial class` | missing | medium | Undine InterfaceFields must map to model fields. No computed interface fields. |
| First-or-default list field | Turns a list resolver into a single object field. | hot-chocolate: `[UseFirstOrDefault]`, `[UseSingleOrDefault]` | missing | low | Easy with a custom resolver. |
| Dictionary to key-value list | Maps a dict to a list of key and value objects. | hot-chocolate: `KeyValuePairOf{K}And{V}`. caliban: `Map[A, B]` as `{key, value}` list | partial: unknown `dict` becomes `JSON` | low | JSON is usually fine. |
| Local context for child fields | A resolver passes a value down to its child field resolvers. | graphql-java: `DataFetcherResult.localContext`, `env.getLocalContext()`. spring-graphql: `@LocalContextValue`. hot-chocolate: `[ScopedState]`, `[LocalState]` | missing | low | Resolvers can attach data to the returned object. |
| Response extensions from resolvers | A resolver adds data to the response `extensions`. | graphql-java: `DataFetcherResult.extensions`, `ExtensionsBuilder` | partial: lifecycle hooks can edit `result` | low | No per-resolver API I think. |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Mutation payload convention | Wraps each mutation in a `{Name}Input` argument and a `{Name}Payload` output type. | hot-chocolate: `AddMutationConventions`, `[UseMutationConvention]`, `MutationConventionOptions` | partial: MutationType gives `input` argument, output is the QueryType | low | Undine returns the object directly. A payload wrapper is a style choice. |
| Query field on mutation payloads | Adds `query: Query` to mutation payloads so clients can refetch. | hot-chocolate: `AddQueryFieldToMutationPayloads` | missing | low | Depends on a payload type. |
| Error interface with code | Replaces the default error type with one that has a `code` field. | hot-chocolate: `AddErrorInterfaceType<T>()`, `IPayloadErrorFactory` | partial: `graphql_fields` on exception classes | medium | I think a shared error interface for all errors-as-data types is missing. |
| Explicit null vs not provided | Lets resolvers tell an omitted argument from an explicit `null`. | hot-chocolate: `Optional<T>`. spring-graphql: `ArgumentValue<T>`. netflix-dgs codegen: `trackInputFieldSet` (`has<Field>()`) | partial: update mutations treat missing keys as unchanged | low | I think function entrypoint arguments use Python defaults, so the difference is lost there. |
| User-defined oneOf inputs | Marks an input object as `@oneOf`. | hot-chocolate: `[OneOf]`, `descriptor.OneOf()`. graphql-kotlin: `@GraphQLOneOf`, `@GraphQLOneOfField` | partial: only auto `@oneOf` for GenericForeignKey inputs | medium | No public option on MutationType or TypedDict. I checked `undine/mutation.py`. |
| Global ID decoding on inputs | Decodes a Relay global ID in an argument or input and checks its type. | hot-chocolate: `[ID]`, `[ID<Product>]` on arguments and inputs | missing | medium | `from_global_id` is only used by the `node` resolver. Inputs take raw pk. |
| Constructor-built inputs | Builds immutable input objects (records, dataclasses) from input data. | hot-chocolate: records built through constructor | partial: `TypedDict` inputs | low | Dataclass or Pydantic input classes could be a future idea. |
| Declarative input constraints | Constraint directives on arguments and inputs (min, max, size, pattern, not blank). | graphql-java-extended-validation: `@Size`, `@Pattern`, `@Min`, `@Max`, `@NotBlank`, `ValidationSchemaWiring`. netflix-dgs: `graphql-dgs-extended-validation`. spring-graphql: Bean Validation `@Valid` on arguments | partial: `@<input>.validate` hooks, model validators through `MUTATION_FULL_CLEAN` | medium | Could reuse Django field validators and show them in the schema. |
| Relay client mutation id | Adds `clientMutationId` to mutation input and payload. | graphql-java: `Relay.mutationWithClientMutationId`. sangria-relay: `Mutation.fieldWithClientMutationId` | missing | low | Old Relay convention. |

## 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| List filter quantifiers | Filters on to-many relations with `all`, `none`, `some`, `any`. | hot-chocolate: list filters `all`, `none`, `some`, `any` | partial: `Filter(many=True, match=...)` on values, related lookups | medium | I think "none of the related rows match" needs a function filter in Undine. |
| Limit filter operations per request | Caps the number of filter operations in one argument. | hot-chocolate: `MaxAllowedFilterOperations(64)` | partial: `MAX_FILTERS_PER_TYPE` limits schema size, not request use | medium | Deep `AND`/`OR` nesting is not limited I think. |
| Disable logical operators | Turns off `and`/`or` per filter type. | hot-chocolate: `AllowAnd(false)`, `AllowOr(false)` | missing | low | Logical operators are always added. |
| Filter conventions | Renames filter operations globally and binds custom filter types per runtime type. | hot-chocolate: `FilterConvention`, `Operation(id).Name(...)` | partial: converters | low | |
| Spatial filters | Distance, contains, intersects and other geo filters. | hot-chocolate: `AddSpatialFiltering()` | partial: GIS lookups may work through autogeneration | low | I think GeoDjango fields have no converter. Not verified. |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Separate default and max page size | Uses one default page size and a different max page size. Can require `first` or `last`. | hot-chocolate: `MaxPageSize`, `DefaultPageSize`, `RequirePagingBoundaries` | partial: `page_size` is both the default and the max | low | I checked `undine/relay/validation.py`. |
| `nodes` shortcut on connections | Adds `nodes` next to `edges`. | hot-chocolate: `IncludeNodesField` | missing | medium | Inventory lists it as not supported. |
| Relative cursors for page bars | Gives cursors for numbered page buttons. | hot-chocolate: `forwardCursors`, `backwardCursors`, `EnableRelativeCursors` | missing | low | |
| Disable backward pagination | Removes `last`/`before`. | hot-chocolate: `AllowBackwardPagination` | missing | low | |
| Paginate plain lists | Builds a Relay connection from an in-memory list or function result. | caliban: `Connection.fromList`, `Pagination(args)`. graphql-java: `SimpleListConnection`. sangria-relay: `Connection.connectionFromSeq` | missing | medium | `Connection` and `OffsetPagination` wrap only QueryType, UnionType or InterfaceType. I checked `undine/relay/connection.py`. |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Plural `nodes(ids:)` entrypoint | Fetches many nodes by global ID. | hot-chocolate: `AddNodesField`, `MaxAllowedNodeBatchSize`. sangria-relay: `Node.pluralIdentifyingRootField`, `nodesField` | missing | medium | Inventory lists it as not supported. |
| Check all nodes are resolvable | Schema build check that every Node type can be refetched. | hot-chocolate: `EnsureAllNodesCanBeResolved` | partial: I think QueryType nodes are always resolvable | low | |

## 9. DataLoaders

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Group loader | Returns a list of values per key (one-to-many). | hot-chocolate: `ILookup<TKey,TValue>` group DataLoader | partial: load function can return lists | low | Works by hand. |
| Required load | Raises when a key is not found. | hot-chocolate: `LoadRequiredAsync` | missing | low | |
| Batch resolver | Resolves one field for all parents at once. | hot-chocolate: `[BatchResolver]`, `ResolveBatch`. spring-graphql: `@BatchMapping(maxBatchSize)` | missing | medium | Works in sync mode too, unlike DataLoader. The optimizer covers most model cases. |
| Lookups for extra cache keys | Primes the cache under other keys derived from loaded values. | hot-chocolate: DataLoader `Lookups` | partial: `prime`, `prime_many` | low | |
| Batched pagination in loaders | Paginates per key inside a batch. | hot-chocolate: `ToBatchPageAsync` | partial: optimizer does nested pagination | low | |
| External value cache for DataLoader | Stores loaded values in an external cache like Redis across requests. | java-dataloader: `DataLoaderOptions.setValueCache`, `ValueCacheOptions` | missing | low | Inventory says no cross-request cache. Django cache could back it. |
| Per-key load context | Passes extra context with each key to the batch function. | java-dataloader: `load(key, keyContext)`, `BatchLoaderEnvironment` | missing | low | |
| Streaming batch results | Batch function yields results as they arrive. | java-dataloader: `BatchPublisher`, `MappedBatchPublisher` | missing | low | |
| Mapped batch function | Batch function returns a dict instead of an ordered list. | java-dataloader: `MappedBatchLoader` | missing | low | Simple to add. Avoids key order bugs. Not verified in `undine/dataloaders.py`. |
| DataLoader statistics | Counts loads, batches and cache hits. | java-dataloader: `SimpleStatisticsCollector`, `DataLoaderInstrumentation` | missing | low | |
| Toggle exception caching | Turns off caching of failed loads. | java-dataloader: `setCachingExceptionsEnabled` | missing | low | |
| Relation fetcher | Loads related objects by a relation key, not only by ID. | sangria: `Fetcher.rel`, `Relation`, `deferRelSeq` | partial: optimizer handles model relations | low | |
| Max concurrent batches | Limits how many batches run in parallel. | sangria: `FetcherConfig.maxConcurrentBatches` | missing | low | |

## 12. Directives

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Directive middleware | Attaches resolver behavior to a directive. Runs for type, field and query directives. | hot-chocolate: `descriptor.Use((next, directive) => ...)` | missing | medium | Undine directives are metadata only. |
| Internal directives | Hides some directives from the SDL. | hot-chocolate: `Internal()`, `DisableInternalDirectives` | partial: `Directive.__is_visible__` | low | |
| Opt-in features | Hides fields unless the client opts in by feature name. | hot-chocolate: `@requiresOptIn(feature:)`, `includeOptIn` | missing | low | Proposal-level spec feature. |
| Deprecated object types | Marks whole object types as deprecated. | hot-chocolate: `EnableObjectDeprecation`, `__Type.isDeprecated` | missing | low | RFC stage. |
| Directive introspection | Exposes applied directives in introspection. | hot-chocolate: `EnableDirectiveIntrospection`, `appliedDirectives`. graphql-java: `IntrospectionWithDirectivesSupport` | missing | low | |
| Custom executable directive behavior | A custom query directive can skip selections like `@skip`. | sangria: `Directive(shouldInclude = ...)` | missing | low | Undine directives are metadata. A validation rule can reject but not skip. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Extra scalars | Adds scalars like `Long`, `HexColor`, `PhoneNumber`, `Latitude`, `Longitude`, `MacAddress`, `LocalDateTime`, `UtcOffset`. | hot-chocolate: `HotChocolate.Types.Scalars`. graphql-java-extended-scalars: `PositiveInt`, `NonNegativeInt`, `Locale`, `Currency`, `CountryCode`, `YearMonth`, `GraphQLLong`, `GraphQLBigInteger` | partial: Undine has 19 scalars | low | Add on demand. |
| Range and regex scalar helpers | Base classes for bounded numbers and pattern strings. | hot-chocolate: `IntegerTypeBase<T>`, `RegexType`. graphql-java-extended-scalars: `newRegexScalar`, `newAliasedScalar` | missing | low | `ScalarType` covers it with more code. |
| DateTime precision options | Controls input and output precision of datetimes. | hot-chocolate: `DateTimeOptions` | missing | low | |
| GeoJSON types | Maps geometries to GeoJSON types. | hot-chocolate: `AddSpatialTypes()` | missing | low | GeoDjango support would need this. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative authorization | Marks types and fields with roles or policies. | hot-chocolate: `[Authorize(Roles=, Policy=)]`, `@authorize`, `[AllowAnonymous]` | partial: permission hooks | high | Inventory says no declarative permission classes and no `has_perm` integration. |
| Authorization at validation time | Rejects an operation before execution when a field is not allowed. | hot-chocolate: `ApplyPolicy.Validation` | partial: visibility hides fields per request | medium | |
| Policy engine integration | Delegates authorization to Open Policy Agent. | hot-chocolate: `AddOpaAuthorization` | missing | low | |

## 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cost analysis with list sizes | Estimates cost from `@cost` and `@listSize` with slicing arguments and coerced variables. | hot-chocolate: `@cost`, `@listSize`, `MaxFieldCost`, `MaxTypeCost`, `DefaultListSize`. sangria: `Field(complexity = (ctx, args, childScore) => ...)`, `ScalarType.complexity`, `QueryReducer.rejectComplexQueries`. caliban: `@GQLCost(weight, multipliers)`, `CostEstimation.maxCost` | partial: `MaxComplexityRule` counts queries. `CostDirective` and `ListSizeDirective` exist for federation only | medium | Undine complexity does not multiply by page size. |
| Cost report header | Returns the computed cost in `extensions`, or only validates. | hot-chocolate: `GraphQL-Cost: report`, `GraphQL-Cost: validate`, `extensions.operationCost`. caliban: `CostEstimation.queryCost` | missing | medium | |
| Per-request limits | Sets different cost limits per request (for example by user role). | hot-chocolate: `SetCostOptions(new RequestCostOptions(...))` | missing | medium | Settings are global. |
| Max execution depth | Rejects operations deeper than N. | hot-chocolate: `AddMaxExecutionDepthRule`. graphql-java: `QueryComplexityLimits(maxDepth, maxFieldsCount)`, `MaxQueryDepthInstrumentation`. sangria: `Executor.execute(maxQueryDepth=)`, `QueryReducer.rejectMaxDepth`. caliban: `Wrappers.maxDepth(n)`, `Wrappers.maxFields(n)` | partial: `MAX_LIST_NESTING_DEPTH` | medium | Inventory says no plain depth rule. |
| Field cycle depth | Limits how often a field coordinate repeats in a path. | hot-chocolate: `AddMaxAllowedFieldCycleDepthRule` | partial: list nesting depth | low | |
| Fragment visit and field merge limits | Bounds validation work for big fragment graphs. | hot-chocolate: `MaxAllowedFragmentVisits`, `SetMaxAllowedFieldMergeComparisons` | partial: `MAX_TOKENS`, `MAX_ERRORS` | low | |
| Introspection depth limit | Limits `ofType` nesting in introspection queries. | hot-chocolate: `SetIntrospectionAllowedDepth`. graphql-java: `GoodFaithIntrospection` (500 fields, depth 20) | partial: introspection off by default | low | |
| Max fields and recursion in parser | Parser limits on fields, nodes and depth. | hot-chocolate: `MaxAllowedFields`, `MaxAllowedRecursionDepth`, `MaxAllowedNodes`. graphql-java: `ParserOptions.maxCharacters`, `maxRuleDepth`, `maxWhitespaceTokens` | partial: `MAX_TOKENS` | low | |
| Concurrency gate | Limits concurrent executions per server. | hot-chocolate: `MaxConcurrentExecutions` | missing | low | ASGI server usually handles this. |
| Per-request introspection allow | Allows introspection for some requests (for example staff). | hot-chocolate: `requestBuilder.AllowIntrospection()`. caliban: `Configurator.setEnableIntrospection`, `setSkipValidation` per request | partial: `ALLOW_INTROSPECTION_QUERIES` global | medium | Visibility hooks might cover part of it. |

## 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Topic publish API | Publishes a message to a named topic from any code. Subscribers filter by topic args. | hot-chocolate: `ITopicEventSender.SendAsync`, `[Topic("{arg}")]` | partial: signal subscriptions and brokers | medium | I think there is no simple `publish(topic, payload)` helper for custom events. Not verified. |
| Redis, NATS, Postgres, RabbitMQ brokers | Multi-process pub/sub providers. | hot-chocolate: `AddRedisSubscriptions`, `AddNatsSubscriptions`, `AddPostgresSubscriptions`, `AddRabbitMQSubscriptions` | partial: `ChannelLayerSubscriptionBroker` | medium | Postgres LISTEN/NOTIFY fits Django without extra services. |
| Buffer full mode | Chooses drop oldest, drop newest or drop write on overflow. | hot-chocolate: `TopicBufferFullMode` | partial: `max_backlog` ends the subscription | low | |
| Legacy WebSocket protocol | Supports `subscriptions-transport-ws`. | hot-chocolate: legacy `graphql-ws`. caliban: legacy `graphql-ws`. graphql-kotlin: `APOLLO_SUBSCRIPTIONS_WS` | missing | low | Deprecated protocol. |
| Resumable subscriptions | Clients resume from a cursor after reconnect. | hot-chocolate (Fusion): `@eventStream`, `@eventCursor` | missing | low | |
| Max subscriptions per WebSocket session | Closes the session when a client opens too many subscriptions. | spring-graphql: `GraphQlWebSocketHandler.Builder.maxSubscriptionsPerSession` | missing | medium | I found no limit on `operations` in `undine/utils/graphql/websocket.py`. Cheap DoS guard. |
| Custom connection ack payload | Returns data in the `connection_ack` message. | spring-graphql: `WebSocketGraphQlInterceptor.handleConnectionInitialization`. caliban: `WebSocketHooks.afterInit`, `onAck`, `onMessage` | partial: `WEBSOCKET_CONNECTION_INIT_HOOK` | low | I think the hook can return a payload. Not verified. |
| Subscription cancel and close hooks | Runs code when a subscription is canceled or the connection closes. | spring-graphql: `handleCancelledSubscription`, `handleConnectionClosed`. hot-chocolate: `ISocketSessionInterceptor.OnCloseAsync`. graphql-kotlin: `GraphQLSubscriptionHooks.onOperation`, `onOperationComplete`, `onDisconnect` | missing | low | Async generator `finally` covers per-subscription cleanup. |

## 18. Incremental delivery (@defer and @stream)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Incremental delivery over SSE, JSON Lines and WebSocket | Sends `@defer` payloads over `text/event-stream`, `application/jsonl` or WebSocket `next` messages. | hot-chocolate: `EnableDefer` with `multipart/mixed`, `text/event-stream`, `application/jsonl`. caliban: `@defer`/`@stream` as `next` messages over WebSocket | partial: multipart/mixed only | medium | |
| Incremental format version choice | Client picks the old or new wire format. | hot-chocolate: `incrementalSpec=v0.1`, `IncrementalDeliveryFormat` | missing | low | |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cache scope, Vary and runtime hints | Sets public or private scope and `Vary` headers per field. A resolver can set or disable the cache hint at runtime. | hot-chocolate: `[CacheControl(maxAge, SharedMaxAge, Scope, Vary)]`. caliban: `@GQLCacheControl(maxAge, scope)`, `Caching.setCacheHint`, `Caching.disableCaching` | partial: `Cache-Control` from `cache_time` and `cache_per_user` | low | I think `s-maxage` and `Vary` are not set. Not verified. |
| Cache invalidation by tag | Invalidates cached entries by type or tag on writes. | caliban: `CacheInvalidator`, `extensions.apolloEntityCacheTags` | missing | medium | Inventory says time-based only. Model signals could drive invalidation. |

## 21. Persisted documents and APQ

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Other document stores | Stores persisted documents in files, Redis or blob storage. | hot-chocolate: `AddFileSystemOperationDocumentStorage`, `AddRedisOperationDocumentStorage` | partial: swappable Django model | low | |
| Per-request persisted-only bypass | Lets trusted requests run non-persisted documents. | hot-chocolate: `AllowNonPersistedOperation()` | missing | medium | `PERSISTED_DOCUMENTS_ONLY` is global. Staff or GraphiQL use would need a bypass. |
| REST-like persisted operation URLs | Exposes each persisted operation as a GET URL for CDN caching. | hot-chocolate: `MapGraphQLPersistedOperations` | partial: `documentId` over GET | low | |

## 22. Lifecycle hooks (middleware / extensions)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-field middleware on one field | Attaches middleware to a single field. | hot-chocolate: `descriptor.Use(...)`, `ObjectFieldDescriptorAttribute` | partial: `LifecycleHook.resolve` runs for all fields | low | |
| WebSocket session interceptor | Hooks for connect, request, result, close on WebSocket sessions. | hot-chocolate: `ISocketSessionInterceptor` | partial: `WEBSOCKET_CONNECTION_INIT_HOOK`, ping and pong hooks | low | |
| Diagnostic event listeners | Event callbacks for parse, validate, resolver, DataLoader batch and cache hits. | hot-chocolate: `ExecutionDiagnosticEventListener`, `DataLoaderDiagnosticEventListener` | partial: lifecycle hooks and tracing integrations | low | No DataLoader batch events I think. |
| Execution profiler | Reports timings, resolver counts and DataLoader dispatch counts per request. | graphql-java: `ExecutionInput.profileExecution(true)`, `ProfilerResult` | partial: Debug Toolbar, testing client query log, tracing hooks | low | |
| Execution cancel | Cancels a running operation from outside. | graphql-java: `ExecutionInput.cancel()` | partial: `EXECUTION_TIMEOUT_SECONDS` | low | |
| Apollo Tracing extension | Writes resolver timings into `extensions.tracing`. | graphql-java: `TracingInstrumentation`. netflix-dgs: `TracingInstrumentation` bean. sangria-slowlog: `SlowLog.apolloTracing`. caliban: `ApolloTracing.apolloTracing()` | missing | low | Format is deprecated. |
| Deprecated usage tracker | Reports when an operation uses a deprecated field, argument, input field or enum value. | sangria: `DeprecationTracker`, `LoggingDeprecationTracker`, `schema.analyzer(query).deprecatedUsages` | missing | high | No hits in `undine/` hooks. Helps remove deprecated fields safely. Fits a `LifecycleHook` or validation rule. |
| Slow query log | Logs operations over a time threshold with per-field timing. | sangria-slowlog: `SlowLog(logger, threshold)`, `SlowLog.extension`. caliban: `Wrappers.printSlowQueries`, `logSlowQueries`, `onSlowQueries` | partial: tracing integrations, lifecycle hooks | medium | No grep hit for slow log in settings. A built-in hook would be small. |
| Pre-execution query reducers | Folds over all selected fields before execution, for example to collect permission tags and preload data. | sangria: `QueryReducer`, `QueryReducer.collectTags` | partial: validation rules, optimizer walk | low | |
| Context update between mutations | A mutation field changes the context for later sibling mutations (log in then act). | sangria: `UpdateCtx` | missing | low | |

## 24. Integrations

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| MCP adapter | Exposes GraphQL operations as MCP tools for AI agents. | hot-chocolate: `HotChocolate.Adapters.Mcp`, `MapGraphQLMcp` | missing | medium | New area. Persisted documents could be the tool list. |
| OpenAPI/REST adapter | Exposes GraphQL operations as REST endpoints with OpenAPI. | hot-chocolate: `HotChocolate.Adapters.OpenApi`, `@http(method:, route:)` | missing | low | |
| Composite schemas spec | Subgraph directives for the GraphQL Composite Schemas spec. | hot-chocolate: `@lookup`, `@is`, `@require`, `@internal` | missing | low | Apollo Federation is supported. |
| Federation 1 | Supports Apollo Federation v1 subgraphs. | hot-chocolate: Federation 1.0 | missing | low | Old. |
| Metrics integration | Records timers and counters for operations, errors, resolvers and DataLoader batches with tags like operation name and query hash. | netflix-dgs: `graphql-dgs-spring-boot-micrometer` (`gql.query`, `gql.error`, `gql.resolver`, `gql.dataLoader`), tag cardinality limiter. caliban: `Wrappers.metrics` (`FieldMetrics`). spring-graphql: `GraphQlObservationInstrumentation` (`graphql.request`, `graphql.datafetcher`, `graphql.dataloader`) | missing | high | Inventory says no Prometheus or StatsD integration. Could be a `LifecycleHook` with `prometheus_client`. |
| Query signature hash | Normalizes an operation (strip literals, sort) and hashes it to group metrics. | netflix-dgs: `QuerySignatureRepository`, graphql-java `AstSignature` | partial: Datadog resource uses `<operation>:<hash>` | medium | I think the hash is of the raw document, not a normalized signature. Not verified. |
| Schema and usage reporting | Reports the schema and operation usage to Apollo GraphOS or GraphQL Hive. | caliban: `caliban-reporting` (`SchemaReporter`), PR #3152 `HiveUsage.wrapper` | missing | medium | Inventory says no Apollo Studio usage reporting. |
| REST endpoints as GraphQL | Exposes existing REST endpoint definitions as GraphQL fields. | caliban: `caliban-tapir` `toGraphQL` | missing | low | DRF views would be the Django analog. |
| Remote schema stitching or gateway | Merges remote GraphQL services into one schema. | caliban: `caliban-stitching` `RemoteSchemaResolver`, `caliban-gateway` | missing | low | Out of scope for a Django library. Apollo Router covers it. |

## 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Export schema on startup | Writes SDL to a file when the app starts. | hot-chocolate: `ExportSchemaOnStartup`. graphql-kotlin: `graphql.printSchema` | partial: `print_schema --check` | low | |
| Project template | Starter template for a new project. | hot-chocolate: `dotnet new graphql` | partial: `example_project/` | low | |
| Agent skills | Ships skills for AI coding assistants. | hot-chocolate: `website/content/docs/skills` | partial: `llms.txt` | low | |
| Introspection client | Downloads a remote schema. | hot-chocolate: `IntrospectionClient`. graphql-kotlin: `graphqlDownloadSDL`, `graphqlIntrospectSchema` | missing | low | |
| Query anonymizer | Turns schemas and operations into anonymized ones for bug reports. | graphql-java: `Anonymizer` | missing | low | |
| Query generator | Generates an operation that selects all fields under a path. | graphql-java: `QueryGenerator` | missing | low | Could help tests. |
| Introspection result to SDL | Turns an introspection JSON result back into SDL. | graphql-java: `IntrospectionResultToSchema`. sangria: `Schema.buildFromIntrospection`, `SchemaRenderer.renderSchema(introspectionResult)` | missing | low | |
| Typed client code generation | Generates typed client classes and query builders from the schema. | netflix-dgs codegen: `generateClient`, `<Field>GraphQLQuery`, `<Type>ProjectionRoot`, `DgsGraphQLClient`. graphql-kotlin: `graphqlGenerateClient`, `GraphQLKtorClient` | missing | low | Inventory says no client generator. Python clients use tools like ariadne-codegen. |
| Schema name constants | Generates constants for type and field names. | netflix-dgs codegen: `DgsConstants` | missing | low | |
| Markdown docs from schema | Generates Markdown docs per query field with example queries. | netflix-dgs codegen: `generateDocs` | missing | low | |
| Dev schema reload | Rebuilds the schema on every request in development. | netflix-dgs: `dgs.reload`, `ReloadSchemaIndicator` | partial: Django runserver autoreload | low | |
| Test documents from files | Loads test operations and fragments from `.graphql` files by name. | spring-graphql: `GraphQlTester.documentName`, `fragmentName` | missing | low | |
| Path-based response assertions | Asserts on response values by JSON path with list helpers. | spring-graphql: `GraphQlTester.path(...).entityList().hasSize()`, `matchesJson`. netflix-dgs: `executeAndExtractJsonPath` | partial: `GraphQLClientResponse.results`, `edges`, `node(i)` | low | |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Request batching | Runs a JSON array of operations in one request. | hot-chocolate: `Batching`, `MaxBatchSize`, `requestIndex`. graphql-kotlin: `GraphQLBatchRequest`, cross-operation DataLoader batching `GraphQLSyncExecutionExhaustedDataLoaderDispatcher` | missing | medium | Inventory lists it as not supported. |
| Variable batching | Runs one operation with a list of variable sets. | hot-chocolate: `variables: [...]`, `variableIndex` | missing | low | Draft spec feature. |
| HTTP QUERY method | Accepts the HTTP `QUERY` method for queries. | hot-chocolate: `EnableQueryRequests` | missing | low | New RFC. |
| CSRF preflight header | Requires a `GraphQL-Preflight` header on GET and multipart requests. | hot-chocolate: `EnforceGetRequestsPreflightHeader`, `EnforceMultipartRequestsPreflightHeader` | missing | medium | Undine uses Django CSRF. A header check helps for uploads. No grep hit for preflight. |
| Request size limit | Caps request body size. | hot-chocolate: `maxAllowedRequestSize`, WebSocket `MaxAllowedMessageSize`. caliban: `QuickAdapter#configureHttp(HttpConfig)` | partial: I think Django `DATA_UPLOAD_MAX_MEMORY_SIZE` applies | low | Not verified for WebSocket. |
| Custom status code logic | Overrides the HTTP status code chosen for a result. | hot-chocolate: `OnDetermineStatusCode` | missing | low | |
| Transport version selection | Chooses the GraphQL over HTTP spec version. | hot-chocolate: `HttpTransportVersion` | missing | low | |
| Batch execution with exported variables | Runs several operations in one document. Results of one become variables of the next. | sangria: `BatchExecutor.executeBatch`, `@export(as:)` | missing | low | Experimental in Sangria. |

## 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Error filter | Rewrites every error before it is sent (message, code, extensions). | hot-chocolate: `AddErrorFilter`, `IErrorFilter` | partial: `ERROR_MASKING_PREDICATE`, lifecycle hooks can edit result | medium | A single error formatter callback is simpler than a hook. |
| Client-chosen error mode | Client sends `onError: NULL` to stop null propagation. | hot-chocolate: `onError` request parameter, `ErrorHandlingMode`. graphql-java: open PR #4378 | partial: `@experimental_disableErrorPropagation` | low | Spec proposal. |
| Translated error messages | Engine error messages follow the request locale. | graphql-java: resource bundles by `ExecutionInput.locale` | missing | medium | No `gettext` use in `undine/`. Django has i18n built in. |
| Standard error type taxonomy | Sets `extensions.errorType` from a fixed enum (`BAD_REQUEST`, `NOT_FOUND`, `PERMISSION_DENIED`) plus optional `errorDetail`. | netflix-dgs: `TypedGraphQLError`, `ErrorType`, `ErrorDetail.Common`, `GraphQLJavaErrorInstrumentation` | partial: `error_code` and `status_code` extensions | low | Undine has about 200 specific codes. |
| Masked error with correlation id | Puts a request or execution id in the masked error message and in the log line. | spring-graphql: unresolved exceptions become `INTERNAL_ERROR` with `executionId` | partial: `ERROR_MASKING_MESSAGE` is a fixed text | medium | No grep hit for a request or execution id. Helps support teams find the log. |
| HTTP 294 for partial responses | Uses status 294 when data and errors are both present. | spring-graphql: open issue #1314. hot-chocolate: transport `Draft20260903` | missing | low | Draft spec. |
