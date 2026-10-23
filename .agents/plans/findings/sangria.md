# Sangria findings

Versions checked: `sangria 4.2.19` (latest GitHub release, 2026-07-07). Repo `main` at `d8958b1` (last commit 2026-10-07). Docs source is the separate repo `sangria-graphql/sangria-graphql.github.io` (Jekyll, `learn.md` about 3080 lines, `getting-started.md` about 510 lines). Both read in full. Core source (`modules/core`, `ast`, `parser`, `derivation`, `cats-effect-experimental`) spot-checked. Release notes read from 4.2.19 back to 3.0.0. Related repos `sangria-relay`, `sangria-slowlog`, `sangria-federated` cloned and skimmed. Other org repos checked through the GitHub API.
Sangria is a Scala GraphQL library. Apache-2.0. Cross-built for Scala 2.12, 2.13 and 3.3. Code-first through a schema DSL (`ObjectType`, `Field`, ...), with optional macro derivation and SDL-based schema materialization. Execution is `Future`-based. JSON format is pluggable through separate marshalling modules.

## Maintenance status

- Active but slow. Mostly maintained by one person (`yanns`). 1960 stars. Not archived. 70 open issues plus PRs.
- Releases are small and frequent. Many are performance work or Scala 3 fixes. 4.2.19 (2026-07-07), 4.2.18 (2026-04-13), 4.2.17 (2026-03-16), 4.2.16 (2026-03-08), 4.2.15 (2025-10-20).
- `CHANGELOG.md` stops at v3.0.0 and points to GitHub releases.
- `main` after 4.2.19 (unreleased): more cats-effect `IO` work ("resolve List[IO[_]]", IO tests), sbt 2.0 build.
- Docs website repo last changed 2024-11-07. Its `_config.yml` still says `sangria: 4.0.0`. Docs do not cover anything added since 4.0.
- https://sangria-graphql.github.io/llms.txt returns 404. `Accept: text/markdown` returns HTML.
- Scaladoc on javadoc.io is the API reference.

## Big changes in recent releases

- 3.0.0 (2022-02-14): split into `sangria-ast`, `sangria-parser`, `sangria-core`, `sangria-derivation` (the `sangria` artifact still bundles them). Faster `OverlappingFieldsCanBeMerged` is default. `DeliveryScheme` removed (parser always returns `Try`). Legacy comment-description options removed.
- 3.1.0: required arguments with default values count as optional.
- 3.2.0: repeatable directives (`Directive(repeatable = true)`).
- 3.3.0: first Scala 3 build (core and derivation). `ListType` works with any `Iterable`.
- 3.4.0: simple API to add custom directives (`astDirectives`, `withDirective`).
- 3.5.0: spec-compliant error format for errors before execution.
- 3.5.3: minimal cats-effect `IO` integration.
- 4.0.0 (2023-05-30): interfaces implementing interfaces. Experimental cats-effect module. Built-in scalars can be overridden. `sangria.execution.Resolver` made private.
- 4.0.1 / 4.0.2: `errorsLimit` (limit number of validation and variable errors). Default limit added. Deterministic enum derivation order.
- 4.1.0 (2024-02-01): `@deprecated` on arguments and input fields. Deprecation tracker covers input values. Enums on directive args in introspection.
- 4.2.0 (2024-09-05): `@oneOf` input objects.
- 4.2.4: `Long` scalar accepts string input.
- 4.2.6: schema comparator treats added required argument with default as non-breaking.
- 4.2.11: fix O(N^2) parser allocation on newlines.
- 4.2.15: `AsyncValue` (cats-effect) usable in mutations.
- 4.2.16: `deriveInputObjectType` can deprecate fields (`DeprecateInputField`, `@GraphQLDeprecated`).
- 4.2.17: derivation maps any `Iterable[T]` to `ListType[T]`.
- 4.2.19: Scala 3 fixes for path-dependent method derivation and cats-effect derivation lookups.

## Schema definition DSL (`sangria.schema`)

- `Schema(query, mutation, subscription, additionalTypes, description, directives, validationRules, astDirectives, astNodes)`.
- `ObjectType(name, description, fieldsFn, interfaces, instanceCheck, astDirectives, astNodes)`. Fields can be a thunk (`() => fields(...)`) for recursive types.
- `ObjectType.withInstanceCheck(fn)`: custom runtime check for resolving abstract types. Lightly documented.
- `InterfaceType(...)` with `interfaces` (interface implements interface, 4.0) and `manualPossibleTypes` / `withPossibleTypes`.
- `UnionType(name, description, typesFn)`. `UnionType.mapValue(fn)` creates a typed union for wrapped values like `Either`. Undocumented.
- `Field(name, fieldType, description, arguments, resolve, possibleTypes, tags, complexity, deprecationReason, astDirectives)`. `Field.subs(...)` for subscription fields.
- `Argument(name, argumentType, description, defaultValue)`. Defaults need a `ToInput` instance. `Argument.deprecationReason` (4.1).
- `InputObjectType[T](name, description, fields)`. Typed result needs a `FromInput[T]`. Default result is a `Map`.
- `InputField(name, fieldType, description, defaultValue)`. Can be deprecated (4.1).
- `EnumType[T](name, description, values)`. `EnumValue(name, description, value, deprecationReason)`.
- `OptionType` / `OptionInputType` for nullable. `ListType` / `ListInputType`. Non-null is the default (types are non-null unless wrapped in `Option*`).
- `ScalarType[T](name, description, coerceUserInput, coerceOutput, coerceInput, complexity, scalarInfo)`. Output coercion gets `MarshallerCapability` set (`DateSupport`, `CalendarSupport`, `BlobSupport`) so a scalar can emit native dates or blobs.
- `ScalarType.complexity`: per-scalar complexity cost. Undocumented.
- `ScalarAlias[T, ST](aliasFor, toScalar, fromScalar)`: domain type (value class, refined type) shown as an existing scalar in introspection, with validation.
- Extra built-in scalars: `Long`, `BigInt`, `BigDecimal`. Built-in scalars can be overridden (4.0).
- `Directive(name, description, arguments, locations, repeatable, shouldInclude)`. `shouldInclude: DirectiveContext => Boolean` lets a custom executable directive skip selections, like `@skip`. Undocumented.
- Built-in directives: `@include`, `@skip`, `@deprecated`, `@oneOf`. `BuiltinDirectives` list can be replaced in `Schema(directives = ...)`.
- `astDirectives` and `withDirective(...)` on all type system elements: attach schema directives that show in SDL and in `toAst`. Used by sangria-federated.
- `FieldTag`: free-form field metadata (`tags = Permission("x") :: Nil`). Read by middleware and query reducers. Built-in tags: `ProjectionName`, `ProjectionExclude`, `StringTag` (implicit from `String` and `Symbol`).
- `rename(newName)` on all named types, fields and directives.
- `fields[Ctx, Val](...)`, `interfaces[Ctx, Val](...)`, `possibleTypes` helpers.
- Type parameters: `Ctx` (user context for the whole execution) and `Val` (the parent value).

## Resolvers and actions

- `resolve: Context[Ctx, Val] => Action[Ctx, Res]`. Implicit conversions make plain values, `Future`, `Try` and `Deferred` into actions.
- Actions: `Value`, `TryValue`, `FutureValue`, `PartialValue` (value plus error list), `PartialFutureValue`, `DeferredValue`, `DeferredFutureValue`, `UpdateCtx`, `SequenceLeafAction` (`Action.sequence(...)`, undocumented).
- `UpdateCtx(action)(fn)`: change `Ctx` for child fields and for later sibling mutation fields. Docs use it for "login then mutate" in one request.
- `DeferredValue(...).map(fn)` and `.mapWithErrors(fn)`.
- `Context` fields: `value`, `ctx`, `args`, `schema`, `field`, `parentType`, `marshaller`, `query`, `sourceMapper`, `deprecationTracker`, `astFields`, `path`, `deferredResolverState`, `middlewareAttachments`.
- `Context` helpers: `arg`, `argOpt`, `argDefinedInQuery` (tell "not given" from "given as null"), `withArgs(a1, a2, ...)(fn)` up to 8 args, `isIntrospection`, `attachment[T]`, `attachments[T]`, `renderInputValueCompact`.
- `ValidOutType` compile-time check: resolver result type must fit the declared GraphQL output type.
- Mutation top-level fields run in order. Other fields run in parallel.
- Root value: `Executor.execute(..., root = ...)`.

## Projections (look-ahead)

- `Projector((ctx, projected) => ...)`: wrap a resolver to get the nested selected field names (`Vector[ProjectedName]` with children and `args`).
- `Projector(levels, fn)`: limit projection depth.
- `ProjectionName("_id")` field tag renames a field in the projection (DB column name). `ProjectionExclude` drops it.
- `Context.astFields` gives the raw AST of the current field for custom look-ahead with `AstVisitor`.
- No ORM integration. Projection only gives names. The user builds the DB query.

## Macro derivation (`sangria.macros.derive`, `sangria-derivation`)

- `deriveObjectType[Ctx, Val](settings*)`: case class accessors plus members with `@GraphQLField`.
- `deriveContextObjectType[Ctx, Target, Val](ctx => target, settings*)`: fields from a service object reached through `Ctx` (common for `Query`/`Mutation` roots).
- `deriveInputObjectType[T](settings*)`: case classes only.
- `deriveEnumType[T](settings*)`: Scala `Enumeration` and sealed hierarchies of case objects. Must be in the same file after all children.
- No derivation for interfaces or unions.
- Methods become fields with generated `Argument`s. A `Context[Ctx, Val]` parameter is injected, not exposed.
- Annotations: `@GraphQLName`, `@GraphQLDescription`, `@GraphQLDeprecated`, `@GraphQLFieldTags`, `@GraphQLExclude`, `@GraphQLField`, `@GraphQLDefault`, `@GraphQLInputType`, `@GraphQLOutputType`. The last two override the derived type and are undocumented.
- Object settings: `ObjectTypeName`, `ObjectTypeDescription`, `Interfaces`, `DocumentField`, `DeprecateField`, `RenameField`, `FieldTags`, `FieldComplexity`, `ExcludeFields`, `IncludeFields`, `IncludeMethods`, `AddFields`, `ReplaceField`, `TransformFieldNames`, `MethodArgument`, `MethodArgumentDefault`, `MethodArgumentDescription`, `MethodArgumentsDescription`, `MethodArgumentRename`.
- Input settings: `InputObjectTypeName`, `InputObjectTypeDescription`, `DocumentInputField`, `RenameInputField`, `DeprecateInputField` (4.2.16), `ExcludeInputFields`, `IncludeInputFields`, `ReplaceInputField`, `TransformInputFieldNames`.
- Enum settings: `EnumTypeName`, `EnumTypeDescription`, `DocumentValue`, `DeprecateValue`, `RenameValue`, `ExcludeValues`, `IncludeValues`, `UppercaseValues`, `TransformValueNames`.
- Settings win over annotations. Related types are found through implicits (`GraphQLOutputTypeLookup`, `GraphQLInputTypeLookup`).
- Recursive types need manual `ReplaceField`.

## SDL-first and schema materialization

- `Schema.buildFromAst(document, builder)`: build an executable schema from SDL. Without a builder, resolvers are stubs.
- `Schema.buildStubFromAst(document)`: schema only for validating documents (for example to validate SDL usage of custom directives).
- `Schema.buildFromIntrospection(json, builder)`: rebuild a schema from an introspection result. For proxies, mocks, tooling.
- `Schema.buildDefinitions(document)`: build type definitions only.
- `schema.extend(document, builder)`: add `extend type ...` SDL to a code-first schema (mixed code-first and SDL).
- `AstSchemaBuilder`, `DefaultAstSchemaBuilder`, `IntrospectionSchemaBuilder`, `DefaultIntrospectionSchemaBuilder`: low-level hooks for every element.
- `AstSchemaBuilder.resolverBased[Ctx](resolvers*)` / `ResolverBasedAstSchemaBuilder`: high-level builder from `AstSchemaResolver`s.
- Resolver kinds: `DirectiveResolver` (resolve plus optional complexity by directive), `DynamicDirectiveResolver`, `FieldResolver` (by type and field name), `FieldResolver.map`, `ExistingFieldResolver`, `AnyFieldResolver`, `DirectiveFieldProvider` and `DynamicDirectiveFieldProvider` (directive adds fields), `DirectiveInputTypeResolver`, `DirectiveOutputTypeResolver`, `InputTypeResolver`, `OutputTypeResolver`, `DirectiveScalarResolver`, `ScalarResolver`, `ExistingScalarResolver`, `SimpleEnumValueResolver`, `ExistingEnumResolver`, `InstanceCheck` (with `InstanceCheck.field` for a type discriminator field), `ExistingInstanceCheck`, `ConflictResolver` (merge types from several sources), `AdditionalTypes`, `AdditionalDirectives`, `GenericDirectiveResolver`, `GenericDynamicDirectiveResolver`.
- `builder.validateSchema(ast)` / `validateSchemaWithException(ast)`: check known directives and arguments before building.
- `ResolverBasedAstSchemaBuilder.resolveDirectives(ast, resolvers*)`: collect directive values from SDL before building.
- `MaterializedType` / `MatOrigin`: track where a type came from when merging schemas.
- JSON-backed schemas are a main use case (aggregating JSON APIs).

## Execution (`sangria.execution`)

- `Executor.execute(schema, query, userContext, root, operationName, variables, queryValidator, deferredResolver, exceptionHandler, deprecationTracker, middleware, maxQueryDepth, queryReducers, errorsLimit)`.
- `Executor(...)` case class holds the same config. Its `errorsLimit` default is `Some(10)`. `Executor.execute` default is `None`.
- `Executor.prepare(...)` returns `PreparedQuery`. It validates and runs query reducers but does not execute. Execute later many times with other `userContext` / `root`. Exposes `fields`, `operation` and similar metadata.
- `Executor.getOperation(...)`: pick the operation from a document.
- `ExecutionScheme`: `Default` (`Future` of result), `Extended` (`ExecutionResult` with errors and middleware values), `Stream`, `StreamExtended`. Picked by implicit import.
- `queryValidator = QueryValidator.empty` skips validation (docs suggest it for pre-validated production queries).
- `maxQueryDepth`: reject deeper queries.
- `errorsLimit`: cap number of validation and variable errors (4.0.1).
- `ExecutionPath`: field path. Available as `ctx.path`.
- `ast.Document.operationType` / `operation`: find operation type before execution.
- Performance guidance: build schema once, warm up before first request, `ExecutionContext.parasitic` for expert users.

## Batch executor (experimental)

- `BatchExecutor.executeBatch(schema, query, operationNames = ...)`: run several operations from one document in dependency order.
- `@export(as: "name")` directive (`BatchExecutor.ExportDirective`) passes results of one operation as variables to another.
- Variables are inferred from `@export`. `inferVariableDefinitions` flag turns that off.
- `BatchExecutor.OperationNameExtension` middleware adds the operation name to each streamed result.
- Best used with `Stream` scheme. Docs say it may change or be removed.

## N+1 and data loading

- `Deferred[T]`: marker value returned from a resolver. Executor collects all deferred values for one level and calls the resolver once.
- `DeferredResolver[Ctx].resolve(deferred, ctx, queryState)`: user batch function. Must return results in the same order and size.
- `DeferredResolver.initialQueryState`: per-query state (for a cache).
- `includeDeferredFromField` and `groupDeferred`: split deferred values into separate batches (cheap vs expensive).
- `Fetcher(fetchFn)` high-level loader by ID. `HasId[T, Id]` type class gives the ID.
- `Fetcher.rel(fetch, fetchRel)` with `Relation[T, RelId]("name", fn)`: load by relation (for example category by product). `RelationIds`.
- Fetcher methods: `defer`, `deferOpt`, `deferSeq`, `deferSeqOpt`, `deferSeqOptExplicit`, `deferRel`, `deferRelOpt`, `deferRelSeq`, `deferRelSeqMany`, `clearCache`, `clearCachedId`, `clearCachedRel`, `clearCachedRelId`.
- `Fetcher.caching` / `Fetcher.relCaching`: per-query cache with dedup. `FetcherCache.simple` or a custom `FetcherCache` (custom `cacheKey`, `cacheable`).
- `FetcherConfig.maxBatchSize(n)`.
- `FetcherConfig.maxConcurrentBatches(n)`: limit parallel batches. Undocumented.
- `Fetcher.*WithContext` variants get a `FetcherContext` (with the cache) (1.4.2, not in learn docs).
- `DeferredResolver.fetchers(...)` and `DeferredResolver.fetchersWithFallback(existing, ...)`.
- `Context.deferredResolverState`: resolver state seen from a field.

## Subscriptions

- `Field.subs(...)` on a subscription root. Resolver returns a stream. All root fields must use `Field.subs` or none.
- Stream backends through `SubscriptionStream[S]` type class: `sangria.streaming.akkaStreams`, `sangria.streaming.monix`, `sangria.streaming.rxscala`, `sangria.streaming.future` (single element). Separate artifacts.
- `sangria-pekko-streams` exists in the org. It is not in the docs.
- Execute with `ExecutionScheme.Stream` to get a stream of results.
- Alternative: `Executor.prepare` once, then execute per event.
- No transport. No WebSocket protocol, no SSE, no `graphql-transport-ws`. The user wires the stream to a transport.
- `SingleFieldSubscriptions` validation rule is on by default.
- Docs still mark subscriptions as "Work In Progress".

## Query analysis and limits

- `QueryReducer[Ctx, Out]`: fold over all fields before execution. `reduceCtx` can update `Ctx` or reject the query. Run with `queryReducers = ...`.
- Built-in reducers: `QueryReducer.measureComplexity`, `rejectComplexQueries`, `measureDepth`, `rejectMaxDepth`, `collectTags`, `hasIntrospection`, `rejectIntrospection(includeTypeName)`.
- Complexity: each field costs 1 by default. `Field(complexity = Some((ctx, args, childScore) => ...))` overrides. `ScalarType.complexity`. `FieldComplexity` derive setting. Complexity from SDL directives through `DirectiveResolver(complexity = ...)`.
- `collectTags` pattern: collect `Permission` tags and load user permissions before execution only if needed.
- `QueryReducerExecutor.reduceQueryWithoutVariables(...)`: run reducers on a stored query without variables (meant for persisted queries).
- `rejectIntrospection` is the only way to turn off introspection.

## Validation

- `QueryValidator.allRules`: all spec rules plus `InputDocumentNonConflictingVariableInference` and `ExactlyOneOfFieldGiven` (`@oneOf`).
- `QueryValidator.default`, `QueryValidator.ruleBased(rules)`, `QueryValidator.empty`, `RuleBasedQueryValidator`.
- Custom rules: implement `ValidationRule` with an `AstValidatingVisitor`.
- `validateInputDocument(schema, doc, inputTypeName)`: validate a GraphQL-syntax input value (GraphQL Object Notation) against an input type.
- Schema validation: `SchemaValidationRule.default` (`DefaultValuesValidationRule`, `InterfaceImplementationValidationRule`, `SubscriptionFieldsValidationRule`, full traversal rule with `EnumValueReservedNameValidator`, `ContainerMembersValidator`, `ValidNamesValidator`, `IntrospectionNamesValidator`, `InputObjectTypeRecursionValidator`, `OneOfInputObjectValidator`). Override with `Schema(validationRules = ...)`.
- `Violation` types with source locations and pretty source snippets in messages.
- `ValueCoercionViolation` base class for custom scalar errors.

## Errors

- Pre-execution errors: `QueryReducingError`, `QueryAnalysisError` (client error, docs suggest HTTP 400), `ErrorWithResolver`. All have `resolveError` to render a spec-shaped error.
- `UserFacingError` trait: message shown to the client. Other exceptions show `"Internal server error"`.
- `ExceptionHandler(onException, onViolation, onUserFacingError)`: map exceptions, validation violations and built-in errors to `HandledException`.
- `HandledException(message, additionalFields, positions, addFieldsInExtensions, addFieldsInError)`. `HandledException.multiple(...)` gives several error entries from one exception.
- `addFieldsInExtensions` (default true) and `addFieldsInError` (default false): put extra fields in `extensions` or at top level of the error. The flags are undocumented.
- `PartialValue` / `PartialFutureValue`: return data and errors from one field.
- `MiddlewareErrorField.fieldError`: hook for field errors.

## Middleware

- `Middleware[Ctx]` with `beforeQuery` / `afterQuery`. `QueryVal` per-query state.
- `MiddlewareBeforeField.beforeField` with `FieldVal` per-field state. Returns `BeforeFieldResult`.
- `BeforeFieldResult.attachment(...)`: pass a `MiddlewareAttachment` to the resolver (`ctx.attachment[T]`).
- `MiddlewareBeforeField.overrideAction(action)`: replace the field result without calling the resolver (cache, auth short-circuit). Undocumented.
- `MiddlewareAfterField.afterField`: can replace the field value.
- `MiddlewareErrorField.fieldError`.
- `MiddlewareExtension.afterQueryExtensions`: add `extensions` to the response. `Middleware.simpleExtension(fn)` and `SimpleAstBasedExtensionMiddleware` helpers (undocumented).
- `MiddlewareToScalar` / `MiddlewareFromScalar`: transform scalar values on input and output across the whole schema. `Middleware.composeToScalarMiddleware` / `composeFromScalarMiddleware`. Undocumented.
- `MiddlewareQueryContext` gives executor, query AST, operation name, variables, timing (`TimeMeasurement`).
- Ordering: `beforeField` in list order, `afterField` in reverse.
- Docs show auth with `FieldTag` (`Authorised`, `Permission`) plus a `MiddlewareBeforeField` enforcer. Not built in.

## Deprecation

- `deprecationReason` on fields, enum values, arguments and input fields (args and input fields since 4.1).
- `DeprecationTracker` with `deprecatedFieldUsed`, `deprecatedEnumValueUsed`, `deprecatedDirectiveArgUsed`, `deprecatedInputObjectFieldUsed`, `deprecatedFieldArgUsed`. `DeprecationTracker.print`, `LoggingDeprecationTracker(logFn)`.
- `schema.analyzer(query).deprecatedUsages`: find deprecated usage statically.

## Marshalling (format independence)

- `ResultMarshaller` and `InputUnmarshaller[Node]` abstract the JSON library. Import one (`sangria.marshalling.circe._`) and results come back as that type.
- `ToInput[T, Node]` for default values. `FromInput[T]` for typed input objects. play-json `Reads` / spray-json `JsonFormat` work as `FromInput` automatically.
- `CoercedScalaResultMarshaller`, `sangria.marshalling.queryAst._` (GraphQL value AST as the format).
- `MarshallingUtil` converts between formats (for example circe `Json` to spray `JsValue`).
- `InputDocument` / `graphqlInput"..."` / `QueryParser.parseInputDocument`: "GraphQL Object Notation". GraphQL literal syntax as a data format. `InputDocument.to[T]` deserializes through `FromInput`.
- `MarshallerCapability` (`DateSupport`, `CalendarSupport`, `BlobSupport`): binary formats like MessagePack and Ion can carry native dates and blobs.

## Parser, AST and tooling

- `QueryParser.parse(query, ParserConfig)`. `ParserConfig(experimentalFragmentVariables, sourceIdFn, sourceMapperFn, parseLocations, parseComments)`.
- `experimentalFragmentVariables`: fragments with variable definitions. Undocumented.
- `parseLocations = false` / `parseComments = false` for faster parsing. Undocumented.
- `graphql"..."` / `gql"..."` / `graphqlInput"..."` macros: parse and check syntax at compile time.
- `QueryRenderer.renderPretty` / `renderCompact`, `QueryRendererConfig`. `document.renderPretty`.
- `AstVisitor.visit(doc, AstVisitor {...})` with `VisitorCommand.Delete`, `Transform`, `Skip`, `Break`. Variants with `TypeInfo` and state. Based on `macro-visit`.
- `AstNodeTransformer.withoutAstLocations(node, stripComments)`.
- `ast.Document.merge` / `+`, `withoutSourceMapper`, `separateOperations`, `separateOperation`.
- `DocumentAnalyzer` (`query.analyzer`): `separateOperations`, `getFragmentSpreads`, `getRecursivelyReferencedFragments`, `getVariableUsages`, `getRecursiveVariableUsages`.
- `SchemaBasedDocumentAnalyzer` (`schema.analyzer(query)`): `deprecatedUsages`, `introspectionUsages`, `resolveDirectives`.
- `SourceMapper` keeps source text for error messages. `AstLocation`.

## Schema rendering, introspection and comparison

- `SchemaRenderer.renderSchema(schema)` / `schema.renderPretty` / `schema.renderCompact` / `schema.toAst`.
- `SchemaFilter` for rendering: `default` (= `withoutSangriaBuiltIn`), `withoutGraphQLBuiltIn`, `withoutIntrospection`, `builtIn`, `introspection`, custom. Rendering only, not per-user visibility.
- `SchemaRenderer.renderSchema(introspectionResult)`: SDL from an introspection JSON.
- `sangria.introspection.introspectionQuery(schemaDescription, directiveRepeatableFlag, inputValueDeprecation)` and `introspectionQueryString(...)`.
- `IntrospectionParser.parse(json)`: introspection result into case classes (`IntrospectionSchema`).
- `schema.compare(oldSchema)` / `SchemaComparator.compare`: returns `SchemaChange` list. Each change has `breakingChange`, `dangerousChange` and `description`. About 69 change kinds, including AST directive add/remove on every element and `DirectiveRepeatableChanged`. Docs suggest CI gating and release notes.
- `Schema.isBuiltInType`, `isBuiltInGraphQLType`, `isBuiltInSangriaType`, `isBuiltInDirective`, `isIntrospectionType`.

## Effect systems

- Core is `Future`-based.
- `sangria-cats-effect-experimental` module (4.0): `AsyncValue[Ctx, Val, F]` action for any `cats.effect.Async`. `IOExecutionScheme` / `AsyncExecutionScheme[F]` return `F[...]`. `AsyncValue` works in mutations since 4.2.15. Derivation lookups for `F[A]` (4.2.19).
- Open PR #1321 (2026-09): full `IO` resolver. Deferred values still use `Future` in it.

## Related modules (sangria-graphql org)

- sangria-relay (4.0.1, 2025-03-07): `Node.definition` / `Node.definitionById` (node interface and `node` field), `Node.globalIdField`, `Node.pluralIdentifyingRootField`, `nodesField`, `GlobalId.toGlobalId` / `fromGlobalId`, `Identifiable` type class, `Connection.definition` / `definitionWithEdge`, `ConnectionArgs` (`first`, `last`, `before`, `after`), `Connection.connectionFromSeq` / `connectionFromFutureSeq` (offset cursors with `arrayconnection:` prefix), `ConnectionLike` for custom connections, `Mutation.fieldWithClientMutationId` (Relay classic `input`/`clientMutationId` mutations). Main docs give it one line.
- sangria-slowlog (3.0.1, 2026-10-04): `SlowLog(logger, threshold)` middleware logs slow queries with per-field timing and percentiles rendered as a commented query. `SlowLog.extension` adds metrics to `extensions`. `SlowLog.apolloTracing` (`ApolloTracingExtension`) for Apollo Tracing format. `SlowLog.openTracing()` creates OpenTracing spans per field. `addExtentions` flag.
- sangria-federated (0.9.3, 2026-07-08, "technology preview"): Federation v1 and v2 subgraph. `Federation.federate(schema, customDirectives, entityResolvers*)` adds `_service`, `_entities`, `_Any`, `_Entity`, `_FieldSet`. `EntityResolver` (docs recommend `Fetcher` batching). v2 directives: `Key`, `Shareable`, `Inaccessible`, `Override`, `External`, `Provides`, `Requires`, `Tag`, `Extends`, `InterfaceObject`, `ComposeDirective`, `Authenticated`, `RequiresScopes`, `Policy`, `Link`, `Context`/`FromContext`, `Cost`, `ListSize`. `ApolloFederationTracing` middleware (ftv1). Upgrades the marshaller so `_Any` can hold objects.
- Marshalling modules (one artifact per library): `sangria-circe`, `sangria-play-json`, `sangria-spray-json`, `sangria-argonaut`, `sangria-json4s-native`, `sangria-json4s-jackson`, `sangria-jackson` (README says work in progress), `sangria-msgpack`, `sangria-ion`. Base: `sangria-marshalling-api` (1.2.1, 2026-10-05) and `sangria-marshalling-testkit` (ScalaTest behaviour specs such as `MarshallingBehaviour` to verify a new marshaller).
- Streaming modules: `sangria-streaming-api`, `sangria-akka-streams` (last GitHub release 2020), `sangria-pekko-streams` (no GitHub release), `sangria-monix` (2021), `sangria-rxscala` (2017).
- HTTP: `sangria-akka-http` (`sangria-akka-http-core` plus `sangria-akka-http-circe`, 0.0.4, 2023-06-16). `graphQLRoute` handles GET and POST, `application/json` and `application/graphql` bodies, error formatting. README is mostly TODO. `sangria-pekko-http` repo is empty apart from README and LICENSE. Not in the docs.
- `macro-visit`: macro-based visitor generator used by `AstVisitor`.
- Examples: `sangria-akka-http-example`, `sangria-playground` (Play), `sangria-relay-playground`, `sangria-subscriptions-example` (akka-http SSE subscriptions example).

## Not supported or not in scope

- No `@defer` / `@stream` incremental delivery.
- No `@specifiedBy` directive in built-ins.
- No HTTP server, GraphiQL or request parsing in core. Only the thin `sangria-akka-http` module.
- No subscription transport (WebSocket, SSE, `graphql-transport-ws`) in core.
- No persisted queries or APQ. `Executor.prepare` and `reduceQueryWithoutVariables` are building blocks only.
- No file uploads.
- No built-in auth or permission system. Docs show do-it-yourself patterns with `FieldTag` plus middleware or checks in resolvers.
- No per-request schema visibility or field hiding. `SchemaFilter` only affects rendering.
- No ORM or database integration. No auto filtering, ordering or pagination. Projections only give selected field names.
- No pagination in core. Relay connections are in `sangria-relay` and are offset-based.
- No input validation framework beyond scalar coercion, `ScalarAlias` and `@oneOf`.
- No rate limiting. No query timeout setting.
- No client code generation. No schema-to-Scala codegen.
- No derivation for interfaces or unions.
- No toggle to disable introspection other than the `rejectIntrospection` reducer.
- No built-in tracing in core. Tracing is in `sangria-slowlog`.

## Upcoming and unreleased work

- `main` after 4.2.19: more cats-effect `IO` resolver work and tests. sbt 2.0 build.
- Open PRs: #1321 "IO implementation" of the resolver (2026-09), #1285 integration tests (WIP), #1264 reduce map contention, #1239 type safety, #1216 cats-effect implicit ambiguity, #869 make `SubscriptionValue` public, #915 / #916 custom directive API (old, 2022), #993 call scalar `coerceUserInput` before `coerceOutput`.

## Docs and code disagree

- Docs show `QueryValidator.default.validateQuery(schema, query)`. The code requires `validateQuery(schema, query, variables, errorsLimit)` with no defaults since 4.0.1. The doc example does not compile.
- Docs say the site covers `sangria 4.0.0`. Code is at 4.2.19. Docs do not mention `@oneOf`, argument and input-field deprecation, interfaces implementing interfaces, `errorsLimit`, the cats-effect module, Scala 3, or `Long` accepting strings.
- Docs list streaming modules for akka-streams, RxScala and monix. RxScala had no release since 2017. The org also has `sangria-pekko-streams`, which the docs do not list.
- `Executor(...)` case class defaults `errorsLimit` to `Some(10)`. `Executor.execute(...)` and `Executor.prepare(...)` default it to `None`. Behaviour depends on which entry point is used.
- Docs say `Fetcher.caching` is per query. A `FetcherCache` instance passed through `FetcherConfig.caching(cache)` is shared across queries if it is created outside the request. I think this is intended but it is not stated.
- `CHANGELOG.md` in the repo stops at 3.0.0. Release notes are only on GitHub.

## Sources

- https://sangria-graphql.github.io/learn/ (source: https://github.com/sangria-graphql/sangria-graphql.github.io/blob/main/learn.md)
- https://sangria-graphql.github.io/getting-started/ (source: `getting-started.md` in the same repo)
- https://github.com/sangria-graphql/sangria (README, `CHANGELOG.md`, `modules/`)
- https://github.com/sangria-graphql/sangria/releases
- https://github.com/sangria-graphql/sangria/pulls
- https://github.com/sangria-graphql/sangria-relay
- https://github.com/sangria-graphql/sangria-slowlog
- https://github.com/sangria-graphql/sangria-federated
- https://github.com/sangria-graphql/sangria-akka-http
- https://github.com/sangria-graphql/sangria-marshalling-api
- https://github.com/sangria-graphql (org repo list)
- https://sangria-graphql.github.io/llms.txt (404)
