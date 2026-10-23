# Lighthouse findings

Versions checked: `nuwave/lighthouse` v6.71.0 (2026-09-27). Repo `master` at `14205c8` (2026-10-07).
Lighthouse is a Laravel package. It is SDL-first: the schema is `.graphql` files, and behavior comes from server-side directives that map fields to Eloquent queries, mutations, validation, auth and caching.
The engine is webonyx/graphql-php (see `graphql-php.md`). This file does not repeat engine features (parser, validation rules, `Deferred`, `QueryComplexity`/`QueryDepth`, `ClientAware`, `ProvidesExtensions`).
PHP `^8`. Laravel 9 to 13 (`illuminate/*`). Needs `laragraph/utils` (HTTP request parsing) and `webonyx/graphql-php ^15`. MIT.
Optional: `laravel/pennant` (`@feature`), `laravel/scout` (`@search`), `mll-lab/graphql-php-scalars` (`@whereConditions`), `pusher/pusher-php-server`, `google/protobuf` (federated tracing), `mll-lab/laravel-graphiql` (IDE).
Docs source is in the repo under `docs/<major>/` (VuePress). `docs/6` and `docs/master` are identical. Site https://lighthouse-php.com/6/ is live. No `llms.txt` or `llms-full.txt` (404).
Changelog: `CHANGELOG.md` (Keep a Changelog). Upgrade notes: `UPGRADE.md`, already has a "v6 to v7" section.

## Maintenance status

- Active. Last commit on `master` 2026-10-07. Last push 2026-10-08. About 3500 stars. 140 open issues plus PRs. Not archived.
- Small, frequent minor releases on major 6. v6.71.0 (2026-09-27), v6.70.1 and v6.70.0 (2026-09-02), v6.69.2 (2026-07-29), v6.69.1 (2026-07-23).
- Lumen support is deprecated (v6.63.0). `_ide_helper.php` stub is deprecated (v6.71.0).
- Recent work: OPcache file-based query cache, validation result cache, `@bind`, Reverb broadcaster, encrypted subscription channels, `@hasOneThrough`, `@withoutGlobalScopes`, `SaveAwareArgResolver`, a Rector rule, Laravel 13.

## Architecture and request pipeline

- One route (`route.uri`, default `/graphql`) for `GET` and `POST` to `GraphQLController`. Laravel HTTP middleware applies as usual.
- Request parsing by `Laragraph\Utils\RequestParser` (JSON, `application/graphql`, form, multipart, GET params).
- Batched queries (a JSON array of operations) are always accepted. There is no config flag to turn batching off. Each operation fires `StartExecution`/`EndExecution`.
- Response: `SingleResponse` returns `response($result)`. The status is always 200 and the type is JSON. Bind `CreatesResponse` to change it. Not documented.
- `CanStreamResponse` / `ResponseStream` / `MemoryStream`: streaming response used by `@defer` (multipart chunks). Not documented outside defer.
- I think mutations over `GET` are not blocked. Lighthouse does not call graphql-php's `GetMethodSupportsOnlyQueryOperation` check, and `OperationParams::readOnly` is not used. `EnsureXHR` middleware blocks all `GET` if enabled.
- Context: `GraphQLContext` interface (`user()`, `setUser()`, `request()`). Default `HttpGraphQLContext`. Replace by binding `CreatesContext`. `SerializesContext` / `ContextSerializer` serialize context for queued subscription broadcasts (not documented).
- `transactional_mutations` (default `true`): each mutation field runs in a DB transaction (`TransactionalMutations`).
- Schema built from `schema_path` (default `graphql/schema.graphql`). `#import path.graphql` and wildcard `#import blog/*.graphql`. `extend type|input|interface|enum` is merged into one type.
- Schema transforms at build time: directives implementing manipulator interfaces rewrite the AST (for example `@paginate` creates `XPaginator`/`XConnection` types, `@orderBy` creates inputs and enums). Placeholder type `_` is replaced by the generated type.
- Resolver lookup: a `FieldResolver` directive wins. Else `ProvidesResolver` looks for class `Str::studly($fieldName)` with `__invoke` in `namespaces.queries` / `namespaces.mutations` / `namespaces.types` (`Type\Field` for non-root). Subscriptions use `ProvidesSubscriptionResolver`. Root fields without a resolver fail schema validation. Non-root fields fall back to the graphql-php default resolver.
- Resolver signature `__invoke(mixed $root, array $args, GraphQLContext $context, ResolveInfo $resolveInfo)`. Lighthouse `ResolveInfo` adds `argumentSet` (typed args with directives) and `enhanceBuilder()` (applies arg builder directives to a query builder).
- Programmatic types: `TypeRegistry::register()`, `registerLazy()`, `overwrite()`. Native graphql-php types can be mixed with SDL. `BuildSchemaString` event can add SDL. `SchemaStitcher` loads files with `#import`.
- Enums: `@enum(value:)` on SDL values, native PHP enums, `LaravelEnumType` for `bensampo/laravel-enum`.

## Built-in directives

Grouped by topic. Arguments are listed where useful. "Builder" means the directive takes `model`, `builder` (class@method returning a query builder) and `scopes`.

### Resolvers and model mapping

- `@field(resolver: "Class@method")`: point a field at a resolver function.
- `@method(name)`: call a method on the parent object. Field args are passed positionally.
- `@rename(attribute)`: read a different attribute. Also renames args/input fields (applied by `@renameArgs`).
- `@model(class)`: map an object type to a model class (used by `@node`, nested mutations, model detection).
- `@namespace(field:, ...)` on `FIELD_DEFINITION | OBJECT`: override default class namespaces for other directives.
- `@namespaced`: no-op resolver that returns an empty object. Allows nested "namespaced" query/mutation groups.
- `@interface(resolveType)` and `@union(resolveType)`: custom type resolver class for abstract types.
- `@scalar(class)`: bind a scalar to a PHP class.
- `@enum(value)`: internal value of an enum value.
- `@mock(key)`: test-only resolver hook used by the `MocksResolvers` trait. Not in the directive reference.

### Querying models

- `@all` (builder): return all models as a list.
- `@find` (model, scopes): find one model, args act as constraints. Throws if more than one match.
- `@first` (model, scopes): first matching model.
- `@paginate(type, model, builder, resolver, scopes, defaultCount, maxCount, complexityResolver)`: paginated list. `PaginateType`: `PAGINATOR` (offset, `PaginatorInfo` with total), `SIMPLE` (no count query), `CONNECTION` (Relay shape).
- `@count(relation, model, scopes, columns, distinct)`: count of a relation or model.
- `@aggregate(column, function, relation, model, builder, scopes)`: `AVG`, `SUM`, `MIN`, `MAX` on a relation or model. Batched.
- `@auth(guards)`: return the current user.
- `@search(within)`: Laravel Scout full-text search on an argument. Works only with `ScoutBuilderDirective` filters (`@eq`, `@trashed`/`@softDeletes`, `@builder`).
- `@limit(builder: Boolean)` on an argument: cap the number of returned items. With `builder: true` adds SQL `LIMIT`.
- `@lazyLoad(relations)`: lazy eager load relations on the returned collection. Can combine with `@paginate`.
- `@with(relation, scopes)`: eager load a relation (batched) without returning it.
- `@withCount(relation, scopes)`: eager load a relation count (batched).
- `@builder(method, value)`: call a custom method on the query builder. Works on args and fields.

### Relationships

- `@belongsTo`, `@hasOne`, `@hasOneThrough`, `@morphOne`, `@morphTo` (relation, scopes): single relation, batch loaded.
- `@hasMany`, `@hasManyThrough`, `@belongsToMany`, `@morphMany`, `@morphToMany` (relation, scopes, type, defaultCount, maxCount, edgeType): list relation. `type` gives `PAGINATOR`/`SIMPLE`/`CONNECTION` pagination of the relation, also batched. `edgeType` lets pivot data appear on connection edges.

### Filtering (argument builder directives)

- `@eq(key, value)`, `@neq(key)`, `@in(key)`, `@notIn(key)`, `@like(key, template, value)`: simple column conditions. `@like` `template` wraps the value (for example `%{}%`). `@eq`/`@like` with `value` also work on fields as fixed conditions.
- `@where(operator, key, clause, value, ignoreNull)`: generic `where` with operator or clause name (for example `whereYear`).
- `@whereBetween(key)`, `@whereNotBetween(key)`: input with `from`/`to`.
- `@whereNull(key, value)`, `@whereNotNull(key, value)`: boolean arg or fixed on field.
- `@whereJsonContains(key)`: JSON contains.
- `@whereKey(value)`: primary key condition.
- `@scope(name)`: call a local Eloquent scope with the arg value.
- `@withoutGlobalScopes(names)`: remove global scopes, driven by an arg.
- `@trashed` (arg) and `@softDeletes` (field): `Trashed` enum `ONLY`/`WITH`/`WITHOUT` filter for soft-deleted models.
- `@whereAuth(relation, guards)`: only rows owned by the current user (field builder).
- `@whereConditions(columns, columnsEnum, handler)` and `@whereHasConditions(relation, columns, columnsEnum, handler)`: client-built condition trees. Experimental, opt-in provider. See below.
- `@orderBy(columns, columnsEnum, relations, column, direction)`: on an argument it generates client ordering input. On a field it sets a fixed order. See below.

### Mutations

- `@create(model, relation)`, `@update(model, relation)`, `@upsert(model, identifyingColumns, relation)`, `@delete(model, relation, scopes)`: work on fields and as nested arg resolvers on inputs.
- `@createMany`, `@updateMany`, `@upsertMany(identifyingColumns)`: list variants.
- `@forceDelete(model, scopes)` and `@restore(model, scopes)`: soft delete operations.
- `@nest`: no-op arg resolver that delegates nested args to their own directives.
- `@spread`: flatten an input object into its parent args. Used for the Relay single `input` argument style.
- `@inject(context, name)`: put a context value (for example `user.id`) into args. Dot notation for nested args.
- `@event(dispatch)`: dispatch a Laravel event with the field result.
- `@async(queue)`: run a root mutation as a queued job (`AsyncMutation`). Field must return `Boolean!`. Returns `true` at once.
- `@upload(disk, path, public)`: store an uploaded file and replace the arg with the stored path.
- `@broadcast(subscription, shouldQueue)`: trigger a subscription with the mutation result.

### Input handling, validation and sanitization

- `@trim`, `@convertEmptyStringsToNull`: sanitize. On a field they apply to all args and input fields.
- `@hash`: hash the value with Laravel `Hash`.
- `@drop`: remove the arg before it reaches the resolver.
- `@rules(apply, attribute, messages)`: Laravel validation rules on one arg. Rule references are resolved relative to the arg.
- `@rulesForArray(apply, attribute, messages)`: rules on the list itself.
- `@validator(class)`: validator class on a field, an arg or an `INPUT_OBJECT`. Classes extend `Nuwave\Lighthouse\Validation\Validator` (`rules()`, `messages()`, `attributes()`).
- `@bind(class, column, with, required)`: replace an ID arg by the loaded model (or a callable's result), like route model binding. Lists bind to collections. Validates existence.
- `@globalId(decode)`: encode output as Relay global ID, or decode input to `ID`, `TYPE` or `ARRAY`.
- Internal field middleware, added to every field by `field_middleware` config, not in the reference: `@sanitize`, `@validate`, `@transformArgs`, `@spread` (as field step), `@renameArgs`, `@dropArgs`. They run the per-arg directives in phases.
- Arg phases: sanitize (`ArgSanitizerDirective`), validate, transform (`ArgTransformerDirective`).
- Validation errors go to `extensions.validation` as `{path: [messages]}` (`ValidationException::KEY`).
- Mutating rules like `exclude_if` and `exclude_unless` are not supported.

### Auth and security

- `@guard(with)` on fields or types: require authentication with given guards. Runs before other field middleware.
- `@canFind(ability, find, model, findOrFail, scopes, ...)`: policy check on models found by primary key arg.
- `@canModel(ability, model, ...)`: policy check on the model class (for example `create`).
- `@canQuery(ability, scopes, ...)`: policy check on models matched by the field's builder arg directives.
- `@canResolved(ability, ...)`: policy check on the resolved result. For non-mutating fields only.
- `@canRoot(ability, ...)`: policy check on the parent object.
- Common `@can*` args: `ability`, `injectArgs`, `args` (`CanArgs` literal), `action: CanAction` (`EXCEPTION_PASS`, `EXCEPTION_NOT_AUTHORIZED`, `RETURN_VALUE`), `returnValue`. All are `repeatable`.
- `@can`: deprecated, removed in v7.
- `@throttle(name, maxAttempts, decayMinutes, prefix)`: per-field rate limit with Laravel named limiters. Throws `RateLimitException`. Limiters that return a `response` are not supported.
- `@complexity(resolver)`: custom complexity function for graphql-php `QueryComplexity`.
- No fine-grained permission checks for nested mutation operations. `@can*` applies to the whole field.

### Schema visibility and deprecation

- `@show(env)` and `@hide(env)`: include or exclude by `app()->environment()` at schema build time.
- `@feature(name, when: ACTIVE|INACTIVE)`: include by Laravel Pennant feature at build time. Opt-in `PennantServiceProvider`. With a cached schema only features with nullable scope work.
- `@deprecated(reason)` on fields, args, input fields, enum values.
- There is no per-request visibility. All toggles are fixed when the schema is built.

### Caching

- `@cache(maxAge, private)`: cache a field result in the Laravel cache. `private` keys by user.
- `@cacheKey`: choose the field used as cache key (default the `ID` field).
- `@clearCache(type, idSource, field)`: clear tagged cache entries on mutation. Needs `cache_directive_tags` and a taggable store. Repeatable.
- `@cacheControl(maxAge, scope: PUBLIC|PRIVATE, inheritMaxAge)`: compute an HTTP `Cache-Control` header like Apollo. Experimental, opt-in provider.
- Key generation is replaceable through the `CacheKeyAndTags` interface (`CacheKeyAndTagsGenerator`).

### Relay

- `@node(resolver, model)`: add type to `Node` interface and `node(id:)` query. `NodeRegistry`.
- `@globalId`: see above. Global ID codec is `GlobalId` interface, default `Base64GlobalId`. Field name set by `global_id_field`.

### Subscriptions

- `@subscription(class)`: class extending `GraphQLSubscription` with `authorize()`, `filter()`, optional `encodeTopic()`/`decodeTopic()`.
- `@broadcast`: see mutations.

### Federation (Apollo Federation v2 subgraph, experimental, opt-in)

- `@key`, `@extends`, `@external`, `@requires`, `@provides`, `@shareable`, `@inaccessible`, `@override`, `@tag`, `@link`, `@composeDirective`, `@interfaceObject`. Not in the directive reference. Only in federation docs and source.

### Extension-internal directives

- `@defer(if)`: client directive on `FIELD`. Experimental, opt-in `DeferServiceProvider`.
- `@deferrable`, `@tracing`: added automatically by extensions. Do not use directly.

## Complex where conditions (`@whereConditions`)

- Generates `<Parent><Field><Arg>WhereConditions` input with `column`, `operator: SQLOperator = EQ`, `value: Mixed`, `AND`, `OR`, `HAS`. Column enum generated from `columns`, or reuse via `columnsEnum`. Without either, columns are free `String`.
- `HAS` input: `relation`, `operator` (default `GTE`), `amount` (default 1), `condition`.
- `SQLOperator`: `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `LIKE`, `NOT_LIKE`, `IN`, `NOT_IN`, `BETWEEN`, `NOT_BETWEEN`, `IS_NULL`, `IS_NOT_NULL`.
- No `NOT` combinator. No JSON operators yet (open PR #2793).
- `@whereHasConditions(relation)`: same grammar applied inside `whereHas`.
- Custom operator set: bind `Nuwave\Lighthouse\WhereConditions\Operator`. Custom handler: `handler` argument.
- Experimental, not enabled by default (`WhereConditionsServiceProvider`). Needs `mll-lab/graphql-php-scalars` for `Mixed`.

## Ordering (`@orderBy`)

- On an argument with type `_`: generates `[<Name>OrderByClause!]` input with `column` enum and `order: SortOrder` (`ASC`/`DESC`). Multiple clauses give secondary ordering.
- `columnsEnum` reuses an existing enum.
- `relations: [OrderByRelation!]` (`relation`, `columns`, `columnsEnum`): order by relation aggregates (count, or aggregate of a related column).
- On a field: fixed default order (`column`, `direction`).

## Pagination

- Offset paginator args `first: Int!` and `page: Int`. Returns `data` and `paginatorInfo` (`count`, `currentPage`, `firstItem`, `hasMorePages`, `lastItem`, `lastPage`, `perPage`, `total`).
- `CONNECTION`: args `first` and `after` only. No `last`/`before`. Cursor is base64 of the offset (`Pagination\Cursor`). Docs say real cursor pagination is not supported (issue #311). `PageInfo` adds non-Relay `total`, `count`, `currentPage`, `lastPage`.
- `pagination.default_count` and `pagination.max_count` config, per-field `defaultCount` and `maxCount`.
- Auto optimization: if `paginatorInfo`/`pageInfo` is not selected, it uses the simple paginator and skips the count query (`PaginationArgs`). Not documented.
- Relation pagination is batched across parents (`PaginatedModelsLoader`).

## Nested mutations

- Input fields named like Eloquent relation methods become nested operations. Relation methods must declare return types.
- `BelongsTo`: `connect`, `create`, `update`, `upsert`, `disconnect`, `delete`.
- `MorphTo`: `connect` (needs `id` and `type`), `disconnect`, `delete`.
- `HasOne`/`MorphOne`: `create`, `update`, `upsert`, `delete`.
- `HasMany`/`MorphMany`: `create`, `update`, `upsert`, `delete`, `connect`, `disconnect`.
- `BelongsToMany`/`MorphToMany`: `create`, `update`, `upsert`, `delete`, `connect`, `sync`, `syncWithoutDetaching`, `disconnect`. Pivot data via input with `id` plus pivot fields.
- `identifyingColumns` on `@upsert`/`@upsertMany` also works in nested upserts (v6.66).
- Whole mutation is one transaction when `transactional_mutations` is on.
- `force_fill` (default `true`): `forceFill()` instead of `fill()`, so no mass assignment protection.
- Polymorphic inputs are limited to operations whose input shape does not change (connect by ID, disconnect, delete).
- Build your own with `ArgResolver` and `SaveAwareArgResolver::runBeforeSave()`.

## N+1 and batching

- Relation directives batch load across parents through `RelationBatchLoader` and `ModelsLoader` (`SimpleModelsLoader`, `CountModelsLoader`, `AggregateModelsLoader`, `PaginatedModelsLoader`). `batchload_relations` config (default `true`).
- `BatchLoaderRegistry::instance($path, $factory)`: one batch loader per query path (for example `users.posts`). Resolver returns `GraphQL\Deferred`. Instances are cleared after each execution.
- `shortcut_foreign_key_selection` (default `false`): if the client selects only `id` of a `belongsTo`/`morphTo` target, return it from the foreign key without a query.
- No column projection. Models are loaded with `select *`. No SQL join optimizer.
- Federation `_entities`: one query per entity by default. `BatchedEntityResolver` for batching.

## Subscriptions

- Opt-in `SubscriptionServiceProvider`. Subscription query over HTTP returns a channel in `extensions.lighthouse_subscriptions`. Delivery is by a broadcaster, not a WebSocket server in Lighthouse.
- Broadcasters: `pusher`, `reverb` (Pusher protocol), `echo` (Laravel Echo with Redis), `log`. Custom drivers via `BroadcastManager` (`DriverManager`).
- Storage: `redis` (`RedisStorageManager`) or any Laravel cache store (`CacheStorageManager`). `storage_ttl` expires subscriptions.
- `queue_broadcasts` and `broadcasts_queue_name`: send broadcasts as queued jobs.
- `encrypted_channels`: Pusher/Echo private-encrypted channels.
- `exclude_empty`: omit `lighthouse_subscriptions` from responses without a channel.
- Pusher "channel existence" webhook route deletes vacated subscriptions.
- Trigger by `@broadcast` or `Subscription::broadcast($field, $root, $shouldQueue)`.
- `filter()` per subscriber. "Only to others" uses `X-Socket-ID`.
- No graphql-ws or SSE transport. A `feature/subscription-graphql-ws` branch exists but is stale (last commit 2023-05-24).

## Defer

- `@defer(if)` on fields, experimental, opt-in. Streams `multipart/mixed` chunks.
- `defer.max_nested_fields` and `defer.max_execution_ms`: after the limit, the rest resolves at once.
- No `@stream`.

## Caching and performance config

- Schema cache: `schema_cache.enable` (default off in `local`), `schema_cache.path`. Written atomically. `lighthouse:cache` to prebuild.
- Query cache (parsed AST): `query_cache.enable` (default `true`), `mode`: `store` (Laravel cache), `opcache` (PHP files), `hybrid` (OPcache with store fallback). `opcache_path`, `store`, `ttl`.
- Validation cache: `validation_cache.enable` (default `false`), `store`, `ttl`. Caches only error-free results. `QueryComplexity` always runs.
- APQ: `persisted_queries` (default `true`). Apollo-compatible. Needs the query cache. Returns `PERSISTED_QUERY_NOT_FOUND` and `PERSISTED_QUERY_NOT_SUPPORTED` codes.
- `parse_source_location` (default `true`): set `false` to drop `locations` from errors for speed.
- No trusted documents / persisted-only mode. There is no allow-list setting.

## Tracing

- Opt-in `TracingServiceProvider`. `tracing.driver`: `ApolloTracing` (default, `extensions.tracing`) or `FederatedTracing` (Apollo `ftv1` protobuf, needs `google/protobuf`). The v7 default will be `FederatedTracing`.

## Error handling

- `error_handlers` config chain. Defaults: `AuthenticationErrorHandler`, `AuthorizationErrorHandler`, `ValidationErrorHandler`, `ReportingErrorHandler`. `AlwaysReportingErrorHandler` also reports client-safe errors. Interface `Nuwave\Lighthouse\Execution\ErrorHandler`.
- `ErrorPool`: collect several errors and still return partial data.
- Exceptions: `AuthenticationException`, `AuthorizationException`, `ValidationException`, `RateLimitException`, `ClientSafeModelNotFoundException`, `DefinitionException`, `DirectiveException`, `SchemaSyntaxErrorException`.
- `debug` config uses graphql-php `DebugFlag`.

## Config file (`config/lighthouse.php`)

- `route`: `uri`, `name`, `middleware` (defaults `AcceptJson`, `AttemptAuthentication`, optional `EnsureXHR`, `LogGraphQLQueries`), `prefix`, `domain`, `where`. `route => false` disables the route.
- `guards`: auth guards for `@guard` and `AttemptAuthentication`. First authenticated guard wins.
- `schema_path`, `schema_cache.{enable,path}`.
- `cache_directive_tags`.
- `query_cache.{enable,mode,opcache_path,store,ttl}`, `validation_cache.{enable,store,ttl}`.
- `parse_source_location`.
- `namespaces`: `models`, `queries`, `mutations`, `subscriptions`, `types`, `interfaces`, `unions`, `scalars`, `directives`, `validators`. Each can be a list.
- `security`: `max_query_complexity`, `max_query_depth`, `disable_introspection` (env `LIGHTHOUSE_SECURITY_DISABLE_INTROSPECTION`).
- `pagination.{default_count,max_count}`.
- `debug`.
- `error_handlers`.
- `field_middleware`: global field middleware directive classes applied to every field.
- `global_id_field`.
- `persisted_queries`, `transactional_mutations`, `force_fill`, `batchload_relations`, `shortcut_foreign_key_selection`.
- `subscriptions`: `queue_broadcasts`, `broadcasts_queue_name`, `storage`, `storage_ttl`, `encrypted_channels`, `broadcaster`, `broadcasters` (`log`, `echo`, `pusher`, `reverb`), `exclude_empty`.
- `defer.{max_nested_fields,max_execution_ms}`.
- `federation.entities_resolver_namespace`.
- `tracing.driver`.

## Artisan commands

- `lighthouse:cache`: compile and cache the schema.
- `lighthouse:clear-schema-cache`: clear the schema cache. `lighthouse:clear-cache` is the deprecated alias.
- `lighthouse:clear-query-cache --opcache-only --opcache-ttl-hours=N`: clear the query cache. Not in the commands reference, only in the query caching page.
- `lighthouse:print-schema -W/--write -D/--disk --json --federation --sort`: print SDL or introspection JSON.
- `lighthouse:validate-schema`: build and validate the schema, fires `ValidateSchema`.
- `lighthouse:ide-helper --omit-built-in`: write `schema-directives.graphql` (all directive definitions), `programmatic-types.graphql`, and the deprecated `_lighthouse_ide_helper.php`.
- Generators: `lighthouse:query`, `lighthouse:mutation` (both `--full` for context and info args), `lighthouse:subscription`, `lighthouse:field`, `lighthouse:interface`, `lighthouse:union`, `lighthouse:scalar`, `lighthouse:directive` (`--type`, `--field`, `--argument` pick interfaces), `lighthouse:validator` (not in the commands reference).

## Extension points

- Custom directives: class `<Name>Directive` extending `BaseDirective`, with `definition()` returning SDL. Found in `namespaces.directives`, then namespaces from `RegisterDirectiveNamespaces`, then built-ins. `DirectiveLocator::setResolved()` registers a class directly (takes precedence since v6.70).
- Field interfaces: `FieldResolver`, `FieldMiddleware` (wrap resolver, run in lexical order), `FieldBuilderDirective`, `FieldManipulator` (AST), `ComplexityResolverDirective`, `ValidationDirective` (abstract class).
- Arg interfaces: `ArgDirective` vs `ArgDirectiveForArray` (per item or whole list), `ArgSanitizerDirective`, `ArgTransformerDirective`, `ArgBuilderDirective`, `ArgManipulator`, `ArgResolver`, `SaveAwareArgResolver`, `InputFieldManipulator`, `ArgumentValidation`/`ArgumentSetValidation` (not documented), `PreSaveArgumentsAware` (not documented).
- Type interfaces: `TypeManipulator`, `TypeMiddleware`, `TypeResolver`, `TypeExtensionManipulator`.
- Global field middleware: `field_middleware` config.
- Replaceable services by container binding: `CreatesContext`, `CreatesResponse`, `ProvidesResolver`, `ProvidesSubscriptionResolver`, `ProvidesValidationRules` / `ProvidesCacheableValidationRules` (custom query validation rules), `GlobalId`, `CacheKeyAndTags`, `WhereConditions\Operator`, `SerializesContext`, subscription `StoresSubscriptions`/`BroadcastsSubscriptions`.
- `WithReferenceRule::setArgumentPath()` for custom validation rules that reference other args.
- Default resolver: `Executor::setDefaultFieldResolver()`.

## Events (Laravel events)

- `StartRequest($moment, $request)`: request reached the controller.
- `StartOperationOrOperations($operationOrOperations)`: single or batched operations parsed.
- `BuildSchemaString($userSchema)`: listeners return extra SDL.
- `RegisterDirectiveNamespaces`: listeners return directive namespaces.
- `ManipulateAST($documentAST)`: change the AST before the executable schema is built.
- `StartExecution($moment, $schema, $query, $variables, $operationName, $context)`: per operation.
- `BuildExtensionsResponse($result, $queryComplexity)`: listeners return an `ExtensionsResponse` to add `extensions` keys.
- `ManipulateResult($result)`: change each operation result.
- `EndExecution($moment, $result)`: per operation.
- `EndOperationOrOperations($resultOrResults)`.
- `EndRequest($moment, $response)`.
- `ValidateSchema($schema)`: non-lifecycle, from `lighthouse:validate-schema`.
- Errors thrown in lifecycle events are handled per operation (v6.62).

## Scalars

- Built-in classes: `Date`, `DateTime`, `DateTimeTz`, `DateTimeUtc` (Carbon), `Upload` (input only, `UploadedFile`). Declared with `scalar X @scalar(class: "...")`.
- More scalars (`Mixed`, `JSON`, `Email`) come from `mll-lab/graphql-php-scalars`.

## HTTP, auth middleware and uploads

- `AttemptAuthentication`: log in once per request without rejecting guests.
- `AcceptJson`: force `Accept: application/json`.
- `EnsureXHR`: CSRF guard. Blocks `GET` and form-style `POST`. Enabled by default in v7.
- `LogGraphQLQueries`: log each query. Not documented.
- File uploads follow the graphql-multipart-request-spec.
- Sanctum works by setting the guard to `sanctum`.
- Stateful session login/logout through mutations is shown as an example.
- No built-in GraphiQL. Docs point to `mll-lab/laravel-graphiql`.

## Testing

- `MakesGraphQLRequests` trait: `graphQL($query, $variables)`, `postGraphQL()`, `multipartGraphQL()`, `introspect()`, `introspectType()`, `introspectDirective()`, `introspectByName()`, `streamGraphQL()` (defer chunks), `rethrowGraphQLErrors()`, `graphQLSubscriptionMock()`, `graphQLSubscriptionChannelName()`.
- `RefreshesSchemaCache`, `TestsSubscriptions`, `UsesTestSchema` (`$this->schema = ...`), `MocksResolvers` (`mockResolver()`, `mockResolverExpects()`), `MakesGraphQLRequestsLumen`.
- `TestResponse` mixins: `assertGraphQLValidationError`, `assertGraphQLValidationKeys`, `assertGraphQLValidationPasses`, `assertGraphQLError`, `assertGraphQLErrorMessage`, `assertGraphQLDebugMessage`, `assertGraphQLErrorFree`, `assertGraphQLSubscriptionAuthorized`, `assertGraphQLSubscriptionNotAuthorized`, `assertGraphQLBroadcasted`, `assertGraphQLNotBroadcasted`.
- PHPStan support through Larastan. Rector rule `RootResolverSignatureRector` fixes root resolver `__invoke` signatures (v6.69).

## Deprecation usage detection

- `Nuwave\Lighthouse\Deprecation\DetectDeprecatedUsage::handle(callable)`: experimental. Calls a handler with deprecated fields and literal enum values used in a query. Does not detect enum values in variables or results.

## Not supported

- No code-first API. Native graphql-php types can be added but lose most directive features.
- No real cursor pagination (offset in base64). No `last`/`before` on connections.
- No column projection or SQL join optimization. Only batching.
- No `@stream`. `@defer` is experimental.
- No graphql-ws, `subscriptions-transport-ws` or SSE transport. Subscriptions need Pusher, Reverb or Echo.
- No per-request schema visibility. `@show`/`@hide`/`@feature` are build-time.
- No trusted documents or operation allow-list.
- No GraphQL-over-HTTP status codes or `application/graphql-response+json`. Always 200 JSON.
- No setting to disable batched queries.
- No `NOT` in `@whereConditions`. No fine-grained auth on nested mutation operations.
- No federation gateway. Federation directive renaming and namespaced directives without import are not supported.
- No Apollo authorization directives (`@authenticated`, `@requiresScopes`, `@policy`) yet. Open PR #2774.
- No built-in GraphiQL. No DataLoader class (only `BatchLoaderRegistry` plus `Deferred`).
- No schema diff or breaking-change check command.

## Upcoming and unreleased work

- `CHANGELOG.md` "Unreleased" section is empty.
- `UPGRADE.md` "v6 to v7": automatic test trait setup, `EnsureXHR` on by default, `@can` removed, `lighthouse:clear-cache` removed, `_lighthouse_ide_helper.php` no longer generated. Tracing default will be `FederatedTracing`. No v7 branch or release date found.
- Open PRs (2026-10): pass promise results of chained resolvers to result handlers (#2794), JSON SQL operators in where conditions (#2793), fix built-in validation rules resolved as classes (#2792), force UTF-8 before `json_encode` (#2790), apply `@can*` action when resolver returns a promise (#2786), cache query AST as array in store mode (#2785), pagination with unlimited results (#2781), Apollo authorization directives (#2774), scope nested upsert lookups to parent relation (#2751), use graphql-php `ValidationCache` interface (#2733), read public PHP properties in default resolver (#2693), model events on nested belongsTo delete (#2588), `@with` multiple nested relations (#2525), only allow deletion of related models in nested mutations (#2454).
- Stale branches: `feature/subscription-graphql-ws` (2023), `lazy-root-types` (2023), `void` (2023), `generate-resolvers` (2022), `optional-root-query-type` (2021).

## Docs and code disagree

- `@show`, `@hide` and `@feature` reference SDL lists only `FIELD_DEFINITION` (and `OBJECT` for `@feature`). The code allows `ARGUMENT_DEFINITION | INPUT_FIELD_DEFINITION | FIELD_DEFINITION | OBJECT`, and all three are `repeatable`. The feature toggles guide matches the code.
- `the-basics/fields.md` says `Query.users` maps to class `App\GraphQL\Queries\User`. The code uses `Str::studly($fieldName)`, so it maps to `Users`.
- `complex-where-conditions.md` example uses `@paginated`. The directive is `@paginate`.
- The commands reference does not list `lighthouse:clear-query-cache`, `lighthouse:clear-schema-cache` or `lighthouse:validator`. It still lists the deprecated `clear-cache`.
- The directive reference does not list federation directives, `@defer`, `@mock`, or the internal field middleware directives (`@sanitize`, `@validate`, `@transformArgs`, `@renameArgs`, `@dropArgs`).
- Docs say requests follow "the informal specification at graphql.org". The response is always HTTP 200 JSON.

## Sources

Docs (read from repo source `docs/6/`, site https://lighthouse-php.com/6/):
- `api-reference/directives.md` (https://lighthouse-php.com/6/api-reference/directives.html), parsed for every directive SDL and compared with source.
- `api-reference/commands.md`, `api-reference/events.md`, `api-reference/scalars.md`, `api-reference/resolvers.md` (https://lighthouse-php.com/6/api-reference/commands.html and siblings).
- `eloquent/*.md` (https://lighthouse-php.com/6/eloquent/getting-started.html, https://lighthouse-php.com/6/eloquent/complex-where-conditions.html, https://lighthouse-php.com/6/eloquent/nested-mutations.html).
- `custom-directives/*.md`, `concepts/*.md`, `digging-deeper/*.md`, `performance/*.md`, `security/*.md`, `subscriptions/*.md`, `federation/*.md`, `testing/*.md`, `the-basics/fields.md`, `getting-started/*.md` (read as prose, code blocks skipped).
- `llms.txt` and `llms-full.txt`: 404.

Source: shallow clone of https://github.com/nuwave/lighthouse at `/tmp/lighthouse`. Read `src/lighthouse.php`, `src/Http`, `src/GraphQL.php`, `src/Console`, `src/Events`, `src/Support/Contracts`, `src/WhereConditions`, `src/Pagination`, `composer.json`.

Changelog: https://github.com/nuwave/lighthouse/blob/master/CHANGELOG.md. Upgrade notes: https://github.com/nuwave/lighthouse/blob/master/UPGRADE.md.

GitHub API: releases, repo metadata, branches, open PRs (https://api.github.com/repos/nuwave/lighthouse).
