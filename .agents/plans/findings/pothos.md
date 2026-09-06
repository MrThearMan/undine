# Pothos findings

Versions checked: `@pothos/core` 4.15.1. Repo `main` at `4c8bc28` (2026-09-14).
Pothos is a TypeScript code-first schema builder. `new SchemaBuilder<SchemaTypes>(options)` collects types and fields. `builder.toSchema()` returns a plain graphql-js `GraphQLSchema`.
It is not a server. It has no HTTP, transport, subscriptions transport, persisted queries or caching layer. Docs use GraphQL Yoga or Apollo Server for serving.
Almost all features beyond core are separate `@pothos/plugin-*` packages. Plugins add options and methods to the core API through TypeScript declaration merging (`PothosSchemaTypes` global namespace).
Peer dependency `graphql` `^16.10.0 || ^17.0.0` (GraphQL 17 since core 4.13.0). Pothos 4 needs TypeScript 5.0.2+, Node 18+. TypeScript `strict` mode is required for inference. TypeScript 7 is supported in the Prisma plugin since 4.15.0.
Type safety comes from TypeScript inference only. There is no code generation step for resolver types (Prisma and Prisma-next plugins use a generator for model types).

## Maintenance status

- Actively maintained, mostly by one author (Michael Hayes). Last commit on `main`: `4c8bc28`, 2026-09-14.
- npm `latest`: `@pothos/core` 4.15.1 (2026-09-13), `plugin-prisma` 4.17.0 (2026-09-13), `plugin-relay` 4.8.1 (2026-09-13), `plugin-scope-auth` 4.2.1 (2026-09-13), `plugin-validation` 4.3.4 (2026-09-13), `plugin-drizzle` 0.20.0 (2026-09-14), `plugin-grafast` 0.1.2 (2026-07-08).
- Latest GitHub release: `@pothos/plugin-drizzle@0.20.0`, 2026-09-14. Releases are per package (changesets).
- `@pothos/plugin-prisma-next` is `private: true` in the repo (version 0.1.1). It is not on npm (404).
- Many recent commits come from AI agent branches (`codex/*`, `claude/*`, `copilot/*`). 41 `codex/*` branches exist. A batch of `fix/audit-20260913-*` branches exists.
- Old package name was GiraphQL (`@giraphql/*`). Migration guides exist for GiraphQL to Pothos, v2, and v4.

## Core schema builder (`@pothos/core`)

- `new SchemaBuilder<SchemaTypes>(options)`. `SchemaTypes` generic keys: `Context`, `Root`, `Defaults` (`'v3' | 'v4'`), `Objects`, `Inputs`, `Interfaces`, `Scalars` (`{ Input, Output }` per scalar), `DefaultFieldNullability`, `DefaultInputFieldRequiredness`, `AsyncSelections`, plus plugin keys.
- Builder options: `plugins`, `defaultFieldNullability`, `defaultInputFieldRequiredness`, `defaults: 'v3'` (restore all v3 defaults and option names across core and plugins).
- Three ways to bind a backing model: refs (`builder.objectRef<T>('Name')`, `interfaceRef`, `inputRef`), classes (`builder.objectType(MyClass, { name })`), or string names registered in `SchemaTypes.Objects`/`Interfaces`/`Inputs`.
- Backing model is separate from the GraphQL shape. There is no default resolver by property name. Fields must be declared with `t.expose*` or a resolver.
- Root types: `queryType`, `queryFields`, `queryField`, `mutationType`/`mutationFields`/`mutationField`, `subscriptionType`/`subscriptionFields`/`subscriptionField`.
- Custom root type names: `queryType({ name: 'RootQuery' })` (core 4.4.0). Objects named `Query`, `Mutation`, `Subscription` can then be non-root objects (4.6.0). The API reference does not list the `name` option.
- `objectType(param, options, fields?)`, `objectFields`, `objectField`. Options: `description`, `fields`, `interfaces` (array or thunk), `isTypeOf`, `name`, `astNode`, `extensions`.
- `interfaceType`, `interfaceFields`, `interfaceField`. `resolveType` may return a ref, class, or type name. Interfaces can implement interfaces.
- `unionType(name, { types, resolveType })`. `types` accepts a thunk. Backing type is inferred as the union of member shapes.
- `enumType(nameOrTsEnum, { values, name })`. Values from `as const` string arrays, value maps (`value`, `description`, `deprecationReason`, `extensions`, `astNode`), TypeScript enums (numeric values kept), or `Object.keys`/`Object.values` of objects.
- `scalarType(name, { serialize, parseValue, parseLiteral, specifiedByURL, extensions })`. GraphQL 17 hooks `coerceOutputValue`, `coerceInputValue`, `coerceInputLiteral`, `valueToLiteral` (4.13.0).
- `addScalarType(name, GraphQLScalarType, options?)` registers an existing scalar (for example `graphql-scalars`). `specifiedByURL` is kept since 4.15.0 (changes printed SDL).
- Built-in scalar TypeScript types can be overridden through `SchemaTypes.Scalars` (for example `ID: { Input: string, Output: string }`). Default `ID` is `Input: string`, `Output: number | string | bigint`.
- `inputType(param, { fields, isOneOf, description, astNode })`. `isOneOf: true` builds a OneOf input. The TypeScript type becomes a discriminated union.
- Recursive inputs need `builder.inputRef<Shape>('Name').implement(...)` so TypeScript does not infer through the cycle.
- `builder.args((t) => ({...}))` builds a reusable args map.
- `toSchema({ directives, extensions, sortSchema, astNode, ...pluginOptions })`. `sortSchema` defaults to `true` (lexicographic sort). Each call builds a new schema and new plugin instances.
- `SchemaBuilder.allowPluginReRegistration = true` for HMR.
- `astNode` option on types, fields, args, input fields, enum values and schema (4.11.0). Attaches AST metadata for tools. Does not build anything from SDL.
- `extensions` option on fields, args, types. Used by plugins and tools.
- Deferred field thunks: field callbacks run at `toSchema()`, so circular imports between type modules work. `interfaces: [...]` arrays are evaluated eagerly unless passed as a thunk.

## Core field API (`t`)

- `t.field({ type, args, nullable, description, deprecationReason, resolve, extensions, astNode })`.
- Scalar helpers: `t.string`, `t.id`, `t.int`, `t.float`, `t.boolean`, and `*List` variants.
- Expose helpers: `t.expose(name, { type })`, `t.exposeString`, `t.exposeID`, `t.exposeInt`, `t.exposeFloat`, `t.exposeBoolean`, and `*List` variants. Not available on root types.
- `t.listRef(type, { nullable })` for nested lists. `t.arg.listRef` and `t.input.listRef` for input side.
- Nullability: `nullable: boolean | { list, items }`. Fields are nullable by default in v4 (non-null in v3). List items are non-null by default.
- Args: `t.arg({ type, required, defaultValue, description, deprecationReason, extensions, astNode })`, `t.arg.string()` and other scalar helpers. `required: boolean | { list, items }`. Args optional by default.
- Deprecated args and input fields: `deprecationReason` on args and input fields.
- Resolver return types are type checked against the backing model. List fields accept `Iterable` and `AsyncIterable` (4.7.0, 4.12.0).
- Subscriptions: field `subscribe` returns an `AsyncIterable`, `resolve` maps each event. `subscribe` must be declared before `resolve` for inference.
- Type helpers: `ref.$inferType`, `ref.$inferInput`, `typeof builder.$inferSchemaTypes`, `PothosSchemaTypes.ExtendDefaultTypes<T>`.
- Refs: `ObjectRef`, `InterfaceRef`, `InputObjectRef`, `EnumRef`, `ScalarRef`, `UnionRef`, `ListRef`, `InputListRef`, `ImplementableObjectRef` (has `.implement()`), `ImplementableInterfaceRef`, `ImplementableInputObjectRef`, `FieldRef`, `InputFieldRef`, `ArgumentRef`. `ref.kind` is `Object` or `Interface`.
- `initContextCache()` from core: spread into the per-request context so plugin caches (dataloader, scope-auth, relay node cache) survive context copies by the server. Undocumented sibling `createContextCache`.
- Core utils exported (mostly undocumented): `encodeBase64`, `decodeBase64`, `encodeBase64Bytes`, `decodeBase64Bytes`, `encodeCursorChunk`, `encodeCursorTuple`, `decodeCursorChunk`, `validateConnectionArguments`, `getConnectionPageSize`, `parseCursorConnectionArgs`, `brandWithType`, `getTypeBrand`, `completeValue`, `reduceMaybeAsync`, `sortClasses`.
- Errors: `PothosError`, `PothosSchemaError`, `PothosValidationError`.

## Plugin system (writing plugins)

- A plugin is a class extending `BasePlugin<Types, RequestData>` registered with `SchemaBuilder.registerPlugin(name, Class)`. Types go in `global-types.ts` inside `declare global { namespace PothosSchemaTypes {} }`.
- Plugins add options by extending interfaces: `SchemaBuilderOptions`, `BuildSchemaOptions` (toSchema options), `ObjectTypeOptions` and other type options, `FieldOptionsByKind`, `MutationFieldOptions` and other field options, `UserSchemaTypes` + `ExtendDefaultTypes` (new `SchemaTypes` keys).
- Plugins add methods by extending `SchemaBuilder`, `RootFieldBuilder`, `ObjectFieldBuilder`, `InputFieldBuilder` and similar interfaces, then assigning prototype functions.
- Build hooks: `onTypeConfig`, `onOutputFieldConfig`, `onInputFieldConfig`, `onEnumValueConfig`, `beforeBuild`, `afterBuild` (may return a new schema).
- Runtime hooks: `wrapResolve`, `wrapSubscribe`, `wrapResolveType`, `wrapIsTypeOf`, `wrapArgMappers` (4.10.0, outer error boundary around arg mapping).
- `fieldConfig.argMappers`: ordered, possibly async argument mappers run before `wrapResolve`. Used by validation and relay global IDs.
- Returning `null` from `onOutputFieldConfig`, `onInputFieldConfig` or `onEnumValueConfig` removes that field or value from the schema.
- Inherited interface fields get one config per owner (4.15.0). `parentType` is the owner, `declaringType` is the interface.
- Config objects carry `kind`, `graphqlKind`, `pothosOptions`.
- `this.runUnique(key, cb)`: run once per builder across `toSchema` calls. `createRequestData(context)` + `this.requestData(context)` for per-request plugin state.
- Input mapping helpers: `mapInputFields`, `createInputValueMapper` (build-time selection of which input fields need mapping, including recursive and nested list inputs).
- Other helpers: `builder.configStore.onTypeConfig(ref, cb)`, `fieldRef.onFirstUse(cb)`, `buildCache.getTypeConfig`.
- Ordering: config hooks, resolver wrappers and `afterBuild` run in reverse plugin order. `beforeBuild` runs in list order. The first plugin is the outermost resolver wrapper. Docs say to list `scope-auth` first.
- `@pothos/plugin-example` is a template plugin.

## Add GraphQL plugin (`@pothos/plugin-add-graphql`)

- Builder option `add: { schema?, types? }` imports an executable schema or named types. Dependencies are imported recursively.
- Local Pothos types and fields win over imported ones with the same name. Root fields are merged.
- Methods returning refs: `builder.addGraphQLObject<Shape>(type, { name, fields, extensions })`, `addGraphQLInterface`, `addGraphQLUnion` (`types` override), `addGraphQLEnum` (`values` override), `addGraphQLInput`.
- In a `fields` callback, `null` removes an imported field. A field ref adds or replaces a field.
- Use case: incremental migration from SDL-first or other libraries.

## Converter (`@pothos/converter`)

- CLI `convert <path> --out --types` and class `PothosConverter(schema, { types })`. Generates Pothos TypeScript code from SDL. Not on the docs site (README only points to the site).

## Complexity plugin (`@pothos/plugin-complexity`)

- Builder or `toSchema` option `complexity: { defaultComplexity, defaultListMultiplier, fieldComplexity, limit, complexityError, disabled }`.
- `limit: { complexity, depth, breadth }` or a function `(ctx) => limits` for per-request limits.
- Field option `complexity: number | { field, multiplier } | (args, ctx) => ...`. Default field cost 1, default list multiplier 10.
- Complexity is computed from the document before root fields resolve. It estimates cost from args, not actual row counts.
- `complexityError(kind, result, info)` returns or throws a custom error.
- `complexityFromQuery(query, { schema, ctx, variables })` computes cost without executing.
- `createComplexityRule({ context, variableValues, operationName, maxComplexity, maxDepth, maxBreadth })` returns a graphql-js validation rule.
- `disabled: true` turns checks off. The docs do not mention `disabled`.

## Dataloader plugin (`@pothos/plugin-dataloader`)

- Needs the `dataloader` package. One loader per ref per request context.
- `builder.loadableObject(name, { load(ids, ctx), fields, sort, toKey, cacheResolved, loaderOptions })`. Resolvers may return an ID or a full object. IDs go through the loader, objects skip it.
- `builder.loadableObjectRef`, `loadableInterface`, `loadableInterfaceRef`, `loadableUnion`, `loadableNode` and `loadableNodeRef` (with relay). `loadableInterface`, `loadableInterfaceRef` and `loadableUnion` are not documented.
- Field methods: `t.loadable({ type, load, resolve, byPath, sort, loaderOptions })`, `t.loadableList` (one key to a list), `t.loadableGroup({ load, group })` (flat result grouped by key).
- `byPath: true`: batch per query path so `load` receives the field `args` (and `info` since 4.3.0).
- `sort: (row) => key` reorders results to match keys. Missing keys become `null`.
- `cacheResolved`: prime the loader cache with objects returned by resolvers. `toKey` shares a key function between `sort` and `cacheResolved`.
- `ref.getDataloader(context)` for manual use. `rejectErrors(loadManyResult)` turns `Error` items into rejected promises.
- `clearAllDataLoaders(context)` resets all loaders (for long-lived subscription contexts, 4.4.0).
- Partial failures: `load` may return `Error` items. Pothos maps them to per-item GraphQL errors.

## Directives plugin (`@pothos/plugin-directives`)

- Declares directive types in `SchemaTypes.Directives` (`locations`, `args`). Attaches applied directives with `directives: [{ name, args }]` or `directives: { name: args }` on types, fields, args, enum values.
- Locations: `ARGUMENT_DEFINITION`, `ENUM_VALUE`, `ENUM`, `FIELD_DEFINITION`, `INPUT_FIELD_DEFINITION`, `INPUT_OBJECT`, `INTERFACE`, `OBJECT`, `SCALAR`, `SCHEMA`, `UNION`. Schema directives via `toSchema({ schemaDirectives })`.
- Stores directives in `extensions` and AST nodes. It does not implement directive behavior. A schema transformer (for example `graphql-rate-limit-directive`) applies behavior.
- `directives: { useGraphQLToolsUnorderedDirectives: true }` for the graphql-tools extension format.
- Adds `@deprecated` to mock AST nodes so directive-aware printers keep deprecations.

## Drizzle plugin (`@pothos/plugin-drizzle`, 0.x)

- Needs Drizzle relational query builder v2 (`drizzle-orm` 1.0 release candidate). Options `drizzle: { client, getTableConfig, relations, defaultConnectionSize, maxConnectionSize, filterConnectionTotalCount, skipDeferredFragments }`. `client` may be `(ctx) => db`.
- `builder.drizzleObject(table, { name | variant, select, fields })`, `drizzleInterface`, `drizzleNode` (relay, `id: { column }`, composite keys), `drizzleObjectField(s)`, `drizzleInterfaceField(s)`.
- `t.drizzleField({ type, resolve(query, ...) })`: resolver calls `query(options)` and passes it to `findFirst`/`findMany`. The plugin merges the GraphQL selection into the query.
- `t.drizzleConnection` (cursor pagination with auto tie-breaker on primary key), `t.drizzleFieldWithInput` (with-input plugin), `t.drizzleQueryFromInfo(table, { context, info, path, paths, columns, where })` (0.20.0).
- Object field methods: `t.relation(name, { query, args, type })`, `t.relatedConnection(name, { query, totalCount, cursor })`, `t.relatedCount(name, { where })`, `t.relatedField(name, { type, select(buildFilter), resolve })` (custom SQL aggregates), `t.variant(ref, { isNull, select })`, `t.expose*`.
- Relation `query` callback gets `(args, ctx, pathInfo)` with `path` and `segments` (0.17.0).
- Field `select: { columns, with, extras }` or `select(args, ctx, nestedSelection)`. `extras` are SQL expressions (`sql\`lower(...)\``). Type-level `select` replaces the default "all columns".
- `nestedSelection(query, path, type)`: plan a deeper selection. Path segments `{ name, type }` pin an implementation.
- Fallback queries: missing data is loaded by a batched `findMany` on the primary key per tick. Missing row gives `Model users(1) not found`.
- Two aliases of one relation with different args: first one is planned, the other uses a fallback query.
- Variant selection conflicts on one row throw `PothosValidationError` at runtime.
- Many-to-many through `.through(...)` relations are exposed directly with no junction type.
- Connection `orderBy` can name an `extras` expression (0.18.0). Cursors carry typed values (Date, bigint, bytes, decimals).
- Count-only connection queries skip the row query (`totalCountOnly`).
- `drizzleConnectionHelpers(builder, table, { select, query, args, resolveNode, cursor })` with `getQuery`, `getArgs`, `resolve`, `ref`. Paginates join rows while returning target nodes and custom edge fields.
- `AsyncSelections: true` allows async `select`, relation `query` and `relatedCount` `where` callbacks.
- Docs document ordering pitfalls: nullable ordering columns cannot be paged past, and `Date` truncation of Postgres microsecond timestamps breaks cursors.
- Exports not on the docs site: `drizzleClientCache`, `getSchemaConfig`, `drizzleTableName`, `DrizzleObjectFieldBuilder`.

## Errors plugin (`@pothos/plugin-errors`)

- Field option `errors: { types: [ErrorClass], union, result, dataField, directResult }`. The field becomes a union `<Parent><Field>Result = ErrorType | <Parent><Field>Success { data }`. Thrown instances of listed classes become typed results. Other errors stay GraphQL errors.
- Error classes are registered as object types with `builder.objectType(ErrorClass, { name, interfaces, fields })`. Matching uses `instanceof`.
- Builder options `errors: { defaultTypes, directResult, onResolvedError, defaultResultOptions, defaultUnionOptions, defaultItemResultOptions, defaultItemUnionOptions, unsafelyHandleInputErrors }`. Naming callbacks get `{ parentTypeName, fieldName }`.
- `directResult: true`: put the object type directly in the union, no wrapper.
- `itemErrors: {}` on list fields: per-item result unions. Works with sync and async iterators (yielded error becomes an item, thrown error becomes the final item).
- `t.errorUnionField({ types })` and `t.errorUnionListField`: multiple success types plus error types in one union (4.7.0).
- `builder.errorUnion(name, { types, omitDefaultTypes, resolveType })`: reusable error union. Returned or thrown errors are handled.
- `unsafelyHandleInputErrors: true`: validation errors become typed results. They then skip authorization hooks.
- Recommended pattern: shared `Error` interface plus a `BaseError` object in `defaultTypes`.
- Works with dataloader and prisma if listed before them. Subscriptions supported since 4.3.0.

## Federation plugin (`@pothos/plugin-federation`)

- Apollo Federation 2 subgraphs. Needs `@pothos/plugin-directives` and `@apollo/subgraph`.
- `builder.selection<Shape>('id')` type-checked field set strings (template literal types). `FieldSet<Shape>` cast for selections with inline fragments (4.5.0).
- `builder.asEntity(ref, { key | keys, resolveReference, interfaceObject })`. Interface entities (Fed 2.3).
- `builder.externalRef(name, key, resolveReference)` then `.implement({ externalFields, fields })`. `ref.provides(selection)` for `@provides`. Field option `requires: builder.selection(...)`.
- `builder.keyDirective(selection, resolvable)` for `resolvable: false` keys.
- `builder.toSubGraphSchema({ linkUrl, federationDirectives, composeDirectives, schemaDirectives, directives })`. `linkUrl` defaults to Federation v2.6.
- Field and type options: `shareable`, `tag`, `inaccessible`, `override: { from, label }`.
- Undocumented options in `global-types.ts`: `authenticated`, `requiresScopes`, `policy` (typed by `SchemaTypes.FederationScopes` and `FederationPolicies`), `cost`, `listSize: { assumedSize, slicingArguments, sizedFields, requireOneSlicingArgument }` (demand control, 4.4.0).
- `hasResolvableKey(type)` helper for sub-graph `explicitlyIncludeType`.
- No gateway or router. No Federation 1 support mentioned.

## Grafast plugin (`@pothos/plugin-grafast`, experimental)

- Define Grafast plans instead of resolvers. Field option `plan`. Resolvers still allowed but get no `info`.
- `interfaceRef.withPlan({ planType })`, `unionType(...).withPlan(...)`, `planForType` for polymorphic plans.
- Resolver-wrapping plugins (auth, errors, tracing) do not apply to plans.
- Needs `grafast` 1.0 and GraphQL 16. Execute with `grafast({ schema, source })`.

## Mocks plugin (`@pothos/plugin-mocks`)

- `toSchema({ mocks: { TypeName: { fieldName: resolver | { resolve, subscribe } } } })`. Replaces listed resolvers per build. Same builder can build mocked and real schemas.
- No auto-generated fake data. Mocks are hand-written resolvers.

## Prisma plugin (`@pothos/plugin-prisma`)

- Generator `prisma-pothos-types` (options `clientOutput`, `output`, `prismaUtils`) writes `PrismaTypes` and `getDatamodel()`. Options `prisma: { client, dmmf, exposeDescriptions, filterConnectionTotalCount, onUnusedQuery, skipDeferredFragments, defaultConnectionSize, maxConnectionSize }`. `dmmf` required since 4.13.0 (Prisma 7).
- `client` may be `(ctx) => client` (read replicas, per-user clients).
- `exposeDescriptions: boolean | { models, fields }`: Prisma schema comments become GraphQL descriptions.
- `onUnusedQuery: 'warn' | 'error' | fn`: detects resolvers that did not spread the `query` argument (tracks property access).
- `builder.prismaObject(model, { name | variant, include, select, findUnique, fields })`, `prismaInterface`, `prismaNode` (`id: { field | resolve }`, `findUnique`, `nullable`), `prismaObjectField(s)`, `prismaInterfaceField(s)`.
- `t.prismaField({ type, resolve(query, parent, args, ctx, info) })`: `query` has `include`/`select` for all nested relations requested. One Prisma query per root when possible.
- `t.prismaConnection({ type, cursor, defaultSize, maxSize, totalCount, resolve })`. Unsupported arg combinations (`before`+`after`, `first`+`before`, `last`+`after`) throw.
- `t.prismaFieldWithInput` (with-input plugin).
- Object field methods: `t.relation(name, { query, args, type, onNull, nullable })`, `t.relationCount(name, { where })`, `t.relatedConnection(name, { cursor, query, totalCount })`, `t.variant(ref, { isNull })`, `t.expose*`.
- `onNull: 'error' | fn` required for non-null fields on optional relations (v4).
- Type modes: `include` (default, all scalar columns) or `select` (only requested columns). Field-level `select` (static or `(args, ctx, nestedSelection) => ...`) adds columns or relations to the parent row.
- `nestedSelection(query, path, type)` for indirect relations, join tables, and interface or union returns. `PathSegment` `{ name, type }`.
- Fallback queries: batched `findUnique` by primary key or first unique index when data is missing. `findUnique: null` opts out and throws instead.
- Variants: several GraphQL types per model (`variant: 'Viewer'`). Type-level selection conflicts between variants throw.
- `queryFromInfo({ context, info, path, paths, typeName, select, awaitSelections })`: build an optimized query for fields not using `t.prismaField` (payload wrappers).
- `prismaConnectionHelpers(builder, model, { cursor, select, query, args, resolveNode, defaultSize, maxSize })` with `getQuery`, `getArgs`, `resolve`, `ref`.
- `parsePrismaCursor`, `formatPrismaCursor`. Compound cursors carry typed values (bigint, Date, Bytes, booleans) since 4.16.0.
- `skipDeferredFragments` (default `true`): `@defer` selections are left out of the initial query and loaded by fallback queries.
- `AsyncSelections: true` in `SchemaTypes` allows async selection callbacks (4.16.0).
- The Prisma and Drizzle plugins share one selection planner, `@pothos/selection-mapper` (internal, not a public API).
- Exports not on the docs site: `prismaClientCache`, `getModel`, `getRefFromModel`, `prismaModelKey`, `PrismaObjectRef`, `PrismaNodeRef`, `PrismaInterfaceRef`.

## Prisma Utils plugin (`@pothos/plugin-prisma-utils`, "highly experimental")

- Needs `prismaUtils = true` in the generator.
- Filters: `builder.prismaFilter(scalarOrEnum, { ops })` (for example `contains`, `equals`, `startsWith`, `not`, `mode`), `prismaScalarListFilter` (`has`, `hasSome`, `hasEvery`, `isEmpty`, `equals`), `prismaListFilter(where, { ops: ['every','some','none'] })`, `prismaWhere(model, { fields })` (AND/OR/NOT accept refs), `prismaWhereUnique`.
- Ordering: `prismaOrderBy(model, { fields })`, `orderByEnum` (undocumented).
- Mutation inputs: `prismaCreate`, `prismaCreateMany`, `prismaCreateRelation` (`create`, `connect`), `prismaUpdate`, `prismaUpdateRelation` (`create`, `createMany`, `set`, `disconnect`, `delete`, `connect`, `update`, `updateMany`, `deleteMany`), `prismaIntAtomicUpdate({ ops: ['increment','decrement'] })`.
- `prismaStringFilterModeEnum` (undocumented).
- No official CRUD generator. Example static and dynamic generators live in the package tests to be copied.

## Prisma-next plugin (`@pothos/plugin-prisma-next`, unreleased)

- Targets Prisma ORM 8 (formerly Prisma Next) `8.0.0-rc.9`. SQL family only (PostgreSQL, SQLite). MongoDB not supported.
- Docs are only in `packages/plugin-prisma-next/docs/` and `README.md`. Not on the docs site.
- Same API names as the Prisma plugin: `prismaObject`, `prismaInterface`, `prismaNode`, `prismaField`, `prismaFieldWithInput`, `prismaConnection`, `t.relation`, `t.relationCount`, `t.relatedConnection`, `t.variant`, `prismaConnectionHelpers`.
- New: `t.relationAggregate` (contract-derived aggregates). Resolvers return an unexecuted Collection. The plugin applies the selection and runs `.all()`.
- `prismaNext: { contract, collections }`. `collections` enables batched fallback loading and deferred fragment loading.
- Connections support nullable sort fields with explicit null placement and descending or mixed cursors.
- No equivalent of Prisma Utils (no input generation).

## Relay plugin (`@pothos/plugin-relay`)

- Options `relay: { idFieldName, idFieldOptions, clientMutationId ('omit'|'required'|'optional'), cursorType ('String'|'ID'), edgeCursorType, pageInfoCursorType, nodeQueryOptions, nodesQueryOptions, nodeTypeOptions, pageInfoTypeOptions, brandLoadedObjects, nodesOnConnection, encodeGlobalID, decodeGlobalID, relayMutationFieldOptions, ... }`. Many per-field option objects (`firstArgOptions`, `edgesFieldOptions`, `nodeFieldOptions`, ...).
- `builder.node(ref | class, { id: { resolve, parse }, loadOne | loadMany | loadWithoutCache | loadManyWithoutCache, fields })`. Adds `Node` interface and `Query.node`/`Query.nodes`. Node loads are cached per request.
- `builder.nodeRef` (4.3.0), `builder.nodeInterfaceRef()`, `builder.pageInfoRef()`. `nodeRef` and `pageInfoRef` are not documented.
- `brandLoadedObjects` (default `true`): hidden symbol on loaded nodes so `resolveType` works without `isTypeOf`.
- Global IDs: `t.globalID`, `t.globalIDList`, `t.arg.globalID({ for: [Ref] })`, `t.arg.globalIDList`, input `t.globalID`. Args decode to `{ typename, id }`. `for` rejects IDs of other types. `encodeGlobalID`, `decodeGlobalID` helpers. Custom encoding via builder options.
- `t.node({ id })`, `t.nodeList({ ids })`: fields that load nodes by global ID.
- `t.connection({ type, resolve }, connectionOptions, edgeOptions)`: creates `<Parent><Field>Connection` and `Edge` types, `before`/`after`/`first`/`last` args, `PageInfo`.
- `builder.connectionObject`, `builder.edgeObject`, `t.arg.connectionArgs()`: shared connection and edge types.
- Helpers: `resolveArrayConnection`, `resolveOffsetConnection({ args, defaultSize: 20, maxSize: 100, totalCount })`, `resolveCursorConnection({ args, toCursor }, ({ before, after, limit, inverted }) => ...)`.
- `builder.globalConnectionField(s)`: add fields (for example `totalCount`) to all connections. `SchemaTypes.Connection` types the extra properties connection resolvers must return. Per-connection overrides allowed.
- `builder.relayMutationField(name, inputOptions, fieldOptions, payloadOptions)`: creates `<Name>Input`, `<Name>Payload`, and the field. `inputOptions: null` removes the input arg.
- `nodeQueryOptions.resolve(root, args, ctx, info, resolveNode)` for custom `node`/`nodes` resolution.
- Edge and node nullability: `DefaultEdgesNullability`, `DefaultNodeNullability` in `SchemaTypes`, or per connection `edgesNullable`, `nodeNullable`.
- `nodesOnConnection: true` adds a `nodes` shortcut field.
- Docs warn that `node`/`nodes` bypass root-field filters and permission checks.

## Scope Auth plugin (`@pothos/plugin-scope-auth`)

- `SchemaTypes.AuthScopes` declares scope names and parameter types. `scopeAuth.authScopes(ctx)` (sync or async) returns booleans or scope loader functions `(param) => MaybePromise<boolean>`.
- Field option `authScopes: ScopeMap | (parent, args, ctx, info) => ScopeMap | boolean`. Checks run before the resolver.
- Type option `authScopes` applies to all fields of the type. `skipTypeScopes`, `skipInterfaceScopes` opt out per field or object.
- `$any`, `$all` combinators, nestable. `defaultStrategy: 'any' | 'all'` with `SchemaTypes.DefaultAuthStrategy`.
- `$granted` scopes: `grantScopes` on a field (for the returned object path) or on a type (per instance). Not inherited by children.
- `runScopesOnType: true`: run type scopes in `isTypeOf` during object completion (covers `__typename`-only selections). Not compatible with `graphql-jit`.
- `unauthorizedError(parent, ctx, info, result)` globally or per field. String becomes `ForbiddenError`. `result.failure` has an `AuthFailure` tree with `AuthScopeFailureType`.
- `unauthorizedResolver`: return a fallback value (for example `[]`) instead of an error.
- `treatErrorsAsUnauthorized`: errors thrown in scope checks count as denial.
- `authorizeOnSubscribe: true`: check when the subscription is created, not per event.
- `SchemaTypes.AuthContexts` + `t.authField({ authScopes })` or `t.withAuth(scopes).<anyMethod>()`: narrow the context type after a scope passes. `withAuth` works with other plugins' field methods (for example `prismaField`).
- `cacheKey(value)`: custom cache key for object scope parameters. Scope loaders and type scope functions are cached per request.
- `toSchema({ disableScopeAuth: true })` for tests.
- Undocumented: `builder.runAuthScopes(ctx, scopes, unauthorizedError?)` for manual checks, `RequestCache.clearForContext(ctx)` to reset the auth cache mid-request (3.22.0).
- Not supported: scopes based on the field's return value (docs say to move checks to the returned type).
- Relay node guide: gate `node`/`nodes` with `nodeQueryOptions.authScopes`, put a policy on the `Node` interface, or disable the lookup fields.
- `@pothos/plugin-authz` (graphql-authz) was removed in v4.

## Simple Objects plugin (`@pothos/plugin-simple-objects`)

- `builder.simpleObject(name, { fields, interfaces }, extraFields?)`, `builder.simpleInterface`. The backing shape is inferred from the fields. No resolvers needed for passthrough data.
- Limitation: other plugins may see `unknown` as the parent type.

## Smart Subscriptions plugin (`@pothos/plugin-smart-subscriptions`)

- Turns query fields into live subscriptions that re-run when events fire. Field option `smartSubscription: true` on a query field exposes it on `Subscription`.
- Builder options `smartSubscriptions: { subscribe(name, ctx, cb), unsubscribe(name, ctx), debounceDelay }`. `subscribeOptionsFromIterator((name, ctx) => asyncIterator)` adapter.
- Field and type option `subscribe: (subscriptions, parent, args, ctx, info) => subscriptions.register(name, { refetch, filter, invalidateCache })`. Field `canRefetch: true` re-runs only that field.
- Events registered during execution are tracked. Stale registrations are removed after each re-execution.
- Not supported: async generator list fields for `@stream`.
- Exports internals: `SubscriptionManager`, `FieldSubscriptionManager`, `TypeSubscriptionManager`, `SubscriptionCache`, `CacheNode`.

## Sub-Graph plugin (`@pothos/plugin-sub-graph`)

- Build several filtered schemas (for example public and internal) from one builder. Not federation.
- `SchemaTypes.SubGraphs` names. Options `subGraphs: { defaultForTypes, defaultForFields, fieldsInheritFromTypes, explicitlyIncludeType }`. Type option `subGraphs`, `defaultSubGraphsForFields`. Field, nullable arg and nullable input field option `subGraphs`.
- `toSchema({ subGraph: 'Public' })`, `subGraph: ['A', 'B']` (union), `subGraph: { all: ['A', 'B'] }` (intersection, 4.4.0).
- Fields whose return type is excluded are dropped. Required args and input fields cannot be removed (build error). Unreachable types are pruned.

## Tracing plugin (`@pothos/plugin-tracing`) and tracers

- Options `tracing: { default: (config) => boolean | options, wrap: (resolver, options, fieldConfig) => resolver }`. Field option `tracing: boolean | options | (parent, args, ctx, info) => options`. `SchemaTypes.Tracing` types custom options.
- Predicates: `isRootField`, `isScalarField`, `isEnumField`, `isExposedField`. Utils: `runFunction(fn, onEnd(error, durationMs))`, `wrapResolver`, `pathToString(info)`, `getParentSpan`, `createSpanWithParent`.
- `@pothos/tracing-opentelemetry`: `createOpenTelemetryWrapper(tracer, { includeArgs, includeSource, ignoreError, onSpan })`, `SpanNames`, `AttributeNames`.
- `@pothos/tracing-sentry`: `createSentryWrapper({ includeArgs, includeSource, ignoreError, onSpan })`.
- `@pothos/tracing-newrelic`: `createNewrelicWrapper({ includeArgs, includeSource })`.
- `@pothos/tracing-xray`: `createXRayWrapper({ includeArgs, includeSource, onSegment })`.
- Resolver spans only. Operation, parse and validate spans need server plugins (Yoga or Envelop recipes in docs). Datadog through OTLP exporter.

## Validation plugin (`@pothos/plugin-validation`)

- Uses Standard Schema, so Zod, Valibot, ArkType and others work. Async validation supported.
- Arg: `t.arg.string({ validate: schema })` or `t.arg.string().validate(schema)`. Chained `.validate()` calls run in order and can transform (resolver type follows the output).
- Field: `validate: schema` on the field (all args together) or `args: t.validate(args, schema)` (transforming, typed).
- Input type: `inputType(name, { validate })` or `.validate(schema)` on the ref. Input field: `t.string({ validate })` or `.validate()`.
- Order: input fields, input type, args, field. Separate fields validate in parallel and issues merge.
- Failure throws `InputValidationError` with Standard Schema `issues`. `validation: { validationError(result, args, ctx) }` customizes it.
- Runs as an arg mapper before the resolver, so writes in mutation resolvers never see invalid input.
- Unreleased changeset: chained validators will also run on `null` and omitted values.

## Zod plugin (`@pothos/plugin-zod`, legacy)

- Was `@pothos/plugin-validation` in v3. Docs recommend the new validation plugin.
- `validate` on args, fields, input types and input fields. Constraint object keys map to zod: numbers `min`, `max`, `int`, `positive`, `nonnegative`, `negative`, `nonpositive`. Strings `minLength`, `maxLength`, `length`, `email`, `url`, `uuid`, `regex`. Arrays `minLength`, `maxLength`, `length`, `items`. Base keys `type`, `refine`, `schema`.
- `[value, { message }]` pairs for messages. `createZodSchema(options)` and `ValidationOptions` type for sharing with clients.
- Does not infer transformed arg types.

## With-Input plugin (`@pothos/plugin-with-input`)

- `t.fieldWithInput({ input: { id: t.input.id(...) }, typeOptions, argOptions, ... })`. Creates `<Parent><Field>Input` and a required `input` arg.
- Builder options `withInput: { typeOptions: { name({ parentTypeName, fieldName }) }, argOptions: { required } }`. `SchemaTypes.WithInputArgRequired`.
- Integrations: `t.prismaFieldWithInput`, `t.drizzleFieldWithInput`.

## Test utils (`@pothos/test-utils`)

- `createTestServer(options)` (Yoga-based) and `execute(args)` that collapses GraphQL 17 incremental results into one result. Internal to the repo tests. Not documented.

## Documentation extras

- Browser playground (`/playground?example=...`) runs schemas and queries locally, with Share links and a "Trust and build schema" step. No subscriptions or HTTP.
- Local examples under `website/local-examples/` for federation, grafast, smart-subscriptions, prisma (SQLite publishing API). Run with `pnpm --dir website check:local`.
- Guides without APIs: app layout, circular references, sharing fields and args through helpers, generating client types with graphql-code-generator, printing SDL with `printSchema`, troubleshooting.
- Community tools listed: Prisma generator codegen, Nexus-to-Pothos codemod, protoc-gen-pothos, NestJS integration, rumble (Drizzle + abilities).

## Not supported or not in scope

- No server, HTTP handling, GraphiQL, WebSocket or SSE transport. Use Yoga, Apollo Server, or another server.
- No persisted queries, APQ, response caching, rate limiting or CSRF handling.
- No built-in filtering or ordering DSL except Prisma Utils (experimental, Prisma only). No generic filter or ordering for Drizzle or plain objects.
- No automatic CRUD mutation generation. Prisma Utils only builds input types. Example generators must be copied.
- No SDL-first mode. SDL can be imported through `add-graphql` or converted once with `@pothos/converter`.
- No default resolvers by property name. Every field is declared explicitly.
- No depth or complexity limits in core. They come from the complexity plugin.
- No schema visibility per request. `sub-graph` builds separate static schemas.
- No `@defer`/`@stream` implementation. Pothos only plans queries around `@defer` (`skipDeferredFragments`). The executor and transport must provide incremental delivery.
- No query result caching or cache hints (`@cacheControl`).
- No file upload scalar or multipart handling.
- No mock data generation.
- No runtime schema validation of resolver return values. Types are compile-time only.
- Authorization based on a field's return value is not supported by scope-auth.
- Prisma connections do not support `before`+`after`, `first`+`before`, `last`+`after`.
- Grafast plans do not run resolver-wrapping plugins.
- Smart subscriptions do not support `@stream` async generator lists.
- No federation gateway. Subgraph only.

## Upcoming and unreleased work

- `@pothos/plugin-prisma-next` 0.1.1 for Prisma ORM 8 RC. Private, not published. Adds `t.relationAggregate`.
- `@pothos/plugin-drizzle` stays 0.x until Drizzle 1.0 is final.
- Pending changesets on `main`: scope-auth cache isolated per builder when schemas share a context, scope-auth pending loader rejection handling, directives keep GraphQL 17 defaults in AST, drizzle binary primary key matching, federation builder garbage collection, federation `provides` through `ListRef`, add-graphql root roles when importing schema and types together, prisma-next binary node IDs, validation chained validators run on nullish values.
- Branches include `fix/audit-20260913-*` fixes and feature branches such as `feat/website-theme-editor`, `issue-1125--override-default-directives`, `make-prisma-types-from-client-able-to-infer-composites`. I did not check branch contents.

## Docs and code disagree

- Smart subscriptions `debounceDelay` is typed `number | null`. The code ignores the number and uses a fixed 10 ms (`DEFAULT_DEBOUNCE_DELAY`). `null` disables debounce. The docs state this, so this is a code limitation, not a doc error.
- Federation docs list only `@shareable`, `@tag`, `@inaccessible`, `@override` as field options. The code also supports `authenticated`, `requiresScopes`, `policy`, `cost` and `listSize` on types, fields, enum values and input fields.
- API reference `QueryTypeOptions`/`MutationTypeOptions`/`SubscriptionTypeOptions` omit `name`. The code accepts `name` (custom root names).
- Plugin index page does not list Prisma Utils, Prisma-next, the converter, or test-utils. Prisma Utils has its own page under Prisma.
- Relay docs options list does not mention `edgeCursorType` and `pageInfoCursorType`. They only appear in the v4 migration guide.
- Dataloader docs mention `sort` "also works with loadable nodes, interfaces, unions". The methods `loadableInterface`, `loadableInterfaceRef` and `loadableUnion` are not documented.
- Complexity docs do not mention the `disabled` option.

## Sources

Repo:
- https://github.com/hayes/pothos (shallow clone at `/tmp/pothos-audit`, `main` at `4c8bc28`, 2026-09-14).

Docs read (repo source of the site, `website/content/docs/`, all pages read):
- https://pothos-graphql.dev/docs: `index.mdx`, `design.mdx`, `llms.mdx`, `resources.mdx`, all of `guide/` (app-layout, args, changing-default-nullability, circular-references, context, enums, fields, generating-client-types, inferring-types, inputs, interfaces, objects, patterns, playground, printing-schemas, queries-mutations-and-subscriptions, scalars, schema-builder, troubleshooting, unions, using-plugins, writing-plugins), all of `api/` (schema-builder, field-builder, arg-builder, input-field-builder), `migrations/v4.mdx`.
- All of `plugins/`: index, add-graphql, complexity, dataloader, directives, errors, federation, grafast, mocks, relay, scope-auth (index, relay-nodes), simple-objects, smart-subscriptions, sub-graph, tracing, validation, with-input, zod, prisma (all 13 pages including prisma-utils and without-a-plugin), drizzle (all 13 pages).
- Not read in full: `migrations/v2.mdx`, `migrations/giraphql-pothos.mdx`.
- https://pothos-graphql.dev/llms.txt and https://pothos-graphql.dev/llms-full.txt return 200 `text/plain` (full text about 624 KB). Pages also served as `.mdx` text. I used the repo source.

Package docs not on the site:
- `packages/plugin-prisma-next/README.md`, `docs/*.mdx` (headings and API names), `docs/release-status.md`.
- `packages/selection-mapper/README.md`, `packages/converter/README.md`, `packages/plugin-example/README.md`.

Changelogs:
- `packages/core/CHANGELOG.md` (4.x minor entries).
- Minor entries of `CHANGELOG.md` for relay, prisma, drizzle, scope-auth, errors, federation, dataloader, complexity, validation, sub-graph, smart-subscriptions, tracing, directives, add-graphql, prisma-utils, prisma-next.
- `.changeset/*.md` (pending).

Source files checked:
- `packages/core/src/builder.ts`, `fieldUtils/*.ts`, `utils/index.ts`, `types/global/{type-options,field-options,schema-types}.ts`.
- `packages/*/src/index.ts` (exports) and `packages/plugin-*/src/global-types.ts` (added methods and options) for every plugin.
- `packages/plugin-federation/src/global-types.ts`, `schema-builder.ts`. `packages/plugin-smart-subscriptions/src/index.ts`, `manager/index.ts`. `packages/plugin-complexity/src/index.ts`, `types.ts`. `packages/plugin-scope-auth/src/request-cache.ts`. `packages/plugin-relay/src/utils/connections.ts`, `schema-builder.ts`. `packages/converter/src/cli.ts`. `packages/test-utils/src/*.ts`.

Maintenance data:
- `npm view @pothos/<pkg> dist-tags time` for core, relay, prisma, drizzle, scope-auth, grafast, validation, prisma-next (404).
- https://api.github.com/repos/hayes/pothos/releases/latest and `git ls-remote --heads/--tags`.
