# Tartiflette findings

Version checked: 1.4.1 (PyPI, 2021-11-15, latest release). Last commit on `master`: 2022-01-20 (`421c1e9`, drop Python 3.6). Last push to GitHub: 2023-09. Not archived, but effectively unmaintained. No release in almost 5 years.
Package `tartiflette`. Import `tartiflette`. Depends on `cffi` and `lark>=1.0`. Needs `cmake` to build the bundled C parser `libgraphqlparser` unless a prebuilt wheel exists (Linux and macOS `x86_64` only, since 1.4.0). Python 3.7 to 3.10. Ships `py.typed` (1.3.2).
Built by Dailymotion. Targets the June 2018 GraphQL spec. SDL-first. Own engine. Does not use graphql-core. Async only.
Public API is small: `create_engine`, `Engine`, `Resolver`, `TypeResolver`, `Subscription`, `Scalar`, `Directive`, `TartifletteError` (`tartiflette/__init__.py`).
Docs source is in the repo under `docs/`. The site https://tartiflette.io renders it. No `llms.txt`.

## Engine and schema building

- `await create_engine(sdl, schema_name="default", error_coercer=None, custom_default_resolver=None, custom_default_type_resolver=None, modules=None, query_cache_decorator=UNDEFINED_VALUE, json_loader=None, custom_default_arguments_coercer=None, coerce_list_concurrently=None, coerce_parent_concurrently=None, sdl_file_encoding=None)`: async factory. Returns a built `Engine`.
- `sdl` can be a raw SDL string, a file path, a list of file paths, or a directory. A directory loads every `.graphql` and `.sdl` file in lexicographic order and concatenates them.
- `Engine(...)` plus `await engine.cook(...)`: two-step build. `cook()` is async on purpose, so building can fetch SDL or metadata from remote services. `cook()` is a no-op after the first call (0.12.0).
- The build step is called "baking" internally (`SchemaBakery.bake`, `Resolver.bake`, `Directive.bake`). Precomputes coercers for every type and precomputes introspection data at build time for speed (1.0.0).
- `modules=[...]`: list of module paths to import at build. Removes the need for manual imports of decorated code. Items can be `{"name": "pkg.mod", "config": {...}}` to pass config to the module.
- Module "bake" protocol: if an imported module has a `bake(schema_name, config)` function (sync or async), it is called and the returned string is appended to the SDL. This is how plugins ship both SDL and code (`tartiflette/engine.py` `_bake_module`). Built-in directives and scalars use the same protocol and are only added if the user did not define them.
- `SchemaRegistry`: global registry keyed by `schema_name`. Every decorator takes `schema_name="default"`. Several engines with different schemas can live in one process. `SchemaRegistry.clean()` wipes all registered schemas (0.12.0, for tests).
- Decorators register into the global registry at import time. The engine links them to SDL at build time. Unknown names raise `UnknownFieldDefinition`, `UnknownDirectiveDefinition`, `UnknownScalarDefinition`, `UnknownTypeDefinition`.
- SDL `extend` syntax supported for all type kinds and `schema` (1.0.0). Extensions are validated at build.
- Build-time SDL validation (`GraphQLSchema._validate`): named types exist, root types exist, objects follow interfaces (covariant field types and arguments, 1.2.0), non-empty objects, union members valid, all scalars implemented, unique enum values, argument and input field types are input types, directive implementations match definitions. Raises `GraphQLSchemaError`.
- SDL is parsed with `lark` (`tartiflette/language/parsers/lark`). Queries are parsed with the C library `libgraphqlparser` through CFFI. `LIBGRAPHQLPARSER_DIR` env var overrides the `.so` location (1.3.3).
- `json_loader`: replace `json.loads` used to read the C parser's JSON AST (for example `rapidjson.loads`).
- `sdl_file_encoding`: encoding for SDL files (1.4.1).
- No code-first API. No Python type to GraphQL type mapping. No schema export (SDL is the source).
- No interfaces implementing interfaces (June 2018 grammar only). No `repeatable` directives. No `@specifiedBy`. No `@oneOf`. I did not find any of these in the grammar or source.

## Resolvers

- `@Resolver("Type.field", schema_name="default", type_resolver=None, arguments_coercer=None, list_concurrently=None, parent_concurrently=None)`. `concurrently` was renamed to `list_concurrently` in 1.4.0.
- Resolver signature: `async def fn(parent, args, ctx, info)`. Must be a coroutine. Sync resolvers raise `NonAwaitableResolver` at decoration.
- `args` is a dict. Arguments the client did not send are absent from the dict (not `None`). Strong null vs absent distinction since 1.0.0. `UNDEFINED_VALUE` sentinel in `tartiflette.constants`.
- `info` (`ResolveInfo`): `field_name`, `field_nodes`, `return_type`, `parent_type`, `path`, `schema`, `fragments`, `root_value`, `operation`, `variable_values`, `is_introspection`.
- Default resolver: `getattr(parent, field_name)`, then `parent[field_name]`, else `None`. Replace with `custom_default_resolver`. The docs suggest this for snake_case to camelCase mapping. No built-in name conversion.
- Concurrency control: sibling fields and list items are resolved with `asyncio.gather`. `coerce_list_concurrently` (engine) and `list_concurrently` (per field) control list item concurrency (1.3.0). `coerce_parent_concurrently` and `parent_concurrently` control sibling field concurrency (1.4.0). Useful when resolvers share a non-concurrency-safe resource such as one DB connection.
- `custom_default_arguments_coercer` (engine) and `arguments_coercer` (per `@Resolver`, `@Subscription`, `@Directive`): replace how argument coroutines are awaited. Default uses `asyncio.gather`. A sequential coercer avoids creating many asyncio tasks (1.2.0).
- Mutations use `@Resolver("Mutation.x")`. No special mutation API. Top-level mutation fields run serially per spec. I did not verify this in source.
- No dataloader. No N+1 tooling. No ORM integration. No Django integration.

## Abstract types

- Type resolution order: `type_resolver=` on `@Resolver`, then `@TypeResolver("AbstractType")`, then `custom_default_type_resolver` on the engine (1.0.0).
- Type resolver signature: `(result, ctx, info, abstract_type)`. Returns a type name.
- Default type resolver: `result["_typename"]`, then `result._typename`, then `result.__class__.__name__`.

## Scalars

- `@Scalar("Name")` on a class with `coerce_output(value)`, `coerce_input(value)` and `parse_literal(ast)`. `parse_literal` returns `UNDEFINED_VALUE` for invalid literals.
- Built-in scalars: `ID`, `Int`, `String`, `Float`, `Boolean`, plus `Date`, `Time`, `DateTime` (ISO format). The extra three are always added unless you define them.
- Built-in scalars can be overridden by declaring `scalar Int` in SDL and decorating a class with `@Scalar("Int")`.
- Plugin `tartiflette-plugin-scalars` adds more scalars. Listed as "In Progress" in the docs.

## Directives and hooks (main feature)

- `@Directive("name", schema_name="default", arguments_coercer=None)` on a class (instantiated once) or instance. The SDL must declare the directive. Directive args arrive as the `directive_args` dict.
- Every hook is middleware style: it gets `next_directive` (or `next_resolver`) and must call it. It can change inputs, change outputs, skip the call, or raise. Multiple directives chain. The first directive in SDL order is the outermost wrapper (`tartiflette/utils/directives.py` `wraps_with_directives` iterates `reversed`).
- Documented hooks:
- `on_field_execution(directive_args, next_resolver, parent, args, ctx, info)`: wraps a field resolver. Use for auth, rate limits, remote resolution, caching. Runs for directives on `FIELD_DEFINITION` in SDL and on `FIELD` in the query document. Query directive args can use variables.
- `on_argument_execution(directive_args, next_directive, parent_node, argument_definition_node, argument_node, value, ctx)`: wraps coercion of one argument. Use for validation or access checks on arguments. `argument_node` is `None` when the client did not send it (1.2.0).
- `on_post_input_coercion(directive_args, next_directive, parent_node, value, ctx)`: runs after an input value is coerced. Triggered by directives on `SCALAR`, `ENUM`, `ENUM_VALUE`, `INPUT_OBJECT`, `INPUT_FIELD_DEFINITION`. Runs once per variable value, not per use (1.0.0). A failure here aborts the whole operation.
- `on_pre_output_coercion(directive_args, next_directive, value, ctx, info)`: runs on a resolved value before output coercion. Triggered by directives on `OBJECT`, `SCALAR`, `ENUM`, `ENUM_VALUE`, `UNION`, `INTERFACE`. Union and interface hooks run before the concrete object hooks (1.2.1). Enum value hooks run before enum type hooks.
- `on_introspection(directive_args, next_directive, introspected_element, ctx, info)`: wraps an element in introspection results. Return `None` to hide it. This gives per-request "dynamic introspection" (schema hiding per viewer).
- `on_schema_execution(directive_args, next_directive, schema, document, parsing_errors, operation_name, context, variables, initial_value)`: wraps the whole query or mutation. Triggered by a directive on `schema`. Can change `initial_value` and add keys such as `extensions` to the result (1.1.0). This is the operation-level middleware hook.
- `on_schema_subscription(...)`: same as above for subscriptions. It is an async generator that wraps the result stream (1.1.0).
- Undocumented hooks found in source (`tartiflette/schema/schema.py` `_IMPLEMENTABLE_DIRECTIVE_FUNCTION_HOOKS`):
- `on_post_bake(directive_args, next_directive, element)`: runs once at build time on a schema element. Used by built-in `@deprecated` to set `isDeprecated` and `deprecationReason`. Allows build-time schema transforms from custom directives.
- `on_field_collection(directive_args, next_directive, field_node, ctx)`, `on_fragment_spread_collection(...)`, `on_inline_fragment_collection(...)`: run while collecting selections. Raise `SkipCollection` to drop the node. Used by built-in `@skip` and `@include`. Custom directives can implement conditional selection logic with the request context.
- Hook execution order per field is documented in `docs/api/directive.md` with a diagram (`docs/assets/execution-order-v1-1-0.png`).
- Built-in directives: `@deprecated(reason)` on `FIELD_DEFINITION | ENUM_VALUE`, `@skip(if)`, `@include(if)`, `@nonIntrospectable` on `FIELD_DEFINITION | SCHEMA`. `@nonIntrospectable` on `schema` disables introspection for the whole schema (1.3.1).
- `@deprecated` is not supported on arguments or input fields (June 2018 spec).
- Directives are the only extension point. There is no separate middleware, extension, or plugin class API.
- Directive instances are singletons. State on `self` is shared across requests. The rate limit tutorial relies on this.

## Plugins

- A plugin is a Python package with a `bake(schema_name, config)` function that registers `@Directive`, `@Scalar` or `@Resolver` code and returns extra SDL. Loaded with `modules=[{"name": "tartiflette_plugin_x", "config": {...}}]`.
- Naming convention: PyPI `tartiflette-plugin-*`, import `tartiflette_plugin_*`.
- `cookiecutter-tartiflette-plugin` template exists.
- Curated list in docs has only two plugins: `tartiflette-plugin-scalars` and `tartiflette-plugin-time-it` (logs field timing). I think other community plugins exist outside the docs list, but I did not check.

## Execution API

- `await engine.execute(query, operation_name=None, context=None, variables=None, initial_value=None)`: returns a result dict. `query` can be `str` or `bytes`.
- `engine.subscribe(...)`: same parameters. Returns an async iterator of result dicts.
- `context` can be any object. It is passed as `ctx`.
- `initial_value`: root value for root fields.
- Parse and validate results are cached with `functools.lru_cache(maxsize=512)` by default. `query_cache_decorator` replaces the decorator. `None` disables caching (1.2.0).
- Variables are fully coerced before execution. A variable error stops the whole operation (1.0.0).
- No persisted queries. No query batching in the engine. No `@defer` or `@stream`. No incremental delivery.

## Validation and query cost

- Built-in query validation rules follow the June 2018 spec. List in `docs/graphql-query-rules-supported.md`. Rules live in `tartiflette/language/validators/query/`.
- `OverlappingFieldsCanBeMerged` is not implemented (`docs/graphql-query-rules-missing.md`).
- No API to add custom validation rules. I think validators run inside parsing with no hook, based on `execution/collect.py` `parse_and_validate_query`.
- No query depth limit. No complexity or cost analysis. No max tokens or alias limits.
- Introspection can only be disabled with `@nonIntrospectable` on `schema`, or filtered per request with `on_introspection`.

## Errors

- `TartifletteError(message, path=None, locations=None, user_message=None, more_info=None, extensions=None, original_error=None)`: subclass it and set `extensions` to add fields such as `code`. `user_message` replaces `message` in the output.
- Any other exception is wrapped into a `TartifletteError`. The message is copied. The original is kept in `original_error`.
- `coerce_value(path=, locations=)` on an exception class controls its output shape.
- `error_coercer=async fn(exception, error_dict) -> error_dict`: global hook for all errors. Use to log or hide internal messages. Must be async (1.0.0).
- `MultipleException` aggregates several errors, for example from argument coercion.
- Build errors: `GraphQLSchemaError`, `GraphQLSyntaxError`, `ImproperlyConfigured` subclasses (`NonCallable`, `NonCoroutine`, `NonAwaitableResolver`, `NonAsyncGeneratorSubscription`, `NotSubscriptionField`, `MissingImplementation`), `RedefinedImplementation`.
- No built-in error codes. No result masking by default.

## Subscriptions

- `@Subscription("Subscription.field", schema_name="default", arguments_coercer=None, list_concurrently=None, parent_concurrently=None)` on an async generator. Non-generators raise `NonAsyncGeneratorSubscription`.
- A `@Resolver` on the same subscription field shapes each yielded event. Without it, yielded values go through the default resolver (no wrapping by field name since 1.0.0).
- No pub/sub, broadcast, or channel layer. The docs say to bring your own (Redis, NATS, Google Pub/Sub). Roadmap v2 samples for these were never written.
- Transport is only in the HTTP integrations below.

## HTTP layer: tartiflette-aiohttp

Version 1.4.1 (PyPI, 2021-11-15). Last commit 2022-09. Requires `aiohttp>=3.5.4,<3.9.0`, so it does not install with current aiohttp.
- `register_graphql_handlers(app, engine_sdl=None, engine_schema_name="default", executor_context=None, executor_http_endpoint="/graphql", executor_http_methods=None, engine=None, subscription_ws_endpoint=None, subscription_keep_alive_interval=None, graphiql_enabled=False, graphiql_options=None, engine_modules=None, context_factory=None, response_formatter=None)`.
- Engine is cooked on aiohttp startup.
- GET and POST. POST accepts JSON only. `variables` may be a JSON string. Bad requests return a GraphQL error body with HTTP 200 (I think, based on `_handler.py`).
- Context: shallow copy of `executor_context` plus `req` (aiohttp request) and `app`. `context_factory` is an `asynccontextmanager` `(context, req)` so per-request setup and teardown is possible (1.3.0).
- `set_response_headers({...})`: set HTTP response headers from inside a resolver. Uses a `ContextVar` (1.2.0).
- `response_formatter(req, data, ctx) -> web.Response`: full control of the HTTP response (1.3.0).
- WebSocket subscriptions with the legacy `graphql-ws` (subscriptions-transport-ws) protocol only. `subscription_keep_alive_interval` sends `ka` messages (1.4.0). No `graphql-transport-ws` protocol.
- GraphiQL: `graphiql_enabled=True`. `graphiql_options` keys: `endpoint` (default `/graphiql`), `default_query`, `default_variables`, `default_headers`.
- No file uploads. No batching. No SSE. No CSRF handling.

## HTTP layer: tartiflette-asgi

Version 0.12.0 (PyPI, 2022-05-20). Maintained by Florimond Manca. Requires `starlette<1.0` and `tartiflette<1.5`.
- `TartifletteApp(*, engine=None, sdl=None, graphiql=True, path="/", subscriptions=None, context=None, schema_name="default")`: ASGI3 app. Can be mounted in any ASGI framework. Needs the lifespan startup event (`app.startup`) to cook the engine.
- Query from URL query string (GET, POST), JSON body, or raw `application/graphql` body. Variables in query params since 0.12.0.
- HTTP errors: 400 no query, 404 wrong path, 405 bad method, 415 bad content type.
- Context: copy of `context` plus `req` (Starlette `Request`). No per-request context factory.
- `GraphiQL(path=, default_headers=, default_query=, default_variables=, template=)`: custom HTML template supported.
- `Subscriptions(path="/subscriptions")`: WebSocket subscriptions with the legacy subscriptions-transport-ws protocol.
- No file uploads. No batching. No SSE.

## Not supported or not in scope

- Code-first schema definition. Sync resolvers. Sync execution.
- Dataloaders, ORM integration, Django integration, query optimizer.
- Relay (connections, `Node`, global IDs). Planned in roadmap v2 as "built-in directives to handle the Relay specification". Never done.
- Federation. Schema stitching.
- File uploads (multipart spec).
- Persisted queries. Query batching. `@defer` and `@stream`.
- Depth limits, complexity limits, custom validation rules, `OverlappingFieldsCanBeMerged`.
- Built-in permission or auth API (docs show `@auth` directives written by hand).
- Built-in input validation directives such as `@maxLength`. Planned in roadmap v2. Never done.
- Tracing, OpenTelemetry, Apollo tracing. Only the `time-it` plugin.
- Testing helpers. Only the `SchemaRegistry.clean()` reset and a `ttftt_engine` pytest marker used internally.
- Name case conversion.
- `graphql-transport-ws` protocol and SSE subscriptions.

## Ideas relevant to Undine

- Directive hooks at every phase (build, collection, argument coercion, input coercion, field execution, output coercion, introspection, operation). One uniform middleware shape (`next_*` callable) for all of them.
- Directives on types (`OBJECT`, `SCALAR`, `ENUM`, `INPUT_OBJECT`) that run on every value of that type, not just on fields.
- Per-request dynamic introspection through `on_introspection`. This hides schema parts per viewer at runtime.
- Custom selection-collection directives (`on_field_collection` with `SkipCollection`), like a user-defined `@skip`.
- Opt-out of concurrent sibling and list resolution per field (`parent_concurrently`, `list_concurrently`).
- Pluggable query parse cache (`query_cache_decorator`).
- Plugin packages that ship SDL plus code, loaded by module path with config.
- Setting HTTP response headers from a resolver (`set_response_headers`).

## Sources

Docs (read from the repo `docs/` directory, rendered at https://tartiflette.io/docs):
- `docs/welcome/what-is-tartiflette.md`
- `docs/api/engine.md` (https://tartiflette.io/docs/api/engine)
- `docs/api/directive.md` (https://tartiflette.io/docs/api/directive)
- `docs/api/error-handling.md`, `execution.md`, `resolver.md`, `scalar.md`, `schema-registry.md`, `subscription.md`, `type-resolver.md`
- `docs/plugins/introduction.md`, `create-a-plugin.md`, `use-a-plugin.md`, `currated-list.md`
- `docs/graphql-query-rules-supported.md`, `docs/graphql-query-rules-missing.md`
- `docs/roadmaps/milestone-1.md`, `milestone-2.md`
- `docs/migration-guides/migration-guide-0-0-to-1-0.md`
- `docs/tutorial/extend-with-directives.md`, `rate-limit-fields-with-directives.md`, `dynamic-introspection.md` (other tutorial pages only skimmed by title)
- https://tartiflette.io/llms.txt and https://tartiflette.io/llms-full.txt return 404.

Changelog:
- `CHANGELOG.md` and `changelogs/*.md` (0.1.4 to 1.4.1 and `next.md`)
- tartiflette-aiohttp `changelogs/1.1.0.md` to `1.4.1.md`
- tartiflette-asgi `CHANGELOG.md`
- PyPI: https://pypi.org/pypi/tartiflette/json, https://pypi.org/pypi/tartiflette-aiohttp/json, https://pypi.org/pypi/tartiflette-asgi/json
- GitHub API for repo status: https://api.github.com/repos/tartiflette/tartiflette

Repos (shallow clones in `/tmp`):
- https://github.com/tartiflette/tartiflette
- https://github.com/tartiflette/tartiflette-aiohttp
- https://github.com/tartiflette/tartiflette-asgi

Source files checked:
- `tartiflette/__init__.py`, `setup.cfg`, `setup.py`
- `tartiflette/engine.py`
- `tartiflette/directive/directive.py`, `tartiflette/directive/builtins/*.py`
- `tartiflette/schema/schema.py` (hook list, validation methods)
- `tartiflette/utils/directives.py` (`wraps_with_directives`)
- `tartiflette/execution/collect.py`, `tartiflette/resolver/factory.py`, `tartiflette/resolver/resolver.py`, `tartiflette/resolver/default.py`
- `tartiflette/types/exceptions/tartiflette.py`
- `tartiflette/language/parsers/lark/graphql_sdl_grammar.lark`, `tartiflette/language/parsers/libgraphqlparser/parser.py`
- `tartiflette/language/validators/query/`
- tartiflette-aiohttp `README.md`, `tartiflette_aiohttp/__init__.py`, `_handler.py`, `_context_factory.py`, `_constants.py`, `_subscription_ws_handler.py`
- tartiflette-asgi `docs/api.md`, `docs/usage.md`, `docs/faq.md`, `src/tartiflette_asgi/__init__.py`, `_app.py`
