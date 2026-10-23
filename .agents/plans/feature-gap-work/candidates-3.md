# Candidates batch 3

Findings files: pothos, nexus, typegraphql, mercurius, graphweaver, graphql-ruby, absinthe. All seven are done.

## 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Several static schemas from one definition | Builds separate schemas (for example public and internal) from tagged types and fields. | pothos: `@pothos/plugin-sub-graph` (`subGraphs`, `toSchema({ subGraph })`). graphql-ruby: visibility `profiles:` | partial: per-request visibility hooks | medium | Visibility is per request and not applied to `print_schema`. |
| Print schema as seen by a context | Dumps the SDL for one visibility profile or request context. | graphql-ruby: `Schema.to_definition(context:)` | missing | medium | `print_schema` always prints the full schema. A public SDL file is not possible. |
| Named visibility profiles | Predefined, cached visibility profiles picked per request. | graphql-ruby: `use GraphQL::Schema::Visibility, profiles: { public:, beta: }`, `context[:visibility_profile]` | partial: per-request hooks and per-user introspection cache | low | Profiles would make visibility cache keys simpler. |
| Schema versioning by release date | Fields, args and types are added or removed in dated changesets. Clients pick a version by header. | graphql-ruby: [Enterprise] `GraphQL::Enterprise::Changeset` (`added_in`, `removed_in`, `context[:changeset_version]`) | partial: visibility hooks can do this by hand | low | Built on visibility, so Undine has the base. |
| Several definitions with one name | Two definitions of the same type or field name where only one is visible per request. | graphql-ruby: Visibility allows duplicate names | missing | low | Used for type migrations. I think the Undine type registry rejects conflicting names. |
| Import types or merge an external schema | Adds types from another executable schema (for example remote or legacy) into the code-first schema. | pothos: `@pothos/plugin-add-graphql` (`add: { schema, types }`, `addGraphQLObject`). nexus: `makeSchema({ mergeSchema })` | partial: `Field(<GraphQL type>)` accepts a raw graphql-core type | low | Useful for migration from graphene or strawberry. Root field merge is missing. |
| SDL to code converter | Generates code-first definitions from SDL. | pothos: `@pothos/converter`. nexus: `convertSDL`, `SDLConverter` | missing | low | One-time migration tool. |
| Schema from introspection result | Builds a schema object from introspection JSON. | graphql-ruby: `Schema.from_introspection` | missing | low | Tooling only. |
| Extend a type from many modules | Adds fields to an existing type from other modules or apps. | nexus: `extendType`, `extendInputType`, `queryField`. absinthe: `extend object`, `import_fields` | missing | low | I think a Django app cannot add fields to another app's QueryType without subclassing. Not verified. |
| Mock resolvers per build | Replaces listed resolvers with hand-written mocks when building a schema. | pothos: `@pothos/plugin-mocks` (`toSchema({ mocks })`) | missing | low | Mostly for frontend work before the backend is ready. |
| Default nullability setting | Sets whether fields are nullable and inputs required by default. | pothos: `defaultFieldNullability`, `defaultInputFieldRequiredness`. nexus: `nonNullDefaults` | partial: per element `nullable=` and `required=` | low | No global switch. |
| Write SDL file automatically in development | Writes the SDL file on every start in development. | nexus: `outputs.schema`, `shouldGenerateArtifacts` | partial: `print_schema` and `print_schema --check` | low | Manual command is enough for CI. |
| Replace or transform schema at runtime | Swaps the schema or applies transform functions while running. | mercurius: `app.graphql.replaceSchema`, `transformSchema`, `schemaTransforms` | missing | low | Django apps restart on deploy. |
| Per-request name conversion | Picks camelCase or snake_case naming per request. | absinthe: `Absinthe.Adapter` (`LanguageConventions`, `Underscore`, `Passthrough`) | partial: global `CAMEL_CASE_SCHEMA_FIELDS` | low | Rarely needed. |
| JIT query compilation | Compiles hot queries into fast executors. | mercurius: `jit`, adaptive JIT (`graphql-jit`) | missing | low | No Python equivalent of `graphql-jit`. I think it is a large project. |

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Detect unoptimized custom resolvers | Warns or errors when a custom resolver does not use the planned query. | pothos: prisma `onUnusedQuery: 'warn' \| 'error' \| fn` | missing | medium | Undine docs say custom resolvers must add their own optimizations. A dev-mode warning would catch N+1 bugs early. |
| Aggregate and group-by entrypoints | Root or relation fields that return count, sum, avg, min, max and grouped results with filters. | typegraphql: typegraphql-prisma `aggregate`, `groupBy`. graphweaver: `users_aggregate(filter)`, relation `albums_aggregate`. pothos: prisma `t.relationCount`, prisma-next `t.relationAggregate` | partial: per-field `Count`, `Subquery` expressions and `Calculation` | medium | No generated aggregate entrypoint and no FilterSet on aggregates. No grep hits for aggregate or group by in `undine/` or `docs/`. |
| Batch field resolver | A field resolver gets all parent objects at once and returns a list. | graphql-ruby: `resolve_batch:` in `Execution::Next` | missing | medium | Would give batching in sync mode, where Undine has no DataLoader. |
| SQL query tags with GraphQL context | Adds operation name and field path to SQL comments. | graphql-ruby: `GraphQL::Current` with `ActiveRecord::QueryLogs` | missing | medium | Helps find slow queries. Django `connection.execute_wrapper` can add the comments. |
| Non-model union and interface members | Resolves abstract types with `isTypeOf` per member or `__typename` in data. | nexus: `features.abstractTypeStrategies`. graphql-ruby: `resolve_type` returning `[Type, object]` | partial: members must be QueryTypes, matched by exact model class | medium | I think function entrypoints cannot return a union of `TypedDict` types. Not verified. |
| Typed object for a JSON column | Exposes a JSON column as a typed nested object instead of the `JSON` scalar. | graphweaver: virtual entities, `serialize`/`deserialize` | partial: function `Field` returning `TypedDict` | medium | I think a `JSONField` cannot be mapped to a declared `TypedDict` directly. Not verified. |
| Non-ORM data providers | Pluggable sources (REST, SaaS APIs) back types with the same list, filter and relation API. | graphweaver: `BackendProvider`, `RestBackendProvider`, `XeroBackendProvider` | partial: function entrypoints and fields | low | Undine is model-centric on purpose. |
| Cross-source relationships | Relations from a model to an entity in another source, batched and filterable. | graphweaver: `@RelationshipField` across providers, `QueryManager` | missing | low | Depends on non-ORM sources. |
| Batched fallback load for missing data | Loads data the planner did not fetch with one batched query by primary key. | pothos: prisma and drizzle fallback queries | missing | low | Django lazy loads per instance instead. I think this is hard with the Django ORM. |
| Read replica or per-request database client | Picks the database client per request. | pothos: prisma and drizzle `client: (ctx) => client` | missing | low | Django database routers cover this. I think no Undine feature is needed. |
| Lookahead helper | Public API to ask if a sub-field is selected, with its arguments. | graphql-ruby: `extras: [:lookahead]`, `Lookahead#selects?`. absinthe: `Absinthe.Resolution.project` | partial: optimizer reads the AST internally | low | I think no public helper exists for custom resolvers. Not verified. |
| Nullability guard | Replaces null in non-null positions with fallback values. | nexus: `nullabilityGuardPlugin` | partial: `@semanticNonNull`, `EXPERIMENTAL_DISABLE_ERROR_PROPAGATION` | low | Hides bugs. Semantic non-null is the modern approach. |
| Per-request enum values | Enum values change per request. | graphql-ruby: `Enum.enum_values(context)`, enum value `visible?` | partial: `Order` visibility only | low | I think model choice enums have no visibility hook. |
| Return pre-built JSON | A resolver returns a raw value that skips further resolution. | graphql-ruby: `context.raw_value(...)` | missing | low | Niche. |
| Response deduplication | Removes repeated objects from the response. The client rebuilds them. | graphweaver: `graphqlDeduplicator` | missing | low | Needs a client helper. Non-standard. |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative input validation | Built-in validators (length, format, range, inclusion, exactly one of) or schema-library validation on arguments and inputs. | pothos: `@pothos/plugin-validation` (Standard Schema), `@pothos/plugin-zod`. graphql-ruby: `validates: { length:, format:, numericality:, inclusion:, required: { one_of: } }`. mercurius: mercurius-validation `@constraint`. typegraphql: `validate` with class-validator, `validateFn` | partial: `__validate__`, `@<input>.validate`, `MUTATION_FULL_CLEAN` | medium | Django model field validators could be reused. No pydantic integration. |
| Atomic number operations | Updates a number with `increment`, `decrement`, `multiply`, `divide`. | pothos: prisma-utils `prismaIntAtomicUpdate`. nexus: nexus-plugin-prisma `atomicOperations` | missing | medium | Maps to `F("x") + n`. Avoids race conditions. |
| Optimistic locking | Rejects an update when the row version changed since the client read it. | graphweaver: mikroorm `version` input, `OptimisticLockError` | missing | medium | Common need in admin-style apps. |
| Filtered bulk update and delete | Updates or deletes all rows that match a filter. | nexus: nexus-plugin-prisma `updateManyUser`, `deleteManyUser`. graphweaver: `deleteUsers(filter:)`. typegraphql: typegraphql-prisma `updateMany`, `deleteMany` | missing | medium | Undine bulk mutations need a list of inputs with pk. |
| Upsert by unique lookup | Creates or updates based on a unique field. | nexus: nexus-plugin-prisma `upsertOneUser`. typegraphql: typegraphql-prisma `upsert`. graphweaver: `createOrUpdateUsers` | partial: `custom` kind acts as create or update by `pk` | medium | Lookup by other unique fields is missing. |
| User-defined oneOf input objects | An input object where exactly one field must be set. | pothos: `inputType(..., { isOneOf: true })`. graphql-ruby: `one_of`. absinthe: `directive :one_of` | partial: `@oneOf` used only for GenericForeignKey inputs | medium | No public way to mark a MutationType or `TypedDict` input as `@oneOf`. |
| Required but nullable input | The client must pass the argument but may pass null. | graphql-ruby: `required: :nullable` | missing | medium | Inventory lists that required and nullable cannot be separated. |
| Load objects from ID arguments | An ID argument loads the object, checks type and authorization before the resolver. | graphql-ruby: `argument ..., loads: Types::Thing`. absinthe: relay `ParseIDs` middleware. pothos: relay `t.arg.globalID({ for: [Ref] })` | partial: `Input(Model)` fetches by pk in MutationTypes | medium | I think function entrypoint arguments cannot load models and global IDs are not decoded. Not verified. |
| Presigned media uploads | Fields that return presigned upload, download and delete URLs for object storage. | graphweaver: `S3StorageProvider`, `getUploadUrl`, `@MediaField` | missing | medium | Inventory lists no presigned-URL flow. Could build on Django storages. |
| Relay mutation input and payload | Creates `<Name>Input` and `<Name>Payload` with `clientMutationId`. | pothos: relay `relayMutationField`. graphql-ruby: `RelayClassicMutation`. absinthe: relay `payload field` | missing | low | Older Relay style. Undine returns the QueryType directly. |
| Replace explicit null with default | Uses the default value when the client sends null. | graphql-ruby: `replace_null_with_default: true` | missing | low | Small option. |
| Audit trail of changes | Records who changed what in each mutation. | graphweaver: mikroorm `TrackedEntity`, `ChangeTracker` | missing | low | Django packages (django-simple-history, django-auditlog) cover it. |
| Client-generated primary keys | Clients send the primary key on create. | graphweaver: `apiOptions.clientGeneratedPrimaryKeys` | partial: I think an explicit `Input("pk")` works for non-auto keys | low | Not verified. |
| Reusable argument maps | Defines a set of arguments once and reuses it. | pothos: `builder.args(...)` | partial: `TypedDict` input arguments, `Calculation` | low | I think Python covers this. |

## 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Nested filter input for relations | Uses the related model's filter input inside the parent filter. | nexus: nexus-plugin-prisma `M_WhereInput` nesting. pothos: prisma-utils `prismaWhere`. graphweaver: relationship filters (`tasks: { name: "x" }`) | missing | medium | `Filter` cannot reference another `FilterSet`. I checked `convert_to_filter_ref`. |
| Relation quantifier filters | Filters by whether some, every or none of the related rows match. | nexus: nexus-plugin-prisma `some`, `every`, `none`. pothos: prisma-utils `prismaListFilter({ ops: ['every','some','none'] })` | partial: relation lookups give "some" semantics | medium | "every" and "none" need a custom function filter. |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Connection from a list or custom source | The resolver returns a list or a slice and the library builds edges, cursors and page info. | pothos: relay `resolveArrayConnection`, `resolveCursorConnection`. nexus: `connectionPlugin` `nodes`. absinthe: relay `Connection.from_list`, `from_slice`. graphql-ruby: `Schema.connections.add`, `ArrayConnection` | partial: custom `PaginationHandler` for querysets | medium | `Connection` wraps only QueryType, UnionType or InterfaceType. Function entrypoints cannot return a connection. |
| Custom edge fields | Adds fields to edge types, for example through-model data. | pothos: `builder.edgeObject`, drizzle and prisma connection helpers. nexus: `extendEdge`. graphql-ruby: custom edge fields. absinthe: `{node, edge_attrs}` tuples | missing | medium | Many-to-many through-model data on edges is a common Django need. |
| `nodes` shortcut on connections | Adds `nodes` next to `edges`. | pothos: relay `nodesOnConnection`. nexus: `includeNodesField`. graphql-ruby: `has_nodes_field` | missing | medium | Inventory lists it as not supported. |
| Extra fields on all connections | Adds custom fields to every connection type or one connection. | pothos: relay `globalConnectionField(s)`. nexus: `extendConnection` | missing | low | I think a custom `PaginationHandler` cannot add schema fields. |
| Restrict pagination direction | Disables forward or backward pagination or requires `first` or `last`. | nexus: `disableBackwardPagination`, `strictArgs`, `validateArgs`. absinthe: relay `paginate: :forward` | missing | low | Backward keyset pagination can be costly. |
| Separate default and max page size | Default size when `first` is missing, and a separate max. | graphql-ruby: `default_page_size`, `max_page_size` | partial: one `page_size` acts as default and max | low | I checked `undine/relay/validation.py`. |
| Encrypted or versioned cursors | Encrypts cursors and IDs and supports encoder versions. | graphql-ruby: [Pro] `GraphQL::Pro::Encoder`, `Encoder.versioned` | missing | low | Undine cursors are base64 of ordering values, so they show data values. |
| Count-only connection query | Skips the row query when only `totalCount` is selected. | pothos: drizzle `totalCountOnly` | missing | low | I think Undine still fetches rows. Not verified. |
| Custom connection type names | Sets connection and edge type names. | nexus: `getConnectionName`, `getEdgeName` | partial: I think names come from the wrapped type | low | Not verified. |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Plural `nodes` entrypoint | Refetches many objects by global ID. | pothos: relay `Query.nodes`, `t.nodeList`. graphql-ruby: `HasNodesField` | missing | medium | Inventory lists it as not supported. |
| Custom global ID encoding | Replaces the global ID format. | pothos: relay `encodeGlobalID`, `decodeGlobalID`. absinthe: relay `IDTranslator`. graphql-ruby: `Schema.id_from_object`, `object_from_id` | missing | low | `to_global_id` is fixed base64. |

## 9. DataLoaders

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| DataLoader in sync mode | Batching without asyncio. | graphql-ruby: fiber-based `GraphQL::Dataloader`. absinthe: `Absinthe.Middleware.Batch` (plugin resolution passes) | missing | medium | Inventory lists no DataLoader in sync mode. A breadth-first pass could do it. |
| Built-in model loaders | Ready loaders by model key and by relation. | graphql-ruby: `ActiveRecordSource`, `ActiveRecordAssociationSource`. absinthe: `Dataloader.Ecto` | missing | low | The optimizer covers most model data. Useful in custom resolvers. |
| Field-bound loaders | A loader attached to a field that batches by parent and args. | pothos: `t.loadable({ byPath: true })`, `loadableObject`. mercurius: `loaders: { Type: { field } }` | missing | low | Manual today with `DataLoader`. |
| Parameterized loader instances | One loader class with batch parameters gives separate instances. | graphql-ruby: `dataloader.with(Source, *params)` | missing | low | Manual today. |
| Loader result helpers | Sort results to keys and group flat results by key. | pothos: dataloader `sort`, `t.loadableGroup` | missing | low | Small helpers. |
| Reset loaders in long-lived contexts | Clears all loaders, for example between subscription events. | pothos: `clearAllDataLoaders(context)` | partial: `clear_all()` per loader, cleared on `request_finished` | low | I think WebSocket subscriptions do not trigger `request_finished`. Not verified. |

## 12. Directives

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Runtime behavior for custom directives | Directive hooks that skip nodes or wrap field resolution. | graphql-ruby: `Directive.include?`, `Directive.resolve`, `Feature`, `Transform`, `Flagged`. absinthe: directive `expand` | missing | medium | Undine directives are metadata only. Behavior needs a validation rule or hook. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Enum value deprecation | Marks single enum values as deprecated. | pothos: `enumType` values `deprecationReason`. nexus: `enumType` `deprecation`. typegraphql: `valuesConfig` | partial: `Order(deprecation_reason=...)` only | low | I think model choice enums cannot deprecate a value. Not verified. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative role or scope permissions | Named scopes or roles attached to types, fields and operations. One global checker evaluates them. | pothos: `@pothos/plugin-scope-auth` (`authScopes`, `$any`, `$all`). typegraphql: `@Authorized(roles)`, `authChecker`. graphweaver: `@ApplyAccessControlList` with per-action `rowFilter` | partial: `__permissions__`, `__filter_queryset__` and decorator hooks | high | Inventory lists no declarative permissions and no `has_perm` integration. Could map to Django groups and permissions. |
| Policy library integration | Uses an existing policy library for objects, fields and list scopes. | graphql-ruby: [Pro] `PunditIntegration`, `CanCanIntegration` | missing | medium | Django equivalents are django-rules and django-guardian. |
| Denied object becomes null or fallback | Returns null or a fallback value instead of an error on denial. | pothos: scope-auth `unauthorizedResolver`. typegraphql: `authMode: "null"`. graphql-ruby: `Schema.unauthorized_object` returning nil | partial: `__filter_queryset__` pattern, `EmptyFilterResult` | medium | No generic fallback for permission failures. |
| Column restrictions that also cover filters and inputs | A restricted field fails when selected, filtered on, or written. | graphweaver: ACL `fieldRestrictions`, `RestrictedFieldError` | partial: separate field, input and inline filter checks | medium | I think a field permission does not stop filtering or ordering by that field. Not verified. |
| Implicit deny by default | Types without an access rule are not accessible. | graphweaver: implicit deny, `setImplicitAllow(true)` | missing | medium | A secure-by-default setting. |
| Authorize once per subscription | Checks permissions when the subscription starts, not per event. | pothos: scope-auth `authorizeOnSubscribe: true` | partial: entrypoint permissions run per yielded value | medium | Per-event checks cost queries. |
| Type-level permission before every field | A permission on a type that runs before each of its fields. | pothos: scope-auth type `authScopes`, `skipTypeScopes` | partial: `QueryType.__permissions__` runs per instance | low | Different timing. |
| Argument-level authorization | Checks permission for a single argument value. | graphql-ruby: `Argument#authorized?` | partial: `@<input>.permissions` for MutationType inputs only | low | No hook for entrypoint or field arguments. |
| Authentication vs authorization errors | Separate error codes for "not logged in" and "not allowed". | typegraphql: `AuthenticationError`, `AuthorizationError` | partial: `GraphQLPermissionError` | low | I think there is no separate unauthenticated error class. Not verified. |
| Superuser bypass | One role skips all access rules. | graphweaver: `setAdministratorRoleName` | missing | low | Easy with `is_superuser` in hooks. |
| Granted scopes along a path | A parent field grants a scope to the returned object path. | pothos: scope-auth `grantScopes`, `$granted` | missing | low | Niche. |
| Disable auth in tests | Builds the schema with auth off. | pothos: `toSchema({ disableScopeAuth: true })` | missing | low | Tests can mock hooks. |
| Step-up multi-factor checks | Requires a recent second factor and returns a challenge error. | graphweaver: `@ApplyMultiFactorAuthentication`, `ChallengeError` | missing | low | Authentication belongs to Django auth packages. |
| Built-in authentication mutations | Login, magic link, OTP, passkey and API key flows. | graphweaver: `Password`, `MagicLink`, `OneTimePassword`, `Passkey`, `ApiKey` | missing | low | Django auth and allauth cover this. I think it is out of scope. |

## 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Plain query depth limit | Rejects documents deeper than N. | pothos: complexity `limit: { depth }`. mercurius: `queryDepth`. graphql-ruby: `max_depth`. graphweaver: GraphQL Armor | partial: `MaxListNestingDepthRule` counts only to-many nesting | medium | Inventory lists no plain depth rule. |
| Argument-based complexity | Field cost from args and child cost, with list multipliers from `first` or `limit`. | pothos: complexity `(args, ctx) => ...`, `defaultListMultiplier`. nexus: `queryComplexityPlugin` `childComplexity`. graphql-ruby: `complexity: ->(ctx, args, child_complexity)`. absinthe: `complexity fn args, child_complexity` | partial: fixed `complexity` numbers counting queries | medium | Undine bounds rows with nesting depth and page size. |
| Rate limiting | Limits requests, concurrent operations or processing time per client. | graphql-ruby: [Enterprise] `ActiveOperationLimiter`, `RuntimeLimiter`, `MutationLimiter` | missing | medium | Inventory lists no rate limiting. Django cache could hold counters. |
| Execution timeout in sync mode | Stops resolving new fields after a time limit. | graphql-ruby: `GraphQL::Schema::Timeout` | partial: `EXECUTION_TIMEOUT_SECONDS` in async only | medium | Inventory lists no sync timeout. |
| Deprecated field usage report | Lists deprecated fields, args and enum values used by an operation. | graphql-ruby: `GraphQL::Analysis::FieldUsage` | missing | medium | Helps plan removals. Could log or add a response extension. |
| Per-request limits and rules | Picks complexity limits or validation rules per request. | pothos: complexity `limit: (ctx) => limits`. mercurius: `validationRules: (...) => rules` | partial: global settings and `ADDITIONAL_VALIDATION_RULES` | medium | Useful for per-user or staff limits. |
| Query breadth limit | Rejects operations that select too many fields. | pothos: complexity `limit: { breadth }` | missing | low | Partly covered by `MAX_TOKENS` and `MAX_ALLOWED_ALIASES`. |
| Compute complexity without executing | Public function that returns the cost of a document. | pothos: `complexityFromQuery` | missing | low | I think the logic is only inside `MaxComplexityRule`. |
| Validation timeout | Limits time spent in validation. | graphql-ruby: `Schema.validate_timeout` | missing | low | Token and error limits cover most cases. |
| Separate cache for invalid documents | Caches validation errors apart so bad queries do not evict good ones. | mercurius: `cache` option | partial: `ValidationCacheHook` | low | I think Undine has one LRU. Not verified. |
| Custom analyzer API | Visitor analyzers that run before execution and can reject operations. | graphql-ruby: `GraphQL::Analysis::Analyzer` | partial: `ADDITIONAL_VALIDATION_RULES` | low | Validation rules are the Python equivalent. |

## 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Topic subscriptions with publish from code | Subscriptions on topics from args, with filters. Code or a mutation publishes events. | typegraphql: `@Subscription({ topics, topicId, filter })`, `pubSub.publish`. mercurius: `pubsub.subscribe`, `withFilter`. absinthe: `config` topic, `trigger :mutation`, `Absinthe.Subscription.publish`. graphql-ruby: `subscriptions.trigger`, `subscription_scope` | partial: `SubscriptionBroker.publish` and `subscribe`, signal subscriptions with `topic` and `filter` | medium | I found no docs for publishing custom events through the broker. |
| Broadcast and shared resolution | Runs one subscription result once and sends it to all matching subscribers. | graphql-ruby: `broadcast: true`, `broadcastable:`. absinthe: `context_id`, batched resolution of subscription docs | missing | medium | I think Undine runs the QueryType per subscriber for signal subscriptions. Not verified. |
| Smart subscriptions (live queries) | A query field re-runs when registered events fire. | pothos: `@pothos/plugin-smart-subscriptions` | partial: `ModelSaveSubscription` and signal subscriptions | medium | Re-running a whole query on change is missing. |
| Subscription catch-up | Sends initial or missed state when a subscription starts. | absinthe: open PR #1168 (priming). graphql-ruby: `#subscribe` initial value | missing | low | Inventory lists no replay. |
| Hosted push transports | Delivers subscriptions through Pusher or Ably. | graphql-ruby: [Pro] `PusherSubscriptions`, `AblySubscriptions` | missing | low | Channels covers self-hosted. |

## 18. Incremental delivery (@defer and @stream)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Optimizer skips deferred fragments | Leaves `@defer` selections out of the first query and loads them later. | pothos: prisma and drizzle `skipDeferredFragments` | missing | medium | I think the optimizer plans deferred fields into the first query. Then `@defer` saves no database time. Not verified. |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cache invalidation on writes | Tags cache entries and invalidates them after mutations, or checks object versions before serving. | mercurius: mercurius-cache `references`, `invalidate`. graphql-ruby: [Enterprise] `ObjectCache` with `object_fingerprint_for` (`cache_key_with_version`) | missing | high | Inventory lists no invalidation. Django signals or `updated_at` could drive it. |
| Resolver-level result cache | Caches single resolver results with TTL and custom keys. | mercurius: mercurius-cache `policy`, `ttl`, `extendKey` | missing | medium | Inventory lists no per-field result caching. |
| Stale-while-revalidate | Serves a stale entry while it refreshes. | mercurius: mercurius-cache `stale` | missing | low | Needs async background work. |
| Concurrent request deduplication | Runs identical concurrent resolver calls once. | mercurius: mercurius-cache (`async-cache-dedupe`) | missing | low | Async mode only. |
| Cache metrics hooks | Callbacks for cache hits, misses and skips. | mercurius: `onHit`, `onMiss`, `onSkip`. graphql-ruby: `context[:object_cache]` metrics | missing | low | Useful for metrics. |

## 20. File upload

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Upload size and count limits | Limits file size and count in multipart requests. | mercurius: mercurius-upload `maxFileSize`, `maxFiles` | partial: I think Django upload settings apply | low | Not verified for the GraphQL multipart parser. |

## 21. Persisted documents and APQ

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-client operation store with usage tracking | Stores operations per client, tracks last use, archives and indexes used fields. | graphql-ruby: [Pro] `GraphQL::Pro::OperationStore` | partial: `PersistedDocument` model, read-only admin | medium | A field usage index helps safe schema changes. |
| Allow lists picked per request | Several trusted document lists. A function picks the lists per user or header. | graphweaver: `trustedDocuments.allowList` function | partial: `PERSISTED_DOCUMENTS_ONLY` with one global set | low | Could limit internal operations to staff. |
| Static document map or manifest | Loads trusted documents from a file or settings at startup. | mercurius: `persistedQueries`, `preparedOnly`. graphweaver: `trustedDocuments.manifest`. absinthe: `DocumentProvider.Compiled` | partial: registration view and database model | low | A file-based allow-list is simpler for some deployments. |
| Pluggable APQ store | Swappable store for APQ (memory LRU, Redis). | mercurius: `persistedQueryProvider`, `.automatic(maxSize)` | partial: swappable model | low | A cache backend option could be faster. I think. |
| Client sync tool with signed requests | CLI that uploads client operations with an HMAC header. | graphql-ruby: `graphql-ruby-client sync` | partial: `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK` can check a signature | low | Frontend tools exist. |

## 22. Lifecycle hooks (middleware / extensions)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Per-field middleware and field extensions | Attaches reusable middleware to selected fields, types or operations. | typegraphql: `@UseMiddleware`. graphql-ruby: `GraphQL::Schema::FieldExtension`. absinthe: `middleware Mod` and schema `middleware/3` callback | partial: `LifecycleHook.resolve` runs for every field | medium | No way to attach middleware to one Field or Entrypoint. |
| Global exception mapping | Maps application exception classes to GraphQL errors. | graphql-ruby: `Schema.rescue_from` | partial: `ERROR_MASKING_PREDICATE`, `IntegrityError` mapping | medium | Django `PermissionDenied`, `ValidationError`, `ObjectDoesNotExist` are not mapped. No grep hits in `undine/`. |
| Subscription lifecycle hooks | Hooks when a subscription ends or the WebSocket closes or errors. | mercurius: `onSubscriptionEnd`, `onSubscriptionConnectionClose`, `onDisconnect` | partial: `WEBSOCKET_CONNECTION_INIT_HOOK`, ping and pong hooks | medium | I found only an internal `websocket_disconnect`. |
| Build-time schema transform hooks | Plugin hooks that edit or remove types and fields at schema build. | pothos: `onTypeConfig`, `onOutputFieldConfig`. nexus: `plugin({ onAddOutputField, onMissingType })`. absinthe: `@pipeline_modifier`, prototype schema directives | partial: converters, undocumented `Directive.__connected__` | low | No documented plugin API for schema transforms. |
| Request logging with redaction | Logs every operation with sensitive variables filtered. | graphweaver: `LogRequests`, `logOnDidResolveOperation`. absinthe: `Absinthe.Logger` `filter_variables` | partial: redaction util for tracing | low | Easy with a `LifecycleHook`. |
| Response extensions from resolvers | Resolvers add keys to the top-level `extensions`. | graphql-ruby: `context.response_extensions` | partial: lifecycle hooks edit the result | low | I think no helper exists inside resolvers. |
| Skip middleware for simple fields | Fields that skip middleware for speed. | typegraphql: `@Field({ simple: true })` | partial: tracing skip predicates | low | Only for tracing hooks. |
| Inject custom resolver parameters | A decorator computes a resolver parameter. | typegraphql: `createParameterDecorator` | missing | low | `info.context.user` covers the common case. |
| Dependency injection container | Resolves resolvers and middleware from a DI container. | typegraphql: `container` | missing | low | Not common in Django. |
| Per-request tracing switch | Turns tracing off per request or by header. | graphweaver: `setDisableTracingForRequest`, `X-GRAPHWEAVER-SUPPRESS-TRACING`. graphql-ruby: field `trace: false` | partial: field span skip predicates | low | Sampling usually handles this. |

## 24. Integrations

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Prometheus and StatsD metrics | Sends operation and field timings as metrics. | graphql-ruby: `PrometheusTrace`, `StatsdTrace` | missing | medium | Inventory lists no Prometheus or StatsD integration. |
| Other APM traces | Traces for New Relic, AppSignal, Scout, X-Ray. | graphql-ruby: `NewRelicTrace`, `AppsignalTrace`, `ScoutTrace`. pothos: `@pothos/tracing-newrelic`, `@pothos/tracing-xray` | missing | low | Most accept OpenTelemetry. |
| Apollo Studio usage reporting | Reports schema and operation metrics to Apollo Studio. | mercurius: community `mercurius-apollo-registry`, `mercurius-apollo-tracing` | missing | low | Inventory lists it as not supported. |
| Resolver hit map | Counts how often each resolver runs. | mercurius: community `mercurius-hit-map` | missing | low | Helps find unused fields. |
| Sampled detailed traces | Samples production operations and stores profiles for review. | graphql-ruby: `DetailedTrace`, `PerfettoTrace`, `GraphQL::Dashboard` | missing | low | Sentry and OpenTelemetry cover this. |
| GraphiQL custom plugins | Adds extra GraphiQL plugins and wraps the fetcher. | mercurius: `graphiql: { plugins }`. absinthe: `Absinthe.Plug.GraphiQL` `interface:` options | partial: built-in explorer and history plugins | low | I think no setting adds plugins. |
| Generated admin UI | Web admin built from schema metadata. | graphweaver: `@exogee/graphweaver-admin-ui` | missing | low | Django admin already exists. |

## 25. Tooling, typing and testing

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Introspection JSON dump | Dumps the introspection result as JSON. | graphql-ruby: `rake graphql:schema:json`. absinthe: `mix absinthe.schema.json` | missing | low | I think `print_schema` only prints SDL. |
| Typed client operation codegen | Generates typed documents for client operations. | mercurius: mercurius-codegen `operationsGlob`. graphweaver: CLI codegen | missing | low | Frontend tools (graphql-codegen) cover this from the SDL. |
| Run one field in tests | Runs a single field with visibility, auth and loaders. | graphql-ruby: `GraphQL::Testing::Helpers#run_graphql_field` | missing | low | The pytest client covers most needs. |
| GraphQL-level backtrace | Adds field path, object and args to unhandled errors. | graphql-ruby: `GraphQL::Backtrace` | partial: `INCLUDE_ERROR_TRACEBACK` | low | Python tracebacks already show resolvers. |
| GraphQL document formatter | Formats `.graphql` files and embedded documents. | absinthe: `Absinthe.Formatter`, `~GQL` sigil | missing | low | Prettier covers `.graphql` files. |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query batching | Runs an array of operations in one HTTP request and shares loaders. | mercurius: `allowBatchedQueries`. graphql-ruby: `Schema.multiplex`. absinthe: absinthe_plug transport batching | missing | medium | Inventory lists it as not supported. |
| CSRF prevention by header or content type | Blocks simple requests without a JSON content type or a custom header. | mercurius: `csrfPrevention: { allowedContentTypes, requiredHeaders }` | partial: Django CSRF middleware | low | Useful for token-auth APIs with `csrf_exempt`. |
| Legacy subscriptions-transport-ws | Supports the old `graphql-ws` subprotocol. | mercurius: `subscription` with `graphql-ws` subprotocol | missing | low | Protocol is deprecated. |
| Custom response serializer | Encodes responses in another format, for example MessagePack. | absinthe: absinthe_plug `:serializer`, `:json_codec` | missing | low | Niche. |
| HTTP QUERY method | Accepts the new HTTP `QUERY` method for reads. | mercurius: open PR (RFC 10008) | missing | low | Not released anywhere yet. |

## 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Default error types for all fields | A global list of error classes that every errors-as-data field catches. | pothos: errors `defaultTypes` | missing | medium | Saves repetition. A shared `Error` interface is the pattern there. |
| Per-item errors in lists | Each list item becomes a result union so one bad item does not fail the list. | pothos: errors `itemErrors` | missing | medium | I think `errors=[...]` works per field, not per list item. |
| Reusable named error union | Defines an error union once and reuses it. | pothos: `builder.errorUnion` | partial: `errors=[...]` builds a union per field | low | Each field gets its own union type. |
| Several success types in an error union | One union with many success types plus error types. | pothos: `t.errorUnionField` | missing | low | Niche. |
| Direct result without wrapper | Puts the object type directly in the result union. | pothos: errors `directResult: true` | partial: Undine builds a `<Type><Field>Value` wrapper | low | From the inventory. |
