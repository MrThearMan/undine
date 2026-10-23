# graphql-php findings

Versions checked: `webonyx/graphql-php` v15.38.0 (2026-10-06). Repo `master` at `47e6ba3` (2026-10-06).
graphql-php is a PHP port of graphql-js (see `graphql-js.md`). Code-first. Types are built from config arrays (`new ObjectType([...])`) or from SDL (`BuildSchema::build()`). It tracks the October 2021 spec plus `@oneOf`. It does not track graphql-js v16/v17 execution features (no `@defer`/`@stream`, no subscriptions, no abort signal, no harness).
This file lists what graphql-php adds or does differently. Spec-level parts that match graphql-js (parser, visitor, validation rules, `BuildSchema`, `SchemaExtender`, `BuildClientSchema`, `BreakingChangesFinder`, `TypeInfo`) are only listed where they differ.
PHP `^7.4 || ^8`. Needs `ext-json`, `ext-mbstring`. Optional: `psr/http-message` (server), `react/promise`, `amphp/amp` v2/v3. MIT.
Docs source is in the repo under `docs/` (MkDocs, `mkdocs.yml`). Site https://webonyx.github.io/graphql-php/ is live. No `llms.txt` or `llms-full.txt` (404).
Changelog: `CHANGELOG.md` in the repo (Keep a Changelog). Upgrade notes: `UPGRADE.md`.

## Maintenance status

- Active. Last commit on `master` 2026-10-06. 4713 stars. 71 open issues plus PRs. Not archived.
- Releases are small and frequent. v15.38.0 (2026-10-06), v15.37.3 (2026-10-03), v15.37.2 (2026-08-14). v15.30.0 was 2026-01-20. v15.20.0 was 2025-03-21. Still on major 15. No v16 branch.
- Recent work: security fixes (parser recursion DoS, quadratic `OverlappingFieldsCanBeMerged`), lexer speed-ups, per-schema scalar overrides, `@specifiedBy`, `Printer::stripIgnoredCharacters()`, AMPHP v3 adapter.

## Request pipeline and execution

- `GraphQL::executeQuery($schema, $source, $rootValue, $context, $variableValues, $operationName, $fieldResolver, $validationRules)`: sync facade. Positional arguments only. `$source` can be a string or a parsed `DocumentNode`.
- `GraphQL::promiseToExecute($promiseAdapter, ...same args)`: async facade. Returns a `Promise` of `ExecutionResult`.
- `ExecutionResult` with `data`, `errors`, `extensions` (constructor arg only, no hook fills it). `toArray($debugFlag)`, `jsonSerialize()`, `setErrorFormatter()`, `setErrorsHandler()`.
- `validationRules = []` skips validation. Documented use: persisted queries that were validated before they were stored.
- `GraphQL::setDefaultFieldResolver()`, `Executor::setDefaultFieldResolver()`: global default resolver.
- Resolver precedence: field `resolve`, then type `resolveField`, then the `$fieldResolver` argument, then the global default.
- `Executor::defaultFieldResolver`: array key or `ArrayAccess` key, else object property. If the value is a `\Closure`, it calls it with `($objectValue, $args, $context, $info)`. So a data object can carry per-field closures.
- `argsMapper` on a field, on an `ObjectType`, or globally with `GraphQL::setDefaultArgsMapper()` / `Executor::setDefaultArgsMapper()`. Signature `callable(array $args, FieldDefinition, FieldNode, mixed $context): mixed`. Maps coerced args to a DTO or validates them. The result is cached per `(FieldDefinition, FieldNode)` in `ReferenceExecutor::$fieldArgsCache`, so it runs once per field node, not once per list item.
- `ScopedContext` interface: if the context object implements it, the executor calls `$context->clone()` before passing it to child fields. Child fields can add data to the context without changing siblings or parents. Only in the class reference, not in the guides.
- `Executor::setImplementationFactory(callable)`: replaces the whole executor. Default is `ReferenceExecutor::create`. Interface `ExecutorImplementation { doExecute(): Promise }`. Not in the guides. I think this is how third-party JIT or custom executors plug in.
- `Executor::setDefaultPromiseAdapter()`: global promise adapter.
- Abstract type resolution: `resolveType` on interfaces and unions. `resolveValue` on interfaces and unions (v15.25) runs before `resolveType` and can swap the value (for example unwrap a model). If `resolveType` is missing, it loops over `isTypeOf` of all implementors. `isTypeOf` may return a `Deferred`. If `resolveType` returns `null`, it emits a warning and falls back to the slow `isTypeOf` scan.
- Subscriptions: not supported. There is no `subscribe()` and no source event stream. The docs say the `subscription` root type is "reserved for future subscriptions implementation". A subscription operation runs like a query once. Lighthouse and others build their own.
- `@defer`/`@stream`: not supported.
- No abort or cancellation API. No execution hooks. No middleware. No tracing or instrumentation API. No `extensions` filling hook.

## Batching and async (N+1)

- `GraphQL\Deferred`: `new Deferred(fn () => ...)`. The executor runs all non-deferred fields first, then the deferred queue. The user fills a buffer in the resolver and loads it once in the closure. This is the built-in N+1 tool. There is no built-in DataLoader class. `overblog/dataloader-php` is the external one. `Deferred::create()` is deprecated (v15.29).
- `SyncPromise`, `SyncPromiseQueue`, `SyncPromiseAdapter` (default): the queue that makes `Deferred` work without an event loop. `SyncPromiseAdapter::wait()` drains it.
- Promise adapters: `ReactPromiseAdapter` (react/promise v2 and v3), `AmpPromiseAdapter` (AMPHP v2), `AmpFutureAdapter` (AMPHP v3, v15.32). Swoole through the external Resonance library. Custom: implement `PromiseAdapter`.
- `Promise` and `PromiseAdapter` are generic over the adopted promise type (v15.34, PHPStan only).
- `StandardServer` batching shares one deferred queue across all operations in a batch. So a batch of three `user(id:)` queries can be one DB query.

## HTTP server (`GraphQL\Server`)

- `StandardServer($config)`. Said to be compatible with express-graphql.
- `handleRequest()`: reads PHP globals (`$_GET`, `$_POST`, `php://input`), executes, writes with `header()` and `echo`.
- `executeRequest($parsedBody = null)`: returns `ExecutionResult` or a list of them (or a promise).
- PSR-7: `processPsrRequest($request, $response, $bodyStream)` and `executePsrRequest($request)`. Integration guides link Laravel, Symfony PSR-7 bridge, Slim, Mezzio. No PSR-15 middleware class shipped.
- `Helper`: lower-level API. `parseHttpRequest()`, `parsePsrRequest()`, `parseRequestParams()`, `validateOperationParams()`, `executeOperation()`, `executeBatch()`, `sendResponse()`, `toPsrResponse()`.
- Content types: `application/json`, `application/graphql` (raw query body), `application/x-www-form-urlencoded`, `multipart/form-data` (reads `$_POST` only, no file upload spec). GET reads query params.
- GET allows only `query` operations (`GetMethodSupportsOnlyQueryOperation`).
- Response is always `Content-Type: application/json`. The server never sets an HTTP status code. No `application/graphql-response+json`. No `Accept` negotiation. So it does not follow the GraphQL-over-HTTP spec status rules.
- `OperationParams`: `query`, `queryId`, `operation`, `variables`, `extensions`, `readOnly`, `originalInput`. `queryId` is read from `queryId`, `documentId` or `id`. If `extensions.persistedQuery.sha256Hash` is set, it becomes `queryId` (Apollo APQ shape).
- `ServerConfig` (array or fluent `ServerConfig::create()->set...()`): `schema`, `rootValue`, `context`, `fieldResolver`, `validationRules`, `queryBatching` (default `false`), `debugFlag`, `persistedQueryLoader`, `errorFormatter`, `errorsHandler`, `promiseAdapter`.
- `context` and `rootValue` can be callables: `fn (OperationParams $op, DocumentNode $doc, string $operationType)`. Gives per-operation context. Not in the docs table.
- `validationRules` can be a callable with the same signature. Documented use: skip validation for persisted queries.
- `persistedQueryLoader($queryId, OperationParams $params)`: returns a query string or a `DocumentNode`. The server does not store anything. It does not implement the APQ "PersistedQueryNotFound" register flow.
- Request errors are distinct classes (v15.10) under `GraphQL\Server\Exception`: `BatchedQueriesAreNotSupported`, `CannotParseJsonBody`, `CannotParseVariables`, `CannotReadBody`, `FailedToDetermineOperationType`, `GetMethodSupportsOnlyQueryOperation`, `HttpMethodNotSupported`, `InvalidOperationParameter`, `InvalidQueryIdParameter`, `InvalidQueryParameter`, `MissingContentTypeHeader`, `MissingQueryOrQueryIdParameter`, `PersistedQueriesAreNotSupported`, `UnexpectedContentType`. All extend `RequestError`.
- No GraphiQL or other IDE. No WebSocket or SSE. No file uploads (external `ecodev/graphql-upload` PSR-15 middleware).

## Security and limits

- `QueryComplexity($max)`: port of Sangria. Each field scores 1 plus its children. Field `complexity` config: `fn (int $childrenComplexity, array $args): int`. Args are coerced with the request variables. Fields skipped by `@skip`/`@include` score 0. `__schema` and everything under it scores 0 (v15.26). `getQueryComplexity()` returns the computed score after validation (v15.8). `getMaxQueryComplexity()`, `setMaxQueryComplexity()`, `getRawVariableValues()`, `setRawVariableValues()`.
- `QueryComplexity` checks every operation in the document, not only the selected one. It stops at the first operation over the limit. It does nothing when other validation errors exist.
- `QueryDepth($max)`: port of Sangria. Counts only fields with a selection set. Fragments are followed. A fragment cycle returns `max + 1`. Introspection fields count. `getMaxQueryDepth()`, `setMaxQueryDepth()`.
- `DisableIntrospection(DisableIntrospection::ENABLED)`: rejects `__schema` and `__type`. `__typename` is still allowed.
- All three extend `QuerySecurityRule`. They are in `DocumentValidator::securityRules()` and in the default rule set, disabled (`DISABLED = 0`). You enable them globally with `DocumentValidator::addRule(new QueryComplexity(100))` or per request in the rule list.
- Global state: rules are static singletons. `DocumentValidator::addRule()`, `removeRule()`, `getRule(QueryComplexity::class)`. `GraphQL::promiseToExecute()` writes the raw variables into the shared `QueryComplexity` instance before validation. I think this is unsafe in long-running servers (Swoole, RoadRunner) that run requests in parallel.
- `Parser::parse($source, ['recursionLimit' => 256])`: parser recursion cap, default 256, `0` disables it. Throws `SyntaxError` before PHP stack overflow (security advisory GHSA-r7cg-qjjm-xhqq, v15.32.3).
- No token limit yet (`maxTokens` is an open PR). No rate limiting. No cost directives (`@cost`, `@listSize`). No breadth or alias limits. No timeout. The docs say to use PHP `max_execution_time`, `memory_limit`, `post_max_size`.
- Field `visible` (bool or `fn (): bool`, v15.7): a hidden field is removed from `getFields()`, introspection and `FieldsOnCorrectType` validation. The executor treats it as undefined. The callable gets no arguments. So per-request visibility needs global state. Only fields, not types, args or enum values.
- `InvariantViolation` for schema errors. `Schema::assertValid()` and `Schema::validate()` do the full check. Not run by default, because it scans the whole schema. Docs say run it in CI or a build step.

## Errors

- Resolver exceptions become `"Internal server error"` unless they implement `ClientAware` with `isClientSafe(): true`. `FormattedError::setInternalErrorMessage()` changes the text.
- `ProvidesExtensions` interface: an exception with `getExtensions(): ?array` adds keys to `extensions`.
- `Error` (with `nodes`, `source`, `positions`, `path`, `previous`, `extensions`), `UserError`, `SyntaxError`, `InvariantViolation`, `SerializationError`, `CoercionError`. Client-safe messages from `parseValue` propagate (v15.18).
- `DebugFlag`: `NONE`, `INCLUDE_DEBUG_MESSAGE` (adds `extensions.debugMessage`), `INCLUDE_TRACE` (adds `extensions.trace`), `RETHROW_INTERNAL_EXCEPTIONS`, `RETHROW_UNSAFE_EXCEPTIONS`. Bit flags, passed to `toArray()` or `ServerConfig::debugFlag`.
- `errorFormatter(Error): array` and `errorsHandler(array $errors, callable $formatter): array`. The handler is the place for logging and filtering.
- `FormattedError::createFromException()`, `FormattedError::toSafeTrace()`, `FormattedError::printError()`.
- `Warning`: runtime warnings for config mistakes. `Warning::suppress()`, `Warning::enable()`, `Warning::setWarningHandler()`. IDs: `WARNING_ASSIGN`, `WARNING_CONFIG`, `WARNING_FULL_SCHEMA_SCAN`, `WARNING_CONFIG_DEPRECATION`, `WARNING_NOT_A_TYPE`.
- No error codes convention. No `onError`/error-propagation control. No semantic non-null.

## Type system and schema

- Types: `ObjectType`, `InterfaceType`, `UnionType`, `InputObjectType`, `EnumType`, `CustomScalarType`, `ScalarType` (subclass), `ListOfType`, `NonNull`. Helpers `Type::string()`, `Type::listOf()`, `Type::nonNull()`.
- Three definition styles: inline config arrays, class per type (`final class StoryType extends ObjectType`), SDL with `BuildSchema::build($sdl, $typeConfigDecorator)`.
- `typeConfigDecorator(array $config, TypeDefinitionNode $node, array $allNodes)` on `BuildSchema::build()`: adds resolvers, `resolveType` and so on to SDL types. Fourth arg `fieldConfigDecorator(array $fieldConfig, FieldDefinitionNode, $typeNode)` (v15.15) does the same per field. Options `assumeValid`, `assumeValidSDL`.
- Lazy loading: `SchemaConfig` option `typeLoader(string $name): ?Type`. Fields, interfaces, union members and arg types can all be callables. Root types `query`, `mutation`, `subscription` can be callables (v15.6). `BuildSchema` produces a lazy schema. Docs show a type registry pattern (`Types::load()`, `lazyByClassName()`). The loader must return the same instance every time.
- `SchemaConfig` options: `query`, `mutation`, `subscription`, `types`, `scalarOverrides`, `directives`, `typeLoader`, `assumeValid`, `description` (v15.30), `astNode`, `extensionASTNodes`. Fluent setters on `SchemaConfig::create()`.
- Per-schema built-in scalar overrides (v15.31): pass a `CustomScalarType` named `String`, `Int`, etc. in `types`, or in `scalarOverrides` to avoid scanning lazy `types`. Replaces the old global `Type::overrideStandardTypes()` (deprecated). `typeLoader` is never asked for built-in scalar names.
- `PhpEnumType(MyEnum::class, ?$name, ?$description)`: GraphQL enum from a native PHP enum. Values are enum cases. Inputs become enum instances. Outputs must be enum instances (backed enums serialize by name, v15.14). Description comes from the `#[Description]` attribute or the PHPDoc of the class and cases. `#[Deprecated(reason)]` attribute on cases. Customizable by subclassing (v15.17). SDL enums can also return native PHP enums (v15.14).
- `EnumType` shorthand: a list of names, or a map of name to value.
- `InputObjectType` `parseValue` (`fn (array $values): mixed`): turns the coerced input array into a value object. `isOneOf: true` for `@oneOf`.
- Deprecation on fields, args, input fields and enum values (`deprecationReason`). `#[Deprecated]` only for PHP enum cases.
- `CustomScalarType` with `serialize`, `parseValue`, `parseLiteral($node, $variables)`, `specifiedByURL` (v15.33).
- `Directive` with `name`, `description`, `locations`, `args`, `isRepeatable`. Custom directives have no execution effect. You read them from `ResolveInfo->fieldNodes` or use them in validation rules. No schema directive (`@key`-style) applied in code-first. Applied directives are not printed (open PR "Add code-first applied directives support for schema printing", branch `code-first-directives`, updated 2026-09-28).
- Built-in directives: `@include`, `@skip`, `@deprecated`, `@specifiedBy`, `@oneOf`. `Directive::builtInDirectives()`, `Directive::isBuiltInDirective()`. `GraphQL::getStandardDirectives()`.
- Custom metadata: every type and field keeps the raw config in public `$config`. You can put your own keys there. Documented.
- Field `complexity` and `visible` are stored on `FieldDefinition` (`complexityFn`, `isVisible()`).
- No Relay helpers in core (external `ivome/graphql-relay-php`). No connections, pagination, filtering, ordering, permissions or DataLoader in core. No federation.

## Resolver info and lookahead

- `ResolveInfo` properties: `fieldDefinition`, `fieldName`, `returnType`, `fieldNodes`, `parentType`, `path`, `unaliasedPath` (v15.12), `schema`, `fragments`, `rootValue`, `operation`, `variableValues`.
- `ResolveInfo::getFieldSelection(int $depth = 0)`: nested array of selected field names. Merges fragments. Docs show it for `SELECT` column pruning.
- `ResolveInfo::getFieldSelectionWithAliases(int $depth = 0)` (v15.19): keyed by field name then alias, with `args`, `type`, `selectionSet`, and `unions` for abstract types (v15.20).
- `ResolveInfo::lookAhead(['groupImplementorFields' => true])` returns a `QueryPlan`: `queryPlan()`, `getReferencedTypes()`, `hasType()`, `getReferencedFields()`, `hasField()`, `subFields($typename)`. Includes args per field. Not in the guides, only the class reference. Open PR "Keep implementor fields from abstract fragments in QueryPlan". Open PR "add directive-aware field selection" (would respect `@skip`/`@include`).

## Introspection and printing

- `Introspection::getIntrospectionQuery($options)`: `descriptions` (default true), `directiveIsRepeatable`, `schemaDescription`, `specifiedByURL`, `typeIsOneOf` (all default false). `Introspection::fromSchema($schema, $options)` turns them all on.
- `includeDeprecated` on `__Directive.args` and non-null with default `false` everywhere (v15.22).
- `SchemaPrinter::doPrint($schema, $options)`, `printType()`, `printIntrospectionSchema()`. Options `sortArguments`, `sortEnumValues`, `sortFields`, `sortInputFields`, `sortTypes`. Methods use `static::` so you can subclass to change printing.
- `Printer::doPrint($ast)`, `Printer::stripIgnoredCharacters($source)` (v15.38).
- Schema order is topological and follows user definition order (v15.0).

## Language and validation

- Parser options: `noLocation`, `allowLegacySDLEmptyFields`, `allowLegacySDLImplementsInterfaces`, `experimentalFragmentVariables`, `recursionLimit`. Invalid UTF-8 is rejected (v15.38).
- `AST::toArray($node)` and `AST::fromArray($array)`: serialize a parsed document to a PHP array. Docs use it to cache SDL as a `var_export` PHP file (opcache-friendly). `fromArray()` is lazy. Same works for query documents.
- `AST::astFromValue()`, `valueFromAST()`, `valueFromASTUntyped()`, `typeFromAST()`, `getOperationAST()`, `concatAST()`.
- `Visitor::visit()`, `visitInParallel()`, `visitWithTypeInfo()`, `Visitor::stop()`, `skipNode()`, `removeNode()`. A node can be replaced by a `NodeList` (v15.23).
- `DocumentValidator::validate($schema, $ast, $rules, $typeInfo)`, `allRules()`, `defaultRules()`, `securityRules()`, `sdlRules()`, `validateSDL()`, `assertValidSDL()`, `assertValidSDLExtension()`.
- `CustomValidationRule($name, callable $visitorFn)`: rule from a closure.
- Spec rules match graphql-js names without the `Rule` suffix (for example `OverlappingFieldsCanBeMerged`, `OneOfInputObjectsRule`). Full October 2021 spec compliance claimed since v15.33.1.
- No validation result cache (open PR "Cache result of validation", branch `validation-cache`).
- `BreakingChangesFinder::findBreakingChanges()` and `findDangerousChanges()`. `SchemaExtender::extend()`. `BuildClientSchema::build()`.

## Not supported

- Subscriptions (execution), `@defer`/`@stream`, file uploads, WebSocket and SSE transports, GraphiQL.
- Federation, schema stitching, Relay helpers, connections, filtering, ordering, DataLoader class, permissions or auth.
- HTTP status codes and GraphQL-over-HTTP media types in `StandardServer`.
- Middleware, extensions/plugin hooks, tracing, metrics, abort signals.
- Applied directives in code-first schemas and their printing.
- Token limit, alias or breadth limits, timeouts.
- Per-request visibility with request context (the `visible` callable gets no arguments).

## Upcoming and unreleased work

- `CHANGELOG.md` "Unreleased" section is empty.
- Open PRs (2026-10): `maxTokens` parser option, directive-aware field selection in `ResolveInfo`, computing query complexity without variable values, reporting `QueryComplexity` variable coercion errors instead of throwing, opt-in `ArrayAccess` property fallback in the default resolver, "Allow disabling return value validation to improve performance", "Cache result of validation", code-first applied directives in `SchemaPrinter`, `types` parameter for `BuildSchema`, "Make deprecated introspection optional for legacy servers", const vs non-const AST nodes, "Drop PHP 7.4", "Parse OperationParams into strongly typed data structures" (2021), "Make root query operation type optional" (2021), "Validate default values match argument type" (2021).
- Some of these branches are years old. I think the PHP 7.4 drop is what would start v16.

## Docs and code disagree

- `docs/security.md` says the introspection query has complexity 109. Since v15.26 the code scores `__schema` and its children as 0. So the introspection query scores close to 0.
- `docs/type-definitions/object-types.md` lists `visible` in the type configuration table. In code `visible` is a field option (`FieldDefinitionConfig`), not an `ObjectType` option. The field options table lists neither `visible` nor `argsMapper`.
- The docs give the `argsMapper` signature as `(array $args, FieldDefinition, FieldNode)`. The code passes a fourth argument, the context value.
- `docs/data-fetching.md` shows a default resolver that checks `isset(...)`. The code uses `Utils::extractKey()` with `??`. The behavior is the same.
- The `ServerConfig` table says `context` and `rootValue` are `mixed`. The code also accepts callables that get `(OperationParams, DocumentNode, string $operationType)`.
- The docs say `StandardServer` produces "a spec-compliant response". It always answers with `application/json` and never sets an HTTP status code.

## Sources

Docs (read from repo source `docs/`, site https://webonyx.github.io/graphql-php/):
- `executing-queries.md` (https://webonyx.github.io/graphql-php/executing-queries/)
- `security.md` (https://webonyx.github.io/graphql-php/security/)
- `data-fetching.md` (https://webonyx.github.io/graphql-php/data-fetching/)
- `error-handling.md` (https://webonyx.github.io/graphql-php/error-handling/)
- `schema-definition.md` (https://webonyx.github.io/graphql-php/schema-definition/)
- `schema-definition-language.md` (https://webonyx.github.io/graphql-php/schema-definition-language/)
- `complementary-tools.md` (https://webonyx.github.io/graphql-php/complementary-tools/)
- `type-definitions/*.md` (directives fully, others by headings plus object types, interfaces, inputs, scalars sections)
- `class-reference.md` (searched, not read end to end)
- `llms.txt` and `llms-full.txt`: 404.

Changelog:
- `CHANGELOG.md` (v15.0.0 to v15.38.0): https://github.com/webonyx/graphql-php/blob/master/CHANGELOG.md
- GitHub releases API for dates: https://github.com/webonyx/graphql-php/releases
- Open PRs and branches via GitHub API: https://github.com/webonyx/graphql-php/pulls

Repo (shallow clone in `/tmp/graphql-php`): https://github.com/webonyx/graphql-php `master` at `47e6ba3`.
Source files checked: `src/GraphQL.php`, `src/Executor/Executor.php`, `src/Executor/ReferenceExecutor.php`, `src/Executor/ScopedContext.php`, `src/Server/Helper.php`, `src/Server/ServerConfig.php`, `src/Server/OperationParams.php`, `src/Validator/Rules/QueryComplexity.php`, `src/Validator/Rules/QueryDepth.php`, `src/Validator/Rules/DisableIntrospection.php`, `src/Validator/DocumentValidator.php`, `src/Type/Definition/*` (config shapes, `ResolveInfo`, `QueryPlan`, `PhpEnumType`), `src/Type/SchemaConfig.php`, `src/Type/Introspection.php`, `src/Language/Parser.php`, `src/Utils/*`, `src/Error/*`, `composer.json`.
