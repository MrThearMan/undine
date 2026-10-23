# Candidates batch 2

Findings files: strawberry, graphene, ariadne, tartiflette, graphql-core, graphql-js, apollo-server, graphql-yoga-envelop.

## 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Build-time schema field filter | Drops fields at schema build, so one codebase gives a public and an internal schema. | strawberry: `Schema.get_fields` override | partial: per-request visibility hooks. `print_schema` ignores visibility. | medium | Useful for exporting a public SDL. I think a "visibility for this request-less context" option would cover it. |
| Merge root types | Merges many root type classes into one root type. | strawberry: `strawberry.tools.merge_types`. ariadne-graphql-modules: roots merging of many `Query` classes | partial: I think `RootType` subclassing can combine entrypoints. Not documented. | medium | Helps apps that each define their own Query parts. |
| Create types at runtime | Builds an object or input type from a list of fields at runtime. | strawberry: `strawberry.tools.create_type`. graphene: `BaseType.create_type` | missing | low | Undine is class based. Dynamic classes are possible with `type()`. |
| Replace default attribute resolver | Replaces the default `getattr` lookup for all fields. | strawberry: `StrawberryConfig(default_resolver=...)`. graphene: `set_default_resolver`, `Meta.default_resolver` | missing | low | Undine fields are model based. Little need. |
| Custom name converter | Pluggable class to rename types, fields, enum values and directives. | strawberry: `StrawberryConfig(name_converter=NameConverter())`. ariadne: `convert_names_case=callable` | partial: `CAMEL_CASE_SCHEMA_FIELDS` and `schema_name` | low | A dotted-path name converter setting is cheap to add. |
| Generic object types | Builds named types from `Generic[T]` classes (for example `Page[T]` to `UserPage`). | strawberry: `Generic[T]` types, PEP 695 | missing | low | Undine builds wrappers like `Connection` itself. |
| Dynamic field | Field whose type is decided at schema build. Returning nothing drops the field. | graphene: `graphene.Dynamic(lambda: ...)` | partial: `Field(lambda: ...)` lazy reference. I think it cannot drop the field. | low | Useful for optional apps. |
| Rich schema build errors | Shows code frames and a docs link per schema build error. | strawberry: rich errors, `docs/errors/` | partial: `UndineErrorGroup` lists all schema errors | low | Nice developer experience only. |
| Translated schema descriptions | Keeps lazy translation strings as descriptions, so introspection can follow the request language. | graphql-core: `register_description(cls)` for non-str descriptions | missing: `help_text` is turned into `str` at build (`undine/converters/impl/convert_to_description.py`) | medium | Fits Django i18n and the modeltranslation integration. Needs a per-request introspection path. |
| Multiple schemas in one project | Serves several schemas (for example public and internal APIs) from one process. | tartiflette: `SchemaRegistry` with `schema_name=`. strawberry: one `Schema` per view. yoga: `schema` factory per request, envelop `useSchemaByContext` | missing: one global `SCHEMA` setting used by views, hooks and commands | medium | Common need for separate public and admin APIs. |
| Plugin modules that add schema parts | Loads packages by module path with config. Each package adds types and code. | tartiflette: `create_engine(modules=[{"name": ..., "config": ...}])`, module `bake()` | missing | low | Django apps already give a module system. |
| SDL-first schema definition | Writes the schema in SDL and binds Python resolvers by name. | ariadne: `make_executable_schema(type_defs, *bindables)`, `load_schema_from_path` | missing: code-first only | low | Against Undine's model-centric design. |
| Schema proxy and stitching | Combines local and remote schemas and routes queries to them. | ariadne-graphql-proxy: `ProxySchema.add_remote_schema` | missing | low | Federation covers the multi-service case. |

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Configurable enum type | Declares a GraphQL enum with a name, description, and per-value description, deprecation and directives. | strawberry: `@strawberry.enum`, `strawberry.enum_value`. graphene: `Enum.from_enum(description=, deprecation_reason=)` with callables per member | partial: Python enums and model choices convert automatically. Values get descriptions. No deprecation or directives per value outside `OrderSet`. | medium | Deprecating a choice value is a common need. |
| Null vs absent input marker | Tells apart an omitted argument and an explicit `null`. | strawberry: `strawberry.Maybe[T]`, `strawberry.Some`, `UNSET`. graphene: absent args not passed, `set_input_object_type_default_value(Undefined)` | partial: I think update mutations leave absent inputs out of input data. Function entrypoint and field arguments have no marker. | medium | Matters for function entrypoints that do partial updates. |
| Union and interface over non-model objects | Lets a resolver tag any object (dict, dataclass) with its GraphQL type for union or interface resolution. | strawberry: `strawberry.cast`. graphene: `Meta.possible_types`, `is_type_of`. tartiflette: `_typename` key, `@TypeResolver` | partial: union members must be QueryTypes. Matched by exact model class. | medium | Needed for unions over function entrypoint results. |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Input object from resolver arguments | Wraps function arguments into one `input` argument with a generated input type. | strawberry: `InputMutationExtension`. ariadne: `InputType(out_type=)` converts input dicts | partial: `MutationType` gives an `input` argument. Function entrypoints take a `TypedDict` argument as input object. | low | Mostly covered. |
| Relay client mutation ID | Adds `clientMutationId` to the input and echoes it in the payload. | graphene: `relay.ClientIDMutation` | missing | low | Legacy Relay convention. |
| Pydantic model integration | Builds GraphQL types and inputs from pydantic models. Converts validation errors to structured errors. | strawberry: `strawberry.experimental.pydantic`, `PydanticErrorExtension` | missing | low | Undine is Django model centric. |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Strict connection types | Makes `edges: [Edge!]!` and `node: Node!` non-null. | graphene: `Connection Meta.strict_types = True` | missing: `edges` is `[Edge]` and `node` is nullable (`undine/converters/impl/convert_to_graphql_type.py`) | medium | Better client types. Could be a setting. |
| Extra fields on connection and edge | Adds custom fields to the connection or edge type (for example edge metadata). | graphene: fields on `Connection` subclass and inner `class Edge`. strawberry: `relay.Edge` subclass, `resolve_edge` | missing | medium | Common for many-to-many through data on edges. |
| Pagination over plain lists | Paginates any Python iterable or list from a resolver. | graphene: `relay.ConnectionField` with `connection_from_array`. strawberry: `relay.ListConnection` | partial: `Connection` wraps QueryType, UnionType or InterfaceType only | low | For function entrypoints that return non-model data. |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Plural nodes entrypoint | Fetches many nodes by a list of global IDs. | strawberry: `relay.node()` with `list[Node]` | missing | medium | Listed as not supported in the inventory. |
| Pluggable global ID format | Chooses the global ID encoding (base64, raw id, UUID). | graphene: `Meta.global_id_type` with `DefaultGlobalIDType`, `SimpleGlobalIDType`, `UUIDGlobalIDType` | missing: fixed base64 of `ID:<typename>:<id>` | low | Some teams want readable IDs. |
| Type-restricted node field | Node field that only accepts IDs of one type. | graphene: `relay.Node.Field(OnlyType)`. strawberry: `GlobalID.resolve_node(ensure_type=)` | missing | low | Can be written as a function entrypoint. |
| Global ID argument type | Parses a global ID argument into type name and id. | strawberry: `relay.GlobalID` | partial: `from_global_id` helper | low | Helper exists. |

## 9. DataLoaders

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Pluggable DataLoader cache | Lets the loader use a custom cache map (for example Redis or the Django cache). | strawberry: `DataLoader(cache_map=...)`, `AbstractCache`. graphene: `DataLoader(cache_map=, get_cache_key=)` | missing: only per-request `reuse_loads` | medium | Could plug into the Django cache framework. |
| Sync DataLoader | Batches loads in sync execution with a deferred execution context. | ariadne docs: `graphql_sync_dataloaders.SyncDataLoader`, `DeferredExecutionContext` | missing: DataLoader needs `ASYNC = True` | medium | Many Django sites run sync. |

## 12. Directives

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Executable directive with behavior | Operation directive that transforms the resolved field value (for example `@uppercase`). | strawberry: `@strawberry.directive(locations=[...])` with `DirectiveValue[T]`. tartiflette: `@Directive` with `on_field_execution` on `FIELD` and `FIELD_DEFINITION` | partial: `Directive` is metadata only. Behavior needs a hook or validation rule. | medium | A `__resolve__`-style hook on `Directive` would make this easy. |
| Schema directive visitor | Type-system directive that changes behavior at build, for example wraps the field resolver. | ariadne: `SchemaDirectiveVisitor` with `visit_field_definition` and other `visit_*` methods. tartiflette: `on_post_bake` (undocumented) | partial: `Directive.__connected__` hook (undocumented) runs on attach | medium | Documenting `__connected__` as a public API may be enough. |
| Directive hook on input coercion | Directive on a scalar, enum or input type that runs on every coerced input value (for example `@maxLength`). | tartiflette: `on_post_input_coercion`, `on_argument_execution` | partial: `@<input>.validate` and `@<input>.convert` per Input. No reusable directive form. | medium | Reusable validators per type would reduce repetition. |
| Directive hook on output coercion | Directive on an object, scalar, enum, union or interface that runs on every resolved value of that type. | tartiflette: `on_pre_output_coercion` | missing | low | Could support masking or formatting by type. |
| Custom selection directive | User directive that drops a selection based on request context, like a custom `@skip`. | tartiflette: `on_field_collection`, `on_fragment_spread_collection`, `on_inline_fragment_collection`, `SkipCollection` | missing | low | Feature-flag style queries. |
| Operation-level directive hook | Directive on the schema or operation that wraps the whole execution. | tartiflette: `on_schema_execution`, `on_schema_subscription` | partial: lifecycle hooks and built-in `@atomic` | low | Covered by `LifecycleHook`. |
| Deprecated directives | Marks a directive definition as deprecated with `@deprecated`. | graphql-js 17: directives on directive definitions, `DirectiveLocation.DIRECTIVE_DEFINITION`. graphql-core: `experimental_directives_on_directive_definitions` | missing: I think `Directive` has no `deprecation_reason` | low | Spec feature. Small. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| BigInt scalar | 64-bit integer scalar. | graphene: `graphene.BigInt` | missing: `BigIntegerField` is a subclass of `IntegerField` and maps to 32-bit `Int` (`undine/converters/impl/convert_to_graphql_type.py:565`) | high | I think large `BigIntegerField` values fail serialization today. Not tested. |
| Scalar overrides | Replaces how a built-in scalar or Python type is serialized (for example Unix timestamps). | strawberry: `StrawberryConfig(scalar_map=...)`, `Schema(scalar_overrides=...)` | partial: `singledispatch` `parse` and `serialize`. Converters can be re-registered. | low | Mostly covered. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Reusable permission classes | Declarative permission classes with message, extensions and error class. Listed on fields. | strawberry: `BasePermission`, `strawberry.field(permission_classes=[...])`, `PermissionExtension` | missing: permissions are per-element hook methods | medium | Reuse across many fields is the gain. |
| Silent permission failure | Returns `null` or `[]` instead of an error when a permission fails. | strawberry: `PermissionExtension(fail_silently=True)` | partial: `__filter_queryset__` pattern for rows. `EmptyFilterResult` for filters. | medium | A flag on `@<field>.permissions` would be simple. |
| Permissions shown as schema directives | Adds a directive per permission class to the SDL. | strawberry: `PermissionExtension(use_directives=True)` | missing | low | Documentation value only. |
| Django auth decorators | Requires login or a Django model permission (`has_perm`) for a resolver. | ariadne_django: `login_required()`, `permission_required(perm)` | missing: no `has_perm` integration | high | Natural fit for a Django library. |
| Global default permission | Applies one permission check to all resolvers, with per-field opt-out. | ariadne-auth: `AuthorizationExtension.set_required_global_permissions`, `require_permissions(ignore_global_permissions=)`. envelop: `useGenericAuth(mode: "protect-all")` with `@skipAuth` | missing | medium | I think a lifecycle hook can do it today, but there is no API. |
| Enforced auth directives | `@authenticated`, `@requiresScopes` and `@policy` directives that the server enforces before execution. | envelop: `useGenericAuth` (`protect-granular`, `extractScopes`, `fetchPolicies`) | partial: federation `AuthenticatedDirective`, `RequiresScopesDirective`, `PolicyDirective` are metadata only | medium | I think Undine does not enforce them locally. Not verified. |
| Per-viewer field allowlist | Rejects operations that select schema coordinates the viewer may not use. | envelop: `useOperationFieldPermissions({ getPermissions })` | partial: visibility hides fields per request | low | Visibility covers most of it. |
| JWT authentication | Verifies JWTs from headers, cookies or WebSocket params and puts the payload in context. | yoga: `useJWT`. envelop: `useAuth0` | missing | low | Django auth packages do this. |

## 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query depth limit | Rejects operations deeper than N levels. Can ignore some fields. | strawberry: `QueryDepthLimiter(max_depth, should_ignore=)`. graphene: `depth_limit_validator(max_depth, ignore=, callback=)`. envelop: `useDepthLimit` | partial: `MaxListNestingDepthRule` counts only to-many nesting | medium | A plain depth rule is cheap and common. |
| Disable validation | Skips validation entirely. | strawberry: `DisableValidation()`. apollo-server: `dangerouslyDisableValidation` | missing | low | Risky. Persisted documents are a safer path. |
| Per-request validation rules | Picks validation rules per request (for example stricter for anonymous users). | ariadne: `validation_rules=callable(context, document, data)` | partial: `ADDITIONAL_VALIDATION_RULES` is static | medium | Rules can read the request from context today. Not a documented pattern. |
| Reject deprecated usage rule | Validation rule that reports use of deprecated fields, arguments and enum values. | graphql-core: `NoDeprecatedCustomRule` | partial: can be added with `ADDITIONAL_VALIDATION_RULES` | low | A setting toggle would be enough. |
| Total selection count limit | Rejects operations whose selection count, with named fragments inlined, exceeds a limit. | apollo-server: `maxRecursiveSelections` | missing: `MaxComplexityRule` and `MaxListNestingDepthRule` do not count plain selections | medium | Cheap guard against fragment blow-up. |
| Rate limiting | Limits calls per field per user in a time window. | envelop: `useRateLimiter` with `@rateLimit(max, window, ...)` and `configByField` | missing | high | Listed as not supported. Could use the Django cache. |
| Pagination argument bounds | Requires `first` or `last` and bounds them. Limits total node count. | envelop: `useResourceLimitations({ nodeCostLimit, paginationArgumentMaximum })` | partial: `page_size` and `LIST_ENTRYPOINT_LIMIT`. I think `first` above `page_size` is capped. | low | Verify in `undine/relay/validation.py`. |
| Per-request introspection control | Allows introspection only for some requests (for example staff users). | yoga: `useDisableIntrospection({ isDisabled(request, context) })` | partial: `ALLOW_INTROSPECTION_QUERIES` is a static setting | medium | Common need. Small change. |
| Allowed operation types | Allows only some operation types (for example a read-only endpoint). | envelop: `useFilterAllowedOperations` | partial: per-transport toggles like `ALLOW_MUTATIONS_WITH_SSE` | low | Easy to add as a rule. |
| Execute-time validation rules | Validation rules that run with variables and context. | envelop: `useExtendedValidation` | missing | low | Custom rules can read context today. |
| Cost analysis with argument multipliers | Cost per field multiplied by list size arguments like `first`. | ariadne: `cost_validator(maximum_cost, cost_map=)`, `@cost(complexity:, multipliers:)`. envelop docs: GraphQL Armor `costLimitPlugin` | partial: `MaxComplexityRule` counts database queries. No multipliers. | medium | Undine's choice of counting queries is deliberate. Row cost is bounded by limits. |

## 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Live queries | `@live` query that re-runs and pushes new results when data is invalidated. | envelop: `useLiveQuery`, `InMemoryLiveQueryStore.invalidate('User:1')` | missing | medium | Model signals could drive invalidation. Fits the existing signal subscriptions. |
| Fresh context per subscription event | Creates a new context (fresh DataLoaders) for each subscription event. | envelop: `useContextValuePerExecuteSubscriptionEvent` | partial: I think DataLoader reuse is cleared only on `request_finished` | low | Stale DataLoader values in long subscriptions. Not verified. |

## 18. Incremental delivery

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Incremental delivery over SSE | Sends `@defer` and `@stream` payloads over `text/event-stream`. | yoga: `useDeferStream` with SSE result processor | missing: only `multipart/mixed` | medium | Listed as not supported. |
| Legacy incremental payload format | Sends `@defer`/`@stream` payloads in the older format with `path` and `label`. | graphql-js: `legacyExecuteIncrementally`, `legacyExecuteRootSelectionSet`. apollo-server: `legacyExperimentalExecuteIncrementally` for `deferSpec=20220824` | missing: only the new `pending`/`incremental`/`completed` format from graphql-core 3.3 | low | I think some Apollo Client and Relay versions still expect the old format. Not in graphql-core. |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-resolver result cache | Caches one resolver's result with a pluggable backend. | ariadne-graphql-proxy: `cached_resolver`, `CloudflareCacheBackend`, `DynamoDBCacheBackend` | missing: only whole-operation caching | medium | Could use the Django cache framework. |
| HTTP conditional requests | Sends `ETag` and answers `If-None-Match` with 304. | yoga: `useResponseCache` HTTP caching | missing | medium | Saves bandwidth for cached GET queries. |
| Dynamic cache hints | A resolver sets or tightens the cache max age and scope at runtime. | apollo-server: `cacheControlFromInfo(info).setCacheHint`, `cacheHint.restrict()` | partial: static `cache_time` and `cache_per_user` rules only | medium | Lets per-object data shorten the TTL. |
| Cache metadata in response | Adds `hit`, `didCache` and `ttl` to response extensions. | yoga: `useResponseCache(includeExtensionMetadata: true)` | missing | low | Debug aid. |
| Response cache invalidation | Evicts cached responses when data changes. | apollo-server: technote TN0010 custom `generateCacheKey` prefix plus manual eviction. yoga/envelop: `useResponseCache` with `invalidateViaMutation`, `cache.invalidate([{ typename, id }])` | missing: time-based only | medium | Envelop tracks `typename:id` in results. Undine could use model signals. |
| CDN shared cache header | Sends `s-maxage` or similar for shared caches. | apollo-server: `ApolloServerPluginCacheControl(calculateHttpHeaders: false)` plus custom plugin | partial: `Cache-Control` and `Age` headers. I think no `s-maxage` option. | low | Verify in `undine/hooks.py`. |
| APQ storage TTL and backend | Stores APQ hashes in a cache with a TTL. | apollo-server: `persistedQueries: { cache, ttl }` | partial: APQ stored in the `PersistedDocument` model. No TTL. | low | DB storage is fine for most sites. |

## 21. Persisted documents and APQ

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-request persisted-only mode | Allows arbitrary documents for some requests and only persisted ones for others. | yoga: `usePersistedOperations(allowArbitraryOperations: fn)` | partial: `PERSISTED_DOCUMENTS_ONLY` is global | medium | Useful to let staff use GraphiQL in production. |
| Custom document ID extraction | Reads the document ID from Relay `doc_id`, a header, query param or URL path. | yoga: `extractPersistedOperationId`, `extraParamNames` | partial: `documentId` param only | low | Relay compatibility. |
| Load persisted documents from a manifest file | Loads the allowlist from a JSON file made at build time. | envelop: `JsonFileStore`. yoga: `getPersistedOperation` | partial: registration view `PersistedDocumentsView` | low | A management command could import a manifest. |
| Skip validation for persisted documents | Trusts build-time validation and skips runtime validation. | yoga: `usePersistedOperations(skipDocumentValidation: true)` | partial: `ValidationCacheHook` caches results | low | Covered by caching. |

## 22. Lifecycle hooks

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-field extension | Wraps one field's resolver and can change the field at build time (add args, directives). | strawberry: `FieldExtension` with `resolve`, `resolve_async`, `apply` | partial: `LifecycleHook.resolve` wraps all fields. `@<field>.resolve` replaces one resolver. | medium | A reusable per-field wrapper list would cover many cases. |
| Hook on each streamed result | Hook that runs for every subscription or incremental payload. | strawberry: `SchemaExtension.on_stream_result`. apollo-server: `willSendSubsequentPayload`, `didEncounterSubsequentErrors` | partial: I think `on_operation` and tracing hooks see subscription results. Not checked for incremental payloads. | low | Verify in `undine/hooks.py`. |
| Hook for invalid HTTP requests | Hook that runs on HTTP-level bad requests (bad JSON, bad params, CSRF block). | apollo-server: `invalidRequestWasReceived`. yoga: `onRequest`, `onRequestParse` | missing: lifecycle hooks start after the request is parsed. I think. | low | Useful for logging and metrics. |
| Server start and stop hooks | Hooks on server start, schema load and shutdown. | apollo-server: `serverWillStart`, `schemaDidLoadOrUpdate`, `drainServer`, `serverWillStop` | missing | low | Django `AppConfig.ready` covers start. |
| Custom error processing hook | One override point to log or rewrite errors. | strawberry: `Schema.process_errors`. ariadne: `error_formatter=`, `format_error(debug=True)` with local variables | partial: `ERROR_MASKING_PREDICATE`, hooks can edit `context.result` | low | Mostly covered. |
| Per-request hooks and middleware | Chooses extensions or middleware per request. | ariadne: `extensions=callable(request, context)`, `middleware=callable` | missing: `ADDITIONAL_LIFECYCLE_HOOKS` is static | low | Hooks can check the request and do nothing. |
| Custom parse and validate functions | Replaces the parse or validate step. | ariadne: `query_parser=`, `query_validator=` | partial: `on_parse` and `on_validation` hooks can short-circuit | low | Covered. |
| Concurrency control per field | Turns off concurrent resolution of sibling fields or list items for one field. | tartiflette: `@Resolver(list_concurrently=, parent_concurrently=)`, engine `coerce_list_concurrently` | missing | low | Matters when resolvers share one connection in async mode. |
| Compiled execution | Compiles queries to faster execution functions. | envelop: `useGraphQlJit` | missing | low | No mature Python equivalent. |
| Preload asset hints | Resolvers register asset URLs that the client can preload. | envelop: `usePreloadAssets` | missing | low | Niche. |
| Abort on client disconnect | Cancels execution when the client goes away. | graphql-core: `execute(abort_signal=)`, `AbortController`. yoga: `useExecutionCancellation()` with `request.signal` | partial: abort signal used only for `EXECUTION_TIMEOUT_SECONDS` | low | I think ASGI disconnect could trigger the same controller. Not verified. |
| Pluggable parse cache | Replaces the parse and validate cache decorator. | tartiflette: `query_cache_decorator` | partial: `ParseCacheHook` and `ValidationCacheHook` with size settings. Cross-process cache rejected on purpose. | low | Covered. |
| Profiler extension | Profiles one operation and writes an HTML report. | strawberry: `pyinstrument.PyInstrument` | missing | low | Debug toolbar covers part of this. |
| Apollo tracing response extension | Adds the legacy `tracing` timing data to response extensions. | strawberry: `ApolloTracingExtension`. envelop: `useApolloTracing` | missing | low | Legacy format. OpenTelemetry is preferred. |

## 24. Integrations

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Usage reporting to a schema registry | Sends per-operation and per-field usage stats to a registry. | apollo-server: `ApolloServerPluginUsageReporting` (GraphOS). envelop: `useHive` | missing: only ftv1 traces for federation | low | Proprietary target. OpenTelemetry covers most needs. |
| Schema reporting | Registers the schema with a registry on startup. | apollo-server: `ApolloServerPluginSchemaReporting` | missing | low | Rover CLI with `print_schema` does this in CI. |
| Prometheus and StatsD metrics | Exports counters and histograms per phase, resolver and error. | envelop: `usePrometheus`, `useStatsD`, `useNewRelic`. yoga: `@graphql-yoga/plugin-prometheus` with `/metrics` | missing | medium | Listed as not supported. Common in ops. |
| Client awareness | Reads client name and version headers and adds them to traces. | apollo-server: `apollographql-client-name`, `apollographql-client-version`, `generateClientInfo` | missing | low | Easy to add as span attributes. |

## 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Client code generation | Generates typed result types (Python or TypeScript) from operations. Plugin API. | strawberry: `strawberry codegen`, `QueryCodegenPlugin`. ariadne-codegen: typed pydantic client | missing | medium | Python codegen helps typed tests. Frontend teams use graphql-codegen anyway. |
| SDL to code generator | Converts an SDL file to Python type definitions once. | strawberry: `strawberry schema-codegen` | missing | low | Migration aid only. |
| Locate definition | Prints the source path and line of a type or field. | strawberry: `strawberry locate-definition` | missing | low | Editor integration. |
| Upgrade codemods | Automated code rewrites for breaking changes. | strawberry: `strawberry upgrade <codemod>` | missing | low | Useful only with frequent breaking changes. |
| Dev server command | Runs a dev server with GraphiQL and reload. | strawberry: `strawberry dev` | partial: Django `runserver` with built-in GraphiQL | low | Covered by Django. |
| Execute without HTTP | Runs the full request pipeline in tests without an HTTP request. | apollo-server: `server.executeOperation(request, { contextValue })` | partial: `GraphQLClient` uses the Django test client | low | Covered by the pytest plugin. |
| Schema mocking | Returns fake data for a schema without resolvers. | apollo-server docs: `addMocksToSchema` from `@graphql-tools/mock` | missing | low | Helps frontend work before the backend exists. |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query batching | Accepts a list of operations in one POST. Limit on operation count. | strawberry: `StrawberryConfig(batching_config={"max_operations": N})`. apollo-server: `allowBatchedHttpRequests` | missing | medium | Apollo Client and Relay can use it. |
| Legacy subscriptions-transport-ws | Supports the old `graphql-ws` WebSocket subprotocol. | strawberry: `GRAPHQL_WS_PROTOCOL`. ariadne: `GraphQLWSHandler`. tartiflette-aiohttp and tartiflette-asgi only support this protocol | missing | low | Deprecated protocol. |
| SSE resumption with Last-Event-ID | Reads `Last-Event-ID` to resume a stream. | strawberry: `Last-Event-ID` readable from request | missing | low | Strawberry has no replay buffer either. |
| Alternative GraphQL IDEs | Choice of IDE: GraphiQL, Apollo Sandbox, Pathfinder. | strawberry: `graphql_ide="graphiql", "apollo-sandbox" or "pathfinder"`. ariadne: `ExplorerGraphiQL`, `ExplorerApollo`, `ExplorerPlayground`, custom `Explorer.html(request)` | partial: GraphiQL only | low | Low demand. A per-request hook to allow GraphiQL may matter more. |
| HTTP callback subscriptions | Sends subscription events to a client callback URL with keep-alive and retries. | ariadne: example `subscription_handler_example.py` (Apollo callback protocol) | missing | low | Used by Apollo Router. Example only in ariadne. |
| Response formatter hook | Full control of the HTTP response built from the result. | tartiflette-aiohttp: `response_formatter(req, data, ctx)` | partial: `request.response_headers` for headers. Lifecycle hooks can edit the result. | low | Covered for most cases. |
| Pluggable subscription transport | Interface to add a new HTTP subscription transport. | ariadne: `SubscriptionHandler` with `supports` and `handle` | missing | low | Undine has many transports built in. |
| Serverless handler | Runs the GraphQL endpoint in AWS Lambda. | ariadne-lambda: `GraphQLLambda` | missing | low | Django on Lambda uses other adapters. |
| Custom JSON serializer | Replaces the JSON encoder of the response body (for example orjson). | apollo-server: `stringifyResult` | missing: fixed `json.dumps` in `undine/http/responses.py` | low | Speed gain for large responses. |
| Custom request body parser | Adds support for new request body formats. | yoga: `onRequestParse` with `setRequestParser` | missing | low | Rare need. |
| HTTP status and headers from errors | A resolver error sets the HTTP status and headers of the response. | yoga: `extensions.http: { status, headers }` on `GraphQLError` | partial: errors carry `status_code` extension. I think it does not change the HTTP status for JSON responses. | low | Not verified. |
| REST API from schema | Builds REST endpoints and OpenAPI docs from GraphQL operations. | yoga: `useSofa({ basePath, swaggerUI })` | missing | low | Separate concern. |
| Health check endpoint | Simple endpoint to check the server is up. | apollo-server: docs recipe `GET /graphql?query={__typename}` (removed built-in in v4). yoga: `useHealthCheck`, `useReadinessCheck({ check })` | missing | low | Django apps add their own. |
| Response deduplication | Replaces repeated `{__typename, id}` objects in a result with stubs. | graphene: `graphene.utils.deduplicator.deflate` | missing | low | Undocumented in graphene. Niche. |

## 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Error schema coordinate | Adds the schema coordinate of the failing resolver to the error. | yoga: `useErrorCoordinate()` | missing | low | Spec proposal. `path` gives most of this. |
| Error behavior modes | Lets the client choose `propagate`, `null` or `halt` on errors. | graphql-js: draft PR #4364 `onError` (not merged) | partial: `@experimental_disableErrorPropagation` and `@semanticNonNull` | low | Spec still a proposal. Watch only. |
