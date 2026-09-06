# graphql-js findings

Versions checked: stable `17.0.2` (2026-07-03, `main` at `ee5ce41`, 2026-09-09) and `16.14.2` (2026-06-09, branch `16.x.x`). `17.0.0` final shipped 2026-06-15.
Package `graphql` on npm. Also published to JSR with Deno builds. v17 needs Node.js 22, 24, 25 or 26+. Types target TypeScript 4.4+.
This is the reference implementation. graphql-core is a line-by-line port. Most of the v17 surface is already in graphql-core 3.3 (see `graphql-core.md`). This file lists only what graphql-js has beyond that, and what differs.
graphql-core 3.3.0rc1 tracks `17.0.0rc0` (`version_js`). So graphql-core is one step behind 17.0.0 final.
SemVer. Support policy (`README.md`): latest major gets full support. Previous major gets features for 12 months, then bug and security fixes. No LTS.
Docs source is in the repo under `website/pages/` (Nextra MDX). The site moved to https://graphql-js.org (https://graphql.org/graphql-js/ redirects there). No `llms.txt` on the graphql-js site. https://graphql.org/llms.txt exists (for graphql.org).
Changelog is GitHub releases only. No `CHANGELOG.md`.

## Incremental delivery (`@defer`, `@stream`)

- State: still experimental in 17.0.x. The spec is not final. `@defer`/`@stream` are not in `specifiedDirectives`. You opt in with `GraphQLDeferDirective` and `GraphQLStreamDirective` in `GraphQLSchema({ directives: [...specifiedDirectives, ...] })`.
- `experimentalExecuteIncrementally(args)`: returns `ExecutionResult` or `ExperimentalIncrementalExecutionResults { initialResult, subsequentResults }`. Payload format follows the GraphQL WG RFC (`pending`/`incremental`/`completed` with `id`, `subPath`). Same as graphql-core 3.3.
- `execute()` rejects a schema that contains `@defer`/`@stream` (`ExecutorThrowingOnIncremental`). `graphql()`, `graphqlSync()`, the harness `execute` and `subscribe()` never return incremental results.
- `legacyExecuteIncrementally(args)` and `legacyExecuteRootSelectionSet()` (`src/execution/legacyIncremental/`): the older alpha payload format. Each payload has `path` and optional `label`, no `pending`/`completed`, and can duplicate field data. Built on `BranchingIncrementalExecutor`. Types `LegacyInitialIncrementalExecutionResult`, `LegacySubsequentIncrementalExecutionResult`, `LegacyIncrementalDeferResult`, `LegacyIncrementalStreamResult` and `Formatted*` variants. Not in graphql-core. Useful for clients that still speak the old format (I think older Apollo Client and Relay versions).
- The even older alpha shape with a `singleResult` discriminator is gone.
- Internals rebuilt on a work queue: `src/execution/incremental/` (`buildExecutionPlan`, `WorkQueue`, `Computation`, `IncrementalExecutor`, `IncrementalPublisher`). Deferred fragments are grouped into delivery groups by an execution plan, so a field shared by the initial and deferred parts is sent once.
- `enableEarlyExecution` (default `false`): deferred work starts before the initial payload is done.
- Resolvers of list fields can return async iterables. `@stream` then completes items as they arrive.
- `abortSignal` on incremental execution stops new payloads and closes async iterators.
- Validation rules exported: `DeferStreamDirectiveLabelRule`, `DeferStreamDirectiveOnRootFieldRule`, `DeferStreamDirectiveOnValidOperationsRule`, `StreamDirectiveOnListFieldRule`. `OverlappingFieldsCanBeMergedRule` also rejects two different `@stream` usages on the same field.
- 17.0 validation details: fragment spreads are tracked through the selected operation. Query root fields may use `@defer`/`@stream`. Mutation and subscription root fields may not (also through fragments on interfaces of the root type). Subscriptions reject active `@defer`/`@stream` also through named fragments. Disable it with `if: $var` for fragments shared with subscriptions.
- No transport. The docs say: pick HTTP multipart, SSE or WebSocket framing yourself. graphql-js ships no encoder.
- v16 has no `@defer`/`@stream` at all.

## Request pipeline and host integration

- `graphql(args)` / `graphqlSync(args)`: `GraphQLArgs` adds parse options (`noLocation`, `maxTokens`, `experimentalFragmentArguments`), validation `rules`, `maxErrors`, `hideSuggestions`, `abortSignal`, `hooks`, `harness`. Same as graphql-core 3.3.
- `GraphQLHarness { parse, validate, execute, subscribe }` and `defaultHarness` (`src/harness.ts`). Types `GraphQLParseFn`, `GraphQLValidateFn`, `GraphQLExecuteFn`, `GraphQLSubscribeFn`. Each phase may return a value or a promise, so parse and validate can be async (for example a remote persisted document store). The docs say it is modeled on Envelop and exists so plugin systems can share one pipeline shape. Docs examples: trusted-document cache in `parse`, stored validation results in `validate`.
- `validateExecutionArgs(args)`: returns `ValidatedExecutionArgs` or `GraphQLError[]`. Does schema check, operation selection, variable coercion, fragment details, default resolvers. Then call `executeRootSelectionSet()`, `experimentalExecuteRootSelectionSet()` or `legacyExecuteRootSelectionSet()`. This is how you build a custom executor in graphql-js. I did not find this public helper split in graphql-core 3.3 (it has `execute_root_selection_set` but not `validate_execution_args`).
- `validateSubscriptionArgs()`, then `createSourceEventStream(validatedArgs)`, then `mapSourceToResponseEvent(validatedArgs, stream, rootSelectionSetExecutor)`. `executeSubscriptionEvent()` is the default per-event executor.
- The `Executor` class is not a public export in graphql-js. There is no `executorClass` option. Subclassing the executor is a graphql-core only extension point.
- No middleware in graphql-js. `middleware=` and `MiddlewareManager` are graphql-core only.
- `execute()` and `subscribe()` return a plain value when execution is sync (`PromiseOrValue`). `subscribe()` no longer always returns a promise (v17 breaking change).

## Observability (not in graphql-core)

- Tracing channels on Node.js `node:diagnostics_channel` (`src/diagnostics.ts`, PR #4670). Channels: `graphql:parse`, `graphql:validate`, `graphql:execute`, `graphql:execute:variableCoercion`, `graphql:execute:rootSelectionSet`, `graphql:subscribe`, `graphql:resolve`.
- Each channel emits `start`, `end`, `asyncStart`, `asyncEnd`, `error`. Traced work runs inside `start.runStores`, so an `AsyncLocalStorage` bound with `channel.start.bindStore()` stays active over the async lifecycle. That is how APM spans open in `start` and close in `asyncEnd`.
- Context payload types are exported: `GraphQLParseContext`, `GraphQLValidateContext`, `GraphQLExecuteContext`, `GraphQLExecuteVariableCoercionContext`, `GraphQLExecuteRootSelectionSetContext`, `GraphQLSubscribeContext`, `GraphQLResolveContext`, `GraphQLChannels`, `GraphQLChannelContextByName`.
- `graphql:resolve` fires for every field, also default-resolved ones. No per-field filtering. Hierarchy comes from `fieldPath` in the payload.
- `graphql:execute:rootSelectionSet` fires once per subscription event. For `@defer`/`@stream`, `graphql:execute` ends at the initial result.
- Zero cost when the runtime has no `diagnostics_channel` (browsers). Channels are observe-only. Changing a payload does not change execution.
- Python has no `diagnostics_channel` equivalent. A Python port would need its own hook API.

## Cancellation and hooks

- `abortSignal` on `graphql()`, `execute()`, `subscribe()`, `experimentalExecuteIncrementally()`. Resolvers call `info.getAbortSignal()` (a method, not a property as in graphql-core `info.abort_signal`).
- `AbortedGraphQLExecutionError` carries the cause and the partial result (`abortedResult`, PR #4674).
- All resolvers of one operation share one signal. No per-field cancellation. Internally cancelled parts (for example after null bubbling) abort the shared signal once the returned result is done.
- `ExecutionHooks { asyncWorkFinished(info) }`. Only hook. Resolvers register extra work with `info.getAsyncHelpers()` (`track`, `promiseAll`).
- Same design as graphql-core 3.3. graphql-core has `gather` where graphql-js has `promiseAll`.

## Error handling

- `@experimental_disableErrorPropagation` on `QUERY | MUTATION | SUBSCRIPTION`. The schema must declare it in SDL. `GraphQLDisableErrorPropagationDirective` is defined in `src/type/directives.ts` but I did not find it re-exported from `graphql` or `graphql/type`. graphql-core exports it.
- The docs point to the spec proposals "Error Behavior" (`onError` modes: propagate, null, halt, PR graphql-spec#1163) and "Service Capabilities" (graphql-spec#1208). Draft graphql-js PR #4364 implements `onError`. Not merged on `main`. No semantic non-null support in `main`.
- `GraphQLError(message, { nodes, source, positions, path, cause, extensions })`. Positional constructor removed in v17. `originalError` deprecated for `cause`.
- `printError()` and `formatError()` removed. Use `error.toString()` and `error.toJSON()`.
- No error masking, no error codes. Same as graphql-core.

## Type system and schema

- `@oneOf` input objects: `GraphQLInputObjectType({ isOneOf: true })`, `GraphQLOneOfDirective`, introspection `isOneOf`. In both 16.x and 17.x. Same as graphql-core.
- 17.0.0 final adds "OneOf inhabitability" (PR #4564): schema validation rejects input object cycles that can never get a finite value, also recursive OneOf inputs with no escape branch. Not in graphql-core 3.3.0rc1.
- 17.0 OneOf coercion fixes: count only known fields, fail when a default fills the single field, same error text for null and count errors (PRs #4715 to #4719).
- Directives on directive definitions graduated in 17.0.0 (PR #4819). No parser flag needed. `DirectiveLocation.DIRECTIVE_DEFINITION`, `DirectiveExtensionNode`, `GraphQLDirective.directives`, `@deprecated` on directives with `isDeprecated`/`deprecationReason` in introspection. graphql-core 3.3.0rc1 still needs `experimental_directives_on_directive_definitions=True`. 16.14 has it behind `experimentalDirectivesOnDirectiveDefinitions`.
- Default values are validated by `validateSchema()` in v17 (arguments, input fields, directive arguments).
- `default: { value }` or `default: { literal }` replaces `defaultValue`. Same as graphql-core `GraphQLDefaultInput`.
- `@deprecated(reason:)` argument is non-null in v17. `includeDeprecated` introspection arguments are `Boolean! = false`.
- Schema validation rejects one object type used for two root operation types.
- `bigint` support in built-in scalars (PR #4550). `Int` and `Float` accept `bigint` in range. `ID` serializes `bigint` as a string. JS only.
- `extensions` maps accept symbol keys. JS only.
- `GraphQLSchema.getField(parentType, fieldName)` also returns meta fields (`__typename`, `__schema`, `__type`).
- `assertField()`, `assertArgument()`, `assertInputField()`, `assertEnumValue()` and matching TS types.
- `printDirective()`.
- `TypedQueryDocumentNode<TResult, TVariables>`: typed documents for TS codegen.
- Null-prototype objects for resolver args and coerced inputs (security hardening against prototype pollution). JS only.
- Internally uses unique symbols instead of `instanceof` for type predicates in v17.

## Language and validation

- Schema coordinates: `parseSchemaCoordinate`, `resolveSchemaCoordinate`, `resolveASTSchemaCoordinate`, node types `TypeCoordinateNode`, `MemberCoordinateNode`, `ArgumentCoordinateNode`, `DirectiveCoordinateNode`, `DirectiveArgumentCoordinateNode`. In 16.12+ and 17. `resolveSchemaCoordinate` also resolves meta fields and introspection types (`Business.__typename`, `__Directive.name`). The docs call this implementation-defined. Same as graphql-core.
- Fragment arguments behind `experimentalFragmentArguments` (parser option). Works at runtime (not only parser, unlike the old `allowLegacyFragmentVariables`). `FragmentArgumentNode`, `Kind.FRAGMENT_ARGUMENT`. 17.0.0 raises a request error on invalid fragment variables (PR #4799).
- Executable descriptions (descriptions on operations and variables). In 16.12+ and 17.
- `KnownOperationTypesRule` in v17 `specifiedRules`.
- `hideSuggestions` on validate and execute (v17 only, not in 16.x).
- `maxTokens` does not count comments in graphql-js `main` (the lexer skips `COMMENT` tokens before counting). graphql-core 3.2.12 and 3.3.0rc1 count comments (CVE-2026-75508). I did not find a matching fix in graphql-js.
- `OverlappingFieldsCanBeMergedRule` has no comparison budget in graphql-js `main`. graphql-core added `MAX_FIELD_COMPARISONS = 250_000` (CVE-2026-75507). I did not find a matching limit in graphql-js. I think graphql-core fixed these on its own and graphql-js has not released them yet.
- `MaxIntrospectionDepthRule` in `recommendedRules`. `getIntrospectionQuery({ typeDepth })` since 16.14.
- `getEnterLeaveForKind()` replaces `getVisitFn()`. `visitInParallel()`, `visitWithTypeInfo()`.
- No query depth, cost or complexity rule. No alias limit. The docs point to the external `graphql-query-complexity` and `graphql-depth-limit` packages.

## Utilities

- `findSchemaChanges()` with `SafeChange`/`SafeChangeType`. `findBreakingChanges()`/`findDangerousChanges()` deprecated. 17.0.2 detects default value changes on input object fields (PR #4832).
- `validateInputValue()`, `validateInputLiteral()`, `coerceInputLiteral()`, `valueToLiteral()`, `replaceVariables()`. `coerceInputValue()` returns `undefined` on failure in v17. Same as graphql-core 3.3.
- `mapSchemaConfig` and `sortValueNode` exist in `src/utilities/` but are internal (not exported).
- No mock server, no schema stitching, no federation, no SDL-from-classes. The docs point to `@graphql-tools/stitch`, Apollo Federation and GraphQL Codegen.

## Development mode

- `enableDevMode()` and `isDevModeEnabled()`. Off by default in v17. On with the `development` export condition. `NODE_ENV` is ignored in v17 (it was the switch in v16).
- Only check today: detect two GraphQL.js module copies in one process. JS packaging concern only.

## Documentation guides (not APIs)

- The site has how-to guides for: DataLoader N+1 (`dataloader` package), cursor pagination (hand-written connection types), authorization (resolver checks and directives via `getDirectiveValues`), caching (DataLoader, LRU, Redis, CDN), operation complexity (`graphql-query-complexity`), going to production (depth limit, trusted documents, introspection control, error masking), scaling (stitching, federation), type generation (GraphQL Codegen), HTTP (`graphql-http` `createHandler`), subscriptions (`node:events` `on()` as pub/sub), testing guides.
- None of these are built into graphql-js. graphql-js is the engine only. No HTTP server, no GraphiQL, no persisted documents store, no dataloader, no pagination helpers, no auth.

## Relevance for Undine

- Undine uses graphql-core `>=3.2.12`. graphql-core 3.2 has no `@defer`/`@stream`, harness, abort signals or hooks. All of them need graphql-core 3.3.
- Features in graphql-js that graphql-core 3.3 does not have: tracing channels, `legacyExecuteIncrementally`, `validateExecutionArgs`/`validateSubscriptionArgs` helpers, OneOf inhabitability validation, graduated directives on directives.
- Features in graphql-core that graphql-js does not have: middleware, executor subclassing (`executor_class`), `out_name`/`out_type`, lazy descriptions, comment counting in `max_tokens`, `MAX_FIELD_COMPARISONS`.

## Sources

Docs (read from repo source `website/pages/`, site https://graphql-js.org):
- `upgrade-guides/v16-v17.mdx` (https://graphql-js.org/upgrade-guides/v16-v17)
- `docs/defer-stream.mdx`, `docs/graphql-harness.mdx`, `docs/tracing-channels.mdx`, `docs/development-mode.mdx`, `docs/experimental-specification-features.mdx`, `docs/advanced-execution-pipelines.mdx`, `docs/abort-signals.mdx`, `docs/execution-hooks.mdx`, `docs/schema-coordinates.mdx`, `docs/oneof-input-objects.mdx`, `docs/directives-on-directives.mdx`, `docs/disabling-error-propagation.mdx`, `docs/fragment-arguments.mdx`
- Skimmed headings and imports: `docs/operation-complexity-controls.mdx`, `docs/caching-strategies.mdx`, `docs/going-to-production.mdx`, `docs/scaling-graphql.mdx`, `docs/graphql-http.mdx`, `docs/type-generation.mdx`, `docs/n1-dataloader.mdx`, `docs/authorization-strategies.mdx`, `docs/cursor-based-pagination.mdx`, `docs/subscriptions.mdx`, `docs/nullability.mdx`
- `README.md` (version support policy)
- https://graphql.org/llms.txt returns 200 (graphql.org, not graphql-js). `https://graphql.org/graphql-js/llms.txt` and `https://graphql-js.org/llms-full.txt` return 404.

Changelog:
- GitHub releases via `gh api repos/graphql/graphql-js/releases` (v0.x to v17.0.2 and v15.10.3): https://github.com/graphql/graphql-js/releases

Repos (shallow clones in `/tmp`):
- https://github.com/graphql/graphql-js `main` at 17.0.2 (`/tmp/graphql-js`)
- same repo, branch `16.x.x` at 16.14.2 (`/tmp/graphql-js-16`)
- `/tmp/graphql-core` (from the graphql-core audit) for comparison

Source files checked:
- `src/index.ts` (export diff against graphql-core `__init__.py`), `src/graphql.ts`, `src/harness.ts`, `src/devMode.ts`, `src/diagnostics.ts`
- `src/execution/index.ts`, `ExecutionArgs.ts`, `execute.ts`, `createSharedExecutionContext.ts`, `incremental/IncrementalPublisher.ts`, `incremental/IncrementalExecutor.ts`, `legacyIncremental/legacyExecuteIncrementally.ts`, `legacyIncremental/BranchingIncrementalExecutor.ts`
- `src/type/directives.ts`, `src/type/definition.ts` (`GraphQLResolveInfo`), `src/type/validate.ts`
- `src/language/parser.ts`, `src/language/lexer.ts`
- `src/validation/rules/`, `src/validation/rules/OverlappingFieldsCanBeMergedRule.ts`
