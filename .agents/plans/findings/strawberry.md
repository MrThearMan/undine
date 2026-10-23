# Strawberry findings

Version checked: 0.327.7 (2026-09-07). Package `strawberry-graphql`. Import `strawberry`.
Core library only. Django ORM integration is in `strawberry-django` (see `strawberry-django.md`). It is not repeated here.
Python 3.10+ (3.15 tested since 0.324.1). graphql-core 3.2 and 3.3 (3.3 needed for some features).
Code-first only. The docs say "Strawberry _only_ supports code-first schemas". SDL is an output, or an input for one-off codegen.

## Types and fields

- `@strawberry.type(name=, description=, directives=, extend=)`: object type from a dataclass-like class. Built on `dataclass_transform`.
- `@strawberry.input(name=, description=, directives=, one_of=)`: input type. Input types that inherit from interfaces raise an error (0.273.0).
- `@strawberry.input(one_of=True)`: `@oneOf` input objects (0.230.0). Fields use `strawberry.Maybe[T]`.
- `@strawberry.interface`: interface type. Interfaces can implement interfaces. Interfaces can carry field resolvers that implementing types inherit or override.
- Interface `resolve_type` classmethod: resolvers can return the interface type directly (0.198.0).
- `strawberry.union("Name", description=, directives=)` used inside `Annotated[A | B, ...]`: named union. Plain `A | B` auto-names the union (`AudioVideoImage`).
- Single-member unions via `Annotated[A, strawberry.union("Name")]` (0.196.0). Lazy unions (0.283.3). Unions with generics (0.265.0).
- `@strawberry.enum(name=, description=, directives=, graphql_name_from="key"|"value", print_definition=)`: enum from a Python `Enum`.
- `strawberry.enum_value(value, name=, description=, deprecation_reason=, directives=)`: per-value config. `IntEnum` supported.
- Undecorated Python enums work in the schema (0.246.1). They cannot be configured.
- `Annotated[MyEnum, strawberry.enum(description=...)]`: type alias for an existing enum (mypy friendly).
- `strawberry.field(resolver=, name=, description=, deprecation_reason=, default=, default_factory=, permission_classes=, extensions=, directives=, metadata=, graphql_type=, init=)`.
- `strawberry.field` inside `Annotated[T, strawberry.field(...)]` (0.308.0). Must be on the outermost `Annotated`.
- `strawberry.mutation` and `strawberry.subscription`: same as `field` with operation semantics.
- `graphql_type=` on `field` and `argument`: override the GraphQL type when the Python annotation differs (0.151.0, 0.291.0).
- `metadata=` on fields: arbitrary dict. Used by `Schema.get_fields` filtering.
- `strawberry.argument(name=, description=, deprecation_reason=, directives=, metadata=, graphql_type=)` inside `Annotated`.
- Resolver parameters are injected by type: `strawberry.Info`, `strawberry.Parent[T]`, `self`, legacy `root`. Name-based `info` matching removed (0.296.0).
- `strawberry.Parent[T]`: typed parent value in function or `@staticmethod` resolvers (0.208.0).
- `strawberry.Private[T]`: attribute on the class that is not exposed in GraphQL.
- `strawberry.auto`: take the type from a backing model (used by pydantic and strawberry-django).
- `strawberry.lazy(".module")` in `Annotated["Type", ...]`: lazy forward references across modules to break circular imports.
- `from __future__ import annotations` fully supported (0.165.0).
- `typing.Self` in types and interfaces (0.142.0).
- Generics: `Generic[T]` object types, input types and arguments. PEP 695 syntax `class Edge[T]` (0.199.0). Name is derived (`UserPage`). Variadic generics not supported.
- `strawberry.cast(Type, obj)`: tag a non-Strawberry object (ORM row, pydantic model) so union/interface resolution picks the right type.
- `strawberry.asdict(obj)`: convert a Strawberry instance to dict. Unwraps `Some`, drops absent `Maybe` and `UNSET` (0.312.0).
- `strawberry.tools.create_type(name, fields, is_input=, is_interface=, description=, directives=, extend=)`: build a type from a list of fields at runtime.
- `strawberry.tools.merge_types(name, (A, B))`: merge several root types into one.
- Void mutations: return `None` maps to the `Void` scalar.
- `deprecation_reason=` on fields, input fields, arguments, enum values.
- Descriptions come from `description=`. Docstrings are not used as descriptions. I think this is so (not seen in docs or code search).

## Null vs absent input

- `strawberry.Maybe[T]`: absent is `None`, present is `Some(value)`. Sending `null` to `Maybe[T]` is a validation error.
- `strawberry.Maybe[T | None]`: three states. `Some(None)` means explicit null. Semantics changed in 0.279.0.
- `strawberry.Some`: wrapper with `.value`.
- `strawberry.UNSET`: legacy sentinel. Typed as `Any`. Docs recommend `Maybe`.
- Codemod `strawberry upgrade maybe-optional` converts `Maybe[T]` to `Maybe[T | None]`.

## Scalars

- Built-in: `String`, `Int`, `Float`, `Boolean`, `ID`, `Date`, `DateTime`, `Time`, `Decimal` (string), `UUID` (string), `Void`, `JSON`, `Base16`, `Base32`, `Base64` (`strawberry.scalars`).
- `strawberry.scalar(name=, description=, specified_by_url=, serialize=, parse_value=, parse_literal=, directives=, print_definition=)`: custom scalar definition.
- `StrawberryConfig(scalar_map={NewType_or_class: strawberry.scalar(...)})`: preferred way to register scalars (0.288.0). Works with `NewType` so type checkers stay correct.
- `strawberry.scalar(cls, ...)` wrapping is deprecated (0.288.0). Codemod `replace-scalar-wrappers`.
- `Schema(scalar_overrides={type: ScalarDefinition})`: override built-in scalars or map framework types.
- Override `datetime` in `scalar_map` to change DateTime serialization (for example Unix timestamps or pendulum).
- `StrawberryInputCoercionError` (`strawberry.exceptions`): raise from `parse_value` to mark invalid client input. Built-in scalars and OneOf raise it. Check `error.original_error` too.
- No built-in `BigInt`, `Email`, `URL`, `Duration` scalars. Docs show recipes only.

## Schema

- `strawberry.Schema(query, mutation=, subscription=, directives=, types=, extensions=, execution_context_class=, config=, scalar_overrides=, schema_directives=, exception_handlers=)`.
- `types=[...]`: register types not reachable from roots (interface implementations, federation entities).
- `schema_directives=[...]`: directives applied on the `schema` definition.
- `Schema.execute(...)` (async) and `execute_sync(...)`: args `query, variable_values, context_value, root_value, operation_name, allowed_operation_types, operation_extensions`.
- `Schema.subscribe(...)`: async iterator of results.
- `Schema.stream(...)` (0.319.0): one streaming API for queries, mutations and subscriptions. Base for SSE, multipart and WS transports.
- `Schema.as_str()`, `str(schema)`, `strawberry.printer.print_schema(schema)`: SDL output. Schema directives printed.
- `Schema.introspect()`: introspection result as dict.
- `Schema.get_type_by_name`, `get_field_for_type`, `get_directive_by_name`: lookups.
- `Schema.get_fields(type_definition)` override: filter fields at build time (public vs internal schema from one codebase) (0.218.0). Static, not per request.
- `Schema.process_errors(errors, execution_context)` override: custom error logging. Default logs to the `strawberry.execution` logger.
- `DuplicatedTypeName` error on two types with the same GraphQL name (0.144.0).
- Rich schema-build errors with code frames (`rich` + `libcst`). Disable with `STRAWBERRY_DISABLE_RICH_ERRORS=1`. Each error has a docs page under `docs/errors/`.

## Schema configuration (`strawberry.schema.config.StrawberryConfig`)

- `auto_camel_case`: snake_case to camelCase. Default on.
- `name_converter=NameConverter()`: subclass to rename types, fields, enums, enum values, directives, generics (`from_object`, `from_field`, `from_enum_value`, `from_generic` and so on).
- `default_resolver=getattr`: replace attribute lookup (for example dict access).
- `relay_max_results=100`: default max page size for connections.
- `relay_use_legacy_global_id`: old `GlobalID` scalar name. Default emits `ID` since 0.268.0.
- `disable_field_suggestions`: hide "Did you mean" hints (0.235.0).
- `info_class`: custom `Info` subclass for resolvers.
- `enable_experimental_incremental_execution`: `@defer` and `@stream`.
- `scalar_map`: scalar registry.
- `batching_config={"max_operations": N}`: enable HTTP batching.
- `_unsafe_disable_same_type_validation`: allow duplicate type definitions (0.271.0).

## Resolvers and execution info

- Sync and async resolvers can be mixed.
- `strawberry.Info[ContextType, RootValueType]`: `field_name`, `python_name`, `context`, `root_value`, `variable_values`, `query` (0.309.0), `operation`, `path`, `selected_fields`, `schema`, `return_type`, `input_extensions`, `get_argument_definition(name)`.
- `info.selected_fields`: list of `SelectedField`, `FragmentSpread`, `InlineFragment` (`strawberry.types.nodes`). Includes arguments, directives, sub-selections. This is the only lookahead helper. No built-in ORM optimizer in core.
- `info.input_extensions`: the request `extensions` object from the client (0.269.0, 0.274.2).
- Execution performance: fast `is_awaitable` path (0.289.1, 0.327.7).

## Mutations

- Plain `@strawberry.mutation` resolvers. No CRUD generation in core.
- `InputMutationExtension` (`strawberry.field_extensions`): builds a `<Name>Input` type from resolver arguments and exposes a single `input` argument.
- Namespaced mutations (`Mutation.fruit -> FruitMutations`) documented. Docs warn that nested mutation fields run in parallel.
- Errors-as-data via union return types. See Errors.

## Errors

- Unhandled resolver exceptions go to top-level `errors`. Partial data kept for nullable fields.
- `strawberry.ExceptionHandler[Exc, ErrorType]` + `Schema(exception_handlers=[...])` (0.321.0): map Python exceptions to a member of the field's return union. Covers resolver, argument conversion and field extensions. `handle()` can return `None` to decline. Not for subscriptions or list-of-union fields. Matches first handler.
- Alternative attribute style: `exception_type = ...`, `error_type = ...`.
- `MaskErrors(should_mask_error=, error_message="Unexpected error.")`: hide error messages.
- `StrawberryGraphQLError`: error class with `extensions`. Custom error format by rewriting `execution_context.result.errors` in `on_operation`.
- `PydanticErrorExtension` (0.313.0): pydantic `ValidationError` to structured `extensions.validation_errors`.
- No built-in error codes enum or standard error payload types.

## Permissions and auth

- `strawberry.permission.BasePermission`: `has_permission(self, source, info, **kwargs)` sync or async. Attributes `message`, `error_extensions`, `error_class`. Hook `on_unauthorized()`.
- `strawberry.field(permission_classes=[...])`: shortcut for `PermissionExtension`.
- `PermissionExtension(permissions=[...], use_directives=True, fail_silently=False)`: field extension. `fail_silently=True` returns `None` or `[]` (needs nullable or list type).
- Permissions are auto-added as schema directives. Turn off with `use_directives=False` (the docs wrongly say `add_directives`) or set `_schema_directive` on the class.
- Permissions are field-level only. No type-level or row-level permission API in core.
- Authentication is not provided. Docs say it is the web framework's job. Context carries `request`.
- WebSocket auth via `connection_params` in `info.context` and `on_ws_connect(context)` hook (0.254.0). SSE auth via normal `get_context`.

## Schema extensions (`strawberry.extensions.SchemaExtension`)

- Lifecycle generator hooks: `on_operation`, `on_parse`, `on_validate`, `on_execute`, `on_stream_result` (0.323.0). Each can be sync or async.
- `resolve(self, _next, root, info, *args, **kwargs)`: wraps every resolver (middleware).
- `get_results()`: add data to the response `extensions`.
- `self.execution_context` (`strawberry.types.ExecutionContext`): `query`, `schema`, `context`, `variables`, `root_value`, `operation_name`, `operation_type`, `graphql_document`, `validation_rules`, `pre_execution_errors`, `result`, `extensions_results`, `operation_extensions`.
- Setting `execution_context.result` short-circuits execution (cache, reject). Setting `execution_context.query` in `on_operation` enables persisted-query style lookups (0.152.0).
- Pass extensions as class or factory (`lambda: X(...)`). Instances are deprecated because they leak state across requests.
- Extensions run for subscriptions too (0.240.0).
- Legacy hooks (`on_request_start` and so on) removed (0.295.0).

## Built-in schema extensions

- `QueryDepthLimiter(max_depth, callback=, should_ignore=)`. `IgnoreContext` has `field_name`, `field_args`, `query`, `context`.
- `MaxAliasesLimiter(max_alias_count)`.
- `MaxTokensLimiter(max_token_count)`.
- `DisableIntrospection()` (0.272.0). Federation `_service { sdl }` is not blocked.
- `AddValidationRules([...])`: add graphql-core rules (for example `NoDeprecatedCustomRule`, `NoSchemaIntrospectionCustomRule`).
- `DisableValidation()`.
- `ParserCache(maxsize=128)` and `ValidationCache(maxsize=128)`: LRU caches.
- `MaskErrors`, `PydanticErrorExtension`.
- `pyinstrument.PyInstrument(report_path=)`: profiling to HTML.
- Tracing (`strawberry.extensions.tracing`): `ApolloTracingExtension`, `ApolloFederationTracingExtension` (FTV1, 0.314.0, needs `protobuf`), `DatadogTracingExtension` (`create_span` override), `OpenTelemetryExtension(arg_filter=, tracer_provider=)`. Each has a `...Sync` variant.
- Sentry: `SentryTracingExtension` removed (0.249.0). Sentry SDK ships its own Strawberry integration.
- No query complexity or cost analysis. No rate limiting. No response caching extension. No persisted query / APQ extension. Docs only show recipes.

## Field extensions (`strawberry.extensions.FieldExtension`)

- `resolve(self, next_, source, info, **kwargs)` and `resolve_async(...)`: wrap one field's resolver.
- `apply(self, field: StrawberryField)`: modify the field at schema build (add args, directives, change type).
- Chain order: last extension in the list runs first.
- `SyncToAsyncExtension` inserted automatically when an async-only extension wraps a sync resolver.
- Built on this: `PermissionExtension`, `InputMutationExtension`, relay `ConnectionExtension`, `NodeExtension`.

## Directives

- Built-in operation directives: `@skip`, `@include`. With incremental execution: `@defer(if:, label:)`, `@stream(if:, label:, initialCount:)`.
- `@strawberry.directive(locations=[DirectiveLocation.FIELD, ...], description=, name=)`: custom operation directive. First param `DirectiveValue[T]` is the resolved value. Can take extra args, list args (0.163.0), and `info`. Can be async.
- Operation directive locations: `QUERY`, `MUTATION`, `SUBSCRIPTION`, `FIELD`, `FRAGMENT_DEFINITION`, `FRAGMENT_SPREAD`, `INLINE_FRAGMENT`.
- `@strawberry.schema_directive(locations=[Location.OBJECT, ...], description=, name=, repeatable=, print_definition=)`: type-system directive defined as a dataclass.
- Schema directive locations: `SCHEMA`, `SCALAR`, `OBJECT`, `FIELD_DEFINITION`, `ARGUMENT_DEFINITION`, `INTERFACE`, `UNION`, `ENUM`, `ENUM_VALUE`, `INPUT_OBJECT`, `INPUT_FIELD_DEFINITION`.
- `strawberry.directive_field(name=, default=)`: rename a directive argument.
- Attach via `directives=[...]` on `type`, `field`, `argument`, `enum`, `enum_value`, `scalar`, `union`, `input`, and `Schema(schema_directives=...)`.
- Schema directives are metadata only. They do not change behavior unless a field extension reads them. They appear in introspection and SDL.
- `strawberry.schema_directives.OneOf`: built-in `@oneOf`.

## Relay (`strawberry.relay`)

- `relay.Node` interface. `relay.NodeID[int]` marks the id attribute (private). Implement `resolve_nodes(cls, *, info, node_ids, required)`. Optional `resolve_id`, `resolve_id_attr`.
- Global ID is `base64("TypeName:id")`. Exposed as `ID` since 0.268.0.
- `relay.GlobalID`: argument type. `.type_name`, `.node_id`, `resolve_node(info, ensure_type=)`, `resolve_node_sync`, `resolve_type`. `GlobalIDValueError`.
- `relay.node()`: root node field. Four shapes: `Node`, `Node | None`, `list[Node]`, `list[Node | None]`.
- `@relay.connection(relay.ListConnection[Fruit], max_results=)`: connection field from a resolver that returns list, iterator, generator, async generator, or a sliceable queryset.
- `relay.ListConnection`: limit/offset via slicing (`__getitem__`) or `itertools.islice`. Skips `resolve_edges` when `edges`/`pageInfo` are not selected (0.227.3).
- `relay.Connection[T]`: base class. Override `resolve_connection(nodes, *, info, before, after, first, last)` for custom cursors. Override `resolve_node` to convert ORM rows. `relay.Edge` subclass with custom fields via `resolve_edge(**kwargs)` (0.264.0).
- `relay.PageInfo`, `relay.to_base64`, `relay.from_base64`.
- Optional connections (`Connection | None`) for permission use (0.255.0).
- `totalCount` is not on `ListConnection` by default. Users add it in a subclass. I think this is so (not seen in docs or `relay/types.py` exports).
- Offset and cursor pagination outside relay: only tutorials. No built-in offset pagination type.

## DataLoaders (`strawberry.dataloader`)

- `DataLoader(load_fn, max_batch_size=, cache=True, loop=, cache_map=, cache_key_fn=)`: async only.
- `load`, `load_many`, `clear`, `clear_many`, `clear_all`, `prime`, `prime_many`.
- Errors per key: return an exception in the result list.
- `AbstractCache` with `get`, `set`, `delete`, `clear`: custom cache backends (for example Redis).
- `WrongNumberOfResultsReturned` error on length mismatch.
- No sync dataloader. Loaders are created per request in `get_context` by convention. No automatic registry.

## Subscriptions

- `@strawberry.subscription` async generator resolvers. Cancellation seen as `asyncio.CancelledError`.
- Protocols (`strawberry.subscriptions`): `GRAPHQL_TRANSPORT_WS_PROTOCOL`, `GRAPHQL_WS_PROTOCOL` (legacy), `MULTIPART_SUBSCRIPTION_PROTOCOL` (Apollo multipart HTTP, opt-in since 0.320.0), `GRAPHQL_SSE_PROTOCOL` (0.320.0, opt-in).
- Pick per view with `subscription_protocols=[...]`. Default is the two websocket protocols.
- `graphql-transport-ws` single result operations: queries and mutations over the socket (0.101.0).
- SSE: distinct connections mode only. Single connection mode not supported. Comment heartbeats. `Last-Event-ID` readable from request for resumption. No `id:` lines emitted. No replay buffer.
- SSE and multipart need async streaming integrations (ASGI, FastAPI, AIOHTTP, Litestar, Quart, Sanic, async Django, async Channels). Not Flask, Chalice, sync Django.
- View options `keep_alive`, `keep_alive_interval`, `connection_init_wait_timeout` (ASGI, Litestar, Channels).
- `on_ws_connect(context)`: accept, reject or add payload to `connection_ack`.
- No pub/sub backend in core. Channels integration gives `ws.listen_to_channel("type", groups=[...])` over Django channel layers. Other integrations need a user-provided broker.
- No subscription filtering DSL.

## Incremental delivery (experimental)

- `@defer` and `@stream` with `StrawberryConfig(enable_experimental_incremental_execution=True)`. Needs `graphql-core>=3.3.0a9` (0.277.0).
- `strawberry.Streamable[T]`: list field that can be streamed from an async generator.
- Extensions (including `MaskErrors`) only see the initial payload. Only `on_stream_result` sees patches.

## File uploads

- `strawberry.file_uploads.Upload` scalar. GraphQL multipart request spec. Single, list, nested files.
- Off by default. `multipart_uploads_enabled=True` on the view. Docs require CSRF protection.
- Runtime type depends on framework (Starlette `UploadFile`, Django `UploadedFile`, Werkzeug `FileStorage`, and so on).
- `UploadDefinition` + `scalar_overrides={UploadFile: UploadDefinition}`: use the framework type in annotations (0.289.8).

## HTTP layer and integrations

- Shared base: `strawberry.http.sync_base_view.SyncBaseHTTPView` and `async_base_view.AsyncBaseHTTPView`. Custom integrations implement a request adapter and a few methods. `docs/integrations/creating-an-integration.md`.
- Common view options: `schema`, `graphql_ide="graphiql"|"apollo-sandbox"|"pathfinder"|None`, `allow_queries_via_get=True`, `subscription_protocols`, `multipart_uploads_enabled=False`.
- Common overrides: `get_context`, `get_root_value`, `process_result`, `decode_json`, `encode_json`, `render_graphql_ide`, `on_ws_connect`.
- GET requests only allow queries. Mutations over GET are rejected. GET disabled with `allow_queries_via_get=False`.
- Query batching: list of operations in one POST. `batching_config` with `max_operations` (0.278.0). Not with multipart subscriptions.
- GraphiQL keeps query, variables and headers in the URL for sharing (0.288.4).
- Response headers and status via `info.context["response"]` (`TemporalResponse` in some integrations).
- ASGI: `strawberry.asgi.GraphQL` (Starlette-based). Background tasks via Starlette response.
- FastAPI: `strawberry.fastapi.GraphQLRouter(schema, context_getter=, root_value_getter=, ...)`. Context via FastAPI `Depends`. `BaseContext` class. Accepts `APIRouter` kwargs (0.225.0).
- Starlette: uses the ASGI app.
- AIOHTTP: `strawberry.aiohttp.views.GraphQLView`.
- Django: `strawberry.django.views.GraphQLView` and `AsyncGraphQLView`. Multipart subscriptions only on async view. WebSockets need Channels.
- Channels: `GraphQLProtocolTypeRouter`, `GraphQLHTTPConsumer`, `GraphQLWSConsumer`. `listen_to_channel` for channel layers. Test helper `strawberry.channels.testing.GraphQLWebsocketCommunicator`.
- Flask: `GraphQLView` and `AsyncGraphQLView`. No subscriptions.
- Quart: `GraphQLView` with websockets (0.270.0).
- Sanic: `GraphQLView`.
- Litestar: `strawberry.litestar.make_graphql_controller(...)` with `context_getter`, `root_value_getter`, `path`, `keep_alive`, `connection_init_wait_timeout`.
- Chalice (AWS Lambda): sync only, no subscriptions.
- Starlite removed (0.238.0).

## Pydantic integration (`strawberry.experimental.pydantic`)

- `@type(model=, name=, description=, directives=, all_fields=, include_computed=, use_pydantic_alias=True)`, `@input(...)`, `@interface(...)`.
- `@error_type(model=)`: each field becomes a list of error messages.
- Fields listed with `strawberry.auto`. `all_fields=True` exposes everything. Extra non-model fields allowed.
- `Type.from_pydantic(instance, extra={...})` and `instance.to_pydantic()`. Validation only runs in `to_pydantic`. Custom `from_pydantic`/`to_pydantic` overrides.
- Constrained types map to plain types. Constraints are not in the schema.
- Pydantic v1 and v2 (including `pydantic.v1` on v2).
- Still marked experimental.

## Federation (`strawberry.federation`)

- Apollo Federation 2 only. v1 removed (0.285.0). `strawberry.federation.Schema(..., federation_version="2.0".."2.11")`, default 2.11.
- Adds `_service { sdl }` and `_entities` automatically. `@link` added automatically.
- `@strawberry.federation.type(keys=[...], extend=, shareable=, inaccessible=, authenticated=, policy=, requires_scopes=, tags=)`.
- `@strawberry.federation.interface(keys=[...])` and `@strawberry.federation.interface_object(keys=[...])`.
- `strawberry.federation.field(external=, requires=, provides=, override=, shareable=, inaccessible=, authenticated=, policy=, requires_scopes=, tags=)`.
- Federation variants of `input`, `enum`, `enum_value`, `scalar`, `union`, `argument`, `mutation`.
- `resolve_reference(cls, **key_fields, info=)` classmethod on entities. Default implementation builds the type from key fields (0.141.0).
- Directive classes (`strawberry.federation.schema_directives`): `Key(fields, resolvable=)`, `External`, `Requires`, `Provides`, `Shareable`, `Tag`, `Override(from, label=)` (progressive override), `Inaccessible`, `ComposeDirective`, `InterfaceObject`, `Authenticated`, `RequiresScopes`, `Policy`, `Context`, `FromContext`, `Cost`, `ListSize`, `Link`.
- `@strawberry.federation.schema_directive(..., compose=True)`: expose a custom directive on the supergraph via `@composeDirective`.
- `strawberry.federation.params`: shared TypedDicts for third-party libraries (0.303.0).
- `ApolloFederationTracingExtension`: FTV1 inline traces.
- No gateway or router. Users run Apollo Router or Gateway.
- `federation-compatibility/` directory in the repo runs the Apollo subgraph compatibility suite.

## CLI (`strawberry`, extra `strawberry-graphql[cli]`)

- `strawberry dev module:schema --host --port --log-level --app-dir`: dev server with GraphiQL and auto reload. Renamed from `strawberry server` (removed 0.301.0).
- `strawberry export-schema module:schema --output file.graphql --app-dir`: print SDL. Accepts a callable that returns a schema (0.262.0).
- `strawberry codegen --schema module:schema -o outdir -p python|typescript|<dotted.path> query.graphql`: typed client code from operations (experimental).
- `strawberry schema-codegen schema.graphql -o out.py`: SDL to Strawberry Python code (0.209.0). Handles federation SDL (0.223.0). Nullable input fields become `Maybe[T | None]` (0.290.0).
- `strawberry locate-definition module:schema Type.field`: prints `path:line:column`. Works with the VS Code Relay extension (0.275.0).
- `strawberry upgrade <codemod> paths --python-target --use-typing-extensions`: libcst codemods `annotated-union`, `update-imports`, `maybe-optional`, `replace-scalar-wrappers`.

## Codegen

- Query codegen plugins (`strawberry.codegen`): `PythonPlugin`, `TypeScriptPlugin`, `PrintOperationPlugin`. Custom plugins subclass `QueryCodegenPlugin` with `on_start`, `on_end`, `generate_code(types, operation)`. `ConsolePlugin` orchestrates output.
- Codegen output is result types for one operation. It is not a full client.
- Schema codegen is a one-shot SDL-to-code converter. No schema-first runtime binding.

## Typing and editors

- Works with mypy and Pyright without a plugin through `dataclass_transform` and overloads.
- `strawberry.ext.mypy_plugin`: only needed for `experimental.pydantic`. Removed in 0.302.0, restored minimal in 0.310.2.
- Pylance basic mode supported. Strict mode not supported per docs.

## Testing

- `schema.execute_sync` / `await schema.execute` / `await schema.subscribe` in plain tests.
- HTTP test clients: `strawberry.test.BaseGraphQLTestClient`, `strawberry.asgi.test.GraphQLTestClient`, `strawberry.aiohttp.test.GraphQLTestClient`, `strawberry.django.test.GraphQLTestClient`. `client.query(query, variables=, headers=, files=, assert_no_errors=True)`. Verbose error output (0.325.0).
- Channels: `GraphQLWebsocketCommunicator(application, path, connection_params=)`.

## Upgrades and maintenance

- Breaking changes listed per version in `docs/breaking-changes/`. Codemods for some.
- Release per merged PR. Very high release cadence (0.327 at time of check).
- Continuous compatibility testing against strawberry-django (0.327.1).

## Not supported or not in scope

- No schema-first / SDL-first runtime. SDL is only for codegen.
- No ORM integration in core. Django ORM is in strawberry-django. SQLAlchemy is in strawberry-sqlalchemy.
- No query optimizer or lookahead-based prefetching in core. Only `info.selected_fields`.
- No filtering, ordering or offset pagination primitives in core. Relay connections only.
- No automatic CRUD mutations. No mutation input validation beyond pydantic integration.
- No query complexity or cost limits. Federation `@cost`/`@listSize` are emitted as directives only. I think they are not enforced (no code found that reads them).
- No built-in persisted queries or APQ. Only an extension hook recipe.
- No response caching or `@cacheControl`. Only an example directive in docs.
- No rate limiting.
- No per-request schema visibility (hide fields per user). `get_fields` is build-time only.
- No type-level or row-level permissions. Field-level `BasePermission` only.
- No authentication or JWT.
- No pub/sub broker abstraction for subscriptions outside Channels.
- No SSE single connection mode.
- No sync DataLoader.
- No federation gateway.
- No docstring-to-description mapping. I think this is so (not verified in source).
- No built-in error code system or standard mutation payload types.

## Sources

Repo: https://github.com/strawberry-graphql/strawberry (shallow clone at `/tmp/strawberry`, main branch, 2026-09-27, version 0.327.7).

Docs read (repo `docs/` source of https://strawberry.rocks/docs):
- `docs/index.md` (https://strawberry.rocks/docs)
- `docs/general/schema-basics.md`, `queries.md`, `mutations.md`, `subscriptions.md`, `multipart-subscriptions.md`, `upgrades.md`
- `docs/types/object-types.md`, `resolvers.md`, `schema.md`, `schema-configurations.md`, `scalars.md`, `enums.md`, `input-types.md`, `interfaces.md`, `union.md`, `defer-and-stream.md`, `exceptions.md`, `generics.md`, `lazy.md`, `maybe.md`, `operation-directives.md`, `private.md`, `schema-directives.md`, `unset.md`
- `docs/guides/accessing-parent-data.md`, `authentication.md`, `convert-to-dictionary.md`, `custom-extensions.md`, `dataloaders.md`, `errors.md`, `federation.md`, `federation-v1.md`, `field-extensions.md`, `file-upload.md`, `permissions.md`, `query-batching.md`, `relay.md`, `schema-export.md`, `server.md`, `tools.md`
- `docs/guides/pagination/overview.md`, `offset-based.md`, `cursor-based.md`, `connections.md`
- `docs/extensions.md` and all `docs/extensions/*.md`
- `docs/federation/introduction.md`, `entities.md`, `entity-interfaces.md`, `custom_directives.md`
- `docs/integrations/index.md`, `creating-an-integration.md`, `pydantic.md` (full). `aiohttp.md`, `asgi.md`, `chalice.md`, `channels.md`, `django.md`, `fastapi.md`, `flask.md`, `litestar.md`, `quart.md`, `sanic.md`, `starlette.md` (options and hooks)
- `docs/operations/deployment.md`, `testing.md`, `tracing.md`
- `docs/codegen/query-codegen.md`, `schema-codegen.md`, `docs/cli/locate-definition.md`
- `docs/editors/mypy.md`, `vscode.md`, `docs/concepts/async.md`, `typings.md`, `docs/faq.md`, `docs/errors.md`
- `docs/breaking-changes.md` and `docs/breaking-changes/0.279.0.md`, `0.283.0.md`, `0.285.0.md`, `0.288.0.md`, `0.320.0.md`

Changelog: `CHANGELOG.md` in the repo (0.7 to 0.327.7). Skimmed feature entries.

Source files checked:
- `strawberry/__init__.py`, `schema/config.py`, `schema/schema.py`, `schema/base.py`, `schema/name_converter.py`
- `strawberry/types/object_type.py`, `field.py`, `arguments.py`, `enum.py`, `scalar.py`, `union.py`, `info.py`, `cast.py`, `execution.py`, `nodes.py`
- `strawberry/directive.py`, `schema_directive.py`, `schema_directives.py`, `permission.py`, `dataloader.py`
- `strawberry/extensions/__init__.py`, `extensions/tracing/__init__.py`
- `strawberry/federation/__init__.py`, `field.py`, `object_type.py`, `params.py`, `schema.py`, `schema_directives.py`
- `strawberry/relay/__init__.py`, `strawberry/experimental/pydantic/object_type.py`
- `strawberry/http/__init__.py`, `http/base.py`, `http/async_base_view.py`, `strawberry/asgi/__init__.py`, `strawberry/django/views.py`
- `strawberry/cli/commands/*.py`, `cli/commands/upgrade/__init__.py`, `strawberry/codegen/plugins/`, `strawberry/test/client.py`

Web docs site was not fetched. The docs source is in the repo. `https://strawberry.rocks/llms.txt` returned 404 for an earlier agent. I did not retry it.
