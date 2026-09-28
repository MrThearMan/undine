# Nexus findings

Versions checked: `nexus` 1.3.0 (npm `latest`) and 1.4.0-next.13 (npm `next`). Repo `main` at `9e5c27c` (2023-03-16).
Nexus is a TypeScript/JavaScript code-first schema builder. Type builders (`objectType`, `queryType` and others) go into `makeSchema({ types })`, which returns a plain graphql-js `GraphQLSchema`.
It is not a server. It has no HTTP, subscriptions transport, persisted queries, caching or dataloader layer. Docs use Apollo Server, `apollo-server-micro` (Next.js) or graphql-yoga for serving.
Type safety comes from code generation ("reflection"). `makeSchema` writes a TypeScript typegen file and an SDL file when the program runs in development. The editor then type checks resolvers against the generated `NexusGen*` global types. Plain JavaScript users get the same types through `// @ts-check`.
Peer dependency `graphql` `15.x || 16.x`. Docs suggest TypeScript 4.1. The npm package has CJS and ESM builds.
Old package names: `nexus` 0.20 to 0.27 was the "Nexus Framework" (now dead). `@nexus/schema` was renamed back to `nexus` in 1.0.0.

## Maintenance status

- Effectively unmaintained. Last commit on `main`: `9e5c27c`, 2023-03-16. GitHub `pushed_at` 2023-11-19. Not archived. 254 open issues. 3431 stars.
- npm `latest`: `nexus` 1.3.0 (2022-03-05). npm `next`: 1.4.0-next.13 (2023-03-16). No stable release since March 2022.
- Latest GitHub release: `v1.3.0`, 2022-03-07. A draft-like `next` release lists the unreleased 1.4 work.
- Branches: `main`, `janpio-patch-1`, `janpio-patch-2`, `tgriesser/feat/graphql-16-tests`. No active feature branches.
- Newest issues are user questions (2024-05, 2024-10, 2025-02). No maintainer activity seen.
- `CHANGELOG.md` stops at 0.18.0. Release notes for 0.19 to 1.3 are only on GitHub releases.
- `nexus-prisma` (official Prisma plugin, separate repo): npm `latest` 2.0.8 (2024-12-09). Last real commit 2024-12-09 (dependency bumps). Repo `pushed_at` 2026-09-25 is from bot branches, I think. Peer deps `nexus` `1.2.0 || ^1.3.0`, `@prisma/client` `^5.0.0` (no Prisma 6 or 7 support). Docs still call it "early access".
- `nexus-plugin-prisma` (older Prisma plugin): deprecated. Repo description "Deprecated". Last npm release 0.35.0 (2021-05-21). README points to `nexus-prisma`.

## Core type builders

- `objectType({ name, definition(t), description, sourceType, isTypeOf, nonNullDefaults, extensions, directives, asNexusMethod })`.
- `queryType`, `mutationType`, `subscriptionType`: shorthands for root object types named `Query`, `Mutation`, `Subscription`.
- `queryField(name, config)`, `mutationField(name, config)`, `subscriptionField(name, config)`: add one root field from anywhere. Also accept `(t) => {...}` to get the definition block (for example for `t.connectionField`).
- `extendType({ type, definition(t) })`: add fields to an existing object type from many modules. Can call `t.implements` (1.1.0).
- `extendInputType({ type, definition(t) })`: same for input objects.
- `interfaceType({ name, definition(t), resolveType, sourceType, nonNullDefaults, extensions, directives, asNexusMethod })`. Interfaces can implement interfaces (0.17.0).
- `t.implements(...interfaces)`: copies all interface fields into the object. No need to redeclare interface fields.
- `t.modify(fieldName, { type, description, resolve, args, extensions })`: change an inherited interface field on the implementer (0.19.0). Only non-required args can be added. The API docs mention `modify` in one sentence.
- `unionType({ name, definition(t) { t.members(...) }, resolveType, sourceType, extensions, directives })`.
- `enumType({ name, members, description, sourceType, extensions, directives, asNexusMethod })`. `members` accepts a string array, an object map of name to internal value, a TypeScript enum, or `{ name, value, description, deprecation, extensions, directives }` objects. `ReadonlyArray` accepted (1.1.0).
- `inputObjectType({ name, definition(t), description, nonNullDefaults, extensions, directives, asNexusMethod })`.
- `enumType(...).asArg({ default })` and `inputObjectType(...).asArg({ default })`: use the type directly as an argument (1.0.0).
- `scalarType({ name, serialize, parseValue, parseLiteral, asNexusMethod, sourceType, description, extensions, directives })`. `specifiedByURL` passes through to graphql-js and is printed as `@specifiedBy` in SDL (1.4 printer).
- `asNexusMethod(GraphQLScalarType, 'date', sourceType?)`: expose an existing scalar (for example from `graphql-scalars`) as `t.date('field')` on definition blocks, with typegen.
- `asNexusMethod` also works on object, interface, union, enum and input object types. It adds `t.<method>()` for that type. The docs only show it for scalars.
- `decorateType(graphqlJsType, { asNexusMethod, sourceType })`: attach Nexus metadata to a plain graphql-js type.
- Plain graphql-js types (`GraphQLObjectType`, `GraphQLScalarType` and others) can be passed in `types` and mixed with Nexus types. Nexus rebuilds them internally (`core.rebuildNamedType` and friends).
- Built-in scalar overrides: passing your own `ID` or other built-in scalar replaces the default (1.1.0).
- Types are referenced by string name (with autocomplete from typegen) or by the type object. Names that are never defined produce a `NEXUS__UNKNOWN__TYPE` placeholder scalar, then `makeSchema` throws with "did you mean" suggestions. The placeholder lets typegen still run.
- `makeSchema({ types })` walks arrays and objects recursively, so `import * as types` works. Non-GraphQL values are ignored.
- `NEXUS_TYPE` and `NEXUS_BUILD` symbols (1.1.0): any object or class with `[NEXUS_TYPE]` (type or thunk) can be used as a field `type`. `[NEXUS_BUILD]` returns types to add. For metaprogramming. Not in the docs.
- `groupTypes(schema)`: group a schema's named types by kind. Not in the docs.
- `blocks` namespace exports `ObjectDefinitionBlock`, `InterfaceDefinitionBlock`, `InputDefinitionBlock`, `OutputDefinitionBlock`, `UnionDefinitionBlock`.
- `core` namespace exports almost all internals (builder, typegen printer, wrapping helpers, `completeValue`). Docs say these "may be subject to minor change".

## Field API (`t`)

- Scalar helpers: `t.string`, `t.int`, `t.float`, `t.boolean`, `t.id`. Custom scalar helpers from `asNexusMethod`.
- `t.field(name, { type, args, resolve, description, deprecation, extensions, directives, sourceType, ...pluginOptions })`.
- `t.field({ name, type, ... })`: overload with the name inside the config (1.1.0). Made for `nexus-prisma` (`t.field(User.id)`).
- No `resolve` means the graphql-js default resolver (property of the same name on the source).
- Resolver shorthand `t.string('foo', () => ...)` was removed in 0.18.0.
- Chaining wrappers: `t.list.field`, `t.nonNull.string`, `t.nullable.int`, `t.nonNull.list.nonNull.id` and so on (0.19.0).
- Type wrapper functions: `list(type)`, `nonNull(type)`, `nullable(type)`. Work for field types and args.
- Args: `arg({ type, default, description, extensions, directives })`, `stringArg`, `intArg`, `floatArg`, `booleanArg`, `idArg`. Args can be wrapped with `list`, `nonNull`, `nullable`. Arg type can also be a type name string (`message: 'String'`).
- Input fields: `t.string('x', { default, description, extensions, directives })` and the same chaining on input definition blocks.
- `deprecation: string` on output fields and enum values becomes `deprecationReason`. On args, input fields, scalars and unions the option is accepted by the types but ignored by the builder (see "Docs and code disagree").
- `DeprecationInfo { reason, startDate, supersededBy }` type exists but is not used (commented out in configs).
- Subscriptions: field config `subscribe(root, args, ctx, info)` returns an `AsyncIterator`. `resolve(eventData)` maps each event.
- `sourceType` on a field (1.4.0-next only): set the TypeScript type used for this field in the parent's generated source type. Accepts a string, `{ type, optional }` or `[{ name, type, optional }]`.
- `nonNullDefaults: { input, output }` on `makeSchema`, on a type, or on `connectionPlugin`. Default is `{ input: false, output: false }` (everything nullable). Changed in 0.16.0. List items follow the same default.
- Args with `default` are still typed as nullable inside the resolver, because clients can pass explicit `null` (issue #485).

## Abstract types (unions and interfaces)

- Three strategies, set globally with `makeSchema({ features: { abstractTypeStrategies: { resolveType, isTypeOf, __typename } } })`:
  - Centralized: `resolveType` on the union or interface. Default on.
  - Modular: `isTypeOf` on each member object.
  - Discriminant Model Field (DMF): resolvers of abstract-typed fields return `__typename` in the data.
- Setting `abstractTypeStrategies` turns off all strategies that are not listed (the `resolveType: true` default is not inherited).
- Typegen makes the needed strategy methods required or optional per type, based on what is enabled and implemented.
- `features.abstractTypeRuntimeChecks` (default on): at schema build, checks every abstract type has a valid strategy. Warns in development, throws in production (`NODE_ENV` `production` or `prod`). Turned off when DMF is on.
- Runtime precedence when many are on: `resolveType`, then `__typename`, then `isTypeOf`.
- Per-type strategy settings are not supported (issue #623).

## makeSchema options

- `types` (required), `plugins` (array, order matters for resolver middleware).
- `outputs: { schema, typegen }` or `outputs: false`. `schema` is a path or boolean. Default SDL path is `schema.graphql` in the CWD. SDL generation is on by default in development (0.19.0).
- `outputs.typegen` can be a path or `ConfiguredTypegen { outputPath, globalsPath, globalsHeaders, declareInputs, useReadonlyArrayForInputs }`. Default path is `node_modules/@types/nexus-typegen/index.d.ts`. `globalsPath` splits the global `NexusGen` declarations for monorepos with many schemas. `declareInputs` emits named interfaces for inputs and args. These options are not in the docs.
- `shouldGenerateArtifacts` (default `NODE_ENV !== 'production'`), `shouldExitAfterGenerateArtifacts` (generate then `process.exit`, for CI build steps).
- `sourceTypes: { modules: [{ module, alias, typeMatch, onlyTypes, glob }], mapping, headers, skipTypes, debug }`. Nexus scans TypeScript source text with regexes to find types named like GraphQL types. `mapping` maps type names to TS types by hand (also for scalars). `skipTypes` defaults to `Query`, `Mutation`, `Subscription`. `debug: true` logs matched and missed types. Missing source types give no error.
- Local `sourceType: 'string' | { module, export, alias }` on a type overrides the global setting.
- `contextType: { module, export, alias }`: TypeScript type of the resolver `ctx`.
- `prettierConfig` (path or object) and `formatTypegen(content, type)`: format generated files. Both run if given (1.4).
- `customPrintSchemaFn(schema)`: replace the SDL printer.
- `features: { abstractTypeStrategies, abstractTypeRuntimeChecks }`.
- `schemaRoots: { query, mutation, subscription }`: use other types as roots. Not in the docs.
- `mergeSchema: { schema, mergeTypes, skipTypes, skipFields }` (1.3.0): merge an external graphql-js schema (for example a remote schema) into the Nexus schema. `mergeTypes` defaults to `Query` and `Mutation`. Not in the docs site.
- 1.4.0-next only: `directives`, `schemaDirectives`, `extensions` and any other `GraphQLSchemaConfig` key pass through to `new GraphQLSchema` (the JSDoc example shows `enableDeferStream`).
- `core.generateSchema(config)`: async version that awaits typegen. `core.generateSchema.withArtifacts(config, typegen?)` returns `{ schema, schemaTypes, tsTypes, globalTypes }` without writing files. Meant for tests. Not in the docs.
- `extensions.nexus` on the built schema and on every type holds the Nexus config. Tools can read it.

## Generated artifacts (typegen)

- SDL file: printed by `printSchemaWithDirectives` in 1.4 (includes directive uses and `@specifiedBy`). `printSchema` from graphql-js in 1.3.
- Typegen file: `NexusGenInputs`, `NexusGenEnums`, `NexusGenScalars`, `NexusGenObjects`, `NexusGenInterfaces`, `NexusGenUnions`, `NexusGenRootTypes`, `NexusGenAllTypes`, `NexusGenFieldTypes`, `NexusGenFieldTypeNames`, `NexusGenArgTypes`, `NexusGenAbstractTypeMembers`, `NexusGenTypeInterfaces`, `NexusGenDirectives`/`NexusGenDirectiveArgs` (1.4), `NexusGenFeaturesConfig`, `NexusGenTypes`, and global `interface NexusGen extends NexusGenTypes`.
- Plugins add typed config keys through `NexusGenPluginTypeConfig`, `NexusGenPluginFieldConfig`, `NexusGenPluginInputFieldConfig`, `NexusGenPluginArgConfig`, `NexusGenPluginSchemaConfig`, `NexusGenPluginInputTypeConfig`.
- Resolver return types are `MaybePromiseDeep<T>` (promises allowed at every level).
- The workflow needs the program to run to update types. Docs suggest `ts-node-dev --transpile-only` plus a separate `tsc --noEmit --watch`.
- `nexusSchemaImportId` option for libraries that wrap Nexus.

## SDL converter

- `convertSDL(sdl, commonjs?, json?)` and class `SDLConverter`: turn an SDL string into Nexus code. Supports list/nonNull chaining and interfaces implementing interfaces.
- Web UI at https://nexusjs.org/converter. Recommended for migrating away from `nexus-plugin-prisma`.

## Directives (1.4.0-next only, unreleased as stable)

- `directive({ name, locations, args, description, isRepeatable, extensions })` defines a directive. It is callable to create a use: `MyDirective({ arg })`.
- `addDirective('Name', args)`: typed use by name (typed from `NexusGenDirectiveArgs`).
- `directives: [...]` option on object, interface, union, enum, enum value, scalar, input object, field, arg and input field configs. `schemaDirectives` on `makeSchema`.
- Nexus checks that a directive is valid for the location and that non-repeatable directives are not repeated.
- Directive uses are written into `astNode` and printed into the SDL. They have no runtime behavior. `RequestDirectiveLocation` and `SchemaDirectiveLocation` constants exported.
- Not documented on the docs site.

## Plugin system

- `plugin({ name, description, ...hooks })` (alias `createPlugin`). Class `NexusPlugin`.
- Typegen hooks (strings or `printedGenTyping(...)`/`printedGenTypingImport(...)`): `fieldDefTypes`, `inputFieldDefTypes`, `objectTypeDefTypes`, `inputObjectTypeDefTypes`, `argTypeDefTypes`. They add typed options to configs.
- Build hooks: `onInstall(builder)`, `onBeforeBuild(builder)`, `onAfterBuild(schema)`, `onObjectDefinition(t, config)`, `onInputObjectDefinition(t, config)`, `onAddOutputField(field)`, `onAddInputField(field)`, `onAddArg(arg)` (all three may return a changed config), `onMissingType(name, builder)` (generate types on demand from a name pattern).
- Runtime hooks: `onCreateFieldResolver(info)` returns middleware `(root, args, ctx, info, next) => ...`. `onCreateFieldSubscribe(info)` wraps `subscribe` the same way. Not in the docs.
- `CreateFieldResolverInfo` has `fieldConfig`, `parentTypeConfig`, `schemaConfig`, `schemaExtension`, `builder`.
- `PluginBuilderLens`: `hasType`, `addType`, `setConfigOption`, `hasConfigOption`, `getConfigOption`.
- `plugin.completeValue(valOrPromise, onSuccess, onError)`: sync-or-async helper for middleware. `composeMiddlewareFns`.
- Custom DSL: `dynamicOutputMethod({ name, typeDefinition, factory })`, `dynamicInputMethod(...)`, `dynamicOutputProperty({ name, factory })` add `t.<name>` methods or properties (used by `nexus-plugin-prisma` for `t.model` and `t.crud`). Only mentioned in passing.
- Order: middleware runs first to last in the `plugins` array.
- Docs mark the plugin "Builder Object" section as work in progress.

## Built-in plugins (in the `nexus` package)

### `connectionPlugin` (Relay connections)

- `connectionPlugin(config)` adds `t.connectionField(name, config)`. Many instances can coexist with `typePrefix` and `nexusFieldName` (for example `t.analyticsConnection`).
- Two modes: `nodes(root, args, ctx, info)` returns an array (fetch one extra item) and the plugin builds edges, cursors and `pageInfo`. Or `resolve(...)` returns a full connection object (for example from `graphql-relay` `connectionFromArray`).
- Default cursor is offset based: `cursor:${index}` then base64. Custom `cursorFromNode(node, args, ctx, info, { index, nodes })`, `encodeCursor`, `decodeCursor`, `pageInfoFromNodes`. `connectionPlugin.defaultCursorFromNode` exported.
- Backward pagination with `nodes` needs a `before` cursor or a custom `cursorFromNode`.
- Args: `first`, `after`, `last`, `before`. `disableForwardPagination`, `disableBackwardPagination`, `strictArgs` (makes the remaining `first`/`last` required), `validateArgs(args, info, root, ctx)` (default requires exactly one of `first`/`last`), `additionalArgs`, `inheritAdditionalArgs`.
- `PageInfo`: `hasNextPage`, `hasPreviousPage`, `startCursor`, `endCursor`.
- `includeNodesField: true` adds a GitHub-style `nodes` list on the connection.
- `extendConnection` and `extendEdge` globally (field map with `requireResolver`) or per field (definition block). Per-field extension creates a field-specific type, for example `QueryUsers_Connection`.
- `getConnectionName(fieldName, parentTypeName)`, `getEdgeName(...)` globally or per field. `cursorType` (custom cursor scalar), `nonNullDefaults`, `nullable`, `description`, `deprecation` per connection field.
- No `Node` interface, no global object IDs, no `node`/`nodes` root query, no `totalCount` by default. These are user work.

### `fieldAuthorizePlugin`

- Adds `authorize(root, args, ctx, info) => boolean | Error | Promise<...>` to field configs. Runs before the resolver.
- `false` gives a "Not authorized" error. A returned or thrown `Error` also blocks.
- `fieldAuthorizePlugin({ formatError({ error, root, args, ctx, info }) })` changes the error. Default wraps the original in `originalError`. `formatError` is not in the docs.
- Field level only. No type-level auth, no scopes, no field hiding from introspection.

### `queryComplexityPlugin`

- Adds `complexity: number | ({ type, field, args, childComplexity }) => number | void` to output fields.
- It only copies the value to `field.extensions.complexity`. The limit check itself is done by the external `graphql-query-complexity` library with `fieldExtensionsEstimator`, set up in the server by the user.

### `nullabilityGuardPlugin`

- Replaces `null` in non-null positions with fallback values instead of failing the query. `shouldGuard` (default `NODE_ENV === 'production'`), `onGuarded({ fallback, ctx, info, type })`, `fallbackValues` per type name (functions of `{ ctx, info, type }`).
- Algorithm: null lists become `[]`, list items are filled, abstract types return `{ __typename }` of the first possible type, objects return `{}` or a type fallback.
- Per field `skipNullGuard: true` (avoids iterating large lists). Not in the docs.
- `onAfterBuild` logs an error for each scalar without a fallback.
- The `makeSchema` docs import it as `nullabilityGuard`. The real export name is `nullabilityGuardPlugin`.

### `declarativeWrappingPlugin`

- Brings back the pre-0.19 `nullable`, `list: true | boolean[]`, `required` options on fields and args. Off by default since 1.0.0.
- `declarativeWrappingPlugin({ disable: true })` makes them a runtime error. Option `shouldWarn` is not in the docs.

## nexus-prisma (current official Prisma integration)

- A Prisma generator (`generator nexusPrisma { provider = "nexus-prisma" }`). `prisma generate` writes typed Nexus configs for every model and enum.
- `import { User, SomeEnum } from 'nexus-prisma'`. `User.$name`, `User.$description`, `User.id` (a full field config with `name`, `type`, `description`, `resolve`). Use as `objectType({ name: User.$name, definition(t) { t.field(User.id) } })`.
- It is a projection library, not a Nexus plugin. You still write every type and field by hand. It does not add `t.model` or `t.crud`.
- Enums: `enumType(SomeEnum)`.
- Scalar mapping: Prisma `Boolean`, `String`, `Int`, `Float` to the GraphQL built-ins. `String @id` to `ID`. `Int @id` to `Int` or `ID` via `projectIdIntToGraphQL` (default `Int`).
- Custom scalars `Json`, `DateTime`, `BigInt`, `Bytes`, `Decimal`. Ready implementations in `nexus-prisma/scalars` (default export `NexusPrismaScalars`, based on `graphql-scalars` and Decimal.js). `Unsupported` is not mapped.
- Relations: 1:1 and 1:n fields get a generated resolver: `ctx.prisma.<model>.findUnique({ where: <unique of parent> }).<relation>()` (Prisma fluent API). I think this relies on Prisma's own `findUnique` batching to avoid N+1. No other batching.
- Not supported (roadmap "midterm"): n:n relations, relation filtering, ordering and pagination args.
- Nullability projection is fixed: optional relations nullable, required relations non-null, lists `[T!]!`. Not configurable.
- Doc propagation: `///` comments in the Prisma schema become GraphQL descriptions and JSDoc. Newlines stripped, spaces collapsed.
- Gentime settings file `nexus-prisma.ts` (project root or Prisma dir), read with `ts-node`: `settings({ projectIdIntToGraphQL, jsdocPropagationDefault: 'none' | 'guide', docPropagation: { JSDoc, GraphQLDocs }, prismaClientImportId, output: { directory, name } })`. `output` also allowed in the generator block.
- Runtime settings (`import { $settings } from 'nexus-prisma'`, I think): `prismaClientContextField` (default `'prisma'`), `checks.PrismaClientOnContext: { enabled, strategy: 'instanceOf' | 'duckType' | 'instanceOf_duckType_fallback' }`. Docs only point to JSDoc.
- Peer-dependency check at import time. Disable with `NO_PEER_DEPENDENCY_CHECK=true` or `PEER_DEPENDENCY_CHECK=false`.
- `PleaseRunPrismaGenerate` default export when generation has not run.
- No ESM build yet (discussion #693), though settings mention ESM output.
- Mutations, inputs, filters and CRUD are not generated. Users write them with Prisma Client by hand.

## nexus-plugin-prisma (deprecated older Prisma plugin)

- `nexusPrisma({ experimentalCRUD, prismaClient: (ctx) => ..., shouldGenerateArtifacts, inputs: { prismaClient }, outputs: { typegen }, computedInputs, atomicOperations })` in `makeSchema.plugins`.
- `t.model.<field>()` projects Prisma fields onto object types. `t.model('PrismaModel')` maps a differently named GraphQL type.
- `t.crud.<op>()` (with `experimentalCRUD: true`) publishes root fields with generated resolvers: `user`, `users`, `createOneUser`, `updateOneUser`, `upsertOneUser`, `deleteOneUser`, `updateManyUser`, `deleteManyUser`.
- Field options: `alias`, `type`, `resolve(root, args, ctx, info, originalResolve)` (wrap or replace), `description`, `deprecation`, `filtering`, `ordering`, `pagination` (each `true`/`false` or a field whitelist).
- Filtering: `where: M_WhereInput` with `AND`/`OR`/`NOT`, per-scalar filters (`equals`, `not`, `in`, `notIn`, `lt`, `lte`, `gt`, `gte`, `contains`, `startsWith`, `endsWith`), relation filters `some`/`every`/`none`. Also on `updateMany`/`deleteMany`.
- Ordering: `orderBy: [M_OrderByInput!]` with `asc`/`desc` on scalar fields. No ordering by relations.
- Pagination: Prisma cursor style `first`, `last`, `after`/`before` (a `WhereUniqueInput`), `skip`. On batch reads and list relations.
- Nested writes: `create`/`connect` of related records inside create and update inputs.
- `computedInputs` local (per mutation) and global (all inputs): remove input fields from the schema and fill them from `{ args, ctx, info }` at runtime (for example `createdBy` from the viewer).
- `atomicOperations` (default on): `S_FieldUpdateOperationsInput` with `set`, `increment`, `decrement`, `multiply`, `divide` for number updates.
- List projections are always `[T!]!` ("null-free lists").
- The Nexus docs site still hosts the full API page for this plugin. It also hosts a long migration guide to plain Nexus.

## Nexus Framework (dead, 0.20 to 0.27)

- The framework bundled things the library does not have: HTTP server with CORS, GraphQL Playground, subscriptions server, global error handling, built-in logger, bundled scalars, context and backing type discovery, module auto-discovery with a singleton builder, integrated build step with bundling, integrated system testing, project scaffolding (CLI), and a settings API.
- The adoption guide explains how to replace each with other tools. None of these exist in `nexus` 1.x.

## Documentation extras

- Tutorial (chapters 0 to 6): setup, first schema, mutations, system testing with `graphql-request` and `get-port`, Prisma, testing with Prisma (separate DB per test).
- Guides: schema, nullability, source types, abstract types, library authors, best practices (auto restart, VSCode go-to-type-definition), generated artifacts.
- Adoption guides: Prisma users, Next.js (API route with `apollo-server-micro`), Nexus Framework users, Nexus Framework Prisma users.
- Examples in the repo: `apollo-fullstack`, `ghost` (source types from existing DB types via `@tgriesser/schemats`), `githunt-api`, `kitchen-sink`, `star-wars`, `ts-ast-reader`, `with-prisma`, `zeit-typescript`.
- Many API pages say "Work in progress" (union, interface, args, input, lists, descriptions, deprecations in the schema guide). Docs say to read type definitions and examples instead.
- No `/llms.txt` (404 on nexusjs.org and the nexus-prisma site). `Accept: text/markdown` returns HTML.

## Not supported or not in scope

- HTTP server, transports, subscriptions transport, GraphiQL/Playground (library only builds the schema).
- Dataloader or any batching. N+1 is the user's problem (only Prisma's own batching through `nexus-prisma`).
- ORM query optimization, projections, select-related style prefetching.
- Filtering, ordering and CRUD generation in the maintained plugin (`nexus-prisma`). Only the deprecated `nexus-plugin-prisma` had them.
- Relay `Node` interface, global object IDs, `node` query. Only connections.
- Input validation, input transforms, error-as-types or union error results.
- Auth beyond per-field `authorize`. No scopes, no type-level rules, no schema hiding per viewer.
- Query complexity or depth limits at runtime (only metadata for `graphql-query-complexity`).
- Federation, persisted queries, caching, tracing, mocks, file uploads (only via an external `Upload` scalar).
- OneOf input objects.
- Deprecation of args and input fields.
- `@defer`/`@stream` (only pass-through of graphql-js schema options in 1.4-next).
- SDL-first definition. SDL can only be converted to Nexus code once (`convertSDL`).
- Per-type abstract type strategy settings (#623).
- Schema directives in the stable release (1.3.0). Only in 1.4.0-next.
- Prisma 6 or newer in `nexus-prisma`. n:n relations in `nexus-prisma`.
- GraphQL 17.

## Upcoming and unreleased work

- 1.4.0-next.13 on npm `next` (2023-03-16), from `main`. Never released as stable.
- Contents: schema directives (`directive`, `addDirective`, `directives` on all configs, `schemaDirectives`, `printSchemaWithDirectives`), `sourceType` on field configs (#1106), pass-through of extra `GraphQLSchemaConfig` options, better ESM support (no top-level Node imports, `node.ts`), `formatTypegen` and prettier both applied, `ReadonlyArray` in typings, a fix for backward pagination logic in `connectionPlugin` (#1084).
- No other active branches. The project looks abandoned. `nexus-prisma` roadmap items (n:n, relation filtering/ordering/pagination) are still open.

## Docs and code disagree

- `makeSchema` docs list `typegenConfig` as an escape hatch. Code throws "typegenConfig was removed from the API" when it is passed.
- JSDoc for `deprecation` says it is "provided ... as a comment on input fields". The builder ignores `deprecation` on input fields and args. It only applies it to output fields and enum values.
- `scalarType` and `unionType` accept `deprecation`, but the builder does not use it.
- Source types guide example uses `sourceType: { path: __filename, name: 'UserSourceType' }`. The code type is `{ module, export, alias }`.
- `makeSchema` docs example for `contextType` uses `{ module, alias }`. The code `TypingImport` needs `export` (the name of the exported type).
- `makeSchema` docs example `typeMatch: name => new RegExp(... ${name} ...)`. The code passes a `GraphQLNamedType` and the default regex, so it must use `type.name`.
- `makeSchema` docs import `nullabilityGuard`. The export is `nullabilityGuardPlugin`.
- Nullability guide "flipped at global level" example sets `nonNullDefaults: { input: false, output: false }` but shows `String!` output. The code default is already `false`, so that config changes nothing.
- `extendType` docs call `intArg('id of the user')`. `intArg` takes a config object, not a string description.
- `sourceTypes.skipTypes` JSDoc shows `/(.*?)Edge/` regexes. The code accepts `(string | RegExp)[]`, so that part matches.
- API docs for `subscriptionType` show `subscriptionType(typeName: string, fn)`. The code takes one config object without a separate name.
- Docs never mention `onCreateFieldSubscribe`, `onInputObjectDefinition`, `mergeSchema`, `schemaRoots`, `generateSchema.withArtifacts`, `ConfiguredTypegen` options, `NEXUS_TYPE`/`NEXUS_BUILD`, `skipNullGuard`, `formatError`, or directives.
- `nexus-prisma` feature docs table says `Int @id` maps to "`ID` | `Int` (configurable)". The gentime default is `Int`.
- `nexus-prisma` notes say it is "maintained" and "early access". The repo has only had dependency bumps since early 2024.

## Sources

Repos:
- https://github.com/graphql-nexus/nexus (shallow clone at `/tmp/nexus-audit/nexus`, `main` at `9e5c27c`, 2023-03-16).
- https://github.com/graphql-nexus/nexus-prisma (shallow clone at `/tmp/nexus-audit/nexus-prisma`, `main` at `fb88f52`, 2024-12-09).
- https://github.com/graphql-nexus/nexus-plugin-prisma (README and metadata through the GitHub API only).
- npm tarballs `nexus@1.3.0` and `nexus@1.4.0-next.13` unpacked at `/tmp/nexus-audit/v13` and `/tmp/nexus-audit/v14` to compare released and unreleased source.

Docs read (repo source of the site, `docs/content/`):
- https://nexusjs.org/docs: `index.mdx`, `010-getting-started/04-why-nexus.mdx`, all of `014-guides/` (schema, nullability, source-types, abstract-types, library-authors, best-practices, generated-artifacts), all of `015-api/` (introduction, object-type, subscription-type, union-type, scalar-type, interface-type, enum-type, input-object-type, args, list-nonNull, make-schema, extend-type, mutation-field, query-field, subscription-field, plugins), all of `030-plugins/` (connection, declarativeWrapping, field-authorize, query-complexity, nullability-guard).
- `030-plugins/050-prisma/` (overview, api, removing-the-nexus-plugin-prisma): read the overview in full, the API page by section (all options and system behaviours), the migration guide by headings and intro.
- `040-adoption-guides/`: prisma-users and the start of nexus-framework-users in full. Others by headings.
- Tutorial chapters: headings only.
- https://nexusjs.org/converter (checked it is live).

nexus-prisma docs (repo source of https://graphql-nexus.github.io/nexus-prisma, `docs/pages/`):
- `roadmap.mdx`, `docs/index.mdx`, `docs/features.mdx`, `docs/usage.mdx`, `docs/notes.mdx`, `docs/settings/gentime.md`, `docs/settings/runtime.md`, `docs/architecture.mdx` (first part), `docs/recipes.mdx` (headings).

Changelogs:
- `CHANGELOG.md` in the nexus repo (0.12 to 0.18).
- GitHub releases through `gh api repos/graphql-nexus/nexus/releases` (0.12 to 1.3.0 and the `next` notes).
- `CHANGELOG.md` in the nexus-prisma repo (2.x entries).

Source files checked:
- `src/index.ts`, `src/core.ts`, `src/builder.ts` (config types, merge, directives, deprecation handling), `src/makeSchema.ts`, `src/plugin.ts`, `src/utils.ts`, `src/typegenAutoConfig.ts`, `src/typegenUtils.ts`, `src/typegenMetadata.ts`, `src/typegenPrinter.ts` (generated type names), `src/dynamicProperty.ts`, `src/sdlConverter.ts`, `src/rebuildType.ts`, `src/printSchemaWithDirectives.ts`.
- `src/definitions/{definitionBlocks,objectType,interfaceType,unionType,enumType,scalarType,inputObjectType,args,directive,decorateType,nexusMeta,_types}.ts`.
- `src/plugins/{connectionPlugin,fieldAuthorizePlugin,queryComplexityPlugin,nullabilityGuardPlugin,declarativeWrappingPlugin}.ts`.
- nexus-prisma `src/generator/Settings/{Gentime,Runtime}/settings.ts`, `src/generator/ModuleGenerators/JS.ts`.

Maintenance data:
- `npm view nexus`, `npm view nexus-prisma`, `npm view nexus-plugin-prisma` (dist-tags, time, peerDependencies).
- `gh api repos/graphql-nexus/{nexus,nexus-prisma,nexus-plugin-prisma}` (pushed_at, archived, releases, commits, issues) and `git ls-remote --heads`.
- https://nexusjs.org/llms.txt and https://graphql-nexus.github.io/nexus-prisma/llms.txt return 404.
