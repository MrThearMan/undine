# TypeGraphQL findings

Versions checked: `type-graphql` 2.0.0-rc.3 (npm `latest`) and 2.0.0-rc.4 (npm `next`). Repo `master` at `77a79f2` (2026-07-16). Package version in repo: `2.0.0-rc.4`.
TypeGraphQL is a TypeScript code-first schema builder. Classes and decorators (`@ObjectType`, `@Field`, `@Resolver`, `@Query` and others) are collected into a global metadata storage. `buildSchema({ resolvers })` turns them into a plain graphql-js `GraphQLSchema`.
It is not a server. Docs use `@apollo/server` or `graphql-yoga` to serve the schema. No HTTP layer, no GraphiQL, no persisted queries, no caching, no dataloader.
Type info comes from TypeScript `emitDecoratorMetadata` reflection plus explicit type thunks (`@Field(type => [Rate])`). Requires `experimentalDecorators`, `emitDecoratorMetadata` and a `Reflect.metadata` polyfill (`reflect-metadata` or `core-js/features/reflect`). Other polyfills work since 2.0.0-rc.1.
Peer deps: `graphql` `^16.12.0`, `graphql-scalars` `^1.25.0`, `class-validator` `>=0.14.3` (optional). Runtime deps include `graphql-query-complexity` and `@graphql-yoga/subscription`. Node `>= 20.11.1`. CJS and ESM builds.
Official sister packages: `typegraphql-prisma` (code generator from Prisma schema) and `typegraphql-nestjs` (NestJS module). Same author.

## Maintenance status

- Maintained by one person (Michał Lytek). Slow pace. Last code commit on `master`: `fix(schema): match field resolvers by schemaName instead of methodName (#1806)`, 2026-03-10. Later commits (to 2026-07-16) are sponsor list edits only.
- GitHub `pushed_at` 2026-07-16. Not archived. 8088 stars. 120 open issues.
- npm `latest`: 2.0.0-rc.3 (2026-02-08). npm `next`: 2.0.0-rc.4 (2026-02-26). Last stable release: 1.1.1 (2020-11-04). The 2.0 line has been in beta/rc since 2023. rc.2 (2024-06-07) to rc.3 was a gap of 20 months.
- GitHub releases: `v2.0.0-rc.4` (2026-02-26), `v2.0.0-rc.3` (2026-02-08), `v2.0.0-rc.2` (2024-06-07), `v2.0.0-rc.1` (2024-04-24).
- Branches: `master`, `gh-pages`, one `copilot/fix-fieldresolver-leak-inputtype`, and dependabot branches.
- Open milestones: "2.0 release" (2 issues: #1812 sync middleware dispatch, #1810 FieldResolver metadata leak into dual-type InputType), "2.x versions" (13), "3.0.0 release" (28, described as a rewrite of internals with breaking changes), "Future release" (14).
- `typegraphql-prisma`: npm `latest` 0.28.0 (2024-08-07). Last commit 2025-08-07 (docs typo). Peer `prisma` and `@prisma/client` `^5.18.0` (no Prisma 6 or 7). README says it is no longer sponsored by Prisma, so only bug fixes and Prisma compatibility upgrades (issue #385, 2023-05-10).
- `typegraphql-nestjs`: npm `latest` 0.8.0 (2025-12-27). Peer `@nestjs/graphql` `^13.2.3`, `@nestjs/core` `^11`, `type-graphql` `^2.0.0 || >=2.0.0-rc`.

## Object types and fields

- `@ObjectType(name?, { description, implements, simpleResolvers })`. Name defaults to class name.
- `@Field(typeFunc?, { nullable, defaultValue, description, deprecationReason, name, complexity, simple })` on properties, getters and methods.
- Type thunk syntax `type => X` is used for arrays, promises, enums, unions, custom scalars and circular refs. Array depth by nesting (`[[Int]]`). Internal `array` and `arrayDepth` type options exist but are not in the docs.
- Nullability: non-null by default. `nullable: true`, `nullable: "items"` (`[Item]!`), `nullable: "itemsAndList"` (`[Item]`). Applies to the whole depth of nested lists. Global `nullableByDefault: true` build option.
- Fields without `@Field` are hidden from the schema (plain class properties).
- Field renaming: `@Field({ name: "externalName" })` works for output types only. Disabled for input types since 2.0.0-beta.2. Not supported on `@ArgsType` fields (#263, open).
- Type renaming: `@ObjectType("ExternalName")`, same for `@InputType`, `@InterfaceType`.
- Inline field resolvers: getters (`get name()`) and methods with `@Arg` params on the type class itself. The root value is converted to a class instance (`new Target()` then copy props) before the method runs.
- Defining constructors on type, input or args classes is "strictly forbidden". The library creates instances itself.
- One class can carry both `@ObjectType()` and `@InputType("PersonInput")` to share simple fields (FAQ).
- `ResolverInterface<T>`: type helper that checks field resolver method signatures against the object type class.
- `SymbolKeysNotSupportedError` when a decorator is put on a symbol key.
- Decorators can be applied manually as functions at runtime (`Field(() => String)(Cls.prototype, "dynamicField")`). Covered by `tests/functional/manual-decorators.ts`. Not in the docs.

## Resolvers

- `@Resolver()` or `@Resolver(of => Type)` on a class. Class acts like a controller. Instances come from the IoC container (default: one singleton per class).
- `@Query(returnTypeFunc?, { nullable, defaultValue, description, deprecationReason, name, complexity })`.
- `@Mutation(...)` with the same options.
- `@Subscription(...)` with extra subscription options (see Subscriptions).
- `@FieldResolver(returnTypeFunc?, options)` on a resolver class method resolves a field of the `of` type. If the field does not exist on the type, it is created (computed field).
- Field resolver complexity on `@FieldResolver` wins over the one on `@Field`.
- Return type can be omitted when the method is sync and the TS return type is a class.
- Parameter decorators: `@Arg(name, typeFunc?, { nullable, defaultValue, description, deprecationReason, validate, validateFn })`, `@Args(typeFunc?, { validate, validateFn })`, `@Ctx(propertyName?)`, `@Root(propertyName?)`, `@Info()`.
- `@Root("prop")` returns `root[prop]`. `@Ctx("user")` returns `context.user`. The `@Root` property form and `@Info()` are not in the docs.
- `@Root()` converts a plain root object into the reflected class instance (`convertToType`).
- `@ArgsType()` classes are flattened into separate field arguments. `@InputType()` produces a real input object.
- Default values: `defaultValue` option or a property initializer (`take = 25`). Both show in the schema. `disableInferringDefaultValues: true` build option turns off initializer inference. This option is not in the docs.
- `ConflictingDefaultValuesError` when `defaultValue` and initializer differ.
- Args and input values are converted to class instances, so getters and helper methods on args/input classes work (`get startIndex()`).
- Deprecation of args and input fields with `deprecationReason` (2.0.0-beta.2). Docs only mention it in the changelog.
- Resolver class inheritance: abstract base resolver from a factory function (`createBaseResolver(suffix, objectTypeCls)`), operation names set with `name` option. Overriding a parent operation needs the same schema name.
- Since rc.4 unreleased fix (#1806), inherited field resolvers are matched by schema name, not method name.

## Inputs

- `@InputType(name?, { description })`.
- Input classes can `implements Partial<Model>` for type checks (docs pattern).
- No `@oneOf` input support. I did not find any code for it.
- Field-level `@Authorized` on input fields is not supported (#1723, 3.0 milestone).

## Interfaces

- `@InterfaceType(name?, { description, implements, resolveType, autoRegisterImplementations })` on an abstract class.
- `@ObjectType({ implements: [IPerson, ...] })`. Fields are copied from the interface. The implementer may omit field decorators.
- Interfaces implementing interfaces (`@InterfaceType({ implements: Node })`). Only the closest interface in the chain needs to be listed (2.0.0-beta.2).
- Interface field resolvers: methods on the interface class (inherited by implementers), or `@Resolver(of => IPerson)` with `@FieldResolver`.
- Interface fields with args via `@Arg`. Abstract methods cannot have decorators, so a throwing body is used.
- Implementers can add args by redeclaring the field.
- `autoRegisterImplementations: false` stops emitting all implementers. Then list them in `orphanedTypes`. Meant for Relay `Node` with several schemas.
- Default type resolution: `instanceof` check against implementing classes. Returning plain objects needs `resolveType`, which may return a class or a type name string.
- `InterfaceResolveTypeError` and `UnionResolveTypeError` when `resolveType` returns an unknown value.

## Unions

- `createUnionType({ name, description, types: () => [A, B] as const, resolveType })`. Returns a value usable in type thunks. `typeof Union` gives the TS union type.
- Default resolution by `instanceof`. `resolveType` can return a class or a type name.
- No directives or extensions on unions.

## Enums

- `registerEnumType(Enum, { name, description, valuesConfig: { KEY: { description, deprecationReason } } })`. Needed because decorators cannot go on TS enums.
- Enum values are mapped from GraphQL names to internal TS values (`"UP"` to `0`) at runtime.
- Enum type must always be given explicitly in type thunks.
- No directives or extensions on enums or enum values (#1521 open). No case transform option (#805 open).

## Scalars

- Aliases `Int`, `Float`, `ID` (the graphql-js scalars). `String`, `Boolean`, `Number` (Float) and `Date` are reflected.
- Custom scalars: any `GraphQLScalarType` in a type thunk.
- `scalarsMap: [{ type: ObjectId, scalar: ObjectIdScalar }]` build option maps a reflected class to a scalar so no thunk is needed. Only works for classes.
- Date: `GraphQLISODateTime` (re-export of `graphql-scalars` `GraphQLDateTimeISO`, schema name `DateTimeISO`) is the default for `Date`. `GraphQLTimestamp` is the alternative via `scalarsMap`. Old `dateScalarMode` option removed in 2.0.
- No `@specifiedBy` helper. No directives on scalars.

## Generic types and composition

- Type inheritance: `@ObjectType`, `@InputType`, `@ArgsType` classes can extend parents with the same decorator kind. Fields can be overridden (#1109 fix).
- Generic types via class factory: `function PaginatedResponse<T>(TItemClass) { @ObjectType() abstract class ... }`. Abstract classes are not emitted. Non-abstract factories need unique names.
- Mixin classes example (`examples/mixin-classes`). Only an example, no API.
- No built-in Relay connection, pagination model, `Node` interface or global IDs. Pagination model is an open issue (#142, 3.0 milestone).

## Middleware

- `MiddlewareFn<TContext>` `(resolverData, next) => Promise<any>`. Koa-style `next()` returns the downstream result.
- Can run code before and after, replace the result, short-circuit (guard), or catch errors (error interceptor).
- `MiddlewareInterface<TContext>` class with `use()`. Class middleware is resolved from the IoC container per call, with `resolverData` (so scoped containers work).
- `@UseMiddleware(...middlewares)` on resolver methods, object type fields, and resolver classes (class level since rc.2). Class middlewares run before method ones.
- `globalMiddlewares` build option. Runs for every query, mutation, subscription and every field, including default property resolvers.
- `createMethodMiddlewareDecorator(fn)` and `createResolverClassMiddlewareDecorator(fn)` to build named decorators.
- `next() called multiple times` error guard.
- No scoping of global middlewares (#200 open). No access to resolver metadata in middleware other than via `info` and extensions (#123 open).

## Custom parameter decorators

- `createParameterDecorator<TContext>(resolverData => value, { arg?: { name, typeFunc, options } })`. Value is injected into the resolver param. Can be async.
- The second argument also registers a GraphQL argument for the custom decorator (rc.2).
- Docs show a `@Fields()` example that builds a select projection from `info`. Not shipped as an API (#10 open).

## Authorization

- `@Authorized()` or `@Authorized(roles)` or `@Authorized(...roles)` on object type fields, queries, mutations, field resolvers, and resolver classes (rc.2). Method-level roles override class-level ones. Generic role type (`@Authorized<number>(1, 7)`). Readonly arrays accepted.
- `authChecker` build option: function `AuthCheckerFn(resolverData, roles) => boolean | Promise<boolean>` or class `AuthCheckerInterface` with `check()` (resolved from the container).
- `authMode: "error" | "null"`. `"null"` returns `null` silently.
- Errors: `AuthenticationError` (code `UNAUTHENTICATED`, when no roles were required) and `AuthorizationError` (code `UNAUTHORIZED`, when roles were required). Both extend `GraphQLError`.
- Auth runs as the first middleware in the stack.
- Not supported: auth on input fields (#1723), inverted mode with `@Public()` (#230), schema hiding per viewer, type-level (class) auth on object types. I think `@Authorized` on an `@ObjectType` class is collected but only used for resolver classes.

## Validation

- `validate: true | ValidatorOptions` build option turns on `class-validator` for args and input classes. Default is `false` since 2.0.0-beta.2.
- Per param override: `@Arg("x", { validate: true | { groups: [...] } })`, same for `@Args`.
- Defaults forced: `skipMissingProperties: true`, `forbidUnknownValues: false`.
- Only object values (and arrays of objects) are validated by `class-validator`. Scalar args are skipped.
- `class-validator` is loaded with a dynamic import, so it is optional at runtime.
- Nested inputs need `@ValidateNested()` or `{ each: true }`.
- `ArgumentValidationError` extends `GraphQLError` with `extensions.code = "BAD_USER_INPUT"` and `extensions.validationErrors`.
- Custom validator: `validateFn(argValue, argType, resolverData)` as build option or on `@Arg`/`@Args`. Can be async. Throws to fail. Errors are not wrapped. Example with `joiful`.
- No built-in zod support (#1462 open). No input transform hooks (#340 open).

## Subscriptions

- `@Subscription(returnTypeFunc?, { topics, topicId, filter, ...AdvancedOptions })` or `@Subscription({ subscribe })`. The two forms are exclusive.
- `topics`: string, string array, or function of `{ args, context, info, root }`. Empty array throws `MissingSubscriptionTopicsError`.
- `topicId`: function returning a dynamic id. Published with `pubSub.publish("TOPIC", id, payload)`.
- `filter({ payload, args, context, info })`: boolean or promise.
- `subscribe`: custom `AsyncIterable` source (for example Prisma 1 subscriptions).
- Resolver body maps the payload (`@Root()`) to the result.
- `pubSub` build option is required when subscriptions exist (`MissingPubSubError`). Default is `createPubSub()` from `@graphql-yoga/subscription`. Any object with `publish` and `subscribe` works. Redis example uses `@graphql-yoga/redis-event-target`.
- Transport is the server's job. Docs point to Apollo Server or graphql-yoga.
- `@PubSub` decorator, `Publisher` and `PubSubEngine` types were removed in 2.0.

## Directives

- `@Directive("@sdl(args)")` on object, input and interface types, their fields, field resolvers, `@ArgsType` fields, queries, mutations, subscriptions, and inline `@Arg` params.
- Implementation: TypeGraphQL builds `astNode`s so tools that read AST directives (graphql-tools `mapSchema`, Apollo Federation) see them.
- `directives: [GraphQLDirective]` build option registers directive definitions.
- No runtime directive implementation. Users apply graphql-tools transformers after building.
- Not supported on scalars, enums, enum values or unions.
- Directives are not printed by `emitSchemaFile` (graphql-js `printSchema`). Docs suggest `printSchemaWithDirectives` from `@graphql-tools/utils`.
- `InvalidDirectiveError` for bad SDL. Multi-line and leading spaces allowed (rc.1).

## Extensions

- `@Extensions({ ... })` adds data to graphql-js `extensions`. Repeatable. Same key: bottom decorator wins.
- Applied in code to object types, interface types (rc.3), input types, object/interface fields, field resolvers, queries, mutations, subscriptions, input fields and `@ArgsType` fields.
- Not applied to inline `@Arg` args, enums or unions.
- Field `complexity` is stored as `extensions.complexity`.

## Query complexity

- `complexity: number | ComplexityEstimator` option on `@Field`, `@FieldResolver`, `@Query`, `@Mutation`, `@Subscription`.
- Analysis is done by `graphql-query-complexity` (`getComplexity` with `fieldExtensionsEstimator()` and `simpleEstimator()`) in a server plugin. TypeGraphQL only stores the metadata.
- No depth limit, no rate limiting (#338 open).

## Dependency injection

- `container` build option: any object with `get(cls, resolverData)` (TypeDI, TSyringe, InversifyJS with self-binding).
- Scoped containers: `container: ({ context }) => Container.of(context.requestId)`. User must dispose per request (Apollo `willSendResponse` plugin example).
- Resolvers, class middlewares and class auth checkers are resolved through the container.
- Default container creates one instance per class.

## Schema building and output

- `buildSchema(options)` (async) and `buildSchemaSync(options)`.
- `BuildSchemaOptions`: `resolvers` (non-empty array of classes), `orphanedTypes`, `emitSchemaFile`, `skipCheck`, `directives`, `scalarsMap`, `validate`, `validateFn`, `authChecker`, `authMode`, `pubSub`, `globalMiddlewares`, `container`, `nullableByDefault`, `disableInferringDefaultValues`.
- `skipCheck: true` skips graphql-js schema validation. Used for federation subgraphs without `Query`. Not in the docs.
- Only types reachable from resolvers are emitted, plus `orphanedTypes`.
- Several schemas from one process are possible (metadata storage is cloned per build). Global `BuildContext` is static, so I think concurrent builds with different options are not safe.
- `emitSchemaFile: true | path | { path, sortedSchema }`. Writes SDL with a "generated" header. Sorted alphabetically by default.
- `emitSchemaDefinitionFile(path, schema, options)` and `emitSchemaDefinitionFileSync`. `defaultPrintSchemaOptions` export.
- `buildTypeDefsAndResolvers(options)` and `buildTypeDefsAndResolversSync` return `{ typeDefs, resolvers }` for graphql-tools or `apollo-link-state`. Some features (complexity) do not work this way.
- `createResolversMap(schema)` builds a resolvers map from a built schema. Used by the federation helper. Not in the docs.
- `getMetadataStorage()` is exported. Gives access to all collected metadata. Not in the docs.
- `ensureInstalledCorrectGraphQLPackage()` and `UnmetGraphQLPeerDependencyError` check the installed graphql-js version.
- Resolver glob paths (`resolvers: string[]`) were removed in 2.0.0-beta.2.

## Performance

- Benchmarks folder in the repo compares with raw graphql-js.
- The library avoids async paths when there is no auth, no args validation and no promise.
- `@Field({ simple: true })` and `@ObjectType({ simpleResolvers: true })` skip auth and all middlewares for those fields. Docs claim about 13% overhead vs raw graphql-js.
- Metadata storage build uses HashMap caches (rc.3, #1779).
- Pending: sync dispatch of auth and middlewares (#1812, 2.0 milestone).

## Browser and runtime support

- `type-graphql/shim` entry point: no-op decorators for browser bundles. Webpack `NormalModuleReplacementPlugin` and tsconfig `paths` recipes (CRA, Angular, Next.js).
- ESM docs (`NodeNext`, `.js` imports).
- Recipes for AWS Lambda (cache the schema in a module variable) and Azure Functions.
- No Deno support (#1426 open). No plain JavaScript support (#55, blocked).

## Federation and caching (examples only)

- `examples/apollo-federation` and `examples/apollo-federation-2`: a `buildFederatedSchema` helper builds with `skipCheck: true`, prints with `printSchemaWithDirectives`, adds the `@link` import, and calls `@apollo/subgraph` `buildSubgraphSchema` with `createResolversMap(schema)` merged with reference resolvers. `@key`, `@shareable` and others are added with `@Directive`. Not a package API.
- `examples/apollo-cache`: a user-written `@CacheControl({ maxAge, scope })` decorator that wraps `@Directive("@cacheControl(...)")` plus `ApolloServerPluginCacheControl`.
- Other examples: TypeORM (basic and lazy relations), MikroORM, Typegoose, TSyringe, graphql-scalars, Redis subscriptions, scoped containers, query complexity, custom validation.

## typegraphql-prisma (code generator)

- Prisma generator `provider = "typegraphql-prisma"`. `prisma generate` emits TypeGraphQL classes to `@generated/type-graphql` (or `output`).
- Emits model `@ObjectType` classes, enums, input types, args classes, output types (aggregates), CRUD resolvers, and relation resolvers.
- CRUD actions mirror Prisma Client: `findUnique`, `findFirst`, `findMany`, `create`, `createMany`, `createManyAndReturn`, `update`, `updateMany`, `delete`, `deleteMany`, `upsert`, `aggregate`, `groupBy`. Prisma-style `where` filters and `orderBy` args.
- Resolver classes per model (`UserCrudResolver`, `UserRelationsResolver`) and per action (`FindManyUserResolver`, `CreateUserResolver`) so users expose only what they want. All-in-one `resolvers` export.
- Prisma Client read from context under `prisma` key. `contextPrismaKey` changes it. Helpers `getPrismaFromContext`, `transformFields`, `transformCountFieldIntoSelectRelationsCount` (uses `graphql-fields` for `_count`).
- Enhance maps to add decorators without editing generated files: `applyResolversEnhanceMap`, `applyModelsEnhanceMap`, `applyRelationResolversEnhanceMap`, `applyOutputTypesEnhanceMap`, `applyArgsTypesEnhanceMap`, `applyInputTypesEnhanceMap`. Special `_all` key.
- Prisma schema doc comments: `/// @TypeGraphQL.omit(output: true, input: true | ["update", "where", "orderBy"])`, `/// @TypeGraphQL.field(name: "...")`, `/// @@TypeGraphQL.type(name: "...", plural: "...")`, `/// @@TypeGraphQL.omit(output: true)`.
- Generator options: `output`, `emitTranspiledCode`, `formatGeneratedCode` (`tsc`, `prettier`, `false`), `emitOnly` (`enums`, `models`, `crudResolvers`, `relationResolvers`, `inputs`, `outputs`), `emitIdAsIDType`, `simpleResolvers`, `useSimpleInputs`, `useUncheckedScalarInputs`, `emitRedundantTypesInfo`, `customPrismaImportPath`, `contextPrismaKey`, `omitInputFieldsByDefault`, `omitOutputFieldsByDefault`, `emitIsAbstract`, `useOriginalMapping`, `emitDMMF`. `emitDMMF` is not in the docs.
- Generates a `Decimal` scalar for `Prisma.Decimal`.
- Strict Prisma version check. `SKIP_PRISMA_VERSION_CHECK=true` lifts it.
- Not supported: Prisma 6 or 7, `@nestjs/graphql` 7+ (only via `typegraphql-nestjs`), input unions (so `useSimpleInputs` and `useUncheckedScalarInputs` are either/or).

## typegraphql-nestjs

- `TypeGraphQLModule.forRoot(buildSchemaOptions + Nest GraphQL options)`, `forRootAsync({ useFactory, inject })`, `forFeature({ orphanedTypes, referenceResolvers })`.
- Resolvers are picked up from module `providers`. Nest DI is the container.
- Multiple schemas in one app with module isolation.
- Apollo Federation: `driver: ApolloFederationDriver`, `federationVersion`, `referenceResolvers`. Gateway via Nest `ApolloGatewayDriver`.
- Not supported: Nest guards, interceptors, filters and pipes.

## Documentation extras

- Docs are in the repo (`docs/*.md`), built with Docusaurus from `website/`. Versioned docs from 0.16.0 to 2.0.0-rc.4.
- FAQ, migration guide (v1 to v2: `DateTimeISO` name, subscriptions API change), examples list, Ben Awad video series link.
- No API reference (#17 open).
- No `/llms.txt` (404 on typegraphql.com and prisma.typegraphql.com). `Accept: text/markdown` returns HTML.

## Not supported or not in scope

- HTTP server, transports, subscriptions transport, GraphiQL.
- Dataloader or any batching (#51 open). No N+1 handling.
- ORM integration beyond examples and the Prisma generator. No query optimization or projections (only a docs example of a custom `@Fields()` decorator).
- Built-in filtering, ordering or CRUD generation (only via `typegraphql-prisma`).
- Relay connections, `Node` interface, global IDs, pagination types.
- File uploads (#37 open).
- Federation as an API (only examples and `typegraphql-nestjs`).
- Persisted queries, response caching, tracing, mocks.
- Depth limiting and rate limiting. Complexity only as metadata.
- Schema hiding per viewer or per role.
- OneOf input objects.
- `@defer`/`@stream`.
- SDL-first definition or SDL to classes converter (#251 open). CLI (#66 open).
- Directives and extensions on enums, enum values, unions and scalars.
- Input field renaming. `@ArgsType` field renaming.
- Naming strategy (for example camelCase transform) (#156 open).
- Decorator-free class registration (#294 open).
- Schema generation at build time (#1635 open). Schema is built at runtime from reflection.
- GraphQL 17.

## Upcoming and unreleased work

- Unreleased on `master`: field resolvers matched by `schemaName` instead of `methodName` for resolver inheritance (#1806).
- 2.0 milestone left: sync dispatch of auth and middlewares (#1812), FieldResolver metadata leaking into InputType for dual-type classes (#1810).
- 3.0 milestone (no code yet): new schema generation pipeline (#183), enhanced reflection (#296), typed decorators (#221), scoped middlewares (#200), dataloader integration (#51), pagination model (#142), `@Public()` inverted auth (#230), input field auth (#1723), input transforms (#340), field accessors (#760), debug logs (#368).
- 2.x milestone: directives on enum values (#1521), Deno (#1426), `__typename` support (#181), types transformation utils like Partial/Pick (#453).
- Future milestone: zod validation (#1462), build-time schema generation (#1635), file upload (#37), rate limiting (#338), new nullable mode for inputs (#1276).

## Docs and code disagree

- `validation.md` says "This feature is enabled by default" and shows `validate: false` to disable it. The code default is `validate: false` (`BuildContext.reset`). The same page also says it is disabled by default.
- `validation.md` shows the error as `extensions.code: "INTERNAL_SERVER_ERROR"` with `extensions.exception.validationErrors`. The code sets `extensions.code = "BAD_USER_INPUT"` and `extensions.validationErrors` directly.
- `authorization.md` example passes `resolvers: ["./**/*.resolver.ts"]`. Glob loading was removed in 2.0.0-beta.2. The code requires classes.
- `extensions.md` lists only `@ObjectType`, `@InputType`, `@Field`, `@Query`, `@Mutation`, `@FieldResolver`. The code also applies extensions to `@InterfaceType` (rc.3) and `@Subscription`.
- `getting-started.md` shows `recipe(id: ID!)` and `creationDate: Date!` in SDL. The code reflects `@Arg("id") id: string` as `String!` (I think) and maps `Date` to `DateTimeISO`.
- `performance.md` first table labels 1253.28 ms as "Standard TypeGraphQL". The second table shows that value is "with a global middleware" and standard is 310.36 ms.
- `performance.md` says the middleware stack "will be soon redesigned". Nothing like that is in the code or the 2.0 milestone. Only #1812 (sync dispatch) is open.
- `migration-guide.md` names the package `@graphql-yoga/subscriptions`. The real package is `@graphql-yoga/subscription`.
- `aws-lambda.md` uses `apollo-server-lambda` (Apollo Server 3, end of life). Other pages use `@apollo/server`.
- `directives.md` does not mention `skipCheck`, which the federation example needs.
- Docs never mention `@Info()`, `@Root(propertyName)`, `skipCheck`, `disableInferringDefaultValues`, `createResolversMap`, `getMetadataStorage`, `ensureInstalledCorrectGraphQLPackage`, `AuthenticationError`, `AuthorizationError`, or the `deprecationReason` option on `@Arg`.
- `typegraphql-nestjs` README says it supports "Prisma 2 integration". `typegraphql-prisma` now needs Prisma 5.

## Sources

Repos:
- https://github.com/MichalLytek/type-graphql (shallow clone at `/tmp/type-graphql-audit`, `master` at `77a79f2`, 2026-07-16).
- https://github.com/MichalLytek/typegraphql-prisma (shallow clone at `/tmp/tgp-audit`, `main` at `8f22174`, 2025-08-07).
- https://github.com/MichalLytek/typegraphql-nestjs (shallow clone at `/tmp/tgn-audit`, `master` at `c14ce91`, 2025-12-27).

Docs read (repo source of https://typegraphql.com/docs/introduction.html, `docs/`):
- All 33 pages in full: introduction, installation, getting-started, types-and-fields, resolvers, scalars, enums, unions, interfaces, subscriptions, directives, extensions, middlewares, authorization, validation, inheritance, generic-types, custom-decorators, dependency-injection, complexity, bootstrap, emit-schema, prisma, nestjs, performance, esm, browser-usage, aws-lambda, azure-functions, faq, examples, migration-guide, README.

typegraphql-prisma docs (repo source of https://prisma.typegraphql.com, `docs/`):
- `basics/configuration.md`, `basics/prisma-version.md`, `basics/nest-js.md` in full. `basics/usage.md` by sections (CRUD actions, helpers, `useOriginalMapping`). All `advanced/*` pages by intro and options.

typegraphql-nestjs:
- `README.md` (forRoot, forRootAsync, forFeature, federation, caveats).

Changelogs:
- `CHANGELOG.md` in type-graphql (Unreleased to v1.1.1).
- GitHub releases through the GitHub API.

Source files checked (type-graphql `src/`):
- `index.ts`, `decorators/*` (all decorators and `types.ts`), `utils/{buildSchema,emitSchemaDefinitionFile,graphql-version,container,createResolversMap}.ts`, `schema/{schema-generator,build-context}.ts`, `resolvers/{helpers,create,validate-arg}.ts`, `helpers/{auth-middleware,types}.ts`, `typings/*`, `errors/graphql/*`, `scalars/*`, `metadata/metadata-storage.ts` (auth class metadata).
- `tests/functional/manual-decorators.ts`, `examples/apollo-federation-2/helpers/buildFederatedSchema.ts`, `examples/apollo-cache/*`.
- typegraphql-prisma `src/cli/prisma-generator.ts`, `src/generator/generate-scalars.ts`.

Maintenance data:
- https://registry.npmjs.org/type-graphql, https://registry.npmjs.org/typegraphql-prisma, https://registry.npmjs.org/typegraphql-nestjs (dist-tags, time, peer deps).
- GitHub API: repos, releases, branches, commits, milestones and milestone issues for `MichalLytek/type-graphql`. Repos and issue #385 for `MichalLytek/typegraphql-prisma`.
- https://typegraphql.com/llms.txt and https://prisma.typegraphql.com/llms.txt return 404.
