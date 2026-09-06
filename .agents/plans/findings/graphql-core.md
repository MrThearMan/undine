# graphql-core findings

Versions checked: stable `3.2.13` (2026-09-27, tag `v3.2.13`, GraphQL.js 16.14.2, Python 3.7 to 3.15) and release candidate `3.3.0rc1` (2026-08-27, `main` branch, GraphQL.js 17.0.0rc0, Python 3.10 to 3.14).
Undine pins `graphql-core>=3.2.12` in `pyproject.toml`. That is the 3.2 line.
Package `graphql-core`. Import `graphql`. No runtime dependencies (3.3). Ships `py.typed`. Maintained by Christoph Zwerschke (@Cito).
It is a line-by-line port of GraphQL.js. It does not add features that GraphQL.js does not have, with a few Python exceptions (middleware, `out_name`, `out_type`, custom executor class, lazy descriptions). New features must go to GraphQL.js first (`docs/diffs.rst`).
Versioning is not SemVer. A GraphQL.js major maps to a graphql-core minor. Minor bumps can break the API. The README recommends `~= 3.2.0`.
Changelog is GitHub releases only. No `CHANGELOG.md`. Docs source is in the repo under `docs/`. Docs are thin: usage pages plus autodoc API pages. No `llms.txt`.

## Request entry points

- `graphql(schema, source, root_value, context_value, variable_values, operation_name, field_resolver, type_resolver, middleware, execution_context_class, is_awaitable)`: async parse + validate + execute (3.2).
- `graphql_sync(..., check_sync=False)`: sync version. Raises `RuntimeError` if a resolver returns an awaitable. `check_sync=True` checks every value.
- 3.3 `graphql()` adds `executor_class`, `is_async_iterable`, `hide_suggestions`, `abort_signal`, `no_location`, `max_tokens`, `experimental_fragment_arguments`, `rules`, `max_errors`, `harness`.
- 3.3 `GraphQLHarness(parse, validate, execute, subscribe)` and `default_harness` (`graphql/harness.py`): swap any phase for pre/post hooks with `default_harness._replace(execute=...)`. Not in 3.2.
- `graphql()` and `graphql_sync()` do not support `@defer`/`@stream` in either line.

## Execution

- `execute(schema, document, root_value, context_value, variable_values, operation_name, field_resolver, type_resolver, subscribe_field_resolver, max_coercion_errors=50, middleware, execution_context_class, is_awaitable)` (3.2). Returns `ExecutionResult` or an awaitable of it. Sync and async resolvers can mix.
- `execute_sync(...)`: guarantees sync completion. Added in 3.1.3.
- 3.3 `execute()` adds `enable_early_execution=False`, `executor_class`, `is_async_iterable`, `hide_suggestions`, `abort_signal`, `hooks`, and `**custom_context_args` (passed to a custom executor, 3.3.0a7).
- 3.3 `execute()` raises `GraphQLError` if the schema contains `@defer` or `@stream`. Use `experimental_execute_incrementally` for such schemas.
- `ExecutionResult(data, errors, extensions)`. `.formatted` returns `FormattedExecutionResult` TypedDict. The `extensions` key is supported in results.
- `default_field_resolver(source, info, **args)`: `source.get(name)` for any `Mapping`, else `getattr`. Calls the value with `(info, **args)` if it is callable. No case conversion.
- `default_type_resolver`: checks `__typename` key or attribute (inheritance aware), then `is_type_of` on each possible type.
- Resolver signature: `resolve(obj, info, **args)`. Arguments are keyword arguments. `GraphQLArgument(out_name=...)` renames them for Python.
- `GraphQLResolveInfo` (NamedTuple, generic over context in 3.3): `field_name`, `field_nodes`, `return_type`, `parent_type`, `path`, `schema`, `fragments`, `root_value`, `operation`, `variable_values`, `context`, `is_awaitable`. 3.3 adds `abort_signal` and `async_helpers` (`GraphQLResolveInfoHelpers(gather, track)`).
- Async: asyncio only. Sibling async fields run with `asyncio.gather`. Mutation root fields run serially. 3.3 cancels remaining sibling fields, list items and type resolvers when one raises (3.3.0a8).
- Async iterables as list values: a resolver for a list field can return an async iterable (experimental since 3.2.0rc4).
- `get_argument_values`, `get_directive_values`, `get_variable_values`: public helpers for custom executors. 3.3 adds `VariableValues` type.
- Error propagation: per spec, a null in a non-null field bubbles to the nearest nullable parent.
- 3.3 `@experimental_disableErrorPropagation` (`GraphQLDisableErrorPropagationDirective`, on `QUERY | MUTATION | SUBSCRIPTION`): turns off null bubbling for that operation. Opt-in: the schema must declare it. Not in 3.2.
- 3.3 cancellation: `AbortController`, `AbortSignal`, `AbortError` in `graphql.pyutils`. Pass `abort_signal=` to `execute`. An abort raises `AbortedGraphQLExecutionError` with `aborted_result` (3.3.0b0). Not in 3.2.
- 3.3 `ExecutionHooks(async_work_finished=...)` with `AsyncWorkFinishedInfo(executor)`: called when all tracked async work (also cancelled work) is done. Only hook in this NamedTuple. Not in 3.2.
- No dataloader. No query cost or complexity analysis. No depth limit for normal fields. No persisted queries. No caching of parsed or validated documents. No tracing or timing.

## Custom executor (`ExecutionContext` in 3.2, `Executor` in 3.3)

- 3.2: subclass `ExecutionContext` and pass `execution_context_class=`. `ExecutionContext.build(...)` returns the context or a list of `GraphQLError`.
- 3.2 overridable methods: `build_response`, `execute_operation`, `execute_fields_serially`, `execute_fields`, `build_resolve_info`, `execute_field`, `handle_field_error`, `complete_value`, `complete_list_value`, `complete_leaf_value`, `complete_abstract_value`, `ensure_valid_runtime_type`, `complete_object_value`, `collect_subfields`.
- 3.2 `subscribe()` does not accept `execution_context_class` or `middleware`.
- 3.3.0a14 renamed `ExecutionContext` to `Executor` with no alias. `execution_context_class` became `executor_class` everywhere. `build_per_event_execution_context` became `build_per_event_executor`.
- 3.3 `Executor(Generic[TContext])` adds: `execute_collected_root_fields`, `execute_root_grouped_field_set`, `complete_awaitable_value`, `complete_async_iterator_value`, `complete_iterable_value`, `complete_list_item_value`, `get_stream_usage`, `handle_stream`, `execute_collected_subfields`, abort helpers (`abort`, `with_abort_signal`), async tracking (`track_async_work`, `gather_async_work`).
- `is_awaitable` and `is_async_iterable` are overridable static methods or arguments. Useful for custom awaitable types.
- The Executor is internal-heavy. Method signatures change between minors. Subclassing is a supported but unstable extension point.

## Middleware (graphql-core only, not in GraphQL.js)

- `middleware=` on `execute`/`graphql`: a list of functions or objects with a `resolve` method, or a `MiddlewareManager(*middlewares)`.
- Signature: `def mw(next_, obj, info, **args)`. Wraps every field resolver, also the default resolver. The first middleware in the list is the innermost wrapper, I think (built with `functools.reduce`). I did not test the order.
- `MiddlewareManager` caches wrapped resolvers per resolver function.
- Middleware must handle awaitables itself. There is no async-aware wrapper.
- 3.3 applies middleware to subscriptions too (3.3.0a6). 3.2 does not.
- No operation-level lifecycle hooks (before parse, after validate, on result). Wrap `graphql()` or use the 3.3 `GraphQLHarness` for that.

## Subscriptions

- `subscribe(schema, document, root_value, context_value, variable_values, operation_name, field_resolver, subscribe_field_resolver, max_coercion_errors)` (3.2): `async def`. Returns `AsyncIterator[ExecutionResult]` or an `ExecutionResult` with errors.
- `create_source_event_stream(...)`: runs the `subscribe` resolver of the root field and returns the source stream.
- `GraphQLField(subscribe=...)`: async generator for the source stream. `resolve` maps each event.
- 3.2 uses `MapAsyncIterator`. 3.3 uses `map_async_iterable` (an async generator) and accepts custom async iterables (3.3.0a12).
- 3.3 `subscribe()` stays sync when possible (returns a value or an awaitable, 3.3.0a3). Adds `executor_class`, `middleware`, `hide_suggestions`, `enable_early_execution`. Raises for non-subscription operations (3.3.0b0).
- 3.3 composable pipeline: `Executor.build()`, then `create_source_event_stream(executor)`, then `map_source_to_response_event(executor, stream, root_selection_set_executor=execute_subscription_event)`. `RootSelectionSetExecutor` type alias. `per_event_executor` was removed in 3.3.0b1.
- `SimplePubSub` and `SimplePubSubIterator` in `graphql.pyutils`: in-memory pub/sub, used in tests. Not a production broker.
- No transport. No WebSocket or SSE protocol. The docs say you must maintain the channel yourself.

## Incremental delivery (`@defer`, `@stream`)

- Not supported in 3.2. There is no `@defer`, `@stream` or `experimental_execute_incrementally` in the 3.2 source.
- 3.3 only (first in 3.3.0a3, 2023-06). Still in alpha to rc churn. Rebuilt on a work-queue architecture in 3.3.0rc1.
- Opt-in: add `GraphQLDeferDirective` and `GraphQLStreamDirective` to `GraphQLSchema(directives=[*specified_directives, ...])`. They are not in `specified_directives`.
- `experimental_execute_incrementally(...)`: returns `ExecutionResult` or `ExperimentalIncrementalExecutionResults(initial_result, subsequent_results)`. `subsequent_results` is an async generator.
- Response format follows the newer spec draft (3.3.0a7): `InitialIncrementalExecutionResult(data, errors, pending, has_next, extensions)`, `SubsequentIncrementalExecutionResult(pending, incremental, completed, has_next, extensions)`, `PendingResult(id, path, label)`, `IncrementalDeferResult(data, id, sub_path, errors)`, `IncrementalStreamResult(items, id, sub_path, errors)`, `CompletedResult(id, errors)`. Each has a `Formatted*` TypedDict.
- `@defer(if: Boolean = true, label: String)` on `FRAGMENT_SPREAD | INLINE_FRAGMENT`. `@stream(if, label, initialCount: Int = 0)` on `FIELD`.
- `enable_early_execution=False` (default since 3.3.0a11): when true, deferred work starts before the initial payload is sent.
- Validation rules for it: `DeferStreamDirectiveOnRootField`, `DeferStreamDirectiveOnValidOperationsRule`, `DeferStreamDirectiveLabel`, `StreamDirectiveOnListField`. All are in `specified_rules` in 3.3.
- `@defer`/`@stream` are not allowed in subscriptions (`subscribe()` raises a field error).
- No HTTP multipart or SSE encoding. The server must serialize the payloads.

## Validation

- `validate(schema, document_ast, rules=None, max_errors=None, type_info=None)` (3.2). 3.3 drops `type_info` and adds `hide_suggestions=False`.
- `max_errors` defaults to 100. Then validation stops with "Too many validation errors". `ValidationAbortedError` is importable (3.3.0a7).
- `hide_suggestions` (3.3 only, also on `execute`): removes "Did you mean ...?" hints. Useful to hide schema details. Not in 3.2.
- Custom rules: subclass `ValidationRule` (has `ValidationContext`) or `ASTValidationRule` or `SDLValidationRule`. Rules are `Visitor` subclasses with `enter_<kind>`/`leave_<kind>` methods. Report with `self.report_error(GraphQLError(...))`.
- `ValidationContext`: `get_type`, `get_parent_type`, `get_input_type`, `get_parent_input_type`, `get_field_def`, `get_directive`, `get_argument`, `get_enum_value`, `get_fragment`, `get_fragment_spreads`, `get_recursively_referenced_fragments`, `get_variable_usages`, `get_recursive_variable_usages`. 3.3 adds fragment signature helpers.
- `specified_rules` (3.2, in order): `ExecutableDefinitionsRule`, `UniqueOperationNamesRule`, `LoneAnonymousOperationRule`, `SingleFieldSubscriptionsRule`, `KnownTypeNamesRule`, `FragmentsOnCompositeTypesRule`, `VariablesAreInputTypesRule`, `ScalarLeafsRule`, `FieldsOnCorrectTypeRule`, `UniqueFragmentNamesRule`, `KnownFragmentNamesRule`, `NoUnusedFragmentsRule`, `PossibleFragmentSpreadsRule`, `NoFragmentCyclesRule`, `UniqueVariableNamesRule`, `NoUndefinedVariablesRule`, `NoUnusedVariablesRule`, `KnownDirectivesRule`, `UniqueDirectivesPerLocationRule`, `KnownArgumentNamesRule`, `UniqueArgumentNamesRule`, `ValuesOfCorrectTypeRule`, `ProvidedRequiredArgumentsRule`, `VariablesInAllowedPositionRule`, `OverlappingFieldsCanBeMergedRule`, `UniqueInputFieldNamesRule`, plus `*recommended_rules`.
- 3.3 `specified_rules` adds `KnownOperationTypesRule` and the four defer/stream rules.
- `recommended_rules = (MaxIntrospectionDepthRule,)` in both lines (backported to 3.2.7). It is included in `specified_rules`, so it is on by default.
- `MaxIntrospectionDepthRule`: rejects `__schema`/`__type` queries that nest the list fields `fields`, `interfaces`, `possibleTypes` or `inputFields` 3 or more levels deep (`MAX_LIST_DEPTH = 3`). Follows fragments. `ofType` is not counted. Anti-DoS for introspection only.
- `OverlappingFieldsCanBeMergedRule` has a comparison budget `MAX_FIELD_COMPARISONS = 250_000` (module-level, settable). Added in 3.2.12 and 3.3.0rc1 for CVE-2026-75507.
- `specified_sdl_rules`: `LoneSchemaDefinitionRule`, `UniqueOperationTypesRule`, `UniqueTypeNamesRule`, `UniqueEnumValueNamesRule`, `UniqueFieldDefinitionNamesRule`, `UniqueArgumentDefinitionNamesRule`, `UniqueDirectiveNamesRule`, `KnownTypeNamesRule`, `KnownDirectivesRule`, `UniqueDirectivesPerLocationRule`, `PossibleTypeExtensionsRule`, `KnownArgumentNamesOnDirectivesRule`, `UniqueArgumentNamesRule`, `UniqueInputFieldNamesRule`, `ProvidedRequiredArgumentsOnDirectivesRule`.
- `validate_sdl`, `assert_valid_sdl`, `assert_valid_sdl_extension`: SDL document validation.
- Optional custom rules (`graphql.validation.rules.custom`, since 3.1.3): `NoSchemaIntrospectionCustomRule` (forbids `__schema` and `__type`), `NoDeprecatedCustomRule` (reports deprecated fields, arguments, input fields and enum values).
- No built-in query depth limit, query cost rule, alias limit, or field count limit. No rule for max directives per field.

## Parser and language

- `parse(source, no_location=False, max_tokens=None, ...)`. `max_tokens` limits parser work (3.2.3). Since 3.2.12 and 3.3.0rc1 comments count as tokens (CVE-2026-75508). `DocumentNode.token_count` exposes the count (3.2.9).
- 3.2 `parse(allow_legacy_fragment_variables=False)`. 3.3 replaces it with `experimental_fragment_arguments=False` (fragment arguments, `FragmentArgumentNode`).
- `experimental_directives_on_directive_definitions=False` on `parse` and `build_schema` (3.2.11 and 3.3.0b1). Adds `DirectiveExtensionNode`. Allows `@deprecated` on directive definitions.
- `parse_value`, `parse_const_value`, `parse_type`: parse fragments of the language.
- Schema coordinates: `parse_schema_coordinate`, `SchemaCoordinateNode` and subtypes, `resolve_schema_coordinate(schema, "Type.field(arg:)")`, `resolve_ast_schema_coordinate`. In both lines since 3.2.10.
- Descriptions on executable definitions (for example variable definitions) are supported (3.2.10).
- AST nodes are tuples in 3.2 and frozen dataclasses in 3.3 (3.3.0a12). Code that mutates AST nodes breaks on 3.3.
- `visit(root, visitor)`, `Visitor` (methods `enter`, `leave`, `enter_<kind>`, `leave_<kind>`), `ParallelVisitor`, `BREAK`, `SKIP`, `REMOVE`, `IDLE`, `VisitorKeyMap`.
- `print_ast(node)`: document to string. `print_location`, `print_source_location`: error excerpts.
- `Source(body, name, location_offset)`, `Lexer`, `Token`, `TokenKind`.
- Predicates: `is_definition_node`, `is_executable_definition_node`, `is_selection_node`, `is_value_node`, `is_const_value_node`, `is_type_node`, `is_type_system_definition_node`, `is_type_definition_node`, `is_type_system_extension_node`, `is_type_extension_node`. 3.3 adds `is_subscription_operation_definition_node`, `is_schema_coordinate_node`.
- Client controlled nullability (`!` and `?` on fields) was in 3.3.0a3. I did not find it in the 3.3.0rc1 source. I think it was removed with upstream.

## Type system

- Classes: `GraphQLSchema`, `GraphQLObjectType`, `GraphQLInterfaceType`, `GraphQLUnionType`, `GraphQLEnumType`, `GraphQLEnumValue`, `GraphQLInputObjectType`, `GraphQLInputField`, `GraphQLScalarType`, `GraphQLField`, `GraphQLArgument`, `GraphQLList`, `GraphQLNonNull`, `GraphQLDirective`.
- Every type, field, argument, enum value and directive takes `extensions: dict` and `ast_node`. Named types also take `extension_ast_nodes`. `extensions` is the main place for library metadata. It survives `lexicographic_sort_schema` (3.2.7).
- `GraphQLSchema(query, mutation, subscription, types, directives, description, extensions, ast_node, extension_ast_nodes, assume_valid)`. Methods: `get_type`, `get_root_type`, `get_possible_types`, `get_implementations`, `is_sub_type`, `get_directive`, `get_field`, `validation_errors`, `to_kwargs`. Supports `copy.deepcopy` and pickling (3.3.0a2, 3.2.7).
- Thunks: `fields`, `interfaces`, `types` and (3.2.7) enum `values` accept callables for recursive types.
- Shorthand: pass a type instead of `GraphQLField`/`GraphQLArgument`/`GraphQLInputField`. Pass a Python `Enum` or a dict as enum values.
- `GraphQLEnumType(names_as_values=False)`: `False` uses Enum member values, `True` uses names, `None` uses members (3.2.0rc5).
- `GraphQLInputObjectType(out_type=...)`: convert coerced input dicts to any Python type. graphql-core only.
- `GraphQLArgument(out_name=...)`, `GraphQLInputField(out_name=...)`: snake_case names for Python. graphql-core only.
- `@oneOf` input objects: `GraphQLInputObjectType(is_one_of=True)` and `GraphQLOneOfDirective`. In both lines (3.2.7, 3.3.0a7). Introspection `isOneOf`.
- `deprecation_reason` on fields, arguments, input fields and enum values (arguments and input fields since 3.1.5). 3.3.0b1 also allows it on directive definitions (experimental flag).
- `GraphQLScalarType(serialize, parse_value, parse_literal, specified_by_url, ...)` in 3.2.
- 3.3 scalar API renames: `coerce_output_value`, `coerce_input_value`, `coerce_input_literal`, `value_to_literal`. The old `serialize`, `parse_value`, `parse_literal` still work but are deprecated in 3.3.
- 3.3 `GraphQLDefaultInput(value, literal)` and `default=` on arguments and input fields: keeps the default as a literal for lossless printing. `default_value=` is deprecated in 3.3.
- 3.3 `Float` coercion raises for Python `int` values beyond 2^53 (3.3.0a14).
- Built-in scalars: `GraphQLInt`, `GraphQLFloat`, `GraphQLString`, `GraphQLBoolean`, `GraphQLID`. No date, JSON, UUID or other extra scalars.
- `specified_directives`: `@include`, `@skip`, `@deprecated`, `@specifiedBy`, `@oneOf`. `@defer`, `@stream`, `@experimental_disableErrorPropagation` exist in 3.3 but are opt-in.
- Lazy descriptions: `register_description(cls)` lets non-str objects (for example Django lazy translation strings) act as descriptions. graphql-core only.
- Assertions and predicates: `assert_*_type`, `is_*_type`, `get_named_type`, `get_nullable_type`, `is_input_type`, `is_output_type`, `is_leaf_type`, `is_composite_type`, `is_abstract_type`.
- `validate_schema(schema)` and `assert_valid_schema(schema)`: schema validation. Runs lazily on first `validate()` call.
- Introspection types (`introspection_types`, `TypeKind`, `SchemaMetaFieldDef`, `TypeMetaFieldDef`, `TypeNameMetaFieldDef`) are importable.
- No schema visibility or per-request schema filtering. No code-first class layer. No name case conversion (only `pyutils.snake_to_camel` and `camel_to_snake` helpers).

## Utilities (`graphql.utilities`)

- `build_schema(sdl, assume_valid, assume_valid_sdl, no_location, ...)` and `build_ast_schema(document)`: SDL to schema. No resolvers from SDL.
- `extend_schema(schema, document, assume_valid, assume_valid_sdl)`: apply `extend type` and new types. Returns a new schema.
- `build_client_schema(introspection)`: schema from an introspection result.
- `get_introspection_query(descriptions, specified_by_url, directive_is_repeatable, schema_description, input_value_deprecation, experimental_directive_deprecation, one_of/input_object_one_of, type_depth=9)`. The `one_of` flag is named `input_object_one_of` in 3.2. `type_depth` since 3.2.11.
- `introspection_from_schema(schema, ...)`: introspection dict without running a query. `IntrospectionQuery` TypedDicts for the result.
- `print_schema(schema)`, `print_introspection_schema(schema)`, `print_type(type)`, `print_value(value, type)`. 3.3 adds `print_directive`. `print_schema` prints `@oneOf` (3.3.0a8).
- `lexicographic_sort_schema(schema)`: sort types, fields, args and enum values by name. Keeps descriptions and extensions (3.2.9).
- `find_breaking_changes(old, new)`, `find_dangerous_changes(old, new)`: returns `BreakingChange`/`DangerousChange` with `BreakingChangeType`/`DangerousChangeType`.
- 3.3 `find_schema_changes(old, new)` also returns `SafeChange` with `SafeChangeType`. `SchemaChange` type.
- `TypeInfo(schema)` and `TypeInfoVisitor(type_info, visitor)`: track the current type, field, argument and directive while visiting a document.
- `separate_operations(document)`: split a document into one document per operation, with only the needed fragments.
- `concat_ast(documents)`: merge documents.
- `strip_ignored_characters(source)`: minify a document.
- `get_operation_ast(document, operation_name)`. 3.2 also has `get_operation_root_type` (removed in 3.3).
- `type_from_ast`, `value_from_ast`, `value_from_ast_untyped`, `ast_from_value`, `coerce_input_value`, `ast_to_dict`.
- 3.3 adds `coerce_input_literal`, `replace_variables`, `value_to_literal`, `validate_input_value`, `validate_input_literal`, `get_default_value_ast`.
- `is_equal_type`, `is_type_sub_type_of`, `do_types_overlap`: type comparators.
- 3.2 has `assert_valid_name` and `is_valid_name_error`. Removed in 3.3 (`assert_name` in `graphql.type`).
- No SDL-from-Python-types generation, no mock server, no schema stitching, no federation helpers.

## Errors

- `GraphQLError(message, nodes, source, positions, path, original_error, extensions)`. Attributes: `locations`, `path`, `nodes`, `source`, `positions`, `original_error`, `extensions`. Hashable.
- `.formatted` returns a `GraphQLFormattedError` TypedDict (`message`, `locations`, `path`, `extensions`).
- 3.3.0b2 adds `cause=` and `.cause` (also set as `__cause__`). `original_error` is deprecated in 3.3.
- `located_error(error, nodes, path)`: wraps any exception raised in a resolver into a `GraphQLError` with location and path. Does not double-wrap (3.1.3).
- `GraphQLSyntaxError`: parse errors.
- Resolver exceptions become field errors in `result.errors`. Data is kept for the rest of the tree. No error masking. The server must hide internal messages itself.
- `extensions` from `original_error.extensions` are merged into the error.
- `max_coercion_errors=50`: limits variable coercion errors.
- No error codes, no error classes by category, no error formatter hook.

## pyutils (public helpers)

- `Undefined` sentinel (not an exception since 3.3.0a3). Used for absent arguments and defaults.
- `Path`, `print_path_list`, `inspect`, `did_you_mean`, `suggestion_list`, `natural_comparison_key`, `group_by`, `identity_func`, `cached_property`, `is_awaitable`, `is_iterable`, `is_collection`.
- 3.3 adds `AbortController`, `AbortSignal`, `AbortError`, `gather_with_cancel`, `async_reduce`, `RefMap`, `RefSet`, `and_list`, `or_list`.
- `snake_to_camel`, `camel_to_snake`.

## 3.2 vs 3.3 summary

- Python: 3.2 supports 3.7 to 3.15. 3.3 supports 3.10 to 3.14.
- 3.3 is still a release candidate (rc1). 3.2 gets security and bug fixes. Both got the 2026-08 security fixes.
- New in 3.3: `@defer`/`@stream` with `experimental_execute_incrementally`, `Executor` (renamed), `executor_class`, abort signals, `ExecutionHooks`, `GraphQLHarness`, `hide_suggestions`, `@experimental_disableErrorPropagation`, fragment arguments, `find_schema_changes` with safe changes, new scalar coercion API, `GraphQLDefaultInput`, `GraphQLError.cause`, middleware on subscriptions, sync-when-possible `subscribe`, generic `GraphQLResolveInfo[TContext]`, frozen dataclass AST nodes.
- Removed or renamed in 3.3: `ExecutionContext`, `execution_context_class`, `validate(type_info=)`, `parse(allow_legacy_fragment_variables=)`, `get_operation_root_type`, `assert_valid_name`, `is_valid_name_error`, `per_event_executor`, `FrozenList`/`FrozenDict`.
- Deprecated in 3.3: scalar `serialize`/`parse_value`/`parse_literal`, `default_value=`, `GraphQLError.original_error`.
- Backported to 3.2: `@oneOf`, `recommended_rules` with `MaxIntrospectionDepthRule`, enum values thunk, pickled schema fixes, schema coordinates, `max_tokens`, `type_depth`, directives on directive definitions, `MAX_FIELD_COMPARISONS`.

## Sources

Docs:
- https://graphql-core-3.readthedocs.io/en/latest/ (checked it exists. Read the same content from the repo `docs/` source)
- `docs/intro.rst`, `docs/diffs.rst`, `docs/usage/*.rst` (schema, resolvers, queries, sdl, methods, introspection, parser, extension, validator, other), `docs/modules/*.rst`
- `README.md`
- `/llms.txt` and `/en/latest/llms-full.txt` return 404.

Changelog:
- GitHub releases via `gh api repos/graphql-python/graphql-core/releases` (v1.0.0rc2 to v3.3.0rc1 and v3.2.13): https://github.com/graphql-python/graphql-core/releases

Repos (shallow clones in `/tmp`):
- https://github.com/graphql-python/graphql-core `main` at 3.3.0rc1 (`/tmp/graphql-core`)
- same repo, tag `v3.2.13` (`/tmp/graphql-core-3.2`)

Source files checked:
- `src/graphql/graphql.py`, `src/graphql/harness.py`, `src/graphql/version.py`, `pyproject.toml`
- `src/graphql/execution/__init__.py`, `execute.py`, `executor.py`, `executor_throwing_on_incremental.py`, `middleware.py`, `types.py`, `incremental/` (3.3)
- `src/graphql/execution/execute.py`, `subscribe.py` (3.2)
- `src/graphql/validation/specified_rules.py`, `validate.py`, `validation_context.py`, `rules/__init__.py`, `rules/max_introspection_depth_rule.py`, `rules/overlapping_fields_can_be_merged.py`, `rules/custom/*.py` (both lines)
- `src/graphql/type/definition.py`, `directives.py`, `schema.py`, `scalars.py`, `validate.py`
- `src/graphql/utilities/__init__.py`, `build_ast_schema.py`, `extend_schema.py`, `build_client_schema.py`, `get_introspection_query.py`, `introspection_from_schema.py`, `print_schema.py`, `find_schema_changes.py`, `type_info.py` (both lines where present)
- `src/graphql/error/graphql_error.py`, `src/graphql/language/__init__.py`, `parser.py`, `src/graphql/pyutils/__init__.py`, `abort_signal.py`
- `tests/execution/test_error_propagation.py`, `tests/execution/test_executor_throwing_on_incremental.py`
