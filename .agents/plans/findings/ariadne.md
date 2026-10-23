# Ariadne findings

Version checked: 1.1.0 (PyPI, 2026-06-15, latest release). Last commit on `main`: 2026-08-31 (`d123826`, benchmark results only).
Package `ariadne`. Import `ariadne`. Depends on `graphql-core>=3.2.0`, `starlette>0.17,<2.0`, `typing-extensions`. Python 3.10 to 3.14. Ships `py.typed`. Type-checked with `ty` (replaced mypy in 0.29). `tests_mypy/` checks typing of enums, inputs and middlewares.
Extras: `asgi-file-uploads` (`python-multipart`), `sqlalchemy` (`sqlalchemy>=2.0`, `aiodataloader`), `telemetry` (`opentelemetry-api`).
Schema-first. The schema is SDL text. Python code is "bound" to SDL types by name through bindable objects. Not tied to any web framework. Ships its own ASGI app (Starlette based) and WSGI app.
Maintained by Mirumee. 1.0.0 came out 2026-03-16 after 7 years of 0.x. `CHANGELOG.md` in the repo only holds unreleased changes. Released notes are on GitHub releases.
The docs source is in the main repo under `docs/` (moved from `mirumee/ariadne-website` in 0.28). `llms.txt` is at the repo root.

## SDL-first model and ergonomics

- Schema is written in SDL strings or `.graphql` / `.graphqls` / `.gql` files. Python never defines types, fields, arguments or nullability.
- `gql(sdl)`: parses the string and raises `GraphQLSyntaxError` at import time with a readable location. Returns the string unchanged. Optional.
- `load_schema_from_path(path)`: load one file or every schema file in a directory tree. Raises `ariadne.exceptions.GraphQLFileSyntaxError` with file name.
- `make_executable_schema(type_defs, *bindables, directives=None, convert_names_case=False)`: builds a graphql-core `GraphQLSchema` from SDL and binds Python code. `type_defs` can be a string or list of strings. Order of SDL parts does not matter. Passing bindables as a list still works but may be deprecated.
- Bindables: any object with `bind_to_schema(schema)`. Also accepts a Python `enum.Enum` class directly (bound by class name) and lists of bindables.
- Bindables validate against the SDL at build time. `ValueError` if the named type does not exist, has the wrong kind, or a bound field is missing (`validate_graphql_type`).
- Order of bindables matters. Later bindables replace earlier resolvers for the same field. `InterfaceType` only fills fields that have no resolver.
- No check that every SDL field has a resolver. Missing resolvers silently fall back to the default resolver.
- No schema export command. The SDL is the source. Result is a plain graphql-core `GraphQLSchema`, so `graphql.print_schema` works.
- Types are not generated from any data source (except the SQLAlchemy contrib, which only binds resolvers to types you already wrote in SDL).
- Python types and SDL types are linked only by string names. No static check that resolver signatures match SDL arguments or return types.
- Descriptions come from SDL string descriptions (`"..."` and `"""..."""`, Markdown allowed). No docstring-based descriptions.
- Deprecation comes from SDL `@deprecated(reason:)`. Nothing Python-side.

## Resolvers and object types

- Resolver signature: `(obj, info, **kwargs)`. Sync or async. Any callable works.
- `ObjectType("Name")`: resolver map for a type. `@obj.field("name")` decorator (non-wrapping, returns the function unchanged, so one function can be stacked on many types). `obj.set_field(name, fn)`. `obj.set_alias(field, attr)`.
- `QueryType()`, `MutationType()`: shortcuts for `ObjectType("Query")` and `ObjectType("Mutation")`.
- `ObjectType.create_register_resolver`, `bind_resolvers_to_graphql_type`: lower-level hooks for subclasses.
- Default resolver is graphql-core's `default_field_resolver`. Dict key or attribute lookup. If the value is callable it is called with `(info, **args)`.
- `resolve_to(attr_name)`: resolver that reads another attribute. `is_default_resolver(fn)`: check if a field uses the default.
- Arguments reach resolvers as kwargs. Arguments not sent by the client are not passed. Resolvers must use Python defaults.
- `root_value`: static value or callable `(context, operation_name, variables, document)`. `BaseProxyRootValue` wraps a root value and can post-process the final result (`update_result`). Used by ariadne-graphql-proxy.
- `info.context` default is `{"request": request}`. `context_value` can be a value or a callable `(request, data)`. Async callables are allowed in ASGI. Async generator (yield) context factories are not supported.
- No field-level permission API in core. Docs show manual checks in resolvers or decorators. See ariadne-auth below.
- No field complexity, no field-level middleware config, no visibility or schema hiding.

## Name case conversion

- `make_executable_schema(..., convert_names_case=True)`: camelCase SDL names map to snake_case Python names. Sets resolvers for fields without one, `out_name` on arguments and input fields.
- `convert_names_case=callable`: custom converter `(graphql_name, schema, path) -> str`. Type alias `SchemaNameConverter`. Low-level `convert_schema_names(schema, converter)`.
- `convert_camel_case_to_snake(name)`: the default converter. Handles digits (`streetAddress2` to `street_address_2`). Digit handling changed in 1.0.
- Manual option: mutate `schema.type_map[...].fields[...].out_name` after build.
- `convert_kwargs_to_snake_case` decorator and `FallbackResolvers` were removed in 0.29.

## Inputs

- Input objects arrive as `dict` by default. Keys are SDL names (or converted names).
- `InputType(name, out_type=None, out_names=None)`: `out_names` renames keys. `out_type` is a callable run on the final dict (for example `lambda data: MyDataclass(**data)`).
- No input validation hooks beyond what the `out_type` callable does. No model-form style validation. No `@oneOf` support in docs. I think it depends on the graphql-core version installed.
- `validate_schema_default_enum_values(schema)`: raises `ValueError` if SDL defaults use unknown enum members. `repair_schema_default_enum_values(schema)`: swaps SDL enum defaults to the bound Python values. Both run inside `make_executable_schema`.

## Scalars

- `ScalarType(name, serializer=None, value_parser=None, literal_parser=None)`. Decorators `@scalar.serializer`, `@scalar.value_parser`, `@scalar.literal_parser`. Setters `set_serializer`, `set_value_parser`, `set_literal_parser`.
- Custom scalars without Python code pass values through as JSON.
- `ValueError` or `TypeError` in a value parser becomes a validation error. The message is sent to the client.
- No built-in Date, DateTime, JSON, Decimal or UUID scalars in core. Only `upload_scalar`. ariadne-django ships some (see below).

## Enums

- SDL enums are Python strings by default.
- `EnumType(name, values)`: `values` is a Python `Enum` class or a `dict` of member name to Python value.
- Passing an `Enum` class straight to `make_executable_schema` binds it by class name.
- Plain `enum.Enum` with string values only accepts members as resolver output. `StrEnum` / `IntEnum` also accept raw values.
- `EnumType.bind_to_default_values` was removed in 1.0.

## Unions and interfaces

- `UnionType(name, type_resolver=None)`. `@union.type_resolver` or `set_type_resolver`. Resolver returns a type name string or `None`.
- `InterfaceType(name, type_resolver=None)`. Same type resolver API. It extends `ObjectType`, so `field`, `set_field`, `set_alias` set shared resolvers on all implementing types that have none.
- `type_implements_interface(interface_name, graphql_type)`: helper.
- No automatic type resolution from Python classes. graphql-core `is_type_of` is not wired by Ariadne.

## Mutations

- Plain resolvers on `MutationType`. No mutation base class, no input or payload generation, no model mutations.
- Docs recommend result types with `error` and object fields over raising errors (errors-as-data pattern by convention only).
- No CRUD generation. No nested writes. No transactions or atomic handling.

## Errors

- `format_error(error, debug=False)`: default formatter. With `debug=True` adds `extensions.exception` with `stacktrace` and `context` (local variables of the failing frame).
- `error_formatter=` on servers and `graphql()` replaces it. Helpers: `get_error_extension`, `get_formatted_error_traceback`, `get_formatted_error_context`, `unwrap_graphql_error`.
- No error codes, no error types registry, no mapping of Python exceptions to GraphQL errors.
- Hiding "Did you mean" suggestions is done with a custom error formatter (regex). No setting.
- HTTP errors: `HttpError`, `HttpBadRequestError`, `HttpStatusResponse`. `WebSocketConnectionError` rejects a websocket in `on_connect` with a string or dict payload.
- Logging: `logger=` (name or logger instance) on all servers and `graphql`, `graphql_sync`, `subscribe`. Default logger `ariadne`.

## Schema directives

- `SchemaDirectiveVisitor` subclasses implement behavior for SDL directives. Pass them as `make_executable_schema(..., directives={"name": Visitor})`.
- Visitor methods: `visit_schema`, `visit_scalar`, `visit_object`, `visit_field_definition`, `visit_argument_definition`, `visit_interface`, `visit_union`, `visit_enum`, `visit_enum_value`, `visit_input_object`, `visit_input_field_definition`. `self.args` holds directive arguments.
- Typical use is wrapping `field.resolve`. Port of the graphql-tools visitor.
- Directive arguments are validated at schema build.
- Name conversion runs before directives (since 1.0).
- No operation (executable) directive hooks beyond graphql-core defaults.

## Execution API

- `graphql(schema, data, ...)` async, `graphql_sync(schema, data, ...)`, `subscribe(schema, data, ...)`. Return `(success: bool, result: dict)`.
- Options: `context_value`, `root_value`, `query_parser`, `query_validator`, `query_document` (skip parsing), `debug`, `introspection`, `logger`, `validation_rules`, `require_query` (only allow query operations), `error_formatter`, `middleware`, `middleware_manager_class`, `extensions`, `execution_context_class`. Extra kwargs go to graphql-core.
- `query_parser(context, data) -> DocumentNode`: replace parsing. Docs show an LRU parse cache.
- `query_validator(schema, document_ast, rules, max_errors, type_info)`: replace validation. Docs show caching `ariadne.graphql.validate_query` with `lru_cache`.
- `execution_context_class`: custom graphql-core `ExecutionContext`. Used for `graphql-sync-dataloaders` `DeferredExecutionContext`.
- `introspection=False`: blocks introspection through a validation rule (`ariadne/validation/introspection_disabled.py`).
- Request data must be a JSON object. No query batching (a JSON list is rejected).
- No persisted queries or APQ. No trusted documents.
- No `@defer` / `@stream`.

## Validation and query cost

- `validation_rules=`: list of graphql-core `ValidationRule` classes, or a callable `(context, document, data)` returning a list. Dynamic rules per user are the documented pattern.
- `cost_validator(maximum_cost, default_cost=0, default_complexity=1, variables=None, cost_map=None)` in `ariadne.validation`.
- Costs are set with the `@cost(complexity:, multipliers:, useMultipliers:)` SDL directive (`cost_directive` exports its definition) or a Python `cost_map` dict.
- `multipliers` names `Int` arguments that multiply the cost. Variables must be passed to the validator, or queries with variables fail.
- No depth limit validator. No alias or token limits. No rate limiting. The SQLAlchemy contrib has its own relationship `max_depth`.

## Extensions and middleware

- `Extension` base class (`ariadne.types`). Hooks: `request_started(context)`, `request_finished(context)`, `resolve(next_, obj, info, **kwargs)`, `has_errors(errors, context)`, `format(context)` (adds to response `extensions`).
- `extensions=` takes a list of classes (zero-arg callables) or a callable `(request, context)` returning a list. So extensions can be enabled per request.
- `ExtensionManager` runs them. `as_middleware_manager` turns `resolve` hooks into graphql-core middleware. Extension `resolve` runs before plain middleware.
- Middleware: graphql-core style `(resolver, obj, info, **args)`. `middleware=` list or callable per request. `middleware_manager_class=` custom `MiddlewareManager`.
- Docs warn that middleware runs for every field and async middleware slows queries 1.5x to 2.5x.
- Extensions and middleware do not run for subscriptions. Docs show a decorator workaround (`examples/subscription_middleware_workaround.py`). Release 1.1.0a1 says "Extend subscription with middleware", but `subscribe()` on `main` has no middleware option. I think that change did not land.
- Configured on `GraphQLHTTPHandler(extensions=, middleware=, middleware_manager_class=)` for ASGI. Directly on the WSGI `GraphQL`.

## Monitoring

- `ariadne.contrib.tracing.opentelemetry.OpenTelemetryExtension` and `opentelemetry_extension(arg_filter=, root_span_name=)`. Spans per resolver. Skips default resolvers for speed.
- `arg_filter(args, info)` redacts sensitive arguments. `root_span_name` is a string or `callable(context)`.
- Apollo tracing and OpenTracing extensions were removed in 1.0.
- No metrics, no query logging extension, no schema usage reporting.

## HTTP layer (ASGI)

- `ariadne.asgi.GraphQL(schema, context_value=, root_value=, query_parser=, query_validator=, validation_rules=, execute_get_queries=False, debug=False, introspection=True, explorer=, logger=, error_formatter=, execution_context_class=, http_handler=, websocket_handler=)`.
- Mount as ASGI app, or call `handle_request(request)` and `handle_websocket(websocket)` from Starlette or FastAPI routes.
- `GraphQLHTTPHandler`: strategy class for HTTP. Overridable methods include `extract_data_from_request`, `extract_data_from_json_request`, `extract_data_from_multipart_request`, `extract_data_from_get_request`, `execute_graphql_query`, `get_extensions_for_request`, `get_middleware_for_request`, `create_json_response`, `render_explorer`, `handle_not_allowed_method`.
- `execute_get_queries=True`: run `query` operations sent by GET. Mutations over GET are rejected (`require_query`).
- `OPTIONS` returns 200 with an `Allow` header. No CORS handling in the library.
- JSON response through Starlette `JSONResponse`. Custom JSON by overriding `create_json_response`.
- Status codes: 200 on success, 400 on failure. Fixed in 1.0.1.
- No request body size limit option. No CSRF handling (docs say to disable CSRF checks for the view).

## HTTP layer (WSGI)

- `ariadne.wsgi.GraphQL(...)`: same options plus `extensions`, `middleware`, `middleware_manager_class` directly on the app.
- `GraphQLMiddleware(app, graphql_app, path="/graphql/")`: route one path to GraphQL and the rest to another WSGI app (for example Django).
- Many overridable methods (`handle_request`, `handle_get`, `handle_post`, `get_request_data`, `get_context_for_request`, `return_response_from_result`, and more).
- `FormData`: small multipart parser that replaces the removed stdlib `cgi`.
- No subscriptions on WSGI.

## Explorers

- `ariadne.explorer`: `ExplorerGraphiQL` (default, GraphiQL 5.2.2 since 1.0.1, with SRI hashes), `ExplorerApollo` (Apollo Sandbox), `ExplorerPlayground` (unmaintained, many settings), `ExplorerHttp405` (disables the explorer).
- `ExplorerGraphiQL(title=, explorer_plugin=False, default_query=, subscription_url=)`.
- Custom explorer: subclass `Explorer`, implement `html(request)`. Returning `None` gives 405. Can return an awaitable in ASGI, so access checks per request are possible.
- `render_template(template, vars)`: tiny Django-like template engine (`{% if %}`, `{% ifnot %}`, `{% raw %}`, auto-escaping).

## Subscriptions

- `SubscriptionType()`: `@sub.source("field")` (async generator or sync generator), `@sub.field("field")` resolver for each event. `set_source`, `create_register_subscriber`.
- Sync generators run in worker threads through `anyio.to_thread.run_sync` (added 0.28). `gen.close()` runs on disconnect.
- WebSocket handlers: `GraphQLWSHandler` (legacy `subscriptions-transport-ws`, `keepalive=`) and `GraphQLTransportWSHandler` (`graphql-ws` protocol, `connection_init_wait_timeout=`).
- Handler hooks: `on_connect(websocket, params)` (sync or async, can raise `WebSocketConnectionError`), `on_disconnect(websocket)`, `on_operation(websocket, operation)`, `on_complete(websocket, operation)`. The last two are marked experimental.
- Connection params reach resolvers through `websocket.scope` and the `context_value` callable.
- SSE: `ariadne.contrib.sse.SSESubscriptionHandler(send_timeout=, ping_interval=15, default_response_headers=)` plugged into `GraphQLHTTPHandler(subscription_handlers=[...])`. Only the graphql-sse "distinct connections" mode.
- Pluggable HTTP subscription transports (0.29): subclass `ariadne.SubscriptionHandler`, implement `supports(request, data)` and `handle(...)`. `generate_events(...)` yields `SubscriptionEvent` with `SubscriptionEventType.NEXT`, `ERROR`, `COMPLETE`, `KEEP_ALIVE`. First handler whose `supports` is true wins.
- `examples/subscription_handler_example.py`: HTTP callback transport (Netflix DGS / Apollo style `callbackUri`) with keep-alive and retries. Example only, not shipped.
- No built-in pub-sub. Docs point to `broadcaster`. No subscription filtering helpers. No multipart subscriptions over HTTP.

## DataLoaders

- No DataLoader in core. Docs use `aiodataloader.DataLoader` (async) and `graphql_sync_dataloaders.SyncDataLoader` with `DeferredExecutionContext` (sync).
- Loaders are created per request in `context_value`.

## File uploads

- GraphQL multipart request spec. Add `scalar Upload` to SDL and bind `upload_scalar`.
- Upload values are Starlette `UploadFile` in ASGI and `python-multipart` `File` in WSGI.
- `combine_multipart_data(operations, files_map, files)`: helper for custom integrations.
- `Upload` is input-only. No size limits or type checks.

## Relay (`ariadne.contrib.relay`, since 0.25)

- `RelayQueryType(global_id_decoder=..., node=...)`: adds the `node(id:)` field. `query.bindables` returns the query type and a `RelayNodeInterfaceType`. Node type resolver is required (`@query.node.type_resolver`).
- `RelayObjectType(name, connection_arguments_class=ConnectionArguments)`: `@type.node_resolver` for global ID lookup. `@type.connection("field")` for connection resolvers.
- Connection resolver gets `connection_arguments: ConnectionArguments` (`first`, `after`, `last`, `before`). Also `ForwardConnectionArguments`, `BackwardConnectionArguments`.
- Resolver returns `RelayConnection(edges, total, has_next_page, has_previous_page)`. Overridable `get_cursor`, `get_node`, `get_page_info`, `get_edges`.
- Global IDs: `encode_global_id(type_name, id)` and `decode_global_id(gid)` (base64 of `Type:id`). `GlobalIDTuple`.
- SDL for `Node`, connections, edges and `PageInfo` must be written by hand. No pagination logic. No slicing of querysets.

## SQLAlchemy integration (`ariadne.contrib.sqlalchemy`, since 1.1.0)

- `SQLAlchemyObjectType(name, model, aliases=None, strategies=None, max_depth=3)`: binds a SDL type to a SQLAlchemy 2.0 model. Auto-resolvers for relationships and aliased columns.
- `SQLAlchemyQueryType([object_types])`: root fields whose return type is a bound model get an auto-resolver. Root field arguments that match column names become equality `WHERE` filters.
- `auto_eager_load(stmt, info, model, ...)`: walks the selection set before execution. Applies `selectinload` for collections, `joinedload` for single relations, `load_only` for columns. Handles fragments and inline fragments.
- `strategies={"rel": selectinload}` overrides the loader per relationship. `aliases` maps GraphQL field names to model attributes. `max_depth` limits relationship nesting and raises `GraphQLError`.
- `get_base_query(info, **kwargs)`: override to add default filters (for example soft delete or tenant scoping).
- DataLoader fallback: `SQLAlchemyDataLoader`, `LoaderRegistry(session)`, `SQLAlchemyDataLoaderExtension(session_key=, registry_key=)`. Used when relations are read on objects from manual resolvers.
- `get_session_from_context` and `get_loader_registry_from_context` are static methods to override.
- Sync `Session` and `AsyncSession`. `AsyncSession` fails with sibling root fields (one connection per session). Not usable with `graphql_sync`.
- No filtering grammar beyond equality, no ordering, no pagination, no mutations, no permissions.

## Apollo Federation (`ariadne.contrib.federation`)

- `make_federated_schema(type_defs, *bindables, ...)`: adds `_service { sdl }`, `_entities`, `_Any`, `_Entity`, and federation directives.
- Federation version is picked from the `@link(url: "https://specs.apollo.dev/federation/vX.Y")` in SDL. Bundled definitions for v1.0 and v2.0 to v2.6.
- `FederatedObjectType` and `FederatedInterfaceType` with `@type.reference_resolver` `(obj, info, representation)`.
- `extend_federated_schema` was removed in 1.0.
- Rover subgraph template: `mirumee/subgraph-template-ariadne-fastapi`.

## Integrations

- ASGI: Starlette, FastAPI (mount or route methods, FastAPI `Depends` through `request.scope`).
- WSGI: any, plus `GraphQLMiddleware`. Flask example uses `graphql_sync` in a view.
- AWS Lambda: `ariadne-lambda` (below) or a handler calling `graphql_sync`.
- Django: not in core since 0.13. Docs point to `ariadne_django` (below).
- Other frameworks: docs give a step-by-step algorithm using `graphql_sync` / `graphql`.

## Testing

- No test client in core. Tests call `graphql_sync`, `graphql`, or `subscribe` directly, or use Starlette / httpx test clients.

## Security docs

- Short pages on hiding field suggestions (error formatter), turning off `debug` in production, and external scanners (graphql.security, Escape).
- No built-in security settings beyond `introspection`, `debug`, and `cost_validator`.

## Maintenance

- Active. 0.26 (2025-04) to 1.1.0 (2026-06) had many releases. 1.0 removed deprecated APIs (`EnumType.bind_to_default_values`, Apollo tracing, OpenTracing, `extend_federated_schema`) and renamed base handler classes.
- 0.28 added sync generator subscriptions. 0.29 added pluggable subscription handlers and removed `FallbackResolvers` and `convert_kwargs_to_snake_case`. 1.1 added the SQLAlchemy contrib.
- Repo has `CLAUDE.md`, `AGENTS.md`, `llms.txt`, and `context7.json` for AI tooling.

## Not supported or not in scope

- Code-first type definitions (only in ariadne-graphql-modules, see below).
- Django ORM integration, model types, filters, ordering, pagination (only the stale ariadne_django, which has none of these).
- Permissions framework in core (only ariadne-auth).
- Query batching, persisted queries, APQ, `@defer` / `@stream`, depth limits, rate limiting, CORS, request size limits.
- Built-in DataLoader implementation, built-in pub-sub.
- Mutation helpers (model mutations, input validation, nested writes).
- Schema visibility / per-user schema hiding.
- Built-in date / JSON / decimal scalars.
- Middleware and extensions for subscriptions.
- Schema printing or schema-diff commands (the SDL is already the source).

## Related project: ariadne-graphql-modules

- Repo `mirumee/ariadne-graphql-modules`. PyPI 0.8.0 (2024-02-21). Last `main` commit 2025-09-18. Linked from the Modularization doc page.
- Released API (0.x): each GraphQL type is a Python class with `__schema__ = gql("type X {...}")`. Classes: `ObjectType`, `MutationType`, `SubscriptionType`, `InputType`, `EnumType`, `ScalarType`, `InterfaceType`, `UnionType`, `DirectiveType`, `CollectionType`.
- Resolvers are `resolve_<field>` static methods. `__requires__ = [OtherType]` declares dependencies. `DeferredType("Name")` breaks circular imports.
- Validates SDL against resolvers and dependencies at class definition time.
- `__aliases__ = convert_case`, `__fields_args__ = convert_case`, `__args__ = convert_case` for name conversion.
- Roots merging: many `Query` / `Mutation` classes are merged into one root type.
- Own `make_executable_schema` accepts old Ariadne bindables and SDL too (`MOVING.md`). `directives` is named `extra_directives`.
- Branch `next-api` (last commit 2024-09-09, unreleased, version "dev"): a type-annotation code-first API. `GraphQLObject` with annotated fields (`hello: str`), `GraphQLObject.field(...)`, `GraphQLObject.resolver("field")`, `GraphQLObject.argument(...)`, `GraphQLInput`, `GraphQLEnum` / `graphql_enum`, `GraphQLInterface` (inheritance adds `implements`), `GraphQLUnion`, `GraphQLScalar`, `GraphQLSubscription`, `GraphQLID`, `deferred`, `sort_schema_document`. Supports both `__schema__` SDL and schema-less definitions. The old API moves to `ariadne_graphql_modules.v1`. I think this is not released.

## Related project: ariadne-codegen

- Repo `mirumee/ariadne-codegen`. PyPI 0.19.0 (2026-08-28). Active.
- GraphQL client generator. Takes a schema (file, Python package, or remote introspection) and `.graphql` operation files. Generates a typed Pydantic-based Python client with one method per operation.
- Async (default) or sync client. Subscriptions over `graphql-transport-ws`. File uploads (multipart spec). Custom scalar mapping with `serialize` / `parse` hooks.
- Plugin system with hooks. Standard plugins (shorter results, extract operations, forward refs, and more). Mixins on generated models. Custom base client.
- `graphqlschema` mode writes a copy of a schema (after plugins) to a file. Models-only generation. Custom operation builder for programmatic queries. OpenTelemetry tracing in the client. Deprecation warnings for deprecated schema parts.
- Configured in `pyproject.toml` (`[tool.ariadne-codegen]`). Client side only. It does not generate server code.

## Related project: ariadne_django

- Linked from the Django integration page as `reset-button/ariadne_django`. Also cloned as `mirumee/ariadne-django` (same code, `setup.py` points to reset-button). PyPI `ariadne-django` 0.3.0 (2022-07-19). Last commit 2022-08-23. README says it looks for a new maintainer. I think it is abandoned.
- Split out of Ariadne 0.12. Add `ariadne_django` to `INSTALLED_APPS`.
- Views: `GraphQLView` and `GraphQLAsyncView` (class-based, `BaseGraphQLView`). Options as class attributes: `schema`, `context_value`, `root_value`, `introspection`, `validation_rules`, `error_formatter`, `extensions`, `middleware`, `logger`, `playground_options`. Serves GraphQL Playground from a Django template. JSON and multipart uploads.
- Scalars: `date_scalar`, `datetime_scalar`, `time_scalar`, `decimal_scalar`, `json_scalar`, `uuid_scalar`, plus a timedelta scalar.
- Auth decorators for resolvers: `login_required()`, `permission_required(perm)`.
- Error formatter `format_graphql_error(error, error_map=None, debug=False)` with helpers for Django `ValidationError` details and Postgres error details.
- Test helper `BaseGraphQLQueryTest` (Django `TestCase`).
- No model types, no ORM optimizer, no filters, no pagination, no mutations from models. The README says model mapping may come but will stay optional.

## Related project: ariadne-auth

- Repo `mirumee/ariadne-auth`. PyPI 0.1.1 (2025-04-19). Not linked from the main docs.
- `AuthorizationExtension(permissions_object_provider_fn=)`. `set_required_global_permissions([...])` applies to all resolvers, including default resolvers.
- `@authz.require_permissions(permissions=[...], ignore_global_permissions=False, permissions_object_provider_fn=)` per resolver.
- Permission object follows the `HasPermissions` protocol. Provider can be async.

## Related project: ariadne-graphql-proxy

- Repo `mirumee/ariadne-graphql-proxy`. PyPI 0.5.1 (2026-03-24). README says prototype stage.
- `ProxySchema`: combine local and remote schemas (`add_remote_schema(url)`), route queries to them. `get_final_schema()`, `root_resolver`.
- Foreign keys between services, fields dependencies, subset schemas, low-level schema copy / insert / remove utilities.
- Cache framework: `simple_cached_resolver`, `cached_resolver`, custom cache backends and serializers, `CloudflareCacheBackend`, `DynamoDBCacheBackend`.

## Related project: ariadne-lambda

- Repo `mirumee/ariadne-lambda`. PyPI 0.4.1 (2026-04-09).
- `ariadne_lambda.graphql.GraphQLLambda(schema=...)`: HTTP handler for AWS Lambda and API Gateway events. Called through `asgiref.sync.async_to_sync`.
- Docs also mention Mirumee's `lynara` (ASGI apps on Lambda) and `smyth` (local Lambda testing).

## Sources

Repos (shallow clones in `/tmp`):
- https://github.com/mirumee/ariadne (`/tmp/ariadne`, `main`, commit `d123826`, 2026-08-31)
- https://github.com/mirumee/ariadne-website (`/tmp/ariadne-website`, commit `eb6f102`, 2026-06-24). Only versioned old docs. Current docs are in the main repo.
- https://github.com/mirumee/ariadne-graphql-modules (`/tmp/ariadne-graphql-modules`, `main` `8e1242e` and branch `next-api` `8374a61`)
- https://github.com/mirumee/ariadne-codegen (`/tmp/ariadne-codegen`, `f0a8990`, 2026-08-25)
- https://github.com/mirumee/ariadne-django (`/tmp/ariadne-django`, `8d6fb33`, 2022-08-23)
- https://github.com/mirumee/ariadne-auth (`/tmp/ariadne-auth`, `a1e9c83`, 2025-04-19)
- https://github.com/mirumee/ariadne-graphql-proxy (`/tmp/ariadne-graphql-proxy`, `4cb2ae4`, 2026-04-09)
- https://github.com/mirumee/ariadne-lambda (`/tmp/ariadne-lambda`, `b0d5e01`, 2026-04-09)

Docs read (from `docs/` in the main repo, the source of https://ariadnegraphql.org/server/Docs/intro):
- `llms.txt`
- `docs/01-Docs/01-intro.md` to `24-subscription-handlers.md` (all 24 pages)
- `docs/02-Monitoring/01-open-telemetry.md`
- `docs/03-Security/01` to `04`
- `docs/04-Servers/01-asgi.md`, `02-wsgi.md`, `03-aws-lambda.md`
- `docs/05-Integrations/01` to `05`
- `docs/06-Extensions/01-extensions.md`, `02-middleware.md`, `03-query-validators.md`, `04-query-stack.md`
- `docs/07-Contrib/01-graphql-relay.md`, `02-sqlalchemy.md`
- `docs/08-API-reference/01` to `07` (searched by heading and grep, not read line by line)
- https://ariadnegraphql.org/llms.txt and https://ariadnegraphql.org/llms-full.txt return 404.

Related project docs:
- ariadne-graphql-modules `README.md`, `MOVING.md`, `CHANGELOG.md`, `next-api` branch `README.md`, `docs/api/object_type.md`, `ariadne_graphql_modules/__init__.py`
- ariadne-codegen `README.md`, `docs/` index, `docs/02-guides/11-schema-generation.md`
- ariadne-django `README.md`, `setup.py`, package layout
- ariadne-auth `README.md`
- ariadne-graphql-proxy `README.md`, `GUIDE.md` headings
- ariadne-lambda `README.md`

Changelog:
- `CHANGELOG.md` (unreleased section only)
- GitHub releases through https://api.github.com/repos/mirumee/ariadne/releases (0.26.2 to 1.1.0)
- https://github.com/mirumee/ariadne/releases
- PyPI: https://pypi.org/pypi/ariadne/json and the JSON pages for each related package

Source files checked:
- `ariadne/__init__.py`, `pyproject.toml`
- `ariadne/graphql.py`, `inputs.py`, `enums.py`, `schema_visitor.py`
- `ariadne/asgi/handlers/http.py`, `ariadne/asgi/handlers/base.py`, `ariadne/wsgi.py`, `ariadne/contrib/sse.py`
- `ariadne/explorer/graphiql.py`
- `ariadne/validation/__init__.py`, `introspection_disabled.py`
- `ariadne/contrib/federation/__init__.py`, `schema.py`, `definitions/`
- `ariadne/contrib/relay/*.py`
- `ariadne/contrib/sqlalchemy/*.py`
- `examples/`, `tests_mypy/`
- ariadne-django `ariadne_django/views/base.py`, `scalars/__init__.py`, `auth/decorators/`, `formatters/errors/`, `tests/`
