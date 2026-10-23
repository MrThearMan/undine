# gqlgen findings

Versions checked: v0.17.95 (latest release, 2026-09-01). Repo `master` at `8aab35e` (last commit 2026-10-03, `graphql.Version = "v0.17.95-dev"`). Docs source is in the repo (`docs/content/`, Hugo, about 5800 lines of Markdown). All doc pages read. Config, handler, transports, extensions, plugin and federation code spot-checked.
gqlgen is the 99designs Go GraphQL server library. MIT. Schema-first: you write SDL, run `gqlgen generate`, and get type-safe Go code (exec code, models, resolver stubs). Parser and validator come from `github.com/vektah/gqlparser/v2`.
Stack: Go 1.25 minimum (since v0.17.87). WebSocket on `github.com/coder/websocket`. YAML via `goccy/go-yaml`.

## Maintenance status

- Active. 10763 stars. Not archived. 387 open issues plus PRs. Releases every 2 to 6 weeks.
- Still `0.17.x`. No 1.0. Breaking changes ship in patch releases (for example v0.17.92 changed public defer structs).
- `CHANGELOG.md` is stale. It stops at v0.17.50 (2024-09-13). Changes after that are only in GitHub release notes.
- New maintainer UnAfraid added in v0.17.79. StevenACoffman does most releases.
- https://gqlgen.com/llms.txt returns 404. `Accept: text/markdown` returns HTML.
- Project has `RULES.md` and `RULES_CITATIONS.md` (contribution rules, added v0.17.93) and a JSON schema for the config file (`gqlgen.schema.json`, added v0.17.86).

## Big changes in recent releases

- v0.17.71 (2025-04): complexity functions get `context`. `local_prefix` option. Large-project multi-team example.
- v0.17.73: bind from basic type to named type. `json.Marshaler` removed from resolvers.
- v0.17.75: `UseGrapQLResponseJsonByDefault` on GET/POST transports.
- v0.17.77 / .79: executor exposes GraphQL validation rules for customization (`SetValidationRulesFn`). Support for all signed and unsigned int sizes. Field hooks can return nil to drop a field from the model.
- v0.17.81: CSRF fix in embedded Apollo Sandbox. `federation.options.entity_resolver_multi`.
- v0.17.82: GraphiQL 4. `WithApolloSandboxJs`. Embedded structs. Embedded base types for interfaces. Error presenter can silence errors. Faster `CollectFields` for list fields.
- v0.17.84: `@inlineArguments`. Interface embedding moved from config to `@goEmbedInterface`. Complexity override can lower the score.
- v0.17.85: optional enum JSON marshalers (`omit_enum_json_marshalers`). Complexity functional options. Field middleware can return a marshaler. `@deprecated` on arguments in introspection. Manually extended unions.
- v0.17.86: `gqlgen.yml` JSON schema. `autobind_getter_haser` for protobuf getters. Resolver rewrite keeps directive comments such as `//nolint`.
- v0.17.87: batch resolvers start (`@goField(batch: true)`, `forceGenerate` on `@goField`). Object-level directives on federation entity resolvers.
- v0.17.88: incremental code generation for `follow-schema` layout (`api.GenerateIncremental`).
- v0.17.90: `FieldRequested` / `AnyFieldRequested`. Panic recovery returns 500 (not 422).
- v0.17.91: global `resolver.batch`. `graphql.MarkNonNull` (runtime non-null). SSE `MinEventInterval`. WebSocket `PayloadReadLimit`, custom close code and reason, `WebsocketError` unwrapping. Old pre-0.11 handler compatibility layer removed. Gorilla websocket deprecated.
- v0.17.92: gorilla websocket removed (coder/websocket only). BREAKING: `@defer` de-duplication fix and public defer structs changed.
- v0.17.93: `@subscriptionContext` and `subscription_context_field` (per-event context for subscriptions).
- v0.17.94: federation per-entity `@requires` strategies, `preloaded_requires`, `@computedRequires`. Disable suggestions also for scalar leaves.
- v0.17.95: `resolver.omit_resolver_embedding`. GraphiQL URL state persistence (`WithGraphiqlPersistStateInURL`). Go 1.27 `any` changes.

## Code generation and CLI

- CLI: `gqlgen init` (flags `--config`, `--server`, `--schema`), `gqlgen generate` (`--config`, `--verbose`), `gqlgen version`. Usually run as `go tool gqlgen` (Go 1.24 tool deps) or via `//go:generate`.
- Config lookup: `gqlgen.yml` (also `.gqlgen.yml`, `gqlgen.yaml`) in the current dir or any parent. Falls back to a default config if none found.
- Programmatic: `api.Generate(cfg, opts...)`, `api.GenerateIncremental(cfg, changedSchemas, verbose, opts...)` (only regenerates files for changed schema files, follow-schema layout). Options: `api.AddPlugin`, `api.PrependPlugin`, `api.ReplacePlugin`, `api.NoPlugins`.
- Config loaders: `config.LoadConfigFromDefaultLocations()`, `config.LoadConfig(path)`, `config.LoadDefaultConfig()`.
- Output: exec code (`generated.go` or per-schema `*.generated.go`), models (`models_gen.go`), resolver stubs (`*.resolvers.go`), federation file.
- Resolver regeneration: existing resolver bodies are kept. Unused resolvers move to a commented block at file end. `preserve_resolver` stops rewriting existing resolvers.
- Generated code validation: after generation it compiles the output (`skip_validation`, `fast_validation` tune this). Runs `go mod tidy` (`skip_mod_tidy`).
- Name collision handling for enum constants: CapitalCase first, then suffixes. Order dependent (docs warn about this).

## Config file (`gqlgen.yml`)

Top-level keys in `codegen/config/config.go`:
- `schema`: list of SDL files. Globs (`**`) allowed.
- `exec`: `package`, `layout` (`single-file` or `follow-schema`), `filename`, `dir`, `filename_template` (`{name}`), `worker_limit` (max goroutines per child resolvers, default unlimited).
- `model`: `filename`, `package`, `model_template` (custom gotpl).
- `federation`: `filename`, `package`, `version` (1 or 2), `options` map (`explicit_requires`, `computed_requires`, `entity_resolver_multi`, `preloaded_requires`). Unknown option is an error.
- `resolver`: `package`, `layout` (`follow-schema` or `single-file`), `filename`, `dir`, `filename_template`, `type` (root resolver type name), `batch` (bool or `{enabled: bool}`), `omit_template_comment`, `resolver_template`, `preserve_resolver`, `omit_resolver_embedding`.
- `autobind`: list of Go packages. Types with matching names are bound instead of generated.
- `autobind_getter_haser`: bind to `GetX()` / `HasX()` methods (protobuf editions).
- `models`: map GraphQL type name to `model` (one or list of Go types, first is default), `forceGenerate`, `fields.<name>` (`resolver`, `fieldName`, `type`, `omittable`, `autoBindGetterHaser`, `batch`, `forceGenerate`), `enum_values.<NAME>.value` (bind enum values to Go consts), `extraFields.<GoName>` (`type`, `overrideTags`, `description`), `embedExtraFields`.
- `struct_tag`: tag name used for binding (`gqlgen:"name"`, or `json`).
- `embedded_structs_prefix`: prefix for generated base structs (default `Base`).
- `directives.<name>`: `skip_runtime` (codegen only, hidden from introspection), `Implementation` (static Go func source so no `DirectiveRoot` hook is generated. The struct field has no yaml tag, so I think it is only for plugins).
- `local_prefix`: split local imports into their own group.
- `go_build_tags`: build tags for package loading.
- `go_initialisms`: `replace_defaults`, `initialisms` list for Go names.
- Model shape flags: `omit_slice_element_pointers`, `omit_getters` (interface getters), `omit_interface_checks` (`Is<Name>()`), `omit_root_models`, `omit_resolver_fields`, `struct_fields_always_pointers`, `resolvers_always_return_pointers`, `return_pointers_in_unmarshalinput`, `nullable_input_omittable` (wrap nullable inputs in `graphql.Omittable`), `enable_model_json_omitempty_tag` (default true), `enable_model_json_omitzero_tag` (default false), `omit_enum_json_marshalers`, `omit_typed_input_unmarshalers`.
- Exec flags: `omit_complexity`, `omit_panic_handler` (let panics crash), `omit_gqlgen_file_notice`, `omit_gqlgen_version_in_file_notice`, `use_function_syntax_for_execution_context` (for schemas over 65,000 methods), `subscription_context_field`, `call_argument_directives_with_null`.
- Generation speed flags: `skip_validation`, `skip_mod_tidy`, `fast_validation` (`-gcflags="-N -l"`), `skip_import_grouping` (`go/format` instead of `imports.Process`), `use_buffer_pooling`.
- Removed: `use_light_mode_prefetch` (v0.17.89).
- Default `models` mapping in `gqlgen init`: `ID` to `graphql.ID`/`Int`/`Int64`/`Int32`, `Int` to `graphql.Int32`, `Int64` to `graphql.Int`/`Int64`, `UUID` to `graphql.UUID`.

## Built-in codegen directives

All are `skip_runtime` (not in introspection). You must declare them in your SDL.
- `@goModel(model, models, forceGenerate)` on OBJECT, INPUT_OBJECT, SCALAR, ENUM, INTERFACE, UNION: bind to Go type or force generation.
- `@goField(forceResolver, name, omittable, type, autoBindGetterHaser, forceGenerate, batch)` on FIELD_DEFINITION, INPUT_FIELD_DEFINITION.
- `@goTag(key, value)` repeatable: add struct tags. `value` omitted removes or sets empty.
- `@goExtraField(name, type, overrideTags, description)` repeatable on OBJECT, INPUT_OBJECT: hidden Go-only struct fields. No name means embedded.
- `@goEnum(value)` on ENUM_VALUE: bind enum value to a Go const or var (typed or untyped, int enums possible).
- `@goEmbedInterface` on INTERFACE: generate `Base<Interface>` struct and embed it in implementors.
- `@inlineArguments` on ARGUMENT_DEFINITION: flatten an input object argument into separate resolver parameters.
- `@subscriptionContext` on FIELD_DEFINITION: subscription resolver returns `<-chan graphql.Event[T]` with a per-event `Context`.
- Spec directives `@skip`, `@include`, `@deprecated` (also on arguments and input fields), `@specifiedBy`, `@oneOf` are handled. `@oneOf` shows in introspection (`isOneOf`).
- `@defer(if, label)` is supported at execution. Delivered over `transport.MultipartMixed` or SSE. `@stream` is not supported.

## Custom (runtime) directives

- Declare in SDL. gqlgen adds a field to `DirectiveRoot`. Signature `func(ctx, obj any, next graphql.Resolver, <args>) (any, error)`. Set on `Config.Directives.<Name>`.
- Runtime locations: FIELD_DEFINITION, ARGUMENT_DEFINITION, INPUT_FIELD_DEFINITION, OBJECT, INPUT_OBJECT, plus executable QUERY, MUTATION, SUBSCRIPTION, FIELD (client-written directives, see `MarkNonNull` recipe).
- Not supported at runtime: SCALAR, ENUM, INTERFACE, UNION (issue #760).
- `obj` is the parent object for field directives, and the args map for argument directives.
- `call_argument_directives_with_null`: argument directives run even when the value is null, so they can set defaults.
- Typical use: `@hasRole` auth checks (docs example).

## Type binding and models

- Bind GraphQL fields to struct fields (case-insensitive), methods (optional `ctx` first arg, method runs in parallel then), struct tags (`struct_tag`), or config `fieldName`. Embedded structs are walked. Struct tag binding has top priority.
- A field gets a resolver when no binding exists, or with `forceResolver` / `resolver: true`. Docs recommend this to avoid eager fetching of child objects.
- Interfaces and unions become Go interfaces with marker methods `Is<Name>()` and getters (both optional).
- Input objects generate structs. Map an input to `map[string]interface{}` for changesets (values are coerced to schema types). `graphql.Omittable[T]` (`IsSet`, `Value`, `ValueOK`, `OmittableOf`) for unset vs null.
- Generated input unmarshal helpers: typed `Unmarshal<Input>` and `graphql.UnmarshalNamedInputFromContext` (lookup by GraphQL input name, master change #4334).
- Enums generate string types with constants, `IsValid`, `MarshalGQL`/`UnmarshalGQL`, and JSON marshalers (optional).
- Modelgen hooks: `modelgen.Plugin{MutateHook, FieldHook}`. `BuildMutateHook(*ModelBuild)` and `FieldMutateHook(td, fd, *Field)`. Built-ins `DefaultBuildMutateHook`, `DefaultFieldMutateHook`, `GoTagFieldHook`, `GoFieldHook`. Docs example adds ORM tags and `go-playground/validator` tags from a `@constraint` directive.
- Type-system extensions and manually extended unions are supported (`_examples/type-system-extension`, `_examples/union-extension`).

## Scalars

- Built in: `ID`, `String`, `Int` (bindable to Go `int`, `int32`, `int64`), `Float`, `Boolean`.
- Helpers with marshalers in `graphql`: `Int64`, `Int32`, `Int16`, `Int8`, `Uint`, `Uint64`, `Uint32`, `Uint16`, `Uint8`, `IntID`, `UintID`, `Time` (RFC3339Nano), `Date` (undocumented), `Duration` (ISO 8601), `UUID` (`google/uuid`), `Map`, `Any`, `Upload`.
- Custom scalars: implement `graphql.Marshaler`/`Unmarshaler` (`MarshalGQL`, `UnmarshalGQL`), or `ContextMarshaler`/`ContextUnmarshaler` (with ctx, can return errors). For third-party types, write `MarshalX`/`UnmarshalX` functions and point the model at `pkg.X`.
- Unmarshal errors report the full input path (for example `updateUser.userInput.primaryContactDetails.email`). Marshal errors need the context style.

## Resolvers and execution

- Generated `ResolverRoot` with per-type resolver interfaces (`QueryResolver`, `TodoResolver`, ...). User implements them.
- Field resolvers run concurrently in goroutines. `exec.worker_limit` caps concurrency. Open PR #4270 makes it runtime-configurable.
- Model methods with `ctx` run concurrently.
- Batch resolvers: `@goField(batch: true)` or `resolver.batch: true`. Signature takes `[]*Parent` and returns `[]T` by index. Partial failure via `graphql.BatchErrors` / `graphql.BatchErrorList`. Not for root types, input types, introspection, federation `_Service`/`Entity`. Fields opt out with `batch: false`.
- Field collection helpers: `graphql.CollectFieldsCtx(ctx, satisfies)`, `graphql.CollectFields(opCtx, selections, satisfies)`, `graphql.CollectAllFields(ctx)`, `graphql.FieldRequested(ctx, "a.b.c")`, `graphql.AnyFieldRequested(ctx, paths...)` (respect `@skip`/`@include`, fragments, aliases). Docs show building a preload list for ORMs.
- Runtime non-null: `graphql.MarkNonNull(ctx)` makes a nullable field act as non-null for one request. Docs recipe uses a client `@priority(value: REQUIRED)` directive on FIELD.
- Context accessors: `GetFieldContext` (`Parent`, `Object`, `Args`, `Field`, `Index`, `Result`, `IsMethod`, `IsResolver`, `NonNull`), `GetOperationContext` (`RawQuery`, `Variables`, `OperationName`, `Doc`, `Extensions`, `Headers`, `Operation`, `DisableIntrospection`, `Stats`), `GetRootFieldContext`, `GetPath`.
- Response extensions: `graphql.RegisterExtension(ctx, key, value)`, `GetExtensions`, `GetExtension`.
- Complexity: generated `ComplexityRoot` with one func per field. Set `Config.Complexity.<Type>.<Field> = func(childComplexity, args...) int`.
- `executor.New(es)`: run operations without the HTTP handler.

## Errors

- Resolvers return `error`. Messages go to clients as is.
- Multiple errors: `graphql.AddError(ctx, err)`, `graphql.AddErrorf(ctx, ...)`, or return `gqlerror.List`. `gqlerror.Error{Message, Path, Extensions}`.
- `srv.SetErrorPresenter(func(ctx, err) *gqlerror.Error)`. `graphql.DefaultErrorPresenter`. Presenter can return nil to silence an error (v0.17.82).
- `srv.SetRecoverFunc(func(ctx, any) error)`. `graphql.DefaultRecover`. `omit_panic_handler` turns recovery off in generated code.
- Error helpers: `graphql.HasFieldError`, `GetFieldErrors`, `GetErrors`.
- `graphql/errcode`: codes `GRAPHQL_VALIDATION_FAILED`, `GRAPHQL_PARSE_FAILED`, `errcode.Set(err, code)`, `RegisterErrorType(code, kind)`, `GetErrorKind`. Undocumented.
- HTTP status: 422 for validation and complexity errors. 500 for panics (since v0.17.90).

## HTTP handler (`graphql/handler`)

- `handler.New(es)`. `handler.NewDefaultServer(es)` is deprecated (examples only). It adds Websocket, Options, GET, POST, MultipartForm, LRU query cache (1000), Introspection, APQ (LRU 100).
- Server methods: `AddTransport`, `Use(extension)`, `AroundOperations`, `AroundResponses`, `AroundRootFields`, `AroundFields`, `SetErrorPresenter`, `SetRecoverFunc`, `SetQueryCache(graphql.Cache[*ast.QueryDocument])`, `SetParserTokenLimit`, `SetDisableSuggestion` (no "did you mean" hints), `SetValidationRulesFn(func() *rules.Rules)` (add or remove gqlparser validation rules).
- Inline function types: `handler.OperationFunc`, `handler.ResponseFunc`, `handler.FieldFunc`.
- Cache: `graphql.Cache[T]` interface (`Get`, `Add`). `graphql/handler/lru.New[T](size)`. `graphql.MapCache`, `graphql.NoCache`.
- The server picks the first transport that `Supports` the request, so order matters (SSE and Websocket first).
- No built-in CORS. Docs use `rs/cors`. Works with any `net/http` middleware. Gin recipe.

## Handler extension interfaces

- `graphql.HandlerExtension` (`ExtensionName`, `Validate(schema)`) plus any of:
- `OperationParameterMutator.MutateOperationParameters(ctx, *RawParams)`: before parsing (APQ uses it).
- `OperationContextMutator.MutateOperationContext(ctx, *OperationContext)`: after parse and validate, before execution (complexity, introspection use it).
- `OperationInterceptor.InterceptOperation(ctx, next)`: around each operation.
- `ResponseInterceptor.InterceptResponse(ctx, next)`: around each response (many per subscription).
- `RootFieldInterceptor.InterceptRootField(ctx, next)`.
- `FieldInterceptor.InterceptField(ctx, next)`: around each field.
- Short-circuit rule: wrap error responses with `graphql.OneShot(graphql.ErrorResponse(ctx, msg))`, else streaming transports loop forever.

## Built-in extensions

- `extension.Introspection{}`: introspection is off unless this is added. Per request off via `OperationContext.DisableIntrospection`.
- `extension.AutomaticPersistedQuery{Cache}`: Apollo APQ (SHA-256). Errors `PersistedQueryNotFound`. `extension.GetApqStats(ctx)`.
- `extension.ComplexityLimit{Func}` (per request limit), `extension.FixedComplexityLimit(n, opts...)`. Options `complexity.WithFixedScalarValue(v)`, `complexity.WithIgnoreFields(set)`. `extension.GetComplexityStats(ctx)`. `complexity.Calculate(...)` exposed.
- `apollotracing.Tracer{}`: Apollo tracing v1 in response `extensions`.
- `apollofederatedtracingv1.Tracer{ClientName, Version, Hostname, ErrorOptions, Logger}`: FTV1 traces when header `apollo-federation-include-trace: ftv1`. `ErrorOptions.ErrorOption` `masked`/`all`/`transform` with `TransformFunction`.
- `debug.Tracer{}`: pretty-prints operations and responses to a writer. Undocumented.
- Query document cache via `SetQueryCache`.

## Transports (`graphql/handler/transport`)

- `POST{ResponseHeaders, UseGrapQLResponseJsonByDefault}`: JSON body. Supports `application/graphql-response+json`.
- `GET{ResponseHeaders, UseGrapQLResponseJsonByDefault}`: query in URL. Only query operations. Mutations rejected.
- `MultipartForm{MaxUploadSize, MaxMemory, ResponseHeaders}`: GraphQL multipart request spec (file uploads, `graphql.Upload{File, Filename, Size, ContentType}`).
- `UrlEncodedForm{ResponseHeaders}`: `application/x-www-form-urlencoded`. Mentioned only in the 0.11 migration page.
- `GRAPHQL{ResponseHeaders}`: `application/graphql` body. Mentioned only in the 0.11 migration page.
- `Options{AllowedMethods}`: answers OPTIONS requests.
- `MultipartMixed{Boundary, DeliveryTimeout}`: incremental delivery for `@defer` (`multipart/mixed`). Undocumented.
- `SSE{KeepAlivePingInterval, MinEventInterval}`: graphql-sse "distinct connections" mode. POST with `Accept: text/event-stream`.
- `Websocket{Implementation, InitFunc, InitTimeout, ErrorFunc, CloseFunc, KeepAlivePingInterval, PongOnlyInterval, PingPongInterval, MissingPongOk, PayloadReadLimit}`. Protocols `graphql-ws` (legacy, default) and `graphql-transport-ws`. `transport.CoderWebsocketImplementation{AcceptOptions}` for origin checks and subprotocols. Pluggable adapter interfaces `WebsocketImplementation`, `WebsocketConn`, `WebsocketReadLimiter`, `WebsocketReadDeadliner`. `InitFunc(ctx, InitPayload) (ctx, *InitPayload, error)` for auth with connection params. `transport.AppendCloseReason(ctx, reason)` and `transport.WithWebsocketCloseCode(ctx, code)` for custom close. Default payload limit 1 MB.

## Subscriptions

- Resolver returns `(<-chan T, error)`. Closing the channel ends the subscription. Cancel via `ctx.Done()`.
- Per-event context: `@subscriptionContext` or `subscription_context_field: true`. Returns `<-chan graphql.Event[T]{Context, Value}`. Event context reaches `AroundResponses`. Does not compose with SUBSCRIPTION-location directives yet.
- Transports: Websocket and SSE. No built-in pub/sub broker. Example apps `_examples/chat`, `_examples/mini-habr-with-subscriptions`.

## Federation (`plugin/federation`)

- Apollo Federation v1 and v2. v2 via `version: 2` or `@link` in schema. Supports `@key` (with `resolvable`), `@requires`, `@provides`, `@external`, `@extends`, `@shareable`, `@inaccessible`, `@override(from, label)`, `@tag`, `@interfaceObject`, `@composeDirective`, `@link`, `@authenticated`, `@requiresScopes`, `@policy`. Generates `_service`, `_entities`, `_Any`, `FieldSet`.
- Not supported: `@context` / `@fromContext`, `@cost`, `@listSize`. I did not find them in the code.
- Entity resolvers: `entityResolver.Find<Type>By<Keys>(ctx, keys...)`. Multiple `@key`s generate multiple finders.
- `@entityResolver(multi: true, requires: "...")`: batch finder `Find<Type>By<Keys>s(ctx, reps []*<Type>By<Keys>sInput)`. Global `entity_resolver_multi`. Docs say `multi` becomes the default in a future major.
- `@requires` strategies: default (unmarshal onto returned entity), `explicit_requires` (`Populate<Entity>Requires` hook, deprecated), `computed_requires` (field resolver gets `federationRequires map[string]any`), `preloaded_requires` (requires data on batch input before call, flat scalars and enums only). Per field `@computedRequires`. Per entity override with `@entityResolver(requires:)`.
- Per-entity batch errors with `graphql.BatchErrorList`. Errors are reported at `_entities[i]`.
- Object-level directives apply to entity resolvers (v0.17.87).
- FTV1 tracing via `apollofederatedtracingv1`.

## Playgrounds (`graphql/playground`)

- `playground.Handler(title, endpoint, opts...)`: GraphiQL 4. Options `WithGraphiqlFetcherHeaders`, `WithGraphiqlUiHeaders`, `WithGraphiqlPersistStateInURL`, `WithGraphiqlVersion`, `WithGraphiqlReactVersion`, `WithGraphiqlPluginExplorerVersion`, `WithGraphiqlEnablePluginExplorer`, `WithStoragePrefix`. `HandlerWithHeaders`.
- `playground.ApolloSandboxHandler(title, endpoint, opts...)`: Apollo Sandbox embed with many `WithApolloSandbox*` options.
- `playground.AltairHandler(title, endpoint, options)`: Altair.
- None of these are documented on the site except the basic `playground.Handler`.

## Plugin system (code generation only)

- Plugin interfaces in `plugin/plugin.go` (marked EXPERIMENTAL): `Plugin.Name()`, `ConfigMutator.MutateConfig(cfg)`, `CodeGenerator.GenerateCode(data)`, `SchemaMutator.MutateSchema(schema)`, `EarlySourcesInjector.InjectSourcesEarly()`, `LateSourcesInjector.InjectSourcesLate(schema)`, `ResolverImplementer.Implement(prev, field)`. Deprecated: `EarlySourceInjector`, `LateSourceInjector`.
- Built-in plugins: `modelgen`, `resolvergen`, `federation`, `servergen` (server stub for `init`), `stubgen` (stub resolver struct).
- Use: write a `generate.go` with `api.Generate(cfg, api.AddPlugin(p))` and run it with `go generate`.
- No runtime plugin system besides handler extensions.

## Test client (`client`)

- `client.New(handler, opts...)`: in-process client for tests. `Post`, `MustPost`, `RawPost`, `Websocket`, `WebsocketOnce`, `WebsocketWithPayload`, `SSE`, `IncrementalHTTP` (`@defer` responses). Options `Var`, `Operation`, `Extensions`, `Path`, `AddHeader`, `BasicAuth`, `AddCookie`, `WithFiles`. `SetCustomDecodeConfig`, `SetCustomTarget`. Undocumented.

## Data loading

- No built-in dataloader. Docs recommend `vikstrous/dataloadgen` with a per-request HTTP middleware.
- Built-in alternatives: batch resolvers (`@goField(batch: true)`), federation multi entity resolvers, field collection for JOIN or preload.

## Security

- Introspection off by default (opt in with `extension.Introspection`).
- Query complexity limits (fixed or per request, custom per-field cost functions).
- Parser token limit (`SetParserTokenLimit`). Disable suggestions (`SetDisableSuggestion`).
- WebSocket payload limit and origin checks. Upload size limits.
- No built-in depth limit. No persisted operations allowlist (only APQ). No rate limiting. No auth framework (use directives, context middleware).

## Not supported or not in scope

- Code-first schema definition. Only SDL-first.
- `@stream`.
- Runtime directives on SCALAR, ENUM, INTERFACE, UNION.
- Relay helpers (connections, `Node`, global IDs). Users write SDL by hand.
- Filtering, ordering, pagination generation. ORM integration. Only field-collection helpers.
- Built-in dataloader, depth limiting, trusted documents, rate limiting, CORS, auth.
- OpenTelemetry or OpenTracing in core. The feature comparison page claims "Opentracing". I think this means third-party extensions (for example `otelgqlgen`). I did not verify.
- Schema stitching or gateway. Only subgraph federation.
- GraphQL client code generation. Separate project (`Yamashou/gqlgenc`), not in this repo.
- Input validation. Users add `validate` tags through modelgen hooks.

## Upcoming and unreleased work

- On `master` after v0.17.95: input unmarshalers indexed by GraphQL input name (`NewInputUnmarshalerIndex`, `WithInputUnmarshalerIndex`, `UnmarshalNamedInputFromContext`. Older APIs deprecated). Concurrent-field boilerplate moved into the runtime. `moq` replaced by `mockery` v3. Request path fuzz target and benchmarks.
- Open PRs: `@disableConcurrency` directive to resolve fields inline (#4322), auto-fill missing non-null object fields with zero value (#4340), runtime `worker_limit` (#4270), custom response write fn in POST (#4320), hardened upload path and duplicate subscription handling (#4324), atomic file writes in codegen (#4262), WebSocket shutdown grace period (#3653), concurrent operation scheduler (#3468), goccy/go-json decoding (#3405, #3161), GraphiQL `defaultQuery` (#3266), custom Omittable type (#4082), int enum generation (#1347).
- Federation roadmap: `multi` entity resolution to become default. Single-entity finder to take the same input struct.

## Docs and code disagree

- `reference/plugins.md` says there are "only two hooks" (`MutateConfig`, `GenerateCode`). The code has seven plugin interfaces (`SchemaMutator`, `EarlySourcesInjector`, `LateSourcesInjector`, `ResolverImplementer` too).
- `config.md` sample omits `omit_getters`, `omit_panic_handler`, `enable_model_json_omitempty_tag`, `enable_model_json_omitzero_tag`, `resolver.type`, `resolver.batch`, `models.*.enum_values`, `extraFields`, `embedExtraFields`, `fields.*.batch`. They are documented on other pages (README, errors, model-generation, enum, extra fields, resolvers) or not at all (`resolver.type`).
- `config.md` directive list omits `@goEnum` and `@goEmbedInterface`. They are only on recipe pages.
- `recipes/migration-0.11.md` says a backward-compatibility layer keeps the old handler API. That layer was removed in v0.17.91.
- `reference/complexity.md` final example passes `gqlHandler` to `http.Handle` but names the server `srv`. Minor.
- `feature-comparison.md` claims Opentracing support. The repo has no OpenTracing or OpenTelemetry code.
- `CHANGELOG.md` says it lists "all notable changes" but stops at v0.17.50 (2024-09).
- Features in code but not in docs: `transport.MultipartMixed` and `@defer`, `transport.UrlEncodedForm` and `transport.GRAPHQL` (only migration page), `SetParserTokenLimit`, `SetDisableSuggestion`, `SetValidationRulesFn`, `debug.Tracer`, `apollotracing` (only migration page), `apollofederatedtracingv1`, Altair and Apollo Sandbox handlers, the `client` package, `api.GenerateIncremental`, `graphql/errcode`, `MarshalDate`, small int scalars, `executor.New`, `DirectiveConfig.Implementation`.

## Sources

- Docs site: https://gqlgen.com/ (config: https://gqlgen.com/config/). Source in repo `docs/content/`: `config.md`, `getting-started.md`, `_introduction.md`, `feature-comparison.md`, `reference/` (apq, changesets, complexity, dataloaders, directives, errors, field-collection, file-upload, introspection, middlewares, model-generation, name-collision, plugins, resolvers, scalars, subscription-context), `recipes/` (authentication, cors, dynamic-required-fields, enum, extra_fields, federation, gin, interfaces, migration-0.11, modelgen-hook, subscriptions).
- Repo: https://github.com/99designs/gqlgen (shallow clone, `8aab35e`). Code read in `codegen/config/`, `graphql/handler/`, `graphql/handler/transport/`, `graphql/handler/extension/`, `graphql/executor/`, `graphql/playground/`, `plugin/`, `plugin/federation/`, `api/`, `client/`, `complexity/`, `main.go`.
- Changelog (stale): https://github.com/99designs/gqlgen/blob/master/CHANGELOG.md
- Release notes: https://github.com/99designs/gqlgen/releases (v0.17.66 to v0.17.95 read).
- Unreleased: https://github.com/99designs/gqlgen/compare/v0.17.95...master
- Open PRs: https://github.com/99designs/gqlgen/pulls
- https://gqlgen.com/llms.txt (404).
