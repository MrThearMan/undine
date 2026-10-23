# API Platform findings

Versions checked: `api-platform/core` v5.0.3 and v4.4.4 (both 2026-10-09). Repo `main` at `2bba68f` (2026-10-06).
API Platform builds REST (JSON-LD/Hydra, JSON:API, HAL, OpenAPI) and GraphQL from the same PHP classes plus attribute metadata (`#[ApiResource]`, `#[ApiProperty]`, operations, parameters).
GraphQL is an optional component, `api-platform/graphql`. It is a read-only subsplit of the monorepo `src/GraphQl`. Engine is webonyx/graphql-php `^15` (see `graphql-php.md`). This file does not repeat engine features.
PHP `>=8.2`. Symfony `^7.4 || ^8.0` (6.4 dropped in 4.4/5.0). Laravel is a second first-class host (`src/Laravel`). Data backends: Doctrine ORM, Doctrine MongoDB ODM, Eloquent, Elasticsearch (read only), or any custom state provider.
Docs source is a separate repo, `api-platform/docs`. Default branch is `4.3`. Branches `4.4` (2026-10-01), `5.0` and `main` exist. I read `4.4`. `core/graphql.md` is the GraphQL page (about 3150 lines). No `llms.txt`, `llms-full.txt` or `.md` page variants (all 404).
Changelog: `CHANGELOG.md` in the core repo. Upgrade notes: `docs/core/upgrade-guide.md`.

## Maintenance status

- Very active. Last commit on `main` 2026-10-06. Last push 2026-10-09. About 2580 stars. 152 open issues plus PRs. Not archived.
- Two maintained lines: 5.0.x (v5.0.0 2026-09-17, v5.0.3 2026-10-09) and 4.4.x (v4.4.0 2026-09-17, v4.4.4 2026-10-09). 4.3.x got patches until 2026-09-29.
- 20 commits on `main` after v5.0.3. None touch GraphQL.
- GraphQL gets mostly bug fixes. Last GraphQL features: configurable max depth and complexity (#6880, 4.1), Laravel GraphQL support and Laravel policies (#6550, 4.0), enum support (#5199, 3.1), extra args (#5359, 3.2), disable introspection (#5711, 3.2), partial page pagination (#6120, 3.3).
- No GraphQL code is marked `@experimental`. Laravel GraphQL is thinner than Symfony GraphQL (see "Symfony vs Laravel").

## Architecture and request pipeline

- One endpoint. Symfony route `api_graphql_entrypoint` at `/graphql` (`EntrypointAction`). Laravel route `api_graphql` at `{route_prefix}/graphql`, default `/api/graphql` (`ApiPlatform\Laravel\GraphQl\Controller\EntrypointController`). Both accept `GET` and `POST`.
- Request bodies: JSON (`query`, `variables`, `operationName`), `application/graphql` (must be added to `formats`), `multipart/form-data` per the GraphQL multipart request spec (needs `formats.multipart`), and GET query params.
- No batched queries. A JSON array body is not parsed as a batch. I think it fails with "GraphQL query is not valid".
- I think mutations over `GET` are not blocked. `EntrypointAction` calls `GraphQL::executeQuery` without a read-only check.
- Response is always `JsonResponse` with status 200, also for errors. No `application/graphql-response+json`.
- `GET` with `Accept: text/html` serves the default IDE (`default_ide`).
- Schema is built by `SchemaBuilder::getSchema()` from resource metadata. It is called on each request. Types load lazily through `typeLoader` and `TypesContainer`. Resource metadata is cached by the metadata cache.
- `Executor` adds graphql-php `DisableIntrospection`, `QueryComplexity` and `QueryDepth` rules through the static `DocumentValidator::addRule`. Swap the executor via `ExecutorInterface`.
- Every field resolver comes from `ResolverFactory`. It runs the GraphQL state provider chain, then the GraphQL state processor chain. Your code plugs in as state providers, state processors, or `resolver` classes. There is no free-form field resolver API.
- Provider chain (Symfony, by decoration priority): `ReadProvider` (500), `ParameterProvider` and `DenormalizeProvider` (300), `ValidateProvider` (200), `ResolverProvider` (190), validate after resolver (180), access checker after resolver (170). Access checkers also wrap read, denormalize and validate. Service ids: `api_platform.graphql.state_provider.*`.
- Processor chain: `SubscriptionProcessor` (200), `WriteProcessor` (100, calls the operation `processor`), `NormalizeProcessor` (normalizes with the GraphQL serializer).
- The root resolver normalizes the whole result with the Symfony Serializer. `SerializerContextBuilder` turns the GraphQL selection set (`ResolveInfo::getFieldSelection(PHP_INT_MAX)`) into serializer `attributes`. So only requested fields are normalized. Nested data comes from the normalized array. Nested collection fields that need args go back through the provider with link info (`linkClass`, `linkProperty`).
- No kernel events for GraphQL. `core/events.md` says "GraphQL is not supported". Custom Symfony controllers also do not work with GraphQL.
- Symfony profiler panel shows GraphQL requests (#5072).

## Resource metadata

- `#[ApiResource(graphQlOperations: [...])]`: the list of GraphQL operations. `null` means defaults. `[]` means no GraphQL root fields for the resource.
- Default GraphQL operations: `Query`, `QueryCollection`, `Mutation(name: 'create')`, `Mutation(name: 'update')`, `DeleteMutation(name: 'delete')`. With `mercure: true`, a `Subscription` is also added by default (`OperationDefaultsTrait::addDefaultGraphQlOperations`).
- BackedEnum resources get only `Query` and `QueryCollection(paginationEnabled: false)`.
- If a resource has no `Query` or `QueryCollection`, hidden "nested" ones are added (`Query::withNested(true)`). They allow the type to appear through relations without a root field.
- Resource-level options that also drive GraphQL: `shortName` (type name), `description`, `deprecationReason`, `normalizationContext`, `denormalizationContext`, `validationContext`, `security*`, `filters`, `parameters`, `pagination*`, `order`, `input`, `output`, `provider`, `processor`, `stateOptions`, `mercure`, `messenger`, `read`/`deserialize`/`validate`/`write`/`serialize`, `fetchPartial`, `forceEager`, `map` (Object Mapper), `rules`/`policy` (Laravel), `extraProperties`.
- Resource config also in YAML and XML (Symfony only).
- A resource with `shortName` `Node` throws. The name is reserved for the Relay interface.

## GraphQL operations (`ApiPlatform\Metadata\GraphQl\*`)

- `Operation` base. GraphQL-only options: `resolver`, `args`, `extraArgs`, `links`, `validateAfterResolver`, `securityAfterResolver`, `securityMessageAfterResolver`. Shares the common options above with HTTP operations.
- `Query`: item query. Root field name is `lcfirst(shortName)` (`book`), or `name + shortName` for named ones (`retrievedQueryBook`). Default args `id: ID!` (IRI). Has `nested`.
- `QueryCollection`: collection query. Field name is the pluralized short name (`books`) via Doctrine inflector. Gets pagination and filter args.
- `Mutation`: named mutation. Field `name + shortName` (`createBook`, `updateBook`). One `input` argument of type `{name}{ShortName}Input`. Payload type wraps the resource under `lcfirst(shortName)` plus `clientMutationId`. Default description "Creates a Book."
- `DeleteMutation`: payload has only `id` and `clientMutationId`.
- `Subscription`: field `update{ShortName}Subscribe`. Input `{id, clientSubscriptionId}`. Payload adds `mercureUrl`. Skipped from the schema if the operation has no `mercure` config.
- `create` input omits `id`. `update` makes every input field nullable (partial update). Nested relation input has optional `id`.
- The resource property `id` is exposed as `_id`. The GraphQL `id` field is the IRI. Not documented in `graphql.md`.
- Root operation `description` overrides the generated description. `deprecationReason` on operations and properties produces `isDeprecated`/`deprecationReason` in the schema.

## Properties (`#[ApiProperty]`)

- Relevant options: `description`, `readable`, `writable`, `readableLink`, `writableLink`, `required`, `identifier`, `default`, `example`, `deprecationReason`, `fetchable`, `fetchEager`, `security`, `securityPostDenormalize`, `types`, `schema`, `nativeType`, `property`, `serialize`, `policy` (Laravel), `extraProperties`.
- `readable: false` hides the field from output types. `writable: false` hides it from input types.
- `writableLink: true` lets a nested relation be written as an embedded input object. Otherwise relations in input are IRI strings.
- `security` on a property makes the GraphQL field nullable. Denied fields return `null`.
- A property with a `default` is nullable in the create input (#8568).
- Serializer `#[Groups]` decide which properties appear per operation. `#[SerializedName]` renames fields. A name converter (`CamelCaseToSnakeCaseNameConverter`) renames fields and filter args.

## Type mapping

- `bool` to `Boolean`, `int` to `Int`, `float` to `Float`, `string` to `String`.
- `DateTimeInterface` becomes `String`. There is no built-in `DateTime` scalar. Docs show how to write one.
- `array` and `iterable` of non-resources become the custom scalar `Iterable` (untyped JSON). Open PR #8619 maps scalar arrays to typed lists.
- Non-resource objects (embedded value objects without `#[ApiResource]`) are dropped from the schema. Invalid types are silently ignored (`InvalidTypeException` is caught).
- Related resources become object types. To-many relations become connection types.
- BackedEnums become GraphQL enums (`getEnumType`). Enum collections are supported (#5955). Enums can also be resources.
- Built-in custom scalars: `Iterable`, `Upload`.
- Custom types: implement `ApiPlatform\GraphQl\Type\Definition\TypeInterface` (usually also extend `ScalarType`). Tag `api_platform.graphql.type` or autoconfigure. Laravel tag is `TypeInterface::class`. Use the name in `args` or in a decorated type converter.
- Type overrides: decorate `api_platform.graphql.type_converter` (`TypeConverterInterface::convertType()` and `resolveType()`).
- Different serialization groups make different types: `{ShortName}Item`, `{ShortName}Collection`, `{ShortName}PayloadData`. Docs warn this breaks client cache normalization.
- Only one interface: Relay `Node`. No user-defined interfaces or unions. Doctrine inheritance is not mapped to GraphQL interfaces. I found no code for it.

## Relay

- `node(id: ID!): Node` root field. `id` is the IRI. `RuntimeOperationMetadataFactory` matches the IRI with the router to find the operation.
- Every resource object type implements `Node`.
- `clientMutationId` on all mutation inputs and payloads, always present, even with custom args.
- Cursor connections: `{ShortName}CursorConnection` with `edges { node cursor }`, `pageInfo { startCursor endCursor hasNextPage hasPreviousPage }`, `totalCount`. `{ShortName}Edge`, `{ShortName}PageInfo`.
- Docs (`symfony/index.md`) claim "100% of the Relay server specification".

## Pagination

- Default for collections is cursor pagination. Args `first`, `last`, `before`, `after`.
- Cursors are base64-encoded offsets. Not keyset.
- `paginationType: 'page'` switches to `{ShortName}PageConnection` with `collection` and `paginationInfo { itemsPerPage lastPage totalCount hasNextPage }`. Args `page` and `itemsPerPage` (if `paginationClientItemsPerPage`). Mixed cursor and page types in one schema work.
- `paginationEnabled: false` returns a plain list. Global switch `graphql.collection.pagination.enabled`.
- `paginationPartial` / partial paginator: no total count, `hasNextPage` always `false` for cursor, no backwards paging.
- The count query is skipped when `totalCount`/`pageInfo`/`paginationInfo.totalCount` is not selected (#6068).
- `paginationItemsPerPage`, `paginationMaximumItemsPerPage`, `paginationClientEnabled`, `paginationClientPartial`, `paginationFetchJoinCollection`, `paginationUseOutputWalkers` also apply.
- Nested to-many fields are also paginated and get filter args.

## Filters and ordering

- Two systems. Legacy `#[ApiFilter(Filter::class, properties: [...])]` / `filters: ['service.id']`. New `parameters: ['key' => new QueryParameter(filter: ..., property: ...)]` (the docs now use this form). Both become GraphQL args on collection fields (`buildFilterArgTree`, `buildParameterArgTree`).
- Filters can differ per operation. `QueryCollection(filters: [...])` lets GraphQL use other filters than REST.
- Arg naming: dotted property paths use the nesting separator (`product_color`, or `related_books__title` with `nesting_separator: '__'`). `foo[]` keys become `foo_list` list args. Bracketed keys (`order[name]`, `createdAt[before]`) become input objects.
- Order: `order: [{ id: "ASC" }, { name: "DESC" }]`. A list of single-key objects to keep order. Detected via `SortFilterInterface`.
- Operator filters with a JSON schema object (`ComparisonFilter` `gt`/`gte`/`lt`/`lte`/`ne`, `[between]`) become an input object arg.
- Filter arg types are mostly scalars from the filter description. No generated typed `where` input with `and`/`or`/`not` per type.
- Doctrine ORM filters: `ExactFilter`, `PartialSearchFilter`, `StartSearchFilter`, `EndSearchFilter`, `WordStartSearchFilter`, `FreeTextQueryFilter`, `IriFilter`, `SortFilter`, `ComparisonFilter`, `DateFilter`, `ExistsFilter`, `BooleanFilter`, `NumericFilter`, `RangeFilter` (deprecated), `BackedEnumFilter`, `OrFilter`, `ChainFilter`, `UuidFilter`, `UuidBinaryFilter`, `UlidFilter`. Legacy `SearchFilter`, `OrderFilter`, `BooleanFilter`, `NumericFilter`, `BackedEnumFilter` deprecated in 4.4.
- Eloquent filters: `EqualsFilter`, `PartialSearchFilter`, `StartSearchFilter`, `EndSearchFilter`, `OrderFilter`, `DateFilter`, `RangeFilter`, `BooleanFilter`, `OrFilter`.
- Elasticsearch: `MatchFilter`, `TermFilter`, `OrderFilter`.
- `QueryParameter` options also apply: `required`, `schema`, `security` (`SecurityParameterProvider`), `provider`, constraints (`ParameterValidatorProvider`).
- Default ordering: `order: ['name' => 'ASC']` on the resource or operation.
- Doctrine extensions (`QueryCollectionExtensionInterface`, `QueryItemExtensionInterface`) apply to GraphQL as well. Used for row-level filtering (multi-tenant).

## Security

- Expressions (Symfony ExpressionLanguage) on operations: `security`, `securityPostDenormalize` (has `object` and `previous_object`), `securityPostValidation`, and GraphQL-only `securityAfterResolver`. Each has a `...Message`. Variables: `user`, `object`, `previous_object`, `request`, `is_granted()`.
- Voters work through `is_granted('VIEW', object)`. 4.4 exposes voter reasons (#8448).
- REST and GraphQL security are not linked. You must repeat rules on each `graphQlOperations` entry.
- Operation security applies only to root fields. Relations are not protected by the target resource's operation security. Use `#[ApiProperty(security: ...)]` on relations. Docs warn about traversal attacks.
- `#[ApiProperty(securityPostDenormalize: ...)]` checks writes per field.
- Laravel: `policy` on operations and properties uses Laravel Gates/Policies (`AccessCheckerProvider`). `security` expressions are Symfony only.
- Introspection can be disabled (`graphql.introspection.enabled`). No per-user schema visibility.
- Limits: `graphql.max_query_depth` (Symfony default 20, Laravel config 200) and `graphql.max_query_complexity` (default 500). Both apply graphql-php rules. Not in `graphql.md` or `configuration.md`.
- Services to decorate: `api_platform.graphql.state_provider.access_checker`, `.post_deserialize`, `.post_validate`, `.after_resolver`.

## Validation

- Symfony Validator runs on mutations (`ValidateProvider`) before write. `validationContext: ['groups' => [...]]`, group sequences and service-based groups apply.
- `validateAfterResolver` (GraphQL only) runs validation after the custom resolver.
- `validate: false` turns it off.
- Errors: `ValidationExceptionNormalizer` adds `extensions.status` (422) and `extensions.violations` (`path`, `message`).
- `collectDenormalizationErrors` collects type errors into violations.
- 5.0: denormalization errors on properties with constraints return 422 with violations (#8211). I think this also affects GraphQL error extensions.
- Laravel uses `rules` (Laravel validation). I think Laravel GraphQL mutations do not run it. The Laravel GraphQL provider chain has no validate step (`ApiPlatformDeferredProvider::registerGraphQl`, `ApiPlatformProvider`).

## Serialization

- `normalizationContext` for output, `denormalizationContext` for input. Set per GraphQL operation.
- Queries use only the normalization context. Mutations use denormalization for input and normalization for the payload.
- Embedded relation creation in mutations: put the relation and its fields in the denormalization groups. Then input accepts an object instead of an IRI.
- Dynamic groups: decorate `api_platform.graphql.serializer.context_builder` (`SerializerContextBuilderInterface::create($resourceClass, $operation, $resolverContext, $normalization)`).
- GraphQL serializer services: `api_platform.graphql.normalizer.item`, `api_platform.graphql.denormalizer.item` (split in 4.4), `api_platform.graphql.normalizer.object`.
- Input/output DTOs: `input: Dto::class`, `output: Dto::class`, `output: false`, `input: false`. Tested for GraphQL.
- `map: true` Object Mapper (entity to DTO) also applies.
- `messenger: true` / `'input'` sends the mutation to Symfony Messenger. Tested for GraphQL (`testMessengerWithInputReturnsSynchronousResult`).

## State providers and processors

- `provider` and `processor` on resources or operations. Same interfaces as REST (`ProviderInterface`, `ProcessorInterface`). GraphQL context has `args`, `info`, `source`, `root_class`, `graphql_context`.
- A GraphQL `Query` can have its own provider different from the HTTP `Get` provider (fixed in 4.x tests).
- `stateOptions: new Options(entityClass: ...)` for DTO resources over Doctrine entities. `repositoryMethod` (4.4) works for GraphQL queries.
- Disable built-ins per operation: `read`, `deserialize`, `validate`, `write`, `serialize`, `queryParameterValidationEnabled`.
- Built-in Doctrine provider uses the selection set for eager joins (`EagerLoadingExtension` reads `attributes`). `fetchPartial` selects only needed columns (ORM `^3.3`). `forceEager`, `fetchEager`.

## Custom resolvers and custom mutations

- `QueryItemResolverInterface::__invoke(?object $item, array $context)` and `QueryCollectionResolverInterface::__invoke(iterable $collection, array $context): iterable`. Args in `$context['args']`.
- `MutationResolverInterface::__invoke(?object $item, array $context)`. Args in `$context['args']['input']`. Return `null` to skip persist (response is `null`).
- Register: Symfony autoconfigure or tags `api_platform.graphql.resolver` / `api_platform.graphql.query_resolver` / `api_platform.graphql.mutation_resolver`. Laravel: tag with the interface class.
- Wire with `new Query(name: 'x', resolver: R::class, args: [...], extraArgs: [...], read: false)`. `args` is graphql-php style (`'type' => 'ID!'`, `'description'`). Custom types usable by name.
- Item resolvers must return an instance of the resource (or output) class. They cannot return arbitrary types or scalars.
- Adding any custom operation means you must list the default operations again.
- File upload: `Upload` scalar plus a custom mutation with `deserialize: false`. Multiple files with `[Upload!]!`. Works with VichUploader.
- No way to add a computed field with its own resolver and args on a type. Computed fields come from getters, DTOs or providers.

## Subscriptions (Mercure)

- Only transport is Mercure (SSE hub). No graphql-ws, no WebSocket, no SSE from the GraphQL endpoint.
- Only update subscriptions. No create or delete events. Open PR #6904 (since 2025-01) adds subscriptions for other actions.
- Needs `mercure: true` on the resource, the `update` mutation, and a `Subscription` operation.
- Subscribe query returns `mercureUrl`. The client then subscribes to the hub. Payload is the selected fields.
- `SubscriptionManager` stores subscriptions in cache pool `api_platform.graphql.cache.subscription` (key from the IRI, id from a SHA-256 of the selection). Recommended backend Redis.
- Updates are pushed by the Doctrine `PublishMercureUpdatesListener` on `update` of any kind, also REST `PUT`/`PATCH` (`testReceiveMercureUpdatesAfterPut`). Only changed payloads are pushed.
- Extension points: `SubscriptionIdentifierGeneratorInterface`, `MercureSubscriptionIriGeneratorInterface`, `OperationAwareSubscriptionManagerInterface`.
- Symfony only. Laravel has no GraphQL subscription support. `core/ai-agents.md` also says Mercure is Symfony only.

## Errors

- Default `ErrorHandler` (`api_platform.graphql.error_handler`). Decorate `ErrorHandlerInterface::__invoke(array $errors, callable $formatter)` to log or filter.
- Error formatting uses Symfony normalizers: `ErrorNormalizer`, `HttpExceptionNormalizer` (adds `extensions.status`), `ValidationExceptionNormalizer` (`status`, `violations`), `RuntimeExceptionNormalizer` (shows the real message in prod).
- In prod, non-`RuntimeException` messages are hidden. In debug, `debugMessage` and `trace` are added.
- Custom normalizers for `GraphQL\Error\Error` with `supportsNormalization`, ordered by priority.

## IDE and tooling

- GraphiQL at `/graphql/graphiql` (Symfony) and `{prefix}/graphiql` (Laravel). Laravel options `graphiql.enabled`, `graphiql.domain`, `graphiql.middleware`.
- `default_ide`: `graphiql` or `false`.
- CSP nonce on GraphiQL scripts (5.0, #8310).
- `bin/console api:graphql:export [-o file] [--sort-types] [--comment-descriptions]` prints SDL. Symfony only.
- Test helpers: `ApiPlatform\GraphQl\Test\GraphQlTestTrait` with `executeGraphQl()`, `executeGraphQlMultipart()`, `introspectSchema()`, `assertGraphQlError()`, `assertGraphQlDebugMessage()`, `assertGraphQlFieldDeprecated()`. Not documented.
- `api-platform` AI agent skills include a `graphql` skill (`core/ai-agents.md`).

## Config

- Symfony `api_platform.graphql`: `enabled`, `default_ide` (`graphiql`), `graphiql.enabled`, `introspection.enabled`, `max_query_depth` (20), `max_query_complexity` (500), `nesting_separator` (`_`), `collection.pagination.enabled`.
- Laravel `config/api-platform.php` `graphql`: `enabled` (false), `nesting_separator` (`__`), `introspection.enabled`, `max_query_complexity` (500), `max_query_depth` (200), `middleware`. Plus top-level `graphiql` array.
- Laravel `name_converter` default is `SnakeCaseToCamelCaseNameConverter`, so GraphQL fields are camelCase from snake_case columns.

## Symfony vs Laravel

- Both: queries, mutations, filters, pagination, custom resolvers, custom types, type converter, serializer context builder, error handler, multipart upload, GraphiQL, introspection toggle, depth and complexity limits.
- Symfony only: subscriptions (Mercure), `security` expressions, Symfony Validator, `api:graphql:export`, YAML/XML resource config, profiler panel, Messenger.
- Laravel only: `policy` (Gates), route `middleware` and `domain` for GraphQL and GraphiQL.
- Laravel GraphQL has few tests (`GraphQlTest`: 4 tests, `GraphQlAuthTest`: 4 tests). Symfony GraphQL has about 190 functional tests.

## REST features the GraphQL side does not have

- Kernel events (`core/events.md`) and custom controllers.
- HTTP cache: cache headers, `cacheHeaders`, Varnish/Souin purge and tags.
- Mercure create and delete updates (REST publishes all three).
- Content negotiation and formats (JSON-LD, JSON:API, HAL, CSV). GraphQL is JSON only.
- OpenAPI/JSON Schema docs, `sunset`, `status`, `headers`, `exceptionToStatus`, `HeaderParameter`, `ResponseHeaderParameter`, HTTP `QUERY` method, `uriTemplate`-based subresources (GraphQL uses `Link`/`links` and needs both sides of the relation declared, see `core/subresources.md`).
- Sparse fieldsets (`PropertyFilter`) and `GroupFilter` (not needed, GraphQL selects fields).
- Shared security. GraphQL needs its own copy of every rule.

## Not supported

- No user-defined interfaces or unions. Only the `Node` interface.
- No arbitrary root fields or field resolvers outside the resource/operation model. Custom queries must return the resource type.
- No dataloader or batching of nested resolvers. Joins come from Doctrine eager loading. I think nested collections with args can cause N+1 queries.
- No `@defer`/`@stream`. No custom directives API.
- No federation, no persisted queries or APQ, no trusted documents.
- No batched query requests.
- No GraphQL-over-HTTP status codes or response media type. Always 200 JSON.
- No WebSocket or SSE subscription transport. Only Mercure, only update events, Symfony only.
- No `DateTime`/`Date` scalar by default (strings). No typed lists for scalar arrays (`Iterable`).
- No typed where-input grammar with `and`/`or`/`not` per field.
- No keyset cursor pagination (cursor is an offset).
- No per-request schema visibility.
- No GraphQL events or middleware layer. Use state providers/processors or decorate services.
- No SDL export on Laravel. No GraphQL Playground anymore.

## Upcoming and unreleased work

- Nothing GraphQL-related on `main` after v5.0.3.
- Open PR #8619 (2026-10-01): map scalar arrays to typed GraphQL lists instead of `Iterable`.
- Open PR #8621 (2026-10-01): allow GraphQL operations in parameter attributes on properties.
- Open PR #6904 (2025-01-09): GraphQL subscriptions for actions other than update.
- 5.0 moved filters to `QueryParameter` and deprecated legacy filters. GraphQL arg building from parameters was reworked in 4.4 (#8347, `ParameterFilterParityTest`).

## Docs and code disagree

- GraphQL Playground: docs describe `/graphql/graphql_playground`, its config and `GraphQlPlaygroundAction`. The action is gone from `src/GraphQl/Action` on `4.3`, `4.4` and `main`. Config only has `graphiql`. `default_ide: 'graphql-playground'` serves nothing.
- Laravel route example uses `ApiPlatform\GraphQL\Action\EntrypointAction` with `Route::post`. Laravel code uses `ApiPlatform\Laravel\GraphQl\Controller\EntrypointController` on `GET` and `POST` at `{prefix}/graphql`.
- Laravel custom query example tags a collection resolver with `QueryItemResolverInterface`. It still works because `ResolverProvider` merges both tags.
- Docs say Laravel GraphQL endpoint is `/graphql`. Code default is `/api/graphql` (`laravel/index.md` agrees with code).
- Docs list Laravel `default_ide` and `graphiql.enabled` under `graphql`. Laravel config has `graphiql` as a top-level key.
- Max query depth and complexity settings are not in the docs. Laravel default depth is 200, Symfony is 20.
- XML example for page pagination uses `Mutation name="delete"` instead of `DeleteMutation`.
- Docs say the `id` field is the IRI but do not mention `_id` for the raw identifier.
- Docs default branch is `4.3`. Latest release is 5.0.3.

## Sources

Docs (repo https://github.com/api-platform/docs, branch `4.4`, site https://api-platform.com/docs/):
- `core/graphql.md` (https://api-platform.com/docs/core/graphql/), read in full with YAML/XML blocks skipped.
- `core/configuration.md`, `core/extending.md`, `core/events.md`, `core/subresources.md`, `core/deprecations.md`, `core/state-providers.md`, `core/ai-agents.md`, `core/upgrade-guide.md` (GraphQL parts only).
- `laravel/index.md` (https://api-platform.com/docs/laravel/), `symfony/index.md` (GraphQL parts).
- Compared `graphql.md` on branches `4.3`, `4.4`, `5.0`, `main`.
- `llms.txt`, `llms-full.txt`, `.md` page variants: 404.

Source: shallow clone of https://github.com/api-platform/core at `/tmp/apiplatform-core`. Read `src/GraphQl` (Action, Executor, Type, Resolver, State, Serializer, Subscription, Test), `src/Metadata/GraphQl`, `src/Metadata/ApiResource.php`, `src/Metadata/ApiProperty.php`, `src/Metadata/Resource/Factory/OperationDefaultsTrait.php`, `src/Symfony/Bundle/Resources/config/graphql*.php`, `src/Symfony/Bundle/DependencyInjection/Configuration.php`, `src/Laravel/ApiPlatformProvider.php`, `src/Laravel/ApiPlatformDeferredProvider.php`, `src/Laravel/config/api-platform.php`, `src/Laravel/routes/api.php`, `tests/Functional/GraphQl` test names.

Changelog: https://github.com/api-platform/core/blob/main/CHANGELOG.md.

GitHub API: releases, repo metadata, branches, open PRs, compare `v5.0.3...main` (https://api.github.com/repos/api-platform/core).
