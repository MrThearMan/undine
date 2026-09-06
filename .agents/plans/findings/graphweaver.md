# Graphweaver findings

Version checked: v2.24.1 (2026-09-22). Repo `main` at `cfbcfb2` (2026-10-07).
Graphweaver is a TypeScript (Node) server that builds one GraphQL API from many data sources ("data providers"). It adds a generated React Admin UI, an auth package, a CLI, and AWS CDK constructs.
Packages (npm scope `@exogee`): `graphweaver` (core), `graphweaver-server`, `graphweaver-mikroorm`, `graphweaver-rest`, `graphweaver-rest-legacy`, `graphweaver-xero`, `graphweaver-auth`, `graphweaver-auth-ui-components`, `graphweaver-admin-ui`, `graphweaver-admin-ui-components`, `graphweaver-storage-provider`, `graphweaver-scalars`, `graphweaver-apollo-client`, `graphweaver-aws`, `graphweaver-cdk`, `graphweaver-config`, `graphweaver-builder`, `logger`, `vite-plugin-graphweaver`, CLI package `graphweaver`.
Engine: graphql-js schema built by hand (`SchemaBuilder`). Server: Apollo Server 5 (see `apollo-server.md`). Hosting: Fastify, AWS Lambda, Azure Functions.
Code-first with TS decorators on plain classes. Schema is built once at startup from a global metadata registry (`graphweaverMetadata`).
Docs are not in the repo (`docs/README.md` only links to the site). Docs site https://graphweaver.com/docs is a hosted site (I think Notion based, "Copy" buttons). No `llms.txt`, `llms-full.txt`, or `.md` page variants (404). `Accept: text/markdown` returns HTML. I downloaded the 63 pages from `sitemap.xml`.
No `CHANGELOG.md`. Release notes are GitHub Releases (111 releases, v1.0.0 2024-06-12 to v2.24.1).
License: "Other" on GitHub (I think it is a custom license, not OSI).

## Maintenance status

- Active. Last commit on `main` 2026-10-07. Last push 2026-10-08. About 556 stars. 17 open issues plus PRs. Not archived.
- Latest release v2.24.1 (2026-09-22). v2.24.0 (2026-09-14). v2.23.x (May to Aug 2026). v2.22.0 (2026-04-02). v2.21.0 (2026-01-28). Releases about monthly.
- Mainly one maintainer (thekevinbrown) plus a few Exogee staff. Many dependabot PRs.
- Recent features: Trusted Documents (#2596, v2.24.0), TypeScript config files (`graphweaver-config.ts`, #2597, v2.24.0), direct access to Authorization Context for integrators (#2529, v2.23.0), Azure Functions (#2393, v2.21.0), client side token refresh (#2343, v2.20.9), count relationship behaviour in Admin UI (#2046, v2.20.0), SQL Server beta (#1809, v2.17.0), CSV export per entity (#1803, v2.16.0), cell date/currency formats (#1805, v2.16.0), searchable relationship filters (#1769, v2.15.0), range filters in Admin UI (v2.13.0), `_not` re-enabled (#1677, v2.13.0), rich text and Markdown editors (v2.12), Okta (v2.10.0), Microsoft Entra (v2.7.0), Fastify options (v2.6.0), client side ID generation (v2.4.0), new REST adapter (v2.3.0), column level security (v2.2.0), virtual entities (entities without provider, v2.1.0), Auth0 (v2.0.1), federation namespacing (v2.0.0), OpenTelemetry (v1.0.2).
- v1.0.0 removed TypeGraphQL. v1 added aggregates. v2 rebuilt the Admin UI table and removed `GraphQLEntity` base classes.
- Latest commit after v2.24.1: "Run codegen before generating trusted documents" (#2637), MinIO image move. No open feature branches seen in open PRs (only dependabot).

## Architecture and request pipeline

- `new Graphweaver<TContext>(config: GraphweaverConfig)` in `@exogee/graphweaver-server`. Then `graphweaver.start({ host, port, path })` (Fastify standalone), `graphweaver.handler()` (AWS Lambda API Gateway), `graphweaver.azureHandler()` (Azure Functions), or `graphweaver.executeOperation(request, options)` (in-process).
- `GraphweaverConfig` keys: `adminMetadata` (`enabled`, `config`, `hooks.beforeRead/afterRead` on Admin UI metadata), `apolloServerOptions` (all Apollo options except `schema`), `fastifyOptions`, `federationSubgraphName`, `enableFederationTracing`, `graphQLArmorOptions`, `corsOptions`, `graphqlDeduplicator.enabled`, `fileAutoGenerationOptions` (`typesOutputPath`, `watchForFileChangesInPaths`), `plugins` (`GraphweaverPlugin[]`), `schemaDirectives`, `openTelemetry` (`traceProvider`, `instrumentations`), `trustedDocuments`.
- GraphQL Armor (`@escape.tech/graphql-armor`) is always on. It adds depth, cost, alias, directive and token limits plus block field suggestion. Configure with `graphQLArmorOptions`. Only mentioned in `deployments` doc.
- Field `complexity` option (`ComplexityEstimator | number`, from `graphql-query-complexity`). Not in the decorators doc.
- `graphqlDeduplicator` uses `graphql-deduplicator` to dedupe repeated objects in responses. Client side helper is in `@exogee/graphweaver-apollo-client`. Not documented.
- Built-in Apollo plugins: `LogRequests`, `LogErrors`, `corsPlugin`, `trustedDocumentsPlugin`, `dedupeGraphQL`, inline trace (federation). Providers can add plugins via `BackendProvider.apolloPlugins`.
- `GraphweaverPlugin` with `GraphweaverRequestEvent.OnRequest`: wraps each request in a `next` chain. `BaseLoaderRequestContextPlugin` uses it to make a per-request `RequestContext` (AsyncLocalStorage). `GRAPHWEAVER_DISABLE_ASYNC_LOCAL_STORAGE=true` swaps to a mutex singleton for WebContainers.
- `includeStacktraceInErrorResponses` is on only when `IS_OFFLINE=true`.
- Default field resolver `fieldResolver`: if the source property is a function, it calls `property(source, args, context, info)`. This is how computed fields work (method on the entity class).
- "Multiple version protection" (v2.12.2): a global symbol detects two copies of the core package and fails.
- No subscriptions. Schema has only `Query` and `Mutation`. Trusted documents types list `'subscription'` but no subscription root exists.
- No batched HTTP queries beyond what Apollo Server gives (Apollo `allowBatchedHttpRequests`).
- No file upload scalar or multipart. Media upload uses presigned S3 URLs (see "Media").

## Trusted documents (persisted operations)

- `trustedDocuments: { enabled?, manifest, allowList? }` (v2.24.0). Manifest format `{ format: 'graphweaver-trusted-documents', version: 1, allowLists: Record<listName, Record<documentId, { body, operationName?, operationType? }>> }`.
- `allowList`: `true` (all lists), a list name, an array of list names, or a function `(params: { documentId, operationName, context, headers, request }) => value`. So the allowed set can depend on the user or headers.
- When on, Apollo APQ is turned off (`persistedQueries: false`). It also safelists the Apollo variant of each document (v2.24.1). Admin UI documents are trusted only when the Admin UI is on.
- The CLI generates the manifest (`graphweaver build` runs codegen first, #2637). Not in the docs site.

## Entities and fields (decorators)

- `@Entity(name?, options?)`: registers a class as a GraphQL object type. Name defaults to the class name. `GraphweaverMedia` is a reserved name.
- Entity options: `description`, `plural` (override pluralisation, e.g. `fish` -> `multipleFish`), `provider` (a `BackendProvider`), `directives`, `hooks` (map of `HookRegister` to function arrays), `primaryKeyField`.
- `apiOptions`: `clientGeneratedPrimaryKeys`, `excludeFromBuiltInOperations` (no root fields, also no filtering), `excludeFromBuiltInWriteOperations`, `excludeFromFiltering`, `excludeFromTracing` (sets `X-GRAPHWEAVER-SUPPRESS-TRACING` from Admin UI), `namespaceForFederation`, `resolvableViaFederation`, `excludeFromFederation`.
- `adminUIOptions`: `defaultFilter`, `defaultSort` (not in docs), `exportPageSize` (CSV export page size, default 200), `hideInSideBar`, `hideInFilterBar`, `hideInDetailForm`, `summaryField`, `readonly`, `fieldForDetailPanelNavigationId`, `filterType`.
- An entity with no `provider` is a "virtual entity" (v2.1.0). It gets no root fields. Its relationship fields resolve with `listRelationshipFieldWithoutProvider` from the parent value. Used for nested JSON or computed objects.
- `@Provider(provider)`: class decorator to set the provider separately from `@Entity`.
- `@Field(getType, options?)`: `getType` is `() => String | Number | Boolean | ID | Date | scalar | Entity | Enum | Union | [X]`. Options: `description`, `deprecationReason`, `complexity`, `defaultValue`, `nullable` (`true | 'items' | 'itemsAndList'`), `excludeFromFilterType`, `primaryKeyField`, `readonly`, `additionalInformation` (free-form metadata for plugins), `directives`.
- Field `adminUIOptions`: `filterType` (`AdminUIFilterType`), `filterOptions`, `hideInTable`, `hideInFilterBar`, `hideInDetailForm`, `readonly`, `summaryField`, `fieldForDetailPanelNavigationId`, `format` (`{ type: 'date', timezone, format: DateTimeFormat }` or `{ type: 'currency', variant }`), `detailPanelInputComponent` (`TEXT`, `RICH_TEXT`, `MARKDOWN`, with per-toolbar-button `hide` options), `relationshipBehaviour` (`'load' | 'count'`).
- Field `apiOptions`: `excludeFromBuiltInWriteOperations`, `requiredForCreate`, `requiredForUpdate`. The last two are not in the docs.
- `@RelationshipField<D>(getType, { relatedField?, id?, nullable?, adminUIOptions?, directives? })`: `id` is the data entity column that holds the foreign key, or a function `(dataEntity) => id`. `relatedField` names the field on the other side (one-to-many, many-to-many). One of them is required.
- Relationship `adminUIOptions`: `hideInTable`, `hideInFilterBar`, `hideInDetailForm`, `readonly`, `relationshipBehaviour`, `filterOptions` (limits selectable options in the Admin UI only).
- `@MediaField({ storageProvider, ...FieldOptions })` from `@exogee/graphweaver-storage-provider`. See "Media".
- `@InputType(name | { name, description })`: custom input object types for custom operations. Fields use `@Field`.
- `graphweaverMetadata.collectEnumInformation({ target, name, description, valuesConfig })`: registers a TS enum. `valuesConfig` sets per-value `description` and `deprecationReason`.
- `graphweaverMetadata.collectUnionTypeInformation({ name, description, getTypes })`: union types.
- `graphweaverMetadata.collectDirectiveTypeInformation({ name, description, args, isRepeatable, locations })`: custom schema directives. Entities, fields and custom operations accept `directives: { name: args }`. They go into `extensions.directives` and are printed in SDL.
- Computed fields: put a method on the class with `@Field`. It gets `(source, args, context, info)`. `Field` has no `args` option, so computed fields cannot declare GraphQL arguments.
- Static hooks on the entity class: `fromBackendEntity`, `toBackendEntity`, `toBackendEntityFilter` (`TransformableGraphQLEntityClass`) map between data entity and GraphQL entity. `serialize`/`deserialize` (`SerializableGraphQLEntityClass`) for nested objects stored as JSON.
- `fromBackendEntity(EntityClass, dataEntity)`: wrap custom resolver results so nested relationship fields resolve.
- Pluralisation with `pluralise(name, userSupplied)`. Name clashes throw (`Duplicate query name`).
- `graphweaverMetadata.validateEntities()` runs at schema build (Entity Validation, v2.0.2). It throws if a class got `@Field` but no `@Entity` (for example decorators put on the data entity by mistake).
- Scalars in `@exogee/graphweaver-scalars`: `DateScalar` (date only), `ISOString`, `Decimal`, `Time`, `NanoTimestamp`, `NanoDuration`. Also `GraphQLJSON` used for JSON fields. Core re-exports all of `graphql/type`.

## Generated operations

- Per entity with a provider and not excluded:
  - Query `user(id: ID!)`: get one. Root name is lower-camel entity name.
  - Query `users(filter: UsersListFilter, pagination: UsersPaginationInput): [User]`: list.
  - Query `users_aggregate(filter: UsersListFilter): AggregationResult`: only if the provider sets `supportedAggregationTypes`.
  - Mutations `createUser(input: UserInsertInput!)`, `createUsers(input: [UserInsertInput!]!)`, `updateUser(input: UserUpdateInput!)`, `updateUsers(input: [UserUpdateInput!]!)`, `createOrUpdateUsers(input: [UserCreateOrUpdateInput!]!)`, `deleteUser(filter: UserDeleteOneFilterInput!): Boolean`, `deleteUsers(filter: UsersListFilter!): Boolean`.
- No `createOrUpdateUser` (single). No `upsert` by unique key other than primary key.
- Input types: `insert` omits the primary key (unless `clientGeneratedPrimaryKeys`). `update` requires the primary key and makes other fields optional. `createOrUpdate` has an optional key: present means update, absent means create. Non-nullable fields without `defaultValue` are non-null in insert input.
- Nested writes: relationship fields in inputs take `XCreateOrUpdateInput` (one or list). Pass only the key to link. Pass more fields to create or update the related row. `batched-writes.ts` builds a dependency graph and runs it in topological layers (`layeredToposort`) inside one transaction (`withTransaction`). Works across providers (no cross-provider atomic transaction, I think).
- Delete returns `Boolean`, not the deleted object.
- `defaultValue` on fields is applied server-side before create (`applyDefaultValues`).
- All writes go through `withTransaction(provider, ...)` if the provider has `withTransaction`. Hooks get `transactional: true`.
- Custom root fields: `graphweaverMetadata.addQuery({ name, getType, resolver, args?, description?, directives?, logOnDidResolveOperation? })` and `graphweaverMetadata.addMutation(...)`. `args` is `{ name: () => Type }` or `{ name: { type, description, defaultValue, deprecationReason, nullable } }`. Resolver gets `{ source, args, context, fields (ResolveTree), info, trace }`.
- `logOnDidResolveOperation`: per-operation hook to redact query and variables before logging (sensitive data, v2.11.4). Not documented on the site.
- Custom operations get no access control. The docs say so.
- Root field naming is fixed. No hook to rename generated operations, other than `plural` and the entity name.

## Filtering

- Filter input `<Plural>ListFilter` per entity. Top level `_and: [F]`, `_or: [F]`, `_not: F`.
- Per scalar field `f`: `f` (equals), `f_in`, `f_nin`, `f_ne`, `f_null: Boolean`, `f_notnull: Boolean`.
- Strings also get `f_like`, `f_ilike` (SQL `%` patterns).
- `f_gt`, `f_gte`, `f_lt`, `f_lte` for `Number`, `Date`, `BigInt`, `ID`, `String`, `DateScalar`, `ISOString`, `Float`, and integer scalars. The docs list these for Number, Date, ISOString only. The code also adds them to `ID` and `String`.
- Enums get `f`, `f_in`, `f_nin`.
- Relationship fields take a nested filter of the related entity (`tasks: { name: "x" }`). For to-many relations it means "any related row matches" (I think, provider dependent).
- Relationship filters also work on many-to-many and across providers.
- Cross-provider filters: `QueryManager` walks the filter tree. If a nested branch uses a different `backendId`, it runs that branch on its provider, gets the primary keys, and rewrites it to `{ pk_in: [...] }`. A filter that is only `pk` or `pk_in` skips the extra query. Only used for `list`. The docs say it is not implemented for other operations.
- Fields can opt out with `excludeFromFilterType`. Entities opt out with `apiOptions.excludeFromFiltering`.
- No full-text search, regex, JSON path, array-contains, or geo operators. No `_exists` or count-based relation filters.
- Filters on nested relationship fields: list relationship fields get a `filter` arg if the related provider sets `backendProviderConfig.filter`.

## Sorting and pagination

- `pagination: { offset: Int, limit: Int, orderBy: <Plural>OrderByInput }`. `orderBy` is an object `{ field: ASC | DESC }` (`Sort` enum). Multiple keys give multi-column sort (key order).
- Only scalar fields are sortable. No sort by relationship field or aggregate. No nulls first/last.
- Only offset pagination. No cursor or Relay connections. No `Node` interface.
- `backendProviderConfig.supportsPseudoCursorPagination`: only the Admin UI uses it. When the list is sorted by the primary key only, the Admin UI pages with a keyset filter (`pk_gt: last`) instead of an offset. The API itself has no cursor args. Not documented.
- Relationship list fields take `filter` only. No `pagination` on nested lists.
- No default or max page size in core. GraphQL Armor limits cost instead.

## Aggregates

- `AggregationType` enum has only `COUNT`. `AggregationResult { count: Int! }`.
- Root `users_aggregate(filter)` and relationship `albums_aggregate(filter)` fields. Shown only if the provider declares `supportedAggregationTypes` (and `filter` for relationships).
- No sum, avg, min, max, group by. v1 release notes promise "more aggregate operations". Not done yet.
- Read hooks get `isAggregate: true` for aggregate reads, so ACLs apply to counts.

## Hooks

- `HookRegister`: `BEFORE_CREATE`, `AFTER_CREATE`, `BEFORE_READ`, `AFTER_READ`, `BEFORE_UPDATE`, `AFTER_UPDATE`, `BEFORE_DELETE`, `AFTER_DELETE`.
- Three ways to register: `@Hook(HookRegister.X)` on a class method (instance or static, static fixed in v2.21.0), `@Hook(HookRegister.X, fn)` on the class, or `@Entity(name, { hooks: { [HookRegister.X]: [fn] } })`. Several hooks per type run in order.
- Hook params: `context`, `transactional`, `fields` (ResolveTree of the selection), `entities` (after hooks), `deleted` (delete), `args` (`items` for writes, `filter` and `pagination` for reads, `filter` for deletes), `isAggregate` (reads).
- Hooks return modified params. Before-read hooks can change the filter (used for row-level security). Before-create hooks can set fields, including the primary key ("hook-generated primary keys", v2.5.0).
- Hooks run for nested writes too (`runWritableBeforeHooks` per entity in the batch).
- The docs list an `info` param. The code has no `info` in `HookParams`. The docs use type names `CreateOrUpdateHook`, `ReadHook`, `DeleteHook`. Code names are `CreateOrUpdateHookParams`, `ReadHookParams`, `DeleteHookParams`, `DeleteManyHookParams`.
- No field-level hooks. No hooks on custom operations.
- Admin UI metadata hooks: `adminMetadata.hooks.beforeRead/afterRead` can change which entities the Admin UI sees per user.

## Data providers

- Any class that implements `BackendProvider<D>` is a provider. Methods: `find(filter, pagination, entityMetadata)`, `findOne`, `findByRelatedId(entity, relatedField, relatedIds, filter)`, `updateOne`, `updateMany`, `createOne`, `createMany`, `createOrUpdateMany`, `deleteOne`, `deleteMany?`, `aggregate?(filter, requestedAggregations)`, `withTransaction?`, `foreignKeyForRelationshipField?`, `createTraces?`.
- Provider properties: `backendId` (used to detect cross-source joins), `backendDisplayName` (groups entities in the Admin UI sidebar), `entityType`, `maxDataLoaderBatchSize`, `apolloPlugins`, `backendProviderConfig`.
- `backendProviderConfig`: `filter` (adds `filter` args on relationship fields and enables relationship aggregates), `pagination`, `orderBy`, `supportedAggregationTypes`, `idListLoadingMethod` (`'find'` batch by `pk_in`, or `'findOne'` per id), `supportsPseudoCursorPagination`. I found no code that reads `pagination` or `orderBy`. Root lists always get `pagination` args.
- `BaseDataProvider<D>`: base class whose methods throw "not implemented". Extend it for custom providers (`create-a-data-provider` doc).
- Relationship loading uses DataLoader per request (`BaseLoaders.loadOne({ gqlEntityType, id })`, `BaseLoaders.loadByRelatedId(...)`). Batches by `pk_in` or `findByRelatedId`. `maxDataLoaderBatchSize` splits big batches.
- No query planner or SQL join pushdown across entities. Each relationship level is one batched provider call. MikroORM may join inside one provider for nested filters.

### MikroORM (`@exogee/graphweaver-mikroorm`)

- `new MikroBackendProvider(OrmEntity, connection, options?)`. `connection` is `{ connectionManagerId, mikroOrmConfig, secretArn? }`. `options`: `transactionIsolationLevel` (`IsolationLevel.SERIALIZABLE | REPEATABLE_READ | READ_COMMITTED | READ_UNCOMMITTED`, default `REPEATABLE_READ`), `backendDisplayName`.
- Databases: PostgreSQL, MySQL/MariaDB, SQLite, SQL Server (`mssql`, beta since v2.17.0). Driver chosen from the MikroORM config.
- `secretArn` or env `DATABASE_SECRET_ARN`: read DB credentials from AWS Secrets Manager.
- `ConnectionManager.connect(id, options)`, `ConnectionManager.database(id).em`: named connections. A request plugin (`connectToDatabase`) opens a forked EntityManager per request.
- Config `filter: true`, `supportedAggregationTypes: {COUNT}`, `supportsPseudoCursorPagination: true`.
- Filters translate to MikroORM `FilterQuery` (`gqlToMikro`). Nested relationship filters become joins.
- Custom MikroORM types: `DateType`, `DecimalType`, `TimeType`.
- `@ExternalIdField({ from: 'user' })` on a data entity column. It maps a foreign key column to a relationship that lives in another provider.
- Audit trail: extend `TrackedEntity` and register the `ChangeTracker` MikroORM subscriber. It writes `AuditChange` and `AuditRelatedEntityChange` rows with `createdBy` from `AuthenticationContext.currentUser`. Not documented on the site.
- `AuthenticationContext.set(user)`: per-request current user for auditing.
- Re-exports MikroORM helpers (`wrap`, `Reference`, `Collection`, `QueryOrder`, `LockMode`, ...).
- `mikro-orm-sqlite-wasm`: SQLite driver for WebContainers/browser (used by the online playground, I think).
- Connection env vars when no config is given: `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_NAME`.
- Optimistic locking: if an update input has `version`, the provider calls `em.lock(entity, LockMode.OPTIMISTIC, version)`. On conflict it throws `OptimisticLockError` (code `OPTIMISTIC_LOCK_ERROR`). Not documented on the site.
- To-many writes replace the collection. Items in the input list are created, updated or linked. Items not in the list are removed from the collection (`assign.ts`). There is no "add" or "remove" only mode.
- Composite primary keys are not supported in nested writes (`assign` throws "multiple primary keys ... not yet supported"). Introspection skips tables with a composite primary key or no primary key, and relations to them. It reports a warning.
- `deleteMany` counts matching rows, runs `nativeDelete`, and rolls back if the counts differ.
- `findByRelatedId` uses MikroORM `populate` with `populateWhere: INFER` (select-in loading, not joined loading).
- One-to-one inverse sides are auto-joined on `find` so references are set.
- `@UntrackedProperty()`: excludes a property from the `ChangeTracker` audit log. Not documented.
- `sanitiseFilterForLogging`: hides filter values in trace logs.
- Introspection lives in this package (`generate()`, `IntrospectionError`). It is used by `graphweaver import` (see "CLI").

### REST (`@exogee/graphweaver-rest`, v2.3.0)

- `new RestBackendProvider({ baseUrl, defaultPath, defaultResultKey, endpointOverrides: { list, getOne, create, update, delete: { path, method, resultKey } }, fieldConfig: { field: { transform: { fromApi, toApi } } }, clientOptions (got options, e.g. headers), displayName, relationshipLoadingMethod: 'find' | 'findOne' })`.
- `RestDataAccessor<T>` with a custom `find({ filter, pagination })` for non-standard APIs.
- `find` fetches the full list and filters in memory (`inMemoryFilterFor`). Supports equals, `in`, `nin`, `ne`, `null`, `notnull`, `gt`, `gte`, `lt`, `lte`, `like`, `ilike`, `_and`, `_or` (`operatorFunctionMap`). I found no `_not` handling there. `findOne` uses `GET path/id` when the filter is only the key.
- Read only. All write methods throw `Not implemented`. The doc `connect-to-a-rest-api` describes create, update and delete endpoints and `endpointOverrides.create/update/delete`. The code does not do them.
- No aggregates (no `supportedAggregationTypes`). No filter args on relationship fields (no `filter` flag).
- `@exogee/graphweaver-rest-legacy`: the old adapter with its own `@Field`, `@ManyToOne`, `@OneToMany`, `@ManyToMany`, `@ExternalIdField` decorators, entity manager and date serializer. Kept for old apps.

### Xero (`@exogee/graphweaver-xero`)

- `new XeroBackendProvider(entityTypeName, accessor?, displayName?)`. `XeroDataAccessor` implements `find` per entity. OAuth through env `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_CLIENT_REDIRECT_URIS`, `XERO_SCOPES`. `XeroAuthApolloPlugin` handles the token. Multi-tenant via `forEachTenant` helper in the example.
- Read only. All writes throw `Not implemented`. No filter pushdown (`filter: false`). Filtering is done in the accessor.

### Others

- AWS Cognito (`@exogee/graphweaver-aws`, docs call it `@exogee/graphweaver-aws-cognito`): `createAwsCognitoUserProvider({ userPoolId, region, endpoint })` exposes Cognito users as an entity.
- S3 storage (`@exogee/graphweaver-storage-provider`): see "Media".
- OpenTelemetry trace provider: traces stored as an entity (`Trace`) through any provider (see "Observability").
- Enterprise (private repo, paid): Salesforce (GraphQL API only, `SalesforceBackendProvider`, only `find`/`findOne` on Account), Microsoft Dynamics 365 (`@exogee/graphweaver-microsoft-dynamics`), Eventbrite, Mailchimp. The Eventbrite and Mailchimp doc pages are empty.
- No first-class providers for MongoDB, DynamoDB, Elasticsearch, GraphQL remote schemas (other than enterprise Salesforce), gRPC, or OpenAPI import.

## Cross-source relationships

- A `@RelationshipField` may point to an entity in another provider. Use `id` (foreign key column or function on the data entity) for to-one. Use `relatedField` for to-many.
- Resolution: the related provider's `find` with `pk_in` (or `findByRelatedId`) through DataLoader.
- Filters through relationships across providers are rewritten by `QueryManager` (see "Filtering").
- Nested writes across providers work through the batched write graph (`connecting-a-second-data-source` doc). I think there is no two-phase commit. Each provider gets its own transaction.
- Many-to-many is supported only inside a provider that supports it (MikroORM). Across providers you need a join entity.
- Virtual entities (no provider) can hold nested data from a parent field.

## Auth (`@exogee/graphweaver-auth`)

### Authorization

- `@ApplyAccessControlList(acl, { overrideIfExists? })` on an entity. Or `registerAccessControlListHook(entityName, acl)`. A second ACL for the same entity throws unless `overrideIfExists`.
- `AccessControlList<G, TContext>` is `{ [roleName]: { read?, create?, update?, delete?, write?, all? } }`. `write` means create plus update plus delete. `all` means everything.
- Each value: `true`, a function `(context) => Filter<G> | boolean | Promise<...>`, or `{ rowFilter, fieldRestrictions }`.
- Row-level security: the filter function returns a `Filter<G>`. It is `and`-ed into reads. For writes the row is checked before and after the write (`afterCreateOrUpdate`). The check runs against the DB if the filter is not a simple id filter. The filter can traverse relationships (`{ user: { id: ctx.user.id } }`), also across providers.
- Permissions from several roles are combined with OR. The special role `Everyone` (`BASE_ROLE_EVERYONE`) applies to all. Guests get role `GUEST`.
- Column-level security: `fieldRestrictions: ['field']` or `(context) => [...]` inside `{ rowFilter, fieldRestrictions }`. Restrictions from all roles are added together. A request that selects, filters on (also nested), or writes a restricted field fails with `RestrictedFieldError` (`FieldLocation.FIELD | FILTER | NESTED_FILTER | INPUT`). It does not return null. Added in v2.2.0. The `column-level-security` doc only shows the older manual way with `AFTER_READ` hooks and `adminMetadata` hooks. `fieldRestrictions` is not on the docs site.
- Implicit deny by default: entities without an ACL are not accessible when an auth method is registered. `setImplicitAllow(true)` flips it. The old `authApolloPlugin(addUserToContext, { implicitAllow })` option is deprecated.
- Admin UI metadata entities get a default `Everyone: { read: true }` ACL.
- Superuser: `setAdministratorRoleName('ADMIN')` gives a role full access, bypassing ACLs.
- If an ACL exists but no auth method was imported, the first request throws (`CheckForAuthMethodOnServerStart`).
- Auth context: `upsertAuthorizationContext(ctx)`, `getAuthorizationContext()`, `getRolesFromAuthorizationContext()` (stored in AsyncLocalStorage). Direct access for integrators added in v2.23.0.
- `setAddUserToContext(async (userId, token) => new UserProfile({ id, roles, displayName, username, email, type }))` maps a token to a user and roles. `UserProfile` fields: `id`, `username`, `displayName`, `name { familyName, givenName, middleName }`, `email`, `roles`, `type` (`UserProfileType.USER | SERVICE`).
- Helpers: `checkAuthorization`, `checkEntityPermission`, `assertUserCanPerformRequestedAction`, `assertObjectLevelPermissions`, `getAccessFilter`, `andFilters`, `evaluateAccessControlValue`, `buildAccessControlEntryForUser`.
- Custom queries and mutations are not protected by ACLs. You check by hand.
- Errors: `ForbiddenError` (message `Forbidden`, `GENERIC_AUTH_ERROR_MESSAGE`), `ChallengeError` (code `CHALLENGE`, lists required `providers`), `RestrictedFieldError`.
- No GraphQL directive based auth (no `@auth`). No field-level `read` permission functions other than `fieldRestrictions` lists. No object-type-level schema hiding per role (the schema is the same for all users). The Admin UI metadata can be filtered per user with `adminMetadata.hooks`.

### Multi-factor and step-up auth

- `@ApplyMultiFactorAuthentication<G>((params) => ({ [role]: { Read | Create | Update | Delete | Write | All: [{ factorsRequired, providers: [AuthenticationMethod.X] }] } }))`. It registers before-hooks on the entity.
- If the token lacks recent proof for the needed factors, the API throws `ChallengeError` with the list of allowed providers. The Admin UI then shows a challenge (step-up). The token `acr.values` stores the time each method was done. I think `AUTH_JWT_CHALLENGE_EXPIRES_IN` sets how long a step-up lasts.
- `AuthenticationMethod`: `pwd` (password), `mgl` (magic link), `otp`, `wb3` (Web3 wallet), `pky` (passkey). Tokens carry `amr`.
- MFA data is stored in an `Authentication` table/entity (`type`, `userId`, `data`, `createdAt`). `AuthenticationType` covers passkey options and devices, Web3 wallet addresses, OTP challenges, magic link challenges, forgotten password links.

### Authentication methods (primary and secondary)

- Tokens: Graphweaver issues its own JWTs (`AuthTokenProvider`) signed with `AUTH_PRIVATE_KEY_PEM_BASE64`, verified with `AUTH_PUBLIC_KEY_PEM_BASE64`. Settings `AUTH_JWT_ALGORITHM`, `AUTH_JWT_EXPIRES_IN`. External tokens verify through `AUTH_JWKS_URI`. Read from the `Authorization` header. Client side token refresh added in v2.20.9.
- `Password` (`{ provider, getUserProfile, acl?, assertPasswordStrength?, onUserAuthenticated?, onUserRegistered? }`): mutations `loginPassword`, `challengePassword`, `createCredential`, `updateCredential`. Passwords hashed with argon2id (`hashPassword`, `verifyPassword`). Forgotten password flow: `ForgottenPassword` with `sendResetPasswordLink`, `resetPassword`, rate limit and TTL env vars.
- `MagicLink` (`{ provider, getUser, sendMagicLink }`): `sendLoginMagicLink`, `verifyLoginMagicLink`, `sendChallengeMagicLink`, `verifyChallengeMagicLink`. Rate limit `AUTH_MAGIC_LINK_RATE_LIMIT`/`_RATE_PERIOD`, TTL `AUTH_MAGIC_LINK_TTL`.
- `OneTimePassword` (`{ provider, sendOTP }`): `sendOTPChallenge`, `verifyOTPChallenge`. You deliver the code (email or SMS).
- `Passkey` (WebAuthn via `@simplewebauthn`): `passkeyGenerateRegistrationOptions`, `passkeyVerifyRegistrationResponse`, `passkeyGenerateAuthenticationOptions`, `passkeyVerifyAuthenticationResponse`. Env `AUTH_PASSKEY_RELYING_PARTY_ID`, `_NAME`, `AUTH_PASSKEY_ORIGIN`.
- `Web3` (wallet signature): `canEnrolWallet`, `enrolWallet`, `verifyWeb3Challenge`.
- `ApiKey` (`{ provider, acl? }`): header `X-API-Key: base64(key:secret)`. Secrets hashed with argon2id. Keys have `roles` and `revoked`. Mutations `createApiKey`, `updateApiKey`. The user is a `SERVICE` profile.
- External identity providers: `AuthZero`, `Okta`, `MicrosoftEntra` classes (thin, they verify JWTs via JWKS). The Admin UI does the OAuth redirect flow (`@exogee/graphweaver-auth-ui-components`). AWS Cognito via the example.
- Admin UI config `adminUI.auth.primaryMethods`: `PASSWORD`, `MAGIC_LINK`, `AUTH_ZERO`, `OKTA`, `MICROSOFT_ENTRA`. `secondaryMethods`: `PASSWORD`, `MAGIC_LINK`, `ONE_TIME_PASSWORD`, `WEB3`, `PASSKEY`. `password.enableForgottenPassword`, `password.enableResetPassword`.
- Redirect safety: `X-Auth-Request-Redirect` header or `AUTH_BASE_URI`. Checked against the space separated env `AUTH_WHITELIST_DOMAINS` (`isURLWhitelisted`). Redirects go to `/auth/login` or `/auth/challenge` with `redirect_uri` and `providers` params.
- Sensitive inputs (passwords) are redacted from logs via `logOnDidResolveOperation`.
- `StubAuthMethodForTesting` for tests.
- No OAuth2 authorization server, no sessions or cookies (bearer tokens only, I think). No social login other than through Auth0/Okta/Entra.

## Federation

- Apollo Federation subgraph support. Turn on with `federationSubgraphName: 'team'` in `GraphweaverConfig`. Schema `@link` imports `https://specs.apollo.dev/federation/v2.3`.
- Adds `_service { sdl }` and `_entities(representations: [_Any!]!)`. `_entities` resolves each representation one by one through the get-one resolver. I think there is no batching across representations.
- `@key(fields: <primaryKeyField>)` is added to every entity with a primary key. Single field keys only. The compatibility README lists multi, composite and repeatable `@key` as WARNING.
- Directives through the `directives` option on `@Entity`, `@Field` and `@RelationshipField`: `extends`, `external`, `provides`, `requires`, `shareable`, `tag`, `override`, `inaccessible`, `interfaceObject`, `composeDirective`, `link`.
- Entity `apiOptions`: `resolvableViaFederation` (sets `@key(resolvable:)`), `excludeFromFederation` (hidden from `_service` and `_Entity`), `namespaceForFederation` (renames type to `XFromTeamSubgraph`). Built-in singleton types like `Media` and `AggregationResult` are namespaced when federation is on.
- `enableFederationTracing`: Apollo inline trace (`ftv1`). Off by default.
- `schemaDirectives`: extra schema-level directives (for example a custom `link`).
- Tested against the Apollo subgraph compatibility suite (`src/examples/federation/integration`). v1 and v2 directives PASS.
- Graphweaver is only a subgraph. It is not a gateway or router. No schema stitching or remote GraphQL schema provider.

## Media (`@exogee/graphweaver-storage-provider`)

- `new S3StorageProvider({ type: StorageType.S3, bucketName, region?, expiresIn? (default 3600 s), endpoint? })`. `endpoint` turns on path-style access for S3-compatible stores (MinIO).
- The constructor registers root fields: mutation `getUploadUrl(key): JSON` (presigned PUT, returns `{ url, filename, type }`, file renamed to a random UUID), mutation `getDeleteUrl(key): String`, query `getDownloadUrl(key): String`.
- `@MediaField({ storageProvider })` on an entity field. Stored value is `{ filename, type }` (JSON column). On read the resolver adds a presigned download `url`. Type `Media` with `MediaType.IMAGE | OTHER` (from file extension).
- The Admin UI renders images and has an upload widget for media fields.
- The upload, delete and download root fields are custom operations. ACLs do not cover them. I found no auth check in the provider.
- Only S3. No local disk, GCS or Azure Blob storage. No GraphQL multipart upload.

## Observability

- Logging: Pino logger in `@exogee/logger`. Level from env `LOGGING_LEVEL` (`fatal` to `trace`, default `info`). `safeErrorLog` helper. SQL logging via `DEBUG=knex:query` (MikroORM 6 with knex).
- OpenTelemetry, external mode: env `OTEL_EXPORTER_OTLP_ENDPOINT` (and `OTEL_EXPORTER_OTLP_HEADERS`) sends OTLP HTTP traces. `SERVICE_NAME` sets `service.name` (default `Graphweaver`).
- OpenTelemetry, integrated mode: `openTelemetry: { traceProvider, instrumentations }` in config. `JsonSpanProcessor` writes spans to any provider that has `createTraces` (MikroORM). Spans become the built-in `Trace` entity. The Admin UI shows them in an "Analytics"/trace view with a waterfall.
- `@TraceMethod()` decorator, `trace(fn)`, `traceSync(fn)`: add spans to your own code. `setEnableTracingForRequest` and `setDisableTracingForRequest` turn tracing on or off per request. Entities with `apiOptions.excludeFromTracing` are not traced.
- Header `X-GRAPHWEAVER-SUPPRESS-TRACING` skips tracing for a request (the Admin UI sets it on trace views, I think).
- `Trace` entity needs an ACL when auth is on. Otherwise implicit deny blocks it.
- No metrics endpoint (Prometheus). No Apollo Studio usage reporting setup beyond what Apollo Server gives.

## Admin UI (`@exogee/graphweaver-admin-ui`, `-admin-ui-components`)

- Generated React 19 single page app. Built with Vite. Uses Apollo Client 3, TanStack Table, Formik, GraphiQL 4 and Tiptap. Deploy as static files (S3, Vercel, Netlify, Azure Blob).
- Schema info comes from a custom query `_graphweaver` (`AdminUiMetadata { entities, enums }`), not from introspection. Per entity it has fields, attributes, backend, summary field, supported aggregations, default filter and sort. Turn on or off with `adminMetadata.enabled`. Filter per user with `adminMetadata.hooks.beforeRead/afterRead`.
- Most Admin UI GraphQL documents are built at runtime from this metadata. A static list is enumerated for trusted documents (`documents/enumerate.ts`).
- Pages: entity list (table with filter bar, sort by column, keyset or offset paging, row selection), detail panel (create, edit, delete, nested relationship editing), "Delete selected rows" bulk delete, CSV export (`export-modal`, page size from `exportPageSize`), GraphQL playground (GraphiQL), Analytics trace viewer (spans from the `Trace` entity).
- Sidebar groups entities by `backendDisplayName`. `hideInSideBar` hides an entity.
- Filter widgets per `AdminUIFilterType`: text, dropdown text, boolean, enum, numeric, numeric range, date range, relationship.
- Field editors: text, rich text and markdown (Tiptap, `detailPanelInputComponent`), JSON viewer, media upload with image preview, date and currency formatting (`format`).
- Customisation: `customFields` map from `src/admin-ui/custom-fields` (add or override a field per entity, `index`, `hideInTable`, `hideInDetailForm`, `panelMode`, gets `CustomFieldArgs { entity, context: 'table' | 'detail-form' }`). `customPages` with `routes()` and `navLinks()` from `src/admin-ui/custom-pages` (React Router routes, `DefaultLayout`). `csvExportOverrides` from `src/admin-ui/csv-export-overrides` (custom CSV query per entity, not on the docs site).
- Paths set in `graphweaver-config.(js|ts)` (`defineConfig`): `adminUI.customPagesPath`, `customFieldsPath`, `csvExportOverridesPath`, `adminUI.auth` (see "Auth").
- Env: `VITE_GRAPHWEAVER_API_URL` (default `http://localhost:9001/`), `VITE_ADMIN_UI_BASE` (base path, also `graphweaver build --adminUiBase`), `VITE_AUTH_ZERO_DOMAIN`, `VITE_AUTH_CLIENT_ID`, `VITE_OKTA_DOMAIN`, `VITE_MICROSOFT_ENTRA_CLIENT_ID`, `VITE_MICROSOFT_ENTRA_TENANT_ID`.
- Auth UI (`@exogee/graphweaver-auth-ui-components`): login pages for each primary method, challenge page for step-up, passkey and Web3 enrolment, forgotten and reset password pages. The token and refresh token are kept in `localStorage` (`graphweaver-auth`, `graphweaver-refresh-token`).
- Components are exported for reuse in custom pages: `Table`, `DetailPanel`, `FilterBar`, `Button`, `Modal`, `Select`, `ComboBox`, `DatePicker`, `JsonViewer`, `GraphQlViewer`, `TraceViewer`, `apolloClient`, and others. Storybook stories exist for many.
- `vite-plugin-graphweaver`: injects the custom fields, pages and CSV overrides as virtual modules (`virtual:graphweaver-admin-ui-*`).
- No built-in dashboards, charts or saved views. No per-user column layout. No audit log viewer (the MikroORM `AuditChange` rows are not shown, I think).

## CLI (`graphweaver`) and build tooling

- `graphweaver init [--name] [--backend postgres|mysql|mssql|sqlite|rest ...] [--useVersion]`: scaffold a project (interactive prompts). Needs Node 18+ (docs say Node 22 and pnpm 9).
- `graphweaver import [mssql|mysql|postgresql|sqlite] [--database --host --port --user --password] [-o/--overwrite] [--clientGeneratedPrimaryKeys]`: introspects a database with MikroORM and writes data entities, schema entities, index files and a connection file. Detects many-to-many pivot tables, builds both sides of relations, singular names. Skips tables with composite or no primary key. Defaults can come from the `import` block in `graphweaver-config`.
- `graphweaver init-auth [password|api-key|magic-link]` (alias `auth`): writes `.env` with a fresh EC key pair (`AUTH_PUBLIC_KEY_PEM_BASE64`, `AUTH_PRIVATE_KEY_PEM_BASE64`), writes `graphweaver-config` for the Admin UI login, inserts an `admin` user (argon2id hash) or an API key into an existing `Credentials` or `ApiKey` table, and prints the password or key. Only mysql, postgresql and sqlite.
- `graphweaver start [backend|frontend|all] [--host] [--port]`: dev server. Backend runs through `serverless-offline` (Lambda emulation) on port 9001. Admin UI runs on Vite on port 9000.
- `graphweaver watch [backend|frontend|all]`: like `start` plus chokidar file watching. Rebuilds and regenerates types and trusted documents on change, add or delete.
- `graphweaver build [backend|frontend|all] [--adminUiBase /]`: esbuild bundles the backend into one `dist/backend/index.js` (no `node_modules` needed). Vite builds the Admin UI into `dist/admin-ui`. Runs codegen and then trusted documents.
- `graphweaver build-types`: only type generation (`gw-types` bin).
- `graphweaver print-schema [-o file]`: prints SDL with directives (`printSchemaWithDirectives`). Not on the docs site.
- `graphweaver analyse bundle` (alias `analyze`, `a`): bundle size analysis. Not on the docs site.
- Every option can also come from env vars with prefix `GRAPHWEAVER_` (yargs `.env('GRAPHWEAVER')`).
- Codegen: `@graphql-codegen` with `typescript`, `typescript-operations`, `typescript-react-apollo` and `near-operation-file-preset`. Writes `types.generated.ts` (default `./src/frontend/types.generated.ts`, set by `fileAutoGenerationOptions.typesOutputPath`, string or list). For each `*.ts`/`*.tsx` file with `gql` it writes a `*.generated.ts` with typed Apollo hooks next to it. `watchForFileChangesInPaths` covers frontends in a monorepo.
- `graphweaver-config.(js|ts|mts|cts)` with `defineConfig`: keys `backend.additionalFunctions` (extra Lambda handlers for dev), `adminUI`, `start` and `build` hooks (`onResolveEsbuildConfiguration`, `onResolveViteConfiguration`, `onResolveServerlessOfflineConfiguration`), `import`, `trustedDocuments.allowLists`.
- Deployment: `@exogee/graphweaver-cdk` construct `GraphweaverApp` (`name`, `network { vpc, graphqlSecurityGroup, databaseSecurityGroup }`, `adminUI { buildPath, cert, url, customHeaders, csp }`, `database`, `ecs` or `lambda` options). Admin UI goes to S3 plus CloudFront. API goes to Lambda (`NodejsFunction`) or ECS on EC2 behind an ALB (`ApplicationLoadBalancedEc2Service`, Docker image). Optional RDS database with a Secrets Manager secret. Docs also have Docker and standalone Node guides.
- `NODE_ENV=production` turns off introspection and the Apollo landing page. Re-enable with `apolloServerOptions`.
- `upgrading-from-v0-to-v1` and `upgrading-from-v1-to-v2` migration guides exist. The `pre-commit-hook` doc is for contributors (GitLeaks secret scan).

## Upcoming and unreleased work

- Unreleased on `main` after v2.24.1: codegen now runs before trusted document generation (#2637). MinIO test image moved to Chainguard (#2638). The rest is dependabot.
- `development` branch is at the same commit as `main` (2026-10-07).
- Stale feature branches (no open PRs):
  - `EXOGW-371-Support-Swagger-OpenAPI-Introspection` (WIP, 2025-03-18, 1890 commits behind): `graphweaver import` for OpenAPI/Swagger into the REST provider (`rest/src/introspection`).
  - `spike/extended-auth-token` (2025-09-07): extra data in the auth token from the password method.
  - `cursor/convert-graphweaver-to-esm-0f4d` (2025-08-20): ESM conversion.
  - `chore/upgrade-mikro-orm` (MikroORM 6.5), `chore/upgrade-to-pnpm-v10`, `example-client-side-keys` (2026-02-03, repro for client-side keys).
- Open feature issues: linked columns in Admin UI tables (#1571), field validation from hooks (#1191), docs on custom queries (#1192). Open bugs: nested entity from a custom mutation result (#1458), `bigint` primary key serialisation (#1355), poor DB connection error messages (#1195), `CreateOrUpdateHookParams` typing (#1447).
- No public roadmap. No RFCs. Release notes are the only change record.

## Not supported

- Subscriptions, live queries, `@defer`, `@stream`, `@oneOf`. Schema has only `Query` and `Mutation`.
- GraphQL interfaces. Unions exist only through `collectUnionTypeInformation`. No Relay `Node` interface, no global IDs, no connections or cursor pagination in the API.
- GraphQL multipart file upload. Media goes through presigned S3 URLs only.
- Input validation framework. No validators on fields. Validation is done by hand in hooks (open issue #1191).
- Arguments on computed fields (`@Field` has no `args`).
- Composite primary keys and tables without a primary key (MikroORM writes and introspection).
- Aggregates other than `count`. No group by.
- Sort by relationship or aggregate, nulls ordering, nested list pagination, max page size.
- Full-text, regex, JSON path, array or geo filters. Relation existence filters.
- Upsert by a unique key other than the primary key. Single `createOrUpdate` mutation. Delete mutations do not return the deleted object.
- Renaming generated root fields (only `plural` and the entity name).
- Per-role schema visibility. Directive based auth. ACLs on custom queries and mutations.
- Cookie sessions, CSRF protection, OAuth2 server. Tokens are bearer JWTs only.
- Response caching or `@cacheControl` (beyond what Apollo Server plugins give).
- Federation gateway, schema stitching, remote GraphQL schema provider. Multi-field or composite `@key`.
- Write support in the REST and Xero providers. Providers for MongoDB, DynamoDB, Elasticsearch, gRPC, OpenAPI import (an unfinished branch exists).
- Two-phase commit across providers.
- Storage other than S3 (or S3-compatible).
- Python, Django, or any non-Node runtime. Hosting is Fastify, AWS Lambda or Azure Functions.

## Docs and code disagree

- REST provider: the `connect-to-a-rest-api` doc describes create, update and delete endpoints. The code throws `Not implemented` for all writes.
- Column-level security: the `column-level-security` doc shows only hook based hiding. The code has `fieldRestrictions` in ACLs (v2.2.0), which throws `RestrictedFieldError`.
- Hooks: the docs list an `info` param and type names `CreateOrUpdateHook`, `ReadHook`, `DeleteHook`. The code has no `info` and uses `...HookParams` names.
- Filters: the docs list `_gt/_gte/_lt/_lte` for Number, Date and ISOString. The code also adds them to `ID`, `String` and other scalars.
- AWS Cognito: the docs import `@exogee/graphweaver-aws-cognito`. The package in the repo is `@exogee/graphweaver-aws`.
- Custom Admin UI fields: the doc uses `hideOnDetailForm`. The code reads `hideInDetailForm` (and `hideInTable`).
- Custom fields and pages path: the docs say `[project]/admin-ui/custom-fields` and `.../custom-pages`. The code default is `src/admin-ui/custom-fields` and `src/admin-ui/custom-pages`.
- Several pages (`hooks`, `typescript-type-autogeneration`, `monorepo-automated-types-generation-in-frontends`) still use v1 APIs: `extends GraphQLEntity<...>`, `@ObjectType`, `@SummaryField`, `new Graphweaver({ resolvers })`. v2 removed `GraphQLEntity`, and `GraphweaverConfig` has no `resolvers` key.
- `deployments` doc text says `graphqlArmorOptions`. The real key is `graphQLArmorOptions` (the doc example uses the right one).
- `importing-a-database` lists PostgreSQL, MySQL and SQLite. The CLI also accepts `mssql`. The `import` block type in `graphweaver-config` omits `mssql`.
- `quick-start` asks for Node 22+. The CLI checks only Node 18+.
- `federation` doc says Federation v1 and v2 are supported. The schema always links Federation v2.3. The compatibility README marks multi, composite and repeatable `@key` as WARNING.
- `upload-media` and others do not mention that `getUploadUrl`, `getDeleteUrl` and `getDownloadUrl` bypass ACLs.
- Not on the docs site at all: Trusted Documents, `fieldRestrictions`, `print-schema`, `analyse`, `csvExportOverridesPath`, `requiredForCreate`/`requiredForUpdate`, `logOnDidResolveOperation`, `graphqlDeduplicator`, field `complexity`, optimistic locking, `ChangeTracker` audit trail, `@UntrackedProperty`, `supportsPseudoCursorPagination`.
- `defaultSort` is only shown in an example on the `connect-to-xero` page.
- `eventbrite-integration` and `mailchimp-integration` pages are empty.

## Sources

Docs (https://graphweaver.com/docs, all 63 pages from https://graphweaver.com/sitemap.xml, saved as text in `/tmp/gw-docs/txt`). Base URL `https://graphweaver.com/docs/<page>`. Pages:
`add-custom-fields-to-the-admin-ui`, `add-custom-pages-to-the-admin-ui`, `adding-api-key-authentication`, `adding-local-authentication`, `adding-magic-link-authentication`, `admin-ui`, `admin-ui-default-filters`, `apollo-server-plugins`, `attribute-mapping`, `auth0-authentication`, `authentication`, `authentication-concepts`, `available-demos`, `aws-cognito-integration`, `aws-deployments-cdk`, `column-level-security`, `community-support`, `connect-to-a-data-source`, `connect-to-a-mysql-db`, `connect-to-a-postgresql-db`, `connect-to-a-rest-api`, `connect-to-microsoft-dynamics`, `connect-to-salesforce-graphql-api`, `connect-to-sqlite`, `connect-to-xero`, `connecting-a-second-data-source-to-graphweaver`, `contributing-to-graphweaver`, `create-a-data-provider`, `customising-base-resolver`, `data-entities`, `decorators`, `deployments`, `eventbrite-integration`, `federation`, `filters-and-operators`, `further-learning-resources`, `glossary`, `graphql-entities-and-resolvers`, `hooks`, `how-versioning-works`, `implementing-authorization`, `importing-a-database`, `introduction-to-baseloader`, `introduction-to-baseresolver`, `introduction-to-data-providers`, `linking-entities`, `logging`, `mailchimp-integration`, `monorepo-automated-types-generation-in-frontends`, `opentelemetry`, `pre-commit-hook`, `quick-start`, `security`, `tech-stack`, `two-factor-authentication`, `typescript-type-autogeneration`, `upgrading-from-v0-to-v1`, `upgrading-from-v1-to-v2`, `upload-media`, `what-is-graphql`, `what-is-graphweaver`, `what-is-querymanager`.

Key pages for the closing sections:
- https://graphweaver.com/docs/federation
- https://graphweaver.com/docs/admin-ui
- https://graphweaver.com/docs/add-custom-fields-to-the-admin-ui
- https://graphweaver.com/docs/add-custom-pages-to-the-admin-ui
- https://graphweaver.com/docs/importing-a-database
- https://graphweaver.com/docs/quick-start
- https://graphweaver.com/docs/typescript-type-autogeneration
- https://graphweaver.com/docs/monorepo-automated-types-generation-in-frontends
- https://graphweaver.com/docs/deployments
- https://graphweaver.com/docs/aws-deployments-cdk
- https://graphweaver.com/docs/upload-media
- https://graphweaver.com/docs/opentelemetry
- https://graphweaver.com/docs/logging
- https://graphweaver.com/docs/column-level-security
- https://graphweaver.com/docs/implementing-authorization
- https://graphweaver.com/docs/two-factor-authentication
- https://graphweaver.com/docs/connect-to-a-rest-api

Repo: https://github.com/exogee-technology/graphweaver (clone `/tmp/graphweaver`, `main` at `cfbcfb2`, 2026-10-07). Paths used:
- `src/packages/core/src/` (`schema-builder.ts`, `metadata.ts`, `resolvers.ts`, `decorators/`, `federation/`, `open-telemetry/`, `metadata-service/`, `utils/batched-writes.ts`)
- `src/packages/server/src/` (`server.ts`, `config.ts`, `trace.ts`, `apollo-plugins/`, `integrations/`)
- `src/packages/mikroorm/src/` (`provider/provider.ts`, `provider/assign.ts`, `database.ts`, `introspection/generate.ts`, `utils/`, `decorators/`, `entities/`)
- `src/packages/auth/src/`, `src/packages/auth-ui-components/src/`
- `src/packages/rest/src/`, `src/packages/rest-legacy/src/`, `src/packages/xero/src/`, `src/packages/aws-cognito/src/`
- `src/packages/storage-provider/src/` (`storageProvider.ts`, `decorators/media-field.ts`)
- `src/packages/admin-ui/src/pages/`, `src/packages/admin-ui-components/src/` (`config.ts`, `custom-page-config.ts`, `utils/use-schema.ts`, `utils/schema-types.ts`, `export-modal/`, `selection-bar/`, `filters/`)
- `src/packages/cli/src/` (`index.ts`, `tasks.ts`, `auth/index.ts`, `import/index.ts`, `init/`)
- `src/packages/builder/src/` (`codegen/`, `start/backend.ts`, `build/frontend.ts`, `auth/`)
- `src/packages/config/src/config.ts`, `src/packages/cdk/src/app/`, `src/packages/logger/src/logger.ts`, `src/packages/scalars/src/`
- `src/examples/federation/integration/README.md`, `src/examples/`

GitHub via `gh`:
- Releases: https://github.com/exogee-technology/graphweaver/releases (v1.0.0 to v2.24.1)
- Open issues: https://github.com/exogee-technology/graphweaver/issues
- Branches: https://github.com/exogee-technology/graphweaver/branches (`EXOGW-371-Support-Swagger-OpenAPI-Introspection`, `spike/extended-auth-token`, `cursor/convert-graphweaver-to-esm-0f4d`, `development`)
- Compare: https://github.com/exogee-technology/graphweaver/compare/v2.24.1...main

Not available: `/llms.txt`, `/llms-full.txt`, `.md` page variants, `CHANGELOG.md`.
