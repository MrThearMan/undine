# Candidates batch 5

Findings files: gqlgen, async-graphql, juniper, graphql-php, lighthouse, api-platform, wpgraphql.

## 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Execute operations without HTTP | Runs a GraphQL operation in process, without a request object. | gqlgen: `executor.New(es)`. wpgraphql: `graphql( [ 'query' => ..., 'variables' => ... ] )` (used for server-side rendering and tests) | partial: `execute_graphql_http_sync` and `execute_graphql_http_async` in `undine/execution.py` need a request | medium | Useful for scripts, Celery tasks and tests. I checked `undine/execution.py`. All entry functions take a request. |
| Schema-first (SDL-first) development | Writes the schema in SDL and generates or binds code to it. | gqlgen: `gqlgen generate` from `schema:` SDL files | missing | low | Undine is code-first and model-centric on purpose. |
| Merge many root type classes | Builds one root type from several classes, so each app can own its entrypoints. | async-graphql: `#[derive(MergedObject)]`, `#[derive(MergedSubscription)]` | partial: I think Python inheritance from several `RootType` classes may work. Not verified | medium | Large Django projects split code per app. A documented pattern would help. |
| Runtime schema building | Builds types and fields from data at runtime, not from classes. | async-graphql: `dynamic::Schema::build`, `dynamic::Object`, `dynamic::Field` | missing | low | Python classes can already be made at runtime with `type()`. |
| Validate without executing | Parses and validates an operation and returns its type, without running it. | juniper: `parse_and_validate()` (open PR #1392) | missing | low | Useful for CI checks of client documents. `check_schema_changes` covers schema drift only. |
| Scoped context for child fields | A resolver adds data to the context that only its child fields see. | graphql-php: `ScopedContext` interface (`clone()`) | missing | low | `info.context` is the request and shared by all fields. |
| Per-operation root value and context | Builds root value or context per operation with a callable. | graphql-php: `ServerConfig` `context` and `rootValue` as `fn (OperationParams, DocumentNode, string $operationType)` | partial: `ROOT_VALUE` setting is static | low | Lifecycle hooks can likely do it. Not verified. |
| Argument mapper | Maps coerced arguments to an object (DTO) once per field node. | graphql-php: `argsMapper`, `GraphQL::setDefaultArgsMapper()` | partial: `TypedDict` arguments and `@<input>.convert` | low | |
| Lazy type loading | Loads types on demand to cut schema build time in large schemas. | graphql-php: `SchemaConfig` `typeLoader`, callable fields and root types | missing | low | Undine builds the schema once per process. |
| Namespaced root fields | Groups root fields under a nested object, for example `mutation { blog { createPost } }`. | lighthouse: `@namespaced` | missing | low | Function entrypoint returning a `TypedDict` is close, but its fields are not entrypoints. |
| Single fetch by any unique argument | Fetches one object by a unique field, for example `slug`. Errors on more than one match. | lighthouse: `@find`, `@first`. wpgraphql: `post(id:, idType:)` with `ID`, `DATABASE_ID`, `URI`, `SLUG` | partial: `Entrypoint(QueryType)` fetches by `pk` only | medium | Common need, for example fetch by `slug`. A custom resolver works today. |
| Shared REST and GraphQL resource definition | One resource class drives both REST and GraphQL operations. | api-platform: `#[ApiResource(graphQlOperations: [...])]`, shared `provider`, `processor`, `security` | missing | low | Inventory lists no DRF integration. Undine is GraphQL only. Reusing DRF serializers for mutations would be the Django version. |
| Extend types from other apps | Adds fields to an existing type, renames or removes types and fields, from another app or plugin. | wpgraphql: `register_graphql_field`, `rename_graphql_field`, `deregister_graphql_field`, `register_graphql_interfaces_to_types` | missing | low | Python subclassing covers some cases. I think third-party Django apps cannot add fields to a project QueryType today. |
| Resolve object by URL | Resolves any public URL path to its object. | wpgraphql: `nodeByUri( uri: )`, `UniformResourceIdentifiable` | missing | low | A Django version could use `resolve()` and `get_absolute_url()`. Useful for headless CMS front ends. |

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Field selection helpers | Tells a resolver if a sub-field path is selected. Respects fragments, aliases and `@skip`/`@include`. | gqlgen: `graphql.FieldRequested(ctx, "a.b.c")`, `AnyFieldRequested`, `CollectFieldsCtx`, `CollectAllFields`. async-graphql: `Context::look_ahead()` (`Lookahead::field`, `exists`), `Context::field()` (`SelectionField`). juniper: `Executor::look_ahead()` (`LookAheadSelection`, `has_child`). graphql-php: `ResolveInfo::getFieldSelection`, `getFieldSelectionWithAliases`, `lookAhead()` (`QueryPlan`) | partial: the optimizer walks selections internally. No public helper | medium | Helps custom resolvers skip expensive work. I found no public helper in `undine/utils/graphql/utils.py`. |
| Runtime non-null per request | Makes a nullable field act as non-null for one request. | gqlgen: `graphql.MarkNonNull(ctx)`, `@priority(value: REQUIRED)` recipe | missing | low | Niche. `@semanticNonNull` covers a related need. |
| Derived field from one resolver | Adds a second field that reuses a resolver with a type conversion. | async-graphql: `#[graphql(derived(name, into, with))]` | partial: two `Field`s with the same `field_name` | low | |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative argument and input validators | Built-in validators such as `max_length`, `regex`, `minimum`, `max_items`, applied per argument or input field. | async-graphql: `#[graphql(validator(max_length = 5, regex = "..."))]`, `CustomValidator`, `list`. lighthouse: `@rules(apply:)`, `@rulesForArray`, `@validator(class:)` | partial: `@<input>.validate` hooks and `MUTATION_FULL_CLEAN` (model validators) | medium | Function entrypoint and field arguments have no validation hook I think. Model field validators only run with `full_clean`. |
| Upsert by identifying columns | Creates or updates a row found by chosen columns. Also inside nested mutations. | lighthouse: `@upsert(identifyingColumns:)`, `@upsertMany` | partial: `custom` kind acts as create or update by `pk` | medium | Maps to Django `update_or_create`. |
| Explicit nested relation operations | Client picks `connect`, `create`, `update`, `upsert`, `disconnect`, `delete`, `sync`, `syncWithoutDetaching` per relation. | lighthouse: nested mutation inputs for `BelongsTo`, `HasMany`, `BelongsToMany` and so on | partial: related mutations replace the set. `RelatedAction` handles unselected rows | medium | No add-only (`syncWithoutDetaching`) or remove-only operation. |
| Queued (background) mutation | Runs a mutation as a background job and returns at once. | lighthouse: `@async(queue:)`. api-platform: `messenger: true` (Symfony Messenger) | missing | low | Would need Celery or Django tasks (Django 6 `django.tasks`). |
| Built-in input sanitizers | Trims strings, turns empty strings into null, or hashes a value. | lighthouse: `@trim`, `@convertEmptyStringsToNull`, `@hash` | partial: `@<input>.convert` hook | low | Ready-made helpers only. |
| Soft-delete operations | Restore or force-delete soft-deleted rows. Filter by trashed state. | lighthouse: `@restore`, `@forceDelete`, `@trashed`, `@softDeletes` | missing | low | Django has no built-in soft delete. |
| Input and output DTOs for mutations | Mutation takes a non-model input class and returns a non-model output class. | api-platform: `input: Dto::class`, `output: Dto::class`, `map: true` (Object Mapper) | partial: `custom` kind, `__output_type__`, function entrypoints with `TypedDict` | low | |

## 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-entrypoint FilterSet and OrderSet | A list entrypoint uses a different FilterSet or OrderSet than the QueryType default. | api-platform: `QueryCollection(filters: [...])`, `parameters` per operation | partial: a second QueryType with `register=False` | medium | I checked `undine/entrypoint.py`. `Entrypoint` has no `filterset` or `orderset` argument. |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| `nodes` shortcut on connections | Adds `nodes: [T]` next to `edges`. | async-graphql: `EnableNodesField`. wpgraphql: `nodes` on every connection | missing | medium | Inventory lists it as not supported. Common in GitHub style APIs. |
| Extra fields on connection and edge types | Adds custom fields to the connection or edge object. Example: edge data from a through model. | async-graphql: `Connection<..., ConnectionFields, EdgeFields>`. lighthouse: `@belongsToMany(edgeType:)` (pivot data on edges). wpgraphql: `register_graphql_edge_field`, `connectionFields`, `edgeFields` | missing | medium | `Connection(...)` takes no extra fields. I checked `undine/relay/connection.py`. Through-model data on edges fits Django well. |
| Custom connection and edge type names | Sets the names of the generated connection and edge types. | async-graphql: `ConnectionNameType`, `EdgeNameType` | missing | low | I think names come from the wrapped type only. |
| Page-number pagination | Paginates with `page` and `first`. Returns `currentPage`, `lastPage`, `total`, `hasMorePages`. | lighthouse: `@paginate(type: PAGINATOR)`, `PaginatorInfo`. api-platform: `paginationType: 'page'`, `paginationInfo { itemsPerPage lastPage totalCount hasNextPage }` | missing | medium | Inventory lists it as not supported. Common in admin style UIs. |
| Shared connection interfaces | Connection and edge types implement generic interfaces so clients can share fragments. | wpgraphql: `Connection`, `Edge`, `PageInfo`, `OneToOneConnection`, `{Type}Connection` interfaces | missing | low | |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Global ID inputs | Decodes global IDs in arguments and mutation inputs to raw primary keys. | lighthouse: `@globalId(decode:)` with `ID`, `TYPE` or `ARRAY` | missing | medium | I found `from_global_id` used only in the `node` resolver (`undine/resolvers/query/relay.py`). Relay clients send global IDs back in mutations. |
| `clientMutationId` on mutations | Adds Relay `clientMutationId` to mutation input and payload. | api-platform: `clientMutationId` on all mutations. wpgraphql: added to all mutation inputs and payloads | missing | low | No grep hit in `undine/`. Modern Relay does not need it. |

## 9. DataLoaders

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Batch field resolvers | A field resolver gets all parent objects at once and returns results by index. No separate loader needed. | gqlgen: `@goField(batch: true)`, `resolver.batch`, `graphql.BatchErrors`, `graphql.BatchErrorList` | partial: `DataLoader` in async mode only | medium | Would also work in sync mode. The optimizer covers model relations. This helps for non-ORM data. |
| Concurrency limit for field resolvers | Caps how many field resolvers run at the same time. | gqlgen: `exec.worker_limit` | missing | low | I think async resolvers run with no cap in Undine. |
| Cross-request DataLoader cache | Keeps loaded values across requests with an LRU or custom cache. | async-graphql: `DataLoader::with_cache`, `HashMapCache`, `LruCache`, `CacheFactory` | missing | low | Inventory lists it as not supported. Stale data risk. |
| DataLoader batch delay | Waits a short time to collect more keys before a batch runs. | async-graphql: `DataLoader::delay` | missing | low | Undine batches per event loop tick I think. |

## 11. Unions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Non-model union members | Union members that are not model-backed, with a custom resolver per member. | juniper: `#[graphql_union]`, `#[graphql(on Type = path::to::fn)]`, variant `with = fn` | missing | medium | Inventory says members must be QueryTypes. Errors-as-data unions are built internally only. |

## 12. Directives

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Runtime directive behavior | A directive wraps the field resolver. Example: `@hasRole` auth check, or a client-side `FIELD` directive that changes the value. | gqlgen: `Config.Directives.<Name>` with `func(ctx, obj, next, args)`, `call_argument_directives_with_null`. async-graphql: `CustomDirective::resolve_field`, `#[Directive(location = "Field")]` | missing | medium | Undine directives are metadata only. Behavior needs a validation rule or a hook. |
| Flatten input object argument | Turns one input object argument into separate resolver parameters. | gqlgen: `@inlineArguments` | missing | low | Python `TypedDict` arguments cover most needs. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| 64-bit and unsigned integer scalars | Scalars for integers that do not fit GraphQL `Int` (32-bit). | gqlgen: `graphql.Int64`, `Uint64`, `Int32`, `Uint` and so on. async-graphql: `StringNumber<T>` (number as string). juniper: `ruint` feature scalars `U8` to `U256` | missing | medium | `BigIntegerField` maps to Python `int` and so to `Int` (`convert_model_field_to_python_type.py`). Large values overflow. |
| ISO 8601 duration | Duration scalar in ISO 8601 format. | gqlgen: `graphql.Duration` | partial: `Duration` scalar in seconds | low | Format choice only. |
| Time zone and UTC offset scalars | Scalars for IANA time zone names and UTC offsets. | async-graphql: `chrono-tz` `TimeZone`. juniper: `TimeZone`, `UtcOffset`, `TimeZoneOrUtcOffset` | missing | low | Django uses `zoneinfo`. Easy to add as a `ScalarType`. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Composable permission guards | Reusable guard objects combined with `and` and `or`, attached to types and fields. | async-graphql: `Guard` trait, `GuardExt::and`, `GuardExt::or`, `guard = "..."` | missing | medium | Inventory lists no declarative permission classes. Undine has only hook functions. |
| Django model permission checks | Checks framework permissions (policies) on found models, the model class, the parent or the result. | lighthouse: `@canFind`, `@canModel`, `@canQuery`, `@canResolved`, `@canRoot`, `@guard(with:)`. api-platform: `security: "is_granted('VIEW', object)"` expressions with voters, `securityPostDenormalize`, Laravel `policy` | missing | high | Inventory lists no `has_perm` integration. A Django version would use `user.has_perm` and object permissions (django-guardian). |
| Per-field rate limiting | Limits how often a field can be called, by named limiter. | lighthouse: `@throttle(name:, maxAttempts:, decayMinutes:)` | missing | medium | Inventory lists no rate limiting. Django cache can store counters. |
| Null for denied fields | A field the user may not read returns null instead of an error. The field becomes nullable. | api-platform: `#[ApiProperty(security: ...)]`. wpgraphql: Model field capabilities (`graphql_model_field_capability`), restricted objects with `allowed_restricted_fields` | partial: `@<field>.permissions` raises `GraphQLPermissionError` | medium | Errors-as-data or a custom resolver can do it by hand. |
| Require login for the endpoint | Rejects anonymous requests, except an allow-list of fields such as a login mutation. | wpgraphql: setting `restrict_endpoint_to_logged_in_users`, `RequireAuthentication` rule, `graphql_require_authentication_allowed_fields` | partial: Django view decorators like `login_required` on the URL | medium | The allow-list part is missing. A validation rule could do it. |

## 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Argument-aware complexity | Complexity function gets the field arguments and child complexity. Example: multiply by `first`. | gqlgen: `Config.Complexity.<Type>.<Field> = func(childComplexity, args...) int`, `complexity.WithFixedScalarValue`, `WithIgnoreFields`. graphql-php: `QueryComplexity`, field `complexity: fn (int $childrenComplexity, array $args)` | partial: static `complexity=` value per field | medium | I checked `max_complexity_rule.py`. It does not read arguments. Undine counts queries, not rows. |
| Per-request complexity limit | Chooses the complexity limit per request, for example by user. | gqlgen: `extension.ComplexityLimit{Func}` | missing | medium | `MAX_QUERY_COMPLEXITY` is a global setting. |
| Complexity stats in context | Exposes the computed complexity and depth to the app or in response extensions. | gqlgen: `extension.GetComplexityStats(ctx)`. async-graphql: `extensions::Analyzer` | missing | low | |
| Per-request introspection switch | Turns introspection on or off for one request, for example staff only. Also an introspection-only mode. | gqlgen: `OperationContext.DisableIntrospection`. async-graphql: `Request::disable_introspection`, `only_introspection`, `IntrospectionMode` | partial: `ALLOW_INTROSPECTION_QUERIES` global setting | medium | Visibility can hide parts. It cannot turn introspection on per user. |
| Remove spec validation rules | Adds or removes spec rules. | gqlgen: `SetValidationRulesFn` | partial: `ADDITIONAL_VALIDATION_RULES` adds rules. Spec rules always run | low | |
| Query depth limit | Rejects operations nested deeper than N levels. | async-graphql: `SchemaBuilder::limit_depth`. graphql-php: `QueryDepth($max)` | partial: `MAX_LIST_NESTING_DEPTH` counts only to-many nesting | medium | Inventory lists no plain depth rule. |
| Parser recursion limit | Limits parser recursion depth. | async-graphql: `SchemaBuilder::limit_recursive_depth`. graphql-php: `Parser::parse($source, ['recursionLimit' => 256])` | partial: `MAX_TOKENS` | low | |
| Skip validation for trusted documents | Runs persisted documents without validation, because they were validated when stored. | graphql-php: `ServerConfig` `validationRules` callable returning `[]` for persisted queries | partial: `ValidationCacheHook` caches validation | low | The cache gives most of the gain. |
| Deprecated usage detection | Reports which deprecated fields and enum values an operation uses. | lighthouse: `DetectDeprecatedUsage::handle(callable)` | missing | medium | Helps decide when a deprecated field can be removed. Could be a validation rule or lifecycle hook. |
| Security settings review | Checks the security settings and reports weak ones. | wpgraphql: `register_graphql_settings_review_step`, `wp graphql settings-review` | missing | medium | Django system checks (`manage.py check --deploy`) fit well. I found no `checks` module in `undine/`. Example: warn when introspection is on or limits are off in production. |

## 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-event context in subscriptions | Each event carries its own context that reaches response hooks. | gqlgen: `@subscriptionContext`, `subscription_context_field`, `graphql.Event[T]` | missing | low | |
| Hosted pub/sub broadcasters | Delivers subscription events through an external hub (Pusher, Reverb, Echo, Mercure) instead of a WebSocket server. | lighthouse: `subscriptions.broadcasters` (`pusher`, `reverb`, `echo`), `queue_broadcasts`, `storage_ttl`. api-platform: Mercure hub, `mercureUrl` in payload | missing | low | Undine uses channels and its own brokers. |
| Exclude the sender from a broadcast | Does not send an event to the client that caused it. | lighthouse: "only to others" with `X-Socket-ID` | missing | low | |

## 18. Incremental delivery (@defer and @stream)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Defer limits | Stops deferring after N nested fields or N milliseconds and resolves the rest at once. | lighthouse: `defer.max_nested_fields`, `defer.max_execution_ms` | missing | low | Protects against many small deferred chunks. |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-field result cache | Caches one field result, keyed by parent ID and optionally user. | lighthouse: `@cache(maxAge:, private:)`, `@cacheKey` | missing | medium | Inventory says only the whole operation response is cached. |
| Tag-based cache invalidation | Clears cached responses for a type or object when data changes. | lighthouse: `@clearCache(type:, idSource:, field:)`, `cache_directive_tags`. wpgraphql: Smart Cache `graphql_purge( $key, $event )` on WordPress events | missing | medium | Inventory lists no invalidation on writes. Model signals could clear entries. |
| Cache tag headers for CDN purge | Sends the types and object IDs in a response as a header, so a CDN can purge by tag. | wpgraphql: Query Analyzer `X-GraphQL-Keys` (`list:{type}`, node IDs), `X-GraphQL-Query-ID` | missing | medium | Undine sends `Cache-Control` but no tags. Fits with model signals for purging. |

## 21. Persisted documents and APQ

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Persisted document aliases and per-document settings | Gives a stored document a readable alias, a max-age, groups, and an allow or deny flag. | wpgraphql: Smart Cache `graphql_document` post type (aliases, allow/deny grant, max-age, groups), `createGraphqlDocument` | partial: `PersistedDocument` model and `PERSISTED_DOCUMENTS_ONLY` allow-list | low | Deny-list mode and aliases are missing. |
| Persisted documents at GET URL paths | Serves each persisted operation at its own GET path for URL-based CDN purge. | wpgraphql: branch `feat/wp-graphql-pqu` (`/graphql/persisted/{queryHash}/variables/{variablesHash}`) | partial: `documentId` over GET | low | Unreleased upstream. |

## 22. Lifecycle hooks (middleware / extensions)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Response extensions from resolvers | A resolver adds a key to the response `extensions`. | gqlgen: `graphql.RegisterExtension(ctx, key, value)`, `GetExtensions` | partial: lifecycle hooks can edit `context.result` | medium | No helper for a resolver to add an extension. |
| Per-response interceptor for streams | A hook runs around each response, also each subscription event. | gqlgen: `ResponseInterceptor.InterceptResponse`, `AroundResponses` | partial: `on_execution` hook | low | I think it runs once per operation. Not verified for subscriptions. |
| Root field interceptor | A hook runs around each root field only. | gqlgen: `RootFieldInterceptor`, `AroundRootFields` | partial: `resolve` per-field hook | low | |
| Apollo tracing v1 in extensions | Adds per-field timing to the response `extensions`. | gqlgen: `apollotracing.Tracer{}`. async-graphql: `extensions::ApolloTracing`. lighthouse: `tracing.driver` `ApolloTracing`. wpgraphql: `tracing_enabled`, `tracing_user_role` | missing | low | Apollo deprecated the format. OpenTelemetry covers it. |
| Debug printer | Prints operations and responses to a stream. | gqlgen: `debug.Tracer{}` | missing | low | Debug toolbar and logging cover most of it. |
| Logger hook | Logs each operation and its errors. | async-graphql: `extensions::Logger`. lighthouse: `LogGraphQLQueries` middleware | partial: errors go to the `undine` logger | low | No operation log hook built in. |
| Debug messages in response extensions | Any code adds a message to `extensions.debug` in debug mode. | wpgraphql: `graphql_debug( $message )`, `GRAPHQL_DEBUG` | missing | low | Useful for warnings like clamped page sizes. |
| SQL query log in response extensions | Adds executed SQL queries to `extensions` for allowed users. | wpgraphql: `query_logs_enabled`, `extensions.queryLog`, `query_log_user_role` | partial: Django Debug Toolbar integration | low | |

## 23. Apollo Federation 2

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Batch entity resolver | Resolves many `_entities` representations of one type in one call. | gqlgen: `@entityResolver(multi: true)`, `entity_resolver_multi`, `Find<Type>By<Keys>s`. lighthouse: `BatchedEntityResolver` | missing | high | I checked `undine/federation/entities.py`. It resolves one representation at a time. This is N queries for N entities. |
| `@requires` data on field resolvers | Field resolver gets the `@requires` data as a map. | gqlgen: `computed_requires`, `@computedRequires`, `preloaded_requires` | partial: `RequiresDirective` exists | low | Not verified how Undine passes requires data. |
| Subscriptions in a federated subgraph | Lets a subgraph expose subscriptions. | async-graphql: `enable_subscription_in_federation` | missing | low | I think `create_federation_schema` accepts a subscription root. Not verified. |

## 24. Integrations

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Other IDEs (Apollo Sandbox, Altair, Playground) | Serves another GraphQL IDE instead of GraphiQL. | gqlgen: `playground.ApolloSandboxHandler`, `playground.AltairHandler`. juniper: `playground::playground_source` | missing | low | GraphiQL is built in. |
| CSP nonce for GraphiQL | Adds a Content Security Policy nonce to GraphiQL scripts. | api-platform: CSP nonce on GraphiQL scripts (5.0, #8310) | missing | medium | No grep hit for `nonce` in `undine/`. Sites with strict CSP (django-csp) cannot load GraphiQL. |

## 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Introspection JSON export | Writes the schema as introspection JSON, not only SDL. | lighthouse: `lighthouse:print-schema --json` | missing | low | `print_schema` prints SDL only. I checked its arguments. Some client tools want JSON. |
| Scaffolding commands | Generates boilerplate files for queries, mutations, directives, scalars. | lighthouse: `lighthouse:query`, `lighthouse:mutation`, `lighthouse:directive`, `lighthouse:scalar` and so on | missing | low | |
| Resolver mocking in tests | Replaces a resolver with a mock in a test. | lighthouse: `MocksResolvers` (`mockResolver()`, `mockResolverExpects()`) | missing | low | Python `unittest.mock` covers most of it. |
| Introspection test helpers | Helpers to introspect a type or directive in tests. | lighthouse: `introspectType()`, `introspectDirective()`, `introspectByName()` | missing | low | |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Legacy `graphql-ws` WebSocket protocol | Supports the old `subscriptions-transport-ws` protocol. | gqlgen: `transport.Websocket` (default protocol `graphql-ws`). async-graphql: `http::WebSocket`, `ALL_WEBSOCKET_PROTOCOLS`. juniper: `juniper_graphql_ws` feature `graphql-ws` | missing | low | Deprecated protocol. |
| WebSocket payload limit and custom close | Limits incoming message size. Sets close code and reason. | gqlgen: `Websocket{PayloadReadLimit}`, `transport.WithWebsocketCloseCode`, `AppendCloseReason` | missing | medium | I think the Undine consumer has no payload limit. Not verified. |
| Upload size and count limit | Caps upload size and number of files for GraphQL multipart requests. | gqlgen: `MultipartForm{MaxUploadSize, MaxMemory}`. async-graphql: `MultipartOptions::max_file_size`, `max_num_files` | partial: Django `DATA_UPLOAD_MAX_MEMORY_SIZE` and `FILE_UPLOAD_MAX_MEMORY_SIZE` | low | I think Django settings cover it. |
| OPTIONS handling | Answers `OPTIONS` requests. | gqlgen: `transport.Options{AllowedMethods}` | missing | low | django-cors-headers covers CORS. |
| SSE minimum event interval | Throttles SSE events. | gqlgen: `SSE{MinEventInterval}` | missing | low | |
| Query batching | Runs an array of operations from one HTTP request. | async-graphql: `Schema::execute_batch`, `receive_batch_body`, `GraphQLBatchRequest`. juniper: `GraphQLBatchRequest`, `GraphQLBatchResponse`. graphql-php: `ServerConfig` `queryBatching`, `Helper::executeBatch()` (one shared deferred queue per batch). lighthouse: always on. wpgraphql: `batch_queries_enabled`, `batch_limit` (default 10) | missing | medium | Inventory lists it as not supported. Apollo Client supports batching. |
| Max in-flight operations per WebSocket | Limits how many operations one WebSocket connection runs at once. | juniper: `ConnectionConfig::with_max_in_flight_operations` | missing | medium | I found no limit in `undine/utils/graphql/websocket.py`. One client can open many subscriptions. |

## 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Error presenter | One function transforms or drops each error. | gqlgen: `SetErrorPresenter`, `SetRecoverFunc`. graphql-php: `ServerConfig` `errorFormatter`, `errorsHandler`. lighthouse: `error_handlers` config chain (`ErrorHandler` interface) | partial: `ERROR_MASKING_PREDICATE`, `ERROR_MASKING_MESSAGE` | medium | Undine can mask, not fully transform or drop. A lifecycle hook can edit `result.errors`. |
| Add errors without failing the field | Resolver adds an error but still returns data. | gqlgen: `graphql.AddError(ctx, err)`, `AddErrorf`. async-graphql: `Context::add_error`. lighthouse: `ErrorPool` | missing | medium | I think Undine resolvers can only raise. Not verified. |
