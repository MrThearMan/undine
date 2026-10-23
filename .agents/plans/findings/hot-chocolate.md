# Hot Chocolate findings

Versions checked: Hot Chocolate 16.6.7 (latest stable, GitHub release 2026-09-24). Prerelease 16.7.0-p.17 (2026-10-03). Maintenance line 15.1.18 (2026-09-04). Repo `main` at `e8e1ece` (2026-10-04).
Hot Chocolate is a GraphQL server for .NET on ASP.NET Core. It has its own parser, validator and execution engine (no reference implementation underneath). MIT. Part of the ChilliCream "graphql-platform" monorepo, which also holds Fusion (gateway), Green Donut (DataLoader and data helpers), Strawberry Shake (client), Nitro (IDE and paid control plane, formerly Banana Cake Pop) and Mocha (new messaging/mediator library, out of scope).
Two schema styles: "implementation-first" (C# classes plus attributes, a Roslyn source generator builds the schema) and "code-first" (`ObjectType<T>` descriptor API). Schema-first SDL still works in code but has no page in the v16 docs (see "Docs and code disagree").

## Maintenance status

- Very active. Last commit on `main`: 2026-10-04. GitHub `pushed_at` 2026-10-04. 5761 stars. 385 open issues plus PRs. Not archived. Company-backed (ChilliCream). Main authors Michael Staib, Pascal Senn, Tobias Tengler, Glen, Rafael Staib.
- Release cadence: 16.x patch or minor every one to three weeks. 16.4.0 (2026-07-06), 16.5.0 (2026-07-13), 16.5.1 (2026-07-22), 16.6.0 (2026-08-05), 16.6.2 to 16.6.7 (2026-08-28 to 2026-09-24). 17 prereleases of 16.7.0 since 2026-08-28.
- Major releases: 14.0.0 (2024-10-16), 15.0.0 (2025-02-04), 16.0.0 (2026-05-12). 15.x still gets backports (15.1.18). Milestone `HC-17.0.0` exists with 2 open items.
- No `CHANGELOG.md`. Changes are in GitHub release notes (PR title lists) and migration guides in the docs.
- Docs source is in the repo under `website/content/docs/` (Next.js site). Only one version of the docs is in `main`, and it describes 16.7 (prerelease) behavior. https://chillicream.com/llms.txt exists (`text/plain`) and links scoped catalogs that point to clean Markdown pages. `Accept: text/markdown` on a docs URL returns a 301 redirect to HTML.

## Big changes between majors

- v15: dropped .NET Standard 2.0, .NET 6 and .NET 7. Removed `HotChocolate.Types.FSharp` (now community `FSharp.HotChocolate`). `DateOnly` binds to `LocalDate`, `TimeOnly` to `LocalTime`. `LocalDate`/`LocalTime` moved into core. `DataLoaderOptions` required in DataLoader constructors. DataLoaders must be registered with `AddDataLoader` (manual DI registration breaks batching). `GroupDataLoader` and ad hoc DataLoaders on `IResolverContext` deprecated in favor of source-generated DataLoaders.
- v16: eager schema initialization by default (`InitializeOnStartup` removed, `AddWarmupTask`, `LazyInitialization` opt out). Strict split of schema services and application services (`AddApplicationService<T>()`). Internal directives (for example `@authorize`) hidden from the SDL endpoint (`DisableInternalDirectives`). Many new Roslyn analyzers at Error severity. `HotChocolate.Execution` and `HotChocolate.Fetching` merged into `HotChocolate.Types`. New scalar base API (`OnCoerceInputLiteral`, `OnCoerceInputValue`, `OnCoerceOutputValue`, `OnValueToLiteral`). Scalar renames (`TimeSpan` to `Duration`, `Any` and `Json` merged with `JsonElement` runtime type, `ByteArray` deprecated for `Base64String`, `System.Uri` now `URI`, `Byte`/`SignedByte` renamed). Request batching off by default (`AllowedBatching`). Incremental delivery wire format v0.2 by default. Experimental `@semanticNonNull` removed in favor of the `onError` proposal. Only five NodaTime scalars remain. `HotChocolate.Fusion.SourceSchema` merged into `HotChocolate.Types.Composite`. `QueryContext<T>` replaces `[UseProjection]` as the recommended projection path. OpenTelemetry spans follow the proposed GraphQL semantic conventions. Concurrency gate. Parser and validation budgets. Resolvers on extension types no longer projected by default. Nitro options replace `GraphQLToolOptions`.
- 16.7 (prerelease, documented as current): cost analysis rewritten to compile a cost plan and evaluate it per request with coerced variables. Default `MaxTypeCost` raised to 10,000. Default list size 50. HTTP `QUERY` method. Transport version `Draft20260903` (status `294`, `422`, `413`). `Accept` quality values honored. Pipeline order changed (variable coercion before operation cache).

## Schema definition

- `builder.AddGraphQL()` (on `WebApplicationBuilder`) or `services.AddGraphQLServer()` returns `IRequestExecutorBuilder`. `AddGraphQL(maxAllowedRequestSize:, disableDefaultSecurity:)`.
- Implementation-first root types: `[QueryType]`, `[MutationType]`, `[SubscriptionType]` on `static partial` classes. Many classes merge into one root type. Classes can be spread over assemblies.
- Non-static `[QueryType]` classes are registered as singletons by the source generator.
- Source-generated `AddTypes()` registers all attributed types in the assembly. `[assembly: Module("Name", ModuleOptions...)]` names the generated module.
- Code-first: `ObjectType<T>`, `ObjectType`, `InputObjectType<T>`, `EnumType<T>`, `InterfaceType<T>`, `UnionType<T>`, `DirectiveType<T>`, `ScalarType<TRuntime, TLiteral>`. Override `Configure(I...Descriptor)`.
- `AddQueryType<T>()`, `AddMutationType<T>()`, `AddSubscriptionType<T>()`, `AddType<T>()`, `AddTypeExtension<T>()`, `AddDirectiveType<T>()`.
- Separate resolver classes for a model: `[ObjectType<Author>] static partial class AuthorNode` with `[Parent] Author author` parameters. `static partial void Configure(IObjectTypeDescriptor<T>)` hook inside it.
- Type extensions: `[ExtendObjectType<T>]` / `[ExtendObjectType(typeof(T))]`, `ObjectTypeExtension`. Only mentioned in passing in the v16 docs.
- `[BindMember(nameof(Product.BrandId))]` replaces a model property with a resolver (and keeps it projected). Several members can be bound to one resolver.
- `BindFieldsExplicitly()` per type, or global `ModifyOptions(o => o.DefaultBindingBehavior = BindingBehavior.Explicit)`. `DefaultFieldBindingFlags` (instance or static members).
- Naming conventions: `Get` prefix and `Async` suffix stripped, camelCase fields, `UPPER_SNAKE_CASE` enum values. `INamingConventions` / `DefaultNamingConventions` replaceable with `AddConvention<INamingConventions>(...)`.
- Input class names get `Input` appended when missing.
- Attributes: `[GraphQLName]`, `[GraphQLDescription]`, `[GraphQLIgnore]`, `[GraphQLType(typeof(...))]` / `[GraphQLType<T>]`, `[GraphQLNonNullType]`, `[GraphQLDeprecated]`, `[Obsolete]`, `[ID]`, `[Node]`, `[OneOf]`, `[InterfaceType]`, `[UnionType]`, `[DirectiveType]`, `[DefaultValue]`, `[DefaultValueSyntax("{ ... }")]`.
- Nullability from C# nullable reference types (NRT). Without NRT all reference types are nullable.
- Descriptions from XML doc comments extracted at build time by the source generator: `<summary>`, `<param>`, `<returns>` (appended as "Returns"), `<exception cref code="...">` (appended as "Errors"), `<inheritdoc/>`. `ModuleOptions.DisableXmlDocumentation`. Runtime XML docs with `UseXmlDocumentation` and `ResolveXmlDocumentationFileName`.
- `Dictionary<TKey, TValue>` maps to a list of `KeyValuePairOf{K}And{V}` objects automatically.
- Any `IEnumerable<T>` maps to a list. Nested lists supported.
- Dynamic schemas: `ITypeModule` with `TypesChanged` event and `CreateTypesAsync`, registered with `AddTypeModule<T>()`. Firing the event hot swaps the schema without restart. `ObjectType.CreateUnsafe(ObjectTypeDefinition)` and similar build types from raw definitions. `pureResolver:` vs `resolver:` delegates.
- Schema options (`ModifyOptions`): `QueryTypeName`, `MutationTypeName`, `SubscriptionTypeName`, `StrictValidation`, `SortFieldsByName`, `RemoveUnreachableTypes`, `RemoveUnusedTypeSystemDirectives`, `FieldMiddleware`, `EnableDirectiveIntrospection`, `DefaultDirectiveVisibility`, `DefaultResolverStrategy` (`Parallel` or `Serial`), `ValidatePipelineOrder`, `StrictRuntimeTypeValidation`, `DefaultIsOfTypeCheck`, `EnableFlagEnums` (C# `[Flags]` enums), `EnableDefer`, `EnableStream`, `EnableCovariantFieldMerging`, `EnableEmptySelectionSets`, `StripLeadingIFromInterface`, `EnableTag` (`@tag`), `EnableOptInFeatures`, `EnableObjectDeprecation`, `PreparedOperationCacheSize`, `OperationDocumentCacheSize`, `PublishRootFieldPagesToPromiseCache`, `LazyInitialization`, `DisableInternalDirectives`.
- Schema-first (source only in v16 docs): `AddDocumentFromString`, `AddDocumentFromFile`, `AddResolver(...)`, `BindRuntimeType<TRuntime, TSchemaType>()`.
- `TypeInterceptor` base class to rewrite type definitions during schema building (source only). Used internally by mutation conventions, query conventions, filtering and federation.
- `HotChocolate.Types.Mutable` package: a mutable schema object model (`MutableObjectTypeDefinition` and others) used by Fusion composition (source only).
- `HotChocolate.Types.Validation` package with `SchemaValidator` and rules for type-system validation (source only).
- Default values are validated against their type at schema build time (16.6). `@oneOf` inputs must be finite (`input A @oneOf { self: A }` rejected).

## Object types and fields

- Public properties and methods become fields. Method parameters become arguments unless they are services, `CancellationToken`, `[Parent]`, `[Service]`, `[GlobalState]`, `[ScopedState]`, `[LocalState]`, `ClaimsPrincipal`, `IResolverContext` or other well-known types.
- Services are injected by type without an attribute when they are registered in DI (Minimal API style binding). `[Service]` is optional except for keyed services and batch resolvers.
- `[Parent(requires: nameof(User.Id))]` tells projections which parent columns a resolver needs.
- `[IsSelected("address", "items")]` on a parameter injects whether a sub field is selected (source only, documented in XML comments).
- `descriptor.Field("x").Resolve(ctx => ...)`, `ResolveWith<T>(...)`, `Type<T>()`, `Argument(...)`, `Use(...)` middleware, `Description`, `Deprecated`, `Ignore`.
- `IResolverContext`: `Parent<T>()`, `ArgumentValue<T>()`, `ArgumentKind()`, `Service<T>()`, `Service<T>(key)`, `RequestAborted`, `GetUser()`, `ContextData`, `ScopedContextData`, `LocalContextData`, `GetGlobalStateOrDefault<T>()`, selection inspection APIs.
- Pure resolvers (synchronous, no services) are optimized by the engine and are cheaper in cost analysis (non-pure default weight 10).

## Arguments and input objects

- Method parameters become arguments. `[GraphQLName]` renames. Nullable C# type means optional.
- `[DefaultValue(10)]`, C# default parameter values, and `[DefaultValueSyntax("{ title: null, year: 2024 }")]` for complex defaults.
- Input objects from any class or record parameter. Records and immutable classes are built through the constructor. Constructor shape is validated at schema build.
- `Optional<T>` distinguishes "not provided" from explicit `null` for partial updates.
- `@oneOf` with `[OneOf]` or `descriptor.OneOf()`. Runtime check that exactly one field is set.
- `[ID]`, `[ID("Product")]`, `[ID<Product>]` on arguments and input fields decode global IDs and can restrict the expected type.
- No built-in declarative input validation (length, format, range). Validation is done in resolvers, custom scalars (`RegexType`, `IntegerTypeBase<T>` with min/max), or community packages.

## Enums, scalars

- C# enums map automatically (implementation-first). `EnumType<T>` for code-first. `[GraphQLName]` on values, `[GraphQLIgnore]` / `descriptor.Ignore(value)`. `EnumType<string>` binds an enum to a non-enum runtime type.
- Built-in scalars beyond the spec: `Decimal`, `Long`, `Short`, `DateTime`, `LocalDate`, `Date`, `LocalDateTime`, `LocalTime`, `Duration`, `UUID`, `URI`, `URL` (deprecated), `Base64String`, `UnsignedByte`, `Byte`, `UnsignedShort`, `UnsignedInt`, `UnsignedLong`, `Any`. Each has a spec page on scalars.graphql.org and `@specifiedBy`.
- Only scalars used by the schema are emitted.
- `DateTimeOptions` (`InputPrecision`, `OutputPrecision`, `ValidateInputFormat`, `AlwaysOutputFractionalSeconds`) for `DateTimeType`, `LocalDateTimeType`, `LocalTimeType`.
- `UuidType('N')` sets the output format (`N`, `D`, `B`, `P`, `X`).
- `Any` scalar uses `JsonElement`. `AddJsonTypeConverter()` lets resolvers return dictionaries, `ExpandoObject` or any JSON-serializable object.
- `HotChocolate.Types.Scalars` package: `EmailAddress`, `HexColor`, `Hsl`, `Hsla`, `IPv4`, `IPv6`, `Isbn`, `Latitude`, `Longitude`, `MacAddress`, `PhoneNumber`, `Rgb`, `Rgba`, `UtcOffset`.
- `HotChocolate.Types.NodaTime` with `AddNodaTime()`: NodaTime-backed `DateTime`, `Duration`, `LocalDate`, `LocalDateTime`, `LocalTime` (nanosecond precision).
- `BindRuntimeType<TRuntime, TScalar>()` and `AddTypeConverter<TFrom, TTo>()` reuse scalars for other .NET types.
- Custom scalars: `ScalarType<TRuntime, TLiteral>` with `OnCoerceInputLiteral`, `OnCoerceInputValue`, `OnCoerceOutputValue`, `OnValueToLiteral`. Throw `LeafCoercionException`. Constructor DI supported.
- Helper bases: `IntegerTypeBase<T>` and `FloatTypeBase<T>` (min/max range), `RegexType` (pattern scalars, can be instantiated directly).
- `HotChocolate.Types.Json` package: `AddJsonSupport()` and `descriptor.Field(...).FromJson()` resolve fields from a `JsonElement` parent, plus a `@fromJson` schema directive (source only).
- Spatial (experimental): `HotChocolate.Spatial` with `AddSpatialTypes()` maps NetTopologySuite geometries to GeoJSON output types (`GeoJSONPointType` and others), GeoJSON input types, `Geometry` scalar. `HotChocolate.Data.Spatial` adds `AddSpatialFiltering()` (`distance`, `contains`, `touches`, `intersects`, `overlaps`, `within` and negations) and `AddSpatialProjections()`.

## Interfaces and unions

- C# interfaces and abstract classes map to GraphQL interfaces with `[InterfaceType("Name")]`. Implementing types must be registered (`AddType<T>()`).
- Interfaces implementing interfaces.
- Default resolvers on interfaces: `[InterfaceType<IMessage>] static partial class` fields are inherited by all implementing object types, which can override them.
- Unions from marker interfaces or abstract classes with `[UnionType("Name")]`, or `UnionType` / `UnionType<T>` code-first.
- `StripLeadingIFromInterface` option. `IsOfType` and `ResolveAbstractType` hooks in code-first.

## Mutations

- `[MutationType]` classes. Top-level mutation fields run serially.
- Mutation conventions: `AddMutationConventions(applyToAllMutations: true)` or `[UseMutationConvention]` per field. Generates `{Name}Input` with one `input` argument and `{Name}Payload`. Opt out with `[UseMutationConvention(Disable = true)]`. Existing input or payload types are respected.
- `MutationConventionOptions`: `InputArgumentName`, `InputTypeNamePattern`, `PayloadTypeNamePattern`, `PayloadErrorTypeNamePattern`, `PayloadErrorsFieldName`, `ApplyToAllMutations`. Per-field `InputTypeName`, `PayloadTypeName`.
- Typed domain errors: `[Error(typeof(MyException))]` catches the exception and adds an `errors: [XError!]` union to the payload. `Exception` suffix rewritten to `Error`. Mapping by direct exception, static `CreateErrorFrom(ex)` factory, constructor taking the exception, or `IPayloadErrorFactory<TError, TException>` with DI. `AggregateException` returns many errors.
- `AddErrorInterfaceType<T>()` replaces the default `Error { message }` interface (for example to add `code`).
- Query conventions: `AddQueryConventions()` applies `[Error]` to query fields and returns a union of the result and error types. `FieldResult<TResult, TError...>` return type (source only).
- `AddQueryFieldToMutationPayloads(options => { QueryFieldName, MutationPayloadPredicate })` adds `query: Query` to payloads.
- No auto-generated CRUD mutations from an ORM model.

## Subscriptions

- `[SubscriptionType]` classes with `[Subscribe]` and `[EventMessage]` parameter. Method body can transform the payload.
- Publish with `ITopicEventSender.SendAsync(topic, message)`. Topic defaults to the method name.
- `[Topic("{arg}")]` dynamic topics from argument values, `[Topic("Static")]` fixed topics, multi-placeholder topics.
- `[Subscribe(With = nameof(Method))]` custom subscribe resolver returning `ValueTask<ISourceStream<T>>` via `ITopicEventReceiver.SubscribeAsync<T>`.
- Providers: `AddInMemorySubscriptions()`, `AddRedisSubscriptions(...)` (StackExchange.Redis), `AddNatsSubscriptions()` (NATS v2 client, core pub/sub), `AddPostgresSubscriptions(...)` (LISTEN/NOTIFY), `AddRabbitMQSubscriptions(...)` (source and options table only).
- `SubscriptionOptions`: `TopicPrefix`, `TopicBufferCapacity` (64), `TopicBufferFullMode` (`DropOldest`, `DropNewest`, `DropWrite`).
- `HotChocolate.Subscriptions.Serializers.Newtonsoft` alternative message serializer (source only).
- Transports: WebSocket with `graphql-transport-ws` (graphql-ws) and legacy `graphql-ws` (subscriptions-transport-ws), Server-Sent Events (graphql-sse, content negotiated), multipart and JSON Lines.
- `@skip`/`@include` disallowed on root subscription fields (v16).
- No built-in subscription filtering by predicate beyond topic naming and the resolver body.

## Resolvers, middleware, DI

- Async resolvers with `CancellationToken`.
- Field middleware: `descriptor.Use(next => async context => ...)`, class middleware with `InvokeAsync(IMiddlewareContext)` (constructor and method DI), `Use<T>()`, factory overload. Attribute middleware by subclassing `ObjectFieldDescriptorAttribute` with `[CallerLineNumber]` order. `context.Result` short-circuits the resolver.
- Built-in middleware attributes: `[UsePaging]`, `[UseConnection]`, `[UseOffsetPaging]`, `[UseProjection]`, `[UseFiltering]`, `[UseSorting]`, `[UseFirstOrDefault]`, `[UseSingleOrDefault]`, `[UseDataLoader]`, `[UseRequestScope]`, `[UseResolverScope]`, `[UseMutationConvention]`.
- Middleware order rule `UsePaging > UseProjection > UseFiltering > UseSorting`. Checked at schema build (`ValidatePipelineOrder`) and by analyzer HC0100.
- DI scopes: a new service scope per async resolver and per DataLoader dispatch by default. `DefaultQueryDependencyInjectionScope` (`Resolver`), `DefaultMutationDependencyInjectionScope` (`Request`). Per-field `[UseRequestScope]` / `.UseRequestScope()`.
- Keyed services: `[Service("key")]`, `[Service(EnumKey)]`, `[FromKeyedServices]`, custom `ServiceAttribute` subclasses. `ctx.Service<T>(key)`.
- `RegisterDbContextFactory<T>()` injects `DbContext` from a factory (`HotChocolate.Data.EntityFramework`).
- Swap the DI container per request with `OperationRequestBuilder.SetServices(...)` in interceptors.
- Request middleware: `UseRequest(next => async context => ..., key:, before: WellKnownRequestMiddleware.X)`. Pipeline stages `UseOperationVariableCoercion`, `UseOperationCache`, `UseOperationCompiler`, `UseSkipWarmupExecution`, `UseConcurrencyGate`, `UseOperationExecution`.
- Global state per request (`[GlobalState("key")]`, custom subclasses), scoped state (`[ScopedState]`) and local state (`[LocalState]`).
- `IExecutable<T>` abstraction over data sources (`ToListAsync`, `FirstOrDefaultAsync`, `SingleOrDefaultAsync`, `Print`). Returned executables are treated as lists.

## Batching (DataLoader, batch resolvers)

- Source-generated DataLoaders: `[DataLoader]` on a static method. Kind from signature: `Dictionary<TKey, TValue>` (batch), `ILookup<TKey, TValue>` (group, empty array on miss), single key (cache). Generates `I{Name}DataLoader` and `{Name}DataLoader`.
- `[DataLoader<IMyContract>]` with a custom interface deriving from `IBatchDataLoader<K,V>` or `ICacheDataLoader<K,V>`. Extra interface members implemented in a partial class.
- `[DataLoaderGroup("Name")]` groups DataLoaders into one injectable batching context.
- `[assembly: DataLoaderModule("Name")]` generates `services.AddNameDataLoaders()`. `[DataLoaderDefaults]` assembly defaults.
- Options: `Name` (positional), `MaxBatchSize` (1024, split batches dispatched concurrently), `ServiceScope` (`DataLoaderScope`, `OriginalScope`, `Default`), `AccessModifier` (`Public`, `Internal`, `PublicInterface`), `Lookups` (derive extra cache keys from loaded values).
- Extra DataLoader parameters: services, `CancellationToken`, `[DataLoaderState]`, `PagingArguments`, `QueryContext<T>`, `ISelectorBuilder`.
- `LoadAsync`, `LoadRequiredAsync` (throws `KeyNotFoundException`), `Branch<TState>(...)`, `GetState<T>()`, `ClearCache()`, `.With(queryContext)` to branch per projection.
- Dispatch when no resolver work is ready (not per level). A settle window was added in 16.6. Per-request cache and promise cache (root page results published with `PublishRootFieldPagesToPromiseCache`).
- Manual `BatchDataLoader<K,V>`, `CacheDataLoader<K,V>` classes with `LoadBatchAsync`.
- Analyzer diagnostics HC0122 to HC0133 for DataLoader misuse.
- Batch resolvers: `[BatchResolver]` with `[Parent] List<T>` and list arguments (one entry per parent). Code-first `ResolveBatch(contexts => ...)` returning `ResolverResult.Ok/Fail` for per-parent errors. `ResolveBatchWith<T>` (sync only). Field middleware does not run on batch resolver fields.

## Filtering, sorting, projections (HotChocolate.Data)

- `AddFiltering()` plus `[UseFiltering]` generates `{Type}FilterInput` and a `where` argument. Works on `IQueryable` and `IEnumerable` (expression trees).
- String ops: `eq`, `neq`, `contains`, `ncontains`, `in`, `nin`, `startsWith`, `nstartsWith`, `endsWith`, `nendsWith`. Boolean `eq`, `neq`. Comparable (numbers, `Guid`, `DateTime`, `DateTimeOffset`, `TimeSpan`): `eq`, `neq`, `in`, `nin`, `gt`, `ngt`, `gte`, `ngte`, `lt`, `nlt`, `lte`, `nlte`. Enum `eq`, `neq`, `in`, `nin`. Nested object filters. List filters `all`, `none`, `some`, `any`. `and` / `or` combinators.
- No built-in case-insensitive or `like` operator. Docs show how to add one with a custom `QueryableStringOperationHandler`.
- `FilterInputType<T>` with `BindFieldsExplicitly`, `Field(...)`, `AllowAnd(false)`, `AllowOr(false)`. Custom operation types (`StringOperationFilterInputType`, `DefaultFilterOperations`). Custom scalar filter bindings `BindRuntimeType<string, EmailAddressOperationFilterInputType>()`.
- Filter conventions: `FilterConvention`, `FilterConventionExtension`, `ArgumentName("filter")`, `BindRuntimeType<User, UserFilterType>()`, `Operation(id).Name(...)` to rename ops globally, custom op ids above 1024, `Provider<T>()`.
- Filter providers: `QueryableFilterProvider`, field handlers (`FilterFieldHandler`, `FilterOperationHandler`, `CanHandle`, `TryHandleEnter`, `TryHandleLeave`), visitor context with scopes. `QueryableFilterProviderExtension`.
- `MaxAllowedFilterOperations(64)` per filter argument (error `HC0117`). `null` disables.
- Scoped conventions: `AddMongoDbFiltering("scope")` with `[UseFiltering(Scope = "scope")]` to mix providers.
- `AddSorting()` plus `[UseSorting]` generates `{Type}SortInput` and an `order: [...]` argument with `ASC` / `DESC`. Nested and multi-field sorting. `SortInputType<T>`, `DefaultSortEnumType`, `SortConvention`, `SortConventionExtension`, `ArgumentName`, `DefaultBinding<T>()`.
- `NullOrdering` (`Unspecified`, `NativeNullsFirst`, `NativeNullsLast`) with auto detection for known EF Core providers.
- Projections: `AddProjections()` plus `[UseProjection]` turns the selection set into a LINQ `Select` (SQL column pruning, joins).
- v16 recommended path: `QueryContext<T>` parameter (`Selector`, `Predicate`, `Sorting`) applied with `query.With(...)` in order filter, sort, project. `With(query, sort => sort.IfEmpty(...).AddAscending(...))` for default order. `query.Include(x => x.Id)` forces columns. `QueryContext<T>` works in services and DataLoaders. Analyzer HC0099 forbids mixing with `[UseProjection]`.
- `[IsProjected]` (always project), `[IsProjected(false)]` (never project), `.IsProjected()` descriptor.
- `HotChocolate.Execution.Projections`: selection-to-expression builder used by DataLoaders `.Select(selection)` (source only).
- `[UseFirstOrDefault]` / `[UseSingleOrDefault]` turn a list resolver into a single object field.
- No aggregation (`count`, `sum`, `groupBy`) argument grammar beyond `totalCount` on connections.
- Integrations: EF Core (`HotChocolate.Data.EntityFramework`), MongoDB (`HotChocolate.Data.MongoDb`, `AsExecutable()`, `AddMongoDbFiltering/Sorting/Projections/PagingProviders`, translated to BSON), Marten (`AddMartenFiltering`, `AddMartenSorting`), RavenDB (`HotChocolate.Data.Raven`, `AddRaven...` extensions, only mentioned in a package list in the docs).

## Pagination

- Cursor connections per Relay spec. v16 path: `AddPagingArguments()`, `PagingArguments` parameter, `ToPageAsync(pagingArgs)` returning `Page<T>`, wrap in `PageConnection<T>`. `ToPageAsync` lives in `GreenDonut.Data.EntityFramework`, `.Raven`, `.Marten`, `.Mongo`.
- `[UseConnection(MaxPageSize, DefaultPageSize, IncludeTotalCount, ConnectionName, EnableRelativeCursors)]`. Older `[UsePaging]` on `IQueryable` still works.
- `PagingOptions`: `MaxPageSize` (50), `DefaultPageSize` (10), `IncludeTotalCount`, `AllowBackwardPagination`, `RequirePagingBoundaries`, `InferConnectionNameFromField`, `IncludeNodesField`, `EnableRelativeCursors`, `ProviderName`, `NullOrdering`. Global `ModifyPagingOptions`.
- Relative cursors: `pageInfo { forwardCursors { page cursor } backwardCursors { ... } }` for numbered page bars (implementation-first only).
- Custom connections by subclassing `PageConnection<T>` or `ConnectionBase<TNode, TEdge, TPageInfo>` with `IEdge<T>`. Generic names with `[GraphQLName("{0}Connection")]`.
- Batched paging in DataLoaders: `ToBatchPageAsync(keySelector, pagingArgs)`.
- `Page<T>.Create(...)`, `Page<T>.Empty`, `CreateCursor(index)`, `CreateStartCursor()`, `CreateEndCursor()`.
- Offset paging: `[UseOffsetPaging]` with `skip` / `take` and `CollectionSegment` (source only in v16 docs, only in old migration guides). `AddQueryableOffsetPagingProvider`.
- Paging writes `@listSize` cost metadata automatically.

## Relay and global IDs

- `[ID]` on output fields serializes Base64 global IDs (type name plus raw id). `[ID<Product>]` / `[ID("Product")]` for foreign keys. Same attribute on inputs decodes and can enforce the type.
- `IIdSerializer.Serialize(schemaName, typeName, id)` for manual use. `NodeIdValueSerializer` generated for custom ID types. Complex/composite IDs via `AddTypeConverter`.
- `AddGlobalObjectIdentification(o => ...)` adds `Node`, `node(id:)`, `nodes(ids:)`. Options `RegisterNodeInterface`, `AddNodeField`, `AddNodesField`, `EnsureAllNodesCanBeResolved`, `MaxAllowedNodeBatchSize` (50), `MarkNodeFieldAsLookup` (Fusion).
- `[Node]` with static `Get`/`GetAsync`/`Get{Type}` resolver, `[Node(IdField = ...)]`, `[NodeResolver]`, `[Node(NodeResolverType = ..., NodeResolver = ...)]`. Code-first `ImplementsNode().IdField(...).ResolveNode(...)` / `ResolveNodeWith<T>`.

## Authorization and authentication

- Uses ASP.NET Core authentication (JWT, cookies, any scheme). `ClaimsPrincipal` injectable into resolvers. `context.GetUser()`.
- `HotChocolate.AspNetCore.Authorization`: `AddAuthorization()` registers `@authorize`. `[Authorize]` (from `HotChocolate.Authorization`) on types, fields and resolvers. `Roles = [...]` (any match), `Policy = "..."` (repeatable, all must pass). Code-first `.Authorize(...)`.
- `[AllowAnonymous]` removes other requirements on a field.
- `AuthorizationHandler<TRequirement, IResolverContext>` gives policy handlers access to GraphQL context.
- `ApplyPolicy` enum: `BeforeResolver`, `AfterResolver`, `Validation` (check at validation time). Exposed as `[Authorize(Apply = ...)]` (source only in v16 docs).
- Errors `AUTH_NOT_AUTHENTICATED`, `AUTH_NOT_AUTHORIZED` with field set to `null`.
- `MapGraphQL().RequireAuthorization()` for whole-endpoint auth. Split with `MapGraphQLHttp` plus `MapNitroApp`.
- Open Policy Agent: `HotChocolate.AspNetCore.Authorization.Opa` with `AddOpaAuthorization`, `AddOpaQueryRequestExtensionsHandler`, `AddOpaResultHandler` (source only).
- Analyzer HC0106 flags `Microsoft.AspNetCore.Authorization.AuthorizeAttribute`.
- No per-viewer schema visibility (hiding fields from introspection per user) beyond `@requiresOptIn`, internal directives and introspection on/off. No row-level permission DSL.

## Security, limits and cost analysis

- Default security (unless `disableDefaultSecurity: true`): cost analysis on, introspection off outside Development, `MaxAllowedFieldCycleDepthRule` on outside Development.
- Cost analysis per the IBM Cost Spec draft (`HotChocolate.CostAnalysis`): `@cost(weight:)` and `@listSize(assumedSize, slicingArguments, slicingArgumentDefaultValue, sizedFields, requireOneSlicingArgument)`. `[Cost(100)]`, `[ListSize(...)]`, `.Cost()`, `.ListSize()`.
- Field cost and type cost. Default weights (object fields 1, leaf 0, non-pure resolver 10, input objects 1). `MaxFieldCost` (1,000), `MaxTypeCost` (10,000 in 16.7), `EnforceCostLimits`, `SkipAnalyzer`, `ApplyCostDefaults`, `ApplySlicingArgumentDefaultValue`, `DefaultResolverCost`, `DefaultListSize` (50), `CostPlanCacheSize`, `MaxResponseSize`, `CaseBudget`, `CaseBudgetExceededBehavior` (`EvaluatePerRequest`, `Overestimate`). Filtering and sorting cost options (`DefaultFilterArgumentCost`, `DefaultFilterOperationCost`, `DefaultExpensiveFilterOperationCost`, `DefaultSortArgumentCost`, `DefaultSortOperationCost`).
- Cost uses coerced variables, `@skip`/`@include` values and sums across variable batches. Error `HC0047`.
- `GraphQL-Cost: report` (execute and report) and `GraphQL-Cost: validate` (report only) request headers. `extensions.operationCost { fieldCost typeCost maxResponseSize }`.
- `context.GetCostMetrics()`, `TryGetCostAnalysisResult(out result)` with `CostPlan` and `CostEstimate` list.
- Per-request limits: `OperationRequestBuilder.SetCostOptions(new RequestCostOptions(...))` (for example by user role).
- Parser limits (`ModifyParserOptions`): `MaxAllowedFields` (2048), `MaxAllowedDirectives` (4 per location), `MaxAllowedRecursionDepth` (200), `MaxAllowedNodes`, `MaxAllowedTokens`, `IncludeLocations`.
- Validation limits: `AddMaxExecutionDepthRule(n, skipIntrospectionFields:, allowRequestOverrides:)`, `MaxAllowedFragmentVisits` (1,000), `SetMaxAllowedFieldMergeComparisons` (100,000), `AddMaxAllowedFieldCycleDepthRule(defaultCycleLimit:, coordinateCycleLimits:)` per schema coordinate, `SetMaxAllowedValidationErrors` (5), `SetIntrospectionAllowedDepth(maxAllowedOfTypeDepth:, maxAllowedListRecursiveDepth:)`.
- Execution limits: `ExecutionTimeout` (30 s), `MaxConcurrentExecutions` concurrency gate (64), `MaxAllowedIncludeConditions` and `MaxAllowedDeferConditions` (1,024, 16.7), request size `maxAllowedRequestSize` (about 20 MB), WebSocket `MaxAllowedMessageSize`.
- Introspection: `AllowIntrospection(false)`, per-request `requestBuilder.AllowIntrospection()`, `SetIntrospectionNotAllowedMessage(...)`. Schema still downloadable at `/graphql/schema.graphql`.
- CSRF: `EnforceGetRequestsPreflightHeader`, `EnforceMultipartRequestsPreflightHeader` (`GraphQL-Preflight` header).
- FIPS: switch document hashing to SHA256.

## Persisted operations (trusted documents)

- `UsePersistedOperationPipeline()`. Storage: `AddFileSystemOperationDocumentStorage(dir)` (`{hash}.graphql`), `AddRedisOperationDocumentStorage`, `AddAzureBlobStorageOperationDocumentStorage`, `AddInMemoryOperationDocumentStorage`.
- Hash providers: `AddMD5DocumentHashProvider` (default), `AddSha1DocumentHashProvider`, `AddSha256DocumentHashProvider(HashFormat.Hex|Base64)`.
- `PersistedOperations.OnlyAllowPersistedDocuments = true`. Per-request bypass `AllowNonPersistedOperation()`.
- Automatic persisted queries (Apollo APQ protocol): `UseAutomaticPersistedOperationPipeline()`.
- `MapGraphQLPersistedOperations("/graphql/persisted", requireOperationName:)` gives REST-like GET/POST URLs per operation id and name. Useful for CDN caching.
- Nitro client registry (paid) for versioned operation publishing and validation.
- Warmup requests (`MarkAsWarmupRequest`) skip persisted-operation checks.

## Errors

- Exceptions become field errors with "Unexpected Execution Error" unless `IncludeExceptionDetails` (default only with debugger attached).
- `AddErrorFilter(error => ...)` / `IErrorFilter` rewrite errors. `ErrorBuilder.FromError(...)`, `SetMessage`, `SetCode`, immutable `WithMessage`, `WithCode`, `RemoveExtension`.
- `GraphQLException` (sent as is), with `ErrorBuilder` for codes and extensions, or many errors.
- Type converter errors now reach error filters with code `HC0001`, `coordinate` and `inputPath` extensions (v16).
- Error handling mode: `ModifyRequestOptions(o => o.DefaultErrorHandlingMode = ErrorHandlingMode.Null)` stops null propagation. Requests can send `onError` (`PROPAGATE` or `NULL`) per the GraphQL `onError` proposal (parser support in `Language.Web`).
- Typed errors as data with mutation conventions and query conventions (see Mutations).
- HC error codes documented throughout (`HC0018` non-null violation, `HC0020` APQ not found, `HC0046` introspection not allowed, `HC0047` cost, `HC0082` slicing, `HC0117` filter ops).

## Directives

- Custom directives: `[DirectiveType(DirectiveLocation.X, IsRepeatable = true)]` class with public properties as arguments, or `DirectiveType<T>`. `descriptor.Directive(new MyDirective { ... })` typed application.
- Directive middleware: `descriptor.Use((next, directive) => context => ...)`. Executable directives in queries become a resolver pipeline in directive order (type, then field, then query).
- Directives on directive definitions (`DIRECTIVE_DEFINITION` location), deprecated directives, `extend directive`. Introspection `__Directive.isDeprecated`, `__Schema.directives(includeDeprecated:)`, `appliedDirectives` on `__Directive` (16.6).
- `EnableDirectiveIntrospection`, `DirectiveVisibility`, `Internal()` directives hidden from the SDL.
- Built-ins beyond spec: `@defer`, `@stream`, `@oneOf`, `@specifiedBy`, `@requiresOptIn`, `@tag`, `@cost`, `@listSize`, `@cacheControl`, `@authorize`, composite schema directives (`@lookup`, `@is`, `@require`, `@internal`, `@shareable`, `@inaccessible`, `@key`/`@entityKey`, `@provides`, `@external`, `@override`, `@eventStream`, `@eventCursor`, `@serializeAs`).

## Schema evolution

- `@deprecated` on fields, arguments, input fields, enum values, directives. `[GraphQLDeprecated]` or `[Obsolete]`. Required args and inputs without default cannot be deprecated.
- Deprecated object types (RFC #997) behind `EnableObjectDeprecation`. Only `[GraphQLDeprecated]` works on classes. `__Type.isDeprecated`, `types(includeDeprecated:)`.
- `@requiresOptIn(feature:)` behind `EnableOptInFeatures`: `[RequiresOptIn("x")]`, `.RequiresOptIn()`. Hidden from introspection unless `includeOptIn: [...]`. `__schema { optInFeatures optInFeatureStability { feature stability } }`. `OptInFeatureStability("x", "experimental")`.
- Schema export downgrade: `--spec-version october-2021|september-2025` and `?spec-version=` on schema endpoints strip newer SDL features.
- `@semanticNonNull` schema variant: `MapGraphQLSemanticNonNullSchema()`, `--semantic-non-null`, `SchemaFormatterOptions.RewriteToSemanticNonNull`.

## Incremental delivery

- `@defer` (`EnableDefer`) over `multipart/mixed`, `text/event-stream` or `application/jsonl`. Wire format v0.2 (`pending`/`incremental`/`completed`) default, v0.1 legacy. Client picks with `Accept: ...; incrementalSpec=v0.1`. Server default with `AddHttpResponseFormatter(incrementalDeliveryFormat: IncrementalDeliveryFormat.Version_0_1)`.
- `@stream` (`EnableStream`): see "Docs and code disagree".

## HTTP and transport

- `MapGraphQL(path)` bundles HTTP GET/POST/QUERY, multipart, WebSocket, `?sdl`, schema file and Nitro. Separate `MapGraphQLHttp`, `MapGraphQLWebSocket`, `MapGraphQLSchema`, `MapNitroApp`, `MapGraphQLPersistedOperations`, `MapGraphQLSemanticNonNullSchema`.
- `GraphQLServerOptions` via `ModifyServerOptions` or per endpoint `WithOptions`: `EnableGetRequests`, `AllowedGetOperations`, `EnableQueryRequests`, `EnableMultipartRequests`, `EnableSchemaRequests`, `EnableSchemaFileSupport`, preflight flags, `Batching`, `MaxBatchSize`, `Sockets`, `Tool`.
- GraphQL over HTTP spec with `HttpTransportVersion` (`Latest`, `Legacy`, `Draft20250508`, `Draft20260903`). `application/graphql-response+json`, `application/json`, `multipart/mixed`, `text/event-stream`, `application/jsonl`. `Accept` quality values honored (16.7).
- HTTP QUERY method (RFC 10008) for queries (16.7, off by default).
- Batching: variable batching (`variables: [...]`, `variableIndex`) on by default, request batching (JSON array, `requestIndex`) off by default, operation batching (`?batchOperations=`). Results streamed out of order.
- `DefaultHttpResponseFormatter` subclass, `OnDetermineStatusCode` override. JSON options `NullIgnoreCondition`, `Indented`.
- File uploads: GraphQL multipart request spec, `UploadType` scalar, `IFile` (`Name`, `Length`, `OpenReadStream()`), `UploadValueNode`. `FormOptions` size limits with codes `HC0135`, `HC0136`, `HC0010`.
- Interceptors: `IHttpRequestInterceptor` / `DefaultHttpRequestInterceptor.OnCreateAsync`, delegate form `AddHttpRequestInterceptor((ctx, executor, builder, ct) => ...)`. `ISocketSessionInterceptor` with `OnConnectAsync` (accept or reject with `ConnectionStatus`), `OnRequestAsync`, `OnResultAsync`, `OnCompleteAsync`, `OnPingAsync`, `OnPongAsync`, `OnCloseAsync`.
- `OperationRequestBuilder`: global state, `SetServices`, `AllowIntrospection`, `AllowNonPersistedOperation`, `SkipQueryCaching`, `SetCostOptions`, `MarkAsWarmupRequest`.
- Azure Functions hosting: `HotChocolate.AzureFunctions` and `.IsolatedProcess` with `AddGraphQLFunction()` (source only).
- Client libraries in repo: `HotChocolate.Transport.Http` (`GraphQLHttpClient`), `HotChocolate.Transport.Sockets.Client`, `HotChocolate.Utilities.Introspection` (`IntrospectionClient` to download a schema) (source only).

## Caching

- HTTP cache headers: `HotChocolate.Caching`, `AddCacheControl()`, `UseQueryCache()`, `[CacheControl(maxAge, SharedMaxAge =, Scope =, Vary = [...])]` / `@cacheControl`. Merges the strictest policy over the selection. `ModifyCacheControlOptions` (`Enable`, `DefaultMaxAge`, `DefaultScope`, `ApplyDefaults`). `SkipQueryCaching()` per request.
- Document cache and compiled operation cache (`OperationDocumentCacheSize`, `PreparedOperationCacheSize`).
- No server-side response or field result cache in Hot Chocolate itself. `HotChocolate.Caching.Memory` is an internal LRU cache helper (source only).

## Observability

- Diagnostic listeners: `ServerDiagnosticEventListener`, `ExecutionDiagnosticEventListener`, `DataLoaderDiagnosticEventListener` with `AddDiagnosticEventListener<T>()`. Scoped events return `IDisposable`. `EnableResolveFieldValue` opt in. Events for parsing, validation, cost, variable coercion, compile, execute, resolver, subscription events, caches, executor created/evicted, WebSocket session and connection init (16.7).
- OpenTelemetry: `HotChocolate.Diagnostics`, `AddInstrumentation(o => { Scopes = ActivityScopes.All, RequestDetails = ... })`, `AddHotChocolateInstrumentation()`. Span attributes per the GraphQL OTel semantic conventions (`graphql.operation.type`, `graphql.document.hash`, `graphql.dataloader.batch.size` ...). Custom `ActivityEnricher`.
- Nitro (paid) operation and service monitoring over OpenTelemetry.

## Tooling, startup, testing

- Templates: `dotnet new install HotChocolate.Templates`, `dotnet new graphql`.
- CLI: `app.RunWithGraphQLCommands(args)` returns an exit code. `dotnet run -- schema export --output --schema-name --semantic-non-null --spec-version`.
- `ExportSchemaOnStartup("./schema.graphql")`.
- Eager initialization, `AddWarmupTask(...)` / `IRequestExecutorWarmupTask` (`ApplyOnlyOnStartup`), warm caches on hot reload while the old executor serves traffic.
- Roslyn analyzers (`HotChocolate.Types.Analyzers`): HC0092 to HC0106 and HC0122 to HC0133.
- Multiple named schemas per host: `AddGraphQL("Name")`, `MapGraphQL(path, schemaName)`.
- Testing: in-process execution with `IRequestExecutor.ExecuteAsync`, `BuildSchemaAsync()`, `ExecuteRequestAsync` helpers, `result.ExpectOperationResult()`. Snapshot library `CookieCrumble` in the repo. No dedicated testing guide in v16 docs.
- Agent skills for AI coding assistants (`website/content/docs/skills`).

## Adapters

- MCP: `HotChocolate.Adapters.Mcp`, `AddMcp()`, `MapGraphQLMcp(pattern, schemaName)` (Streamable HTTP at `/graphql/mcp`). Tools and prompts come from an `IMcpStorage` (`AddMcpStorage`) or from Nitro feature collections. Hot reload of tool sets.
- OpenAPI/REST: `HotChocolate.Adapters.OpenApi`, `AddOpenApiDefinitionStorage`, `MapOpenApiEndpoints()`, `AddGraphQLTransformer()`. Operations annotated with `@http(method:, route:, queryParameters:)`, `@body` on variables, `@responseBody` (16.6). Shared fragment documents as models. Hot reload. `OpenApiDiagnosticEventListener`. Works on Fusion gateways too.

## Federation

- Apollo Federation subgraph support: `HotChocolate.ApolloFederation`, `AddApolloFederation()`. Federation versions 1.0 and 2.0 to 2.7. Attributes `[Key]`, `[Shareable]`, `[External]`, `[Provides]`, `[Requires]`, `[Override]`, `[Inaccessible]`, `[InterfaceObject]`, `[Authenticated]`, `[RequiresScopes]`, `[Policy]`, `[ComposeDirective]`, `[Contact]`, `[Link]`, `[ExtendServiceType]` (source only in HC docs, covered in Fusion docs).
- GraphQL Composite Schemas spec subgraph attributes in core (`HotChocolate.Types.Composite`): `[Lookup]`, `[Is]`, `[Require]`, `[Internal]`, `[Shareable]`, `[Inaccessible]`, `[EntityKey]`, `[EventStream]`, `[EventCursor]`. `AddSourceSchemaDefaults()`.
- Schema stitching is gone. I think it was removed after v13. No stitching package is in the repo and Fusion has a "migrating from schema stitching" guide.

## Fusion (gateway, brief)

- Gateway implementing the GraphQL Composite Schemas spec. Build-time composition into a `.far` archive. `AddGraphQLGateway()` (`AddFusionGateway` also appears), `AddInMemoryConfiguration`, `AddHttpClientConfiguration`. CLI and Aspire integration.
- Subgraphs can be GraphQL, OpenAPI REST or gRPC. Apollo Federation connector (16.5) to use Apollo subgraphs.
- Directives `@key`, `@lookup`, `@is`, `@require`, `@interfaceObject`, `@implement`, `@shareable`, `@provides`, `@external`, `@override`, `@internal`, `@inaccessible`.
- Federated event streams for subscriptions with `@eventStream`/`@eventCursor` and brokers NATS, Kafka, Azure Event Hubs, Amazon SQS, Redis. Client-resumable subscriptions. SSE subscriptions.
- Gateway cost analysis, request limits, cache control merging, batching (subgraph alias batching 16.6), auth, MCP and OpenAPI adapters.
- Open PRs: Fusion WebSocket support, rename gateway to router, `Query.nodes` option.

## Green Donut (brief)

- DataLoader library used by Hot Chocolate (`GreenDonut`, `GreenDonut.Abstractions`). Batch, group and cache loaders, branching, state, promise cache, diagnostics.
- `GreenDonut.Data`: `Page<T>`, `PagingArguments`, `QueryContext<T>`, `SortDefinition<T>`, keyset paging with `ToPageAsync` and `ToBatchPageAsync` for EF Core, Marten, Mongo, Raven. Usable outside GraphQL in services.

## Strawberry Shake (client, brief)

- .NET GraphQL client that generates typed C# code from `.graphql` operations. Reactive store with entity normalization and cache invalidation, persisted state, persisted operations (build-time extraction), subscriptions, custom scalars, auth helpers. Docs only cover migration up to v15.

## Nitro (IDE and platform, brief)

- Formerly Banana Cake Pop. Served by `MapGraphQL`/`MapNitroApp` with `NitroAppOptions` (`Enable`, `GraphQLEndpoint`, `UseBrowserUrlAsGraphQLEndpoint`, `Document`, `UseGet`, `HttpHeaders`, `IncludeCookies`, `Title`, `DisableTelemetry`, `GaTrackingId`). Desktop and web app.
- Commercial control plane (free tier, paid from $20/month): schema registry, client registry, stages, deployments, Fusion config publishing, operation reporting, OpenTelemetry monitoring, MCP and OpenAPI feature collections, CLI (`nitro`), agent tooling. Server integration `ChilliCream.Nitro.HotChocolate`, `AddNitro().AddDefaults()`.

## Not supported or not in scope

- No ORM model-to-CRUD generation (no auto create/update/delete mutations). Mutations are hand-written resolvers.
- No declarative input validation rules (length, regex, range) on arguments. Only custom scalars or resolver code.
- No per-user schema visibility or field hiding from introspection (only opt-in features, internal directives and global introspection switch).
- No server-side result cache. Only HTTP cache headers and operation/document caches.
- No aggregation arguments (`count`, `sum`, `groupBy`) on filtered lists.
- No case-insensitive string filter out of the box.
- No schema stitching (replaced by Fusion).
- F# support moved out of the project (v15).
- `Upload` scalar does not work through a gateway (docs).
- Batch resolver fields cannot use paging, filtering, sorting or projection middleware.
- Relative cursors only with implementation-first.

## Upcoming and unreleased work

- 16.7.0 (17 prereleases since 2026-08-28): cost plan compiler with coerced variables, `MaxResponseSize`, `CaseBudget`, HTTP QUERY method, `Draft20260903` transport version, `Accept` q-values, condition flags beyond 64 `@skip`/`@include`/`@defer` conditions, empty variable batches refused, new multipart limits, WebSocket connection init diagnostic event, GraphQL spec version export, SSE `complete` fix.
- Open PRs: `@stream` support (#10438), `IOperationRequestFactory<out T>` (#10394), Fusion WebSocket support (#10367), `InterfaceObjectAttribute`, conditional `totalCount` fix, `Vary: Accept` fix, Nitro telemetry CLI, Fusion gateway renamed to router.
- Cost limits summed across a whole request batch: planned, no target version (docs).
- Milestone `HC-17.0.0` exists. Docs note that unifying `[Obsolete]` and `[GraphQLDeprecated]` for object types is deferred to a future major.

## Docs and code disagree

- `@stream`: the docs intro says Hot Chocolate implements `@stream`, and `EnableStream` is listed as an option. In `Core/src/Types/Execution/Processing/Tasks/ResolverTask.Execute.cs` the stream execution branch is commented out, and PR #10438 "Add support for `@stream`" is still open. I think `@stream` is parsed and validated but not executed as a stream in 16.x.
- Global state API: `server/interceptors.md` and `server/global-state.md` use `requestBuilder.SetProperty(...)`, `SetProperties(...)`, `TryAddProperty`/`TrySetProperty`. `OperationRequestBuilder` in the code has `SetGlobalState`, `AddGlobalState`, `TryAddGlobalState`. No `SetProperty` method exists. The docs also name `context.GetGlobalValue<T>()`. The code has `GetGlobalStateOrDefault<T>()`.
- The docs on `main` describe 16.7 prerelease behavior as current (for example `MaxTypeCost` 10,000, `DefaultListSize` 50, `QUERY` method, `Draft20260903`). The latest stable 16.6.7 uses the older values (`MaxTypeCost` 1,000, unannotated lists size 1).
- `server/options.md` lists `EnableSemanticNonNull` as a schema option. The 15 to 16 guide says the feature was removed, and I found no `EnableSemanticNonNull` in the current source.
- `defining-a-schema/subscriptions.md` lists four providers (in-memory, Redis, NATS, Postgres). The code also ships `AddRabbitMQSubscriptions`, and `server/options.md` mentions RabbitMQ.
- The intro says there are two schema approaches (implementation-first and code-first). Schema-first (`AddDocumentFromString`, `AddResolver`, `BindRuntimeType`) still exists in code with no v16 page.
- Many shipped packages have no v16 docs page: Apollo Federation subgraph package, OPA authorization, Azure Functions hosting, query conventions, offset paging, `[IsSelected]`, `TypeInterceptor`, `HotChocolate.Types.Json`, RavenDB data integration, `[ExtendObjectType]` (only mentioned in passing), introspection and HTTP client packages.
- `server/files.md` still warns about uploads "to stitched services". Stitching no longer exists.
- `server/cache-control.md` repeats the section "How Hot Chocolate Assembles the Final Headers" twice with slightly different rules. `server/options.md` describes `CacheControlOptions.Enable` as "query result caching", while the cache-control page says it controls header generation.
- `defining-a-schema/scalars.md` links to `./object-types.md#explicit-types`. That anchor does not exist in `object-types.md`.

## Sources

Repo (shallow clone in `/tmp/hc-graphql-platform/`):
- https://github.com/ChilliCream/graphql-platform (`main` at `e8e1ece`, 2026-10-04)

Docs read (repo source of https://chillicream.com/docs/hotchocolate/v16, all 68 Hot Chocolate pages read except the 10 to 14 migration guides, which were skimmed):
- `website/content/docs/hotchocolate/` (index, get started, `defining-a-schema/*`, `resolvers/*`, `fetching-data/*`, `server/*`, `performance/*`, `security/*`, `adapters/*`, `migrating/migrate-from-14-to-15.md`, `migrate-from-15-to-16.md`, `migrate-from-16-6-to-16-7.md`).
- Skimmed for brief groups: `website/content/docs/fusion/*` (index, subscriptions, directives reference), `strawberryshake/index.md`, `nitro/index.md`, file lists of `mocha/` and `skills/`.
- https://chillicream.com/llms.txt (works, `text/plain`, links Markdown catalogs).

Changelog and status:
- GitHub releases API (16.0.0, 16.4.0, 16.5.0, 16.6.0, 16.6.7, 16.7.0-p.12/p.16/p.17 notes, release list and dates). GitHub repo API (stars, issues, push date). `gh pr list` (open PRs). Milestones API.

Source checked:
- `src/HotChocolate/*/src` project list and csproj descriptions.
- `Core/src/Types/SchemaOptions.cs`, `Core/src/Types/Types/Attributes/IsSelectedAttribute.cs`, `Core/src/Types/Execution/Processing/Tasks/ResolverTask.Execute.cs`, `Core/src/Execution.Abstractions/Execution/OperationRequestBuilder.cs`, `Core/src/Types/Extensions/ResolverContextExtensions.cs`, `Core/src/Types/Resolvers/IResolverContext.cs`, `Core/src/Authorization/ApplyPolicy.cs`, `Core/src/Types.Queries/*`, `Core/src/Types.Errors/*`, `Core/src/Types.Json/*`, `Core/src/Types/Types/Composite/Directives/*`, `Language/src/Language.Web/ErrorHandlingMode.cs`, `ApolloFederation/src/ApolloFederation/Types/Directives/*`, `AspNetCore/src/AspNetCore.Authorization.Opa/Extensions/*`, `AzureFunctions/src/*/Extensions/*`, `Data/src/Data/*` (folder layout), `GreenDonut/src/GreenDonut/*` (public API names).
