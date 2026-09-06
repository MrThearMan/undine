# async-graphql findings

Versions checked: `8.0.0-rc.5` (latest on crates.io, 2026-04-21). Latest stable is `7.2.1` (2026-01-20). Repo `master` at `82cd1f1` (last commit 2026-04-21, "Bump version"). Docs source is in the repo (`docs/en/src/`, mdBook, about 3500 lines). All English book pages read. Rustdoc attribute tables in `src/docs/*.md` read. Derive args, schema builder, extensions, http, dynamic schema, integrations and extras code spot-checked.
async-graphql is a Rust GraphQL server library. MIT or Apache-2.0. Code-first through procedural macros (derive and attribute macros). Own parser (`async-graphql-parser`) and value crate (`async-graphql-value`). Edition 2024, MSRV 1.89.

## Maintenance status

- Active but slow. 3684 stars. Not archived. 255 open issues plus PRs.
- No commits on `master` since 2026-04-21 (about 6 months). Open PRs and issues still get new activity (latest 2026-09-25).
- 8.0 has been in release-candidate state since 2026-01-22 (rc.1 to rc.5). docs.rs `latest` still shows 7.2.1.
- GitHub tags stop at `v7.0.13`. Issue #1821 "Push missing release tags". GitHub releases list is empty. crates.io is the real release channel.
- `CHANGELOG.md` has no entry for `7.2.1`.
- https://async-graphql.github.io/llms.txt and `/async-graphql/llms.txt` return 404. `Accept: text/markdown` returns HTML.
- Book also exists in Chinese (`docs/zh-CN`). Examples are in a separate repo (`async-graphql/examples`, git submodule).

## Big changes in recent releases

- 7.0.x (2024 to 2025): `@requiresScopes` (#1695), GraphiQL version option, `inputValueDeprecation` introspection, `complexity` on `SimpleObject` fields, SDL export utilities on `ExtensionContext`, type directives in dynamic schema, UUID validator, `boxed-trait` feature, directives on `ComplexObject`, `SchemaBuilder::limit_directives`, GraphiQL WS connection params, `WebSocket::on_ping`, `WebSocket::keepalive_timeout`, `#[doc = ...]` descriptions, `raw_value`, directives on `SelectionField`, directives on subscriptions, `Interface` plus `OneofObject` on one type, axum on wasm (no subscriptions), `TypeDirective` on 8 locations, `Enum(display)`, `Request::set_parsed_query`, `NextExecute::run_with_data`, generic unions, `multipart/mixed` subscriptions, `OutputType` for `Weak`.
- 7.1.0 (2026-01-02): do not bail on the first error when resolving containers. Schema-level data access (`Schema::data`). Tracing for axum subscriptions.
- 7.2.0 (2026-01-16): `trace_scalars` option on Tracing and OpenTelemetry. Macro hygiene. `jiff` support.
- 8.0.0-rc.1 (2026-01-22): lock-free data structures. Removed: `tide` integration, CBOR, BSON, `hashbrown`, `tokio-sync`, `uuid-validator`, `zxcvbn`, `smol_str`, `bigdecimal`, Altair, GraphQL Playground. GraphiQL v5. Timers and spawners are abstracted (`runtime` module). OpenTelemetry moved to `async-graphql-extras`. warp 0.4.
- 8.0.0-rc.2: `errors` serialized before `data`. `custom-error-conversion` removed. `unblock` always on with `tempfile`. Codegen rework for smaller code and faster compile. Email, URL and IP validators removed (use `EmailAddress`, `Url`, `IpAddr` types). `DataLoader::clear_one`.
- 8.0.0-rc.3: `data` entry spec fix when result has errors. No-inline on `resolve_field` helpers (stack overflow fix).
- 8.0.0-rc.4: `MergedObject` and `MergedSubscription` use a balanced tree (130+ merged types). actix integration moves to `actix-ws`. `flatten` for generic params in `InputObject`.
- 8.0.0-rc.5: `MergedObject` flat dispatch. Book tests through a `book-tests` crate. `SchemaBuilder::limit_aliases` (#1822, DoS mitigation).

## Macros (schema definition)

- `#[Object]` on `impl` blocks: one resolver method per field. Resolvers take `&self`, optional `&Context<'_>`, then arguments. Can be sync or async (only `entity` resolvers must be async). Return `T` or `Result<T>`.
- `#[derive(SimpleObject)]`: struct fields become output fields. `#[graphql(complex)]` plus `#[ComplexObject]` impl adds computed fields to it.
- `#[derive(InputObject)]`, `#[derive(OneofObject)]` (Rust enum, each variant one input type, emits `@oneOf`).
- `#[derive(Enum)]`: unit enum. Values auto CONSTANT_CASE.
- `#[derive(Interface)]`: Rust enum of implementors plus `field(...)` declarations. Dispatch to the implementor's resolver. `Into` conversion generated.
- `#[derive(Union)]`: Rust enum of object types.
- `#[Subscription]` on `impl` blocks: methods return `impl Stream<Item = T>` or `Result<impl Stream>`.
- `#[Scalar]` on `impl ScalarType for T` (`parse`, `to_value`, optional `is_valid`). `scalar!(T, "Name", "desc")` macro for serde types.
- `#[derive(NewType)]`: newtype wrapper. With `name` it is a new scalar. Without, it is a transparent proxy.
- `#[derive(MergedObject)]`, `#[derive(MergedSubscription)]`: tuple struct merges several `#[Object]` or `#[Subscription]` blocks into one root type.
- `#[derive(Description)]`: type description from doc comment, used with `use_type_description`.
- `#[Directive(location = "Field")]`: factory fn for a custom executable directive. `#[TypeDirective(location = ...)]`: factory fn for a type-system directive, applied with `directive = name::apply(...)`.
- Doc comments become GraphQL descriptions everywhere (including `#[doc = ...]`).
- `#[cfg(...)]` on fields and resolvers is respected.

## Macro attributes

Type-level (`#[graphql(...)]` or macro args):
- Common: `name`, `name_type` (name from `TypeName` trait), `rename_fields`, `rename_args`, `rename_items` (enum). Rename rules: `lowercase`, `UPPERCASE`, `PascalCase`, `camelCase`, `snake_case`, `SCREAMING_SNAKE_CASE`.
- `visible = false` or `visible = "fn_name"` (per-request introspection hiding, fn gets `&Context`).
- `guard = "expr"` (whole type), `directives = [...]` / `directive = expr`, `cache_control(max_age = N, public, private, no_cache)`.
- `serial` (resolve fields one by one), `concrete(name = ..., input_name = ..., params(...), bounds(...))` (generic instantiation), `input_name` (for types that derive both `SimpleObject` and `InputObject`).
- `use_type_description`, `crate = "path"` (re-exported crate path), `internal`.
- `SimpleObject` only: `complex`, `fake` (I think it registers a placeholder output type with no fields).
- `InputObject` only: `validator(custom = ...)` at object level (`CustomValidator` on the whole object), `complex`.
- `Enum` only: `display` (impl `Display`), `remote = "path::Enum"` (generates `From` both ways).
- `Scalar` / `NewType`: `specified_by_url`.
- Federation: `extends`, `shareable`, `inaccessible`, `interface_object`, `tag = "..."` (repeatable), `unresolvable` or `unresolvable = "fields"`, `requires_scopes = "..."`.

Field-level (output):
- `skip`, `skip_output`, `name`, `desc`, `deprecation` / `deprecation = "reason"`, `owned` (SimpleObject field returns owned value).
- `guard`, `visible`, `complexity = N` or `complexity = "expr with child_complexity"`, `cache_control(...)`, `directives`.
- `derived(name = ..., into = "Type", with = "fn", owned)`: extra field from same resolver with `Into` conversion.
- `flatten`: SimpleObject field inlines child fields. On `#[Object]` method, I think it inlines the returned object's fields.
- Federation: `entity` (entity resolver on Query), `external`, `provides = "..."`, `requires = "..."`, `shareable`, `inaccessible`, `tag`, `override_from = "Subgraph"`, `requires_scopes`.

Argument and input-field level:
- `name`, `desc`, `default`, `default = value`, `default_with = "expr"`, `validator(...)`, `process_with = "fn"` (post-parse `fn(&mut T)` mutation), `secret` (value hidden in logs and traces), `visible`, `deprecation`, `directives`, `flatten` (input), `skip` / `skip_input` (input, uses `Default`).
- Federation: `key` (entity key arg), `inaccessible`, `tag`, `shareable` (input field).

Interface `field(...)`: `name`, `ty`, `method`, `desc`, `arg(name, ty, desc, default, default_with, visible, secret, ...)`, `deprecation`, `external`, `provides`, `requires`, `override_from`, `shareable`, `inaccessible`, `tag`, `visible`, `directives`, `requires_scopes`.
Union variant: `flatten` (merge a nested union's members).
Directive macros: `name`, `name_type`, `visible`, `repeatable`, `rename_args`, `location`. `TypeDirective` also `composable = "url"` (`@composeDirective`).

## Generics

- `concrete(...)` attribute per instantiation, or `name_type` plus `impl TypeName`.
- Generic `SimpleObject`, `InputObject`, `Union`, `Object`. `flatten` works on generic input params (8.0).

## Scalars and built-in types

- Built in: `bool`, `String`, `&str`, `Cow<str>`, `char`, all ints `i8`..`i64`, `u8`..`u64`, `isize`, `usize` (all map to `Int`, so 64-bit values exceed the spec's 32-bit range), `NonZero*` ints, `f32`, `f64`, `ID`, `IpAddr`, `Bytes`, `Json<T>` (any serde value as JSON scalar), `Any` (`_Any`), `MaybeUndefined<T>` (distinguish absent vs null input), `Upload`, `StringNumber<T>` (feature), `EmptyFields`.
- Containers: `Option`, `Vec`, slices, arrays, `HashSet`, `BTreeSet`, `VecDeque`, `LinkedList`, `HashMap` / `BTreeMap` (as JSON object scalar), `Box`, `Arc`, `Weak`, `Cow`.
- Feature scalars: `chrono` (`DateTime<Utc|Local|FixedOffset>`, `NaiveDate`, `NaiveTime`, `NaiveDateTime`), `chrono-duration` (ISO 8601 `Duration`), `chrono-tz` (`TimeZone`), `time`, `jiff` (`Date`, `Time`, `DateTime`, `Timestamp`, `Zoned`), `decimal` (`Decimal`), `url` (`Url`), `uuid` (`UUID`), `secrecy` (`SecretString` etc.).
- Extras crate: `EmailAddress` scalar (default feature `email-address`).

## Resolvers, Context and execution

- Query root fields resolve concurrently. Mutation root fields resolve serially. `serial` attribute forces serial on any object.
- `Context`: `data::<T>()`, `data_unchecked`, `data_opt`, `insert_http_header`, `append_http_header`, `http_header_contains`, `add_error` (partial errors), `look_ahead()` (`Lookahead::field`, `exists`, `selection_fields`), `field()` (`SelectionField::name`, `alias`, `arguments`, `directives`, `selection_set`), `param_value`, `path_node`.
- Data scopes: schema data (`SchemaBuilder::data`), request data (`Request::data`), WebSocket connection data (`on_connection_init`), `Schema::data` access (7.1).
- `Schema::execute`, `execute_batch` (batched requests), `execute_stream` (subscriptions), `execute_stream_with_session_data`.
- `Executor` trait so integrations accept both static and dynamic schemas.
- Error bubbling: errors in a container no longer stop sibling fields (7.1).

## Schema builder (`SchemaBuilder`)

- `register_input_type`, `register_output_type` (register types not reachable from roots).
- `disable_introspection`, `introspection_only`, `IntrospectionMode` per request (`Request::disable_introspection`, `only_introspection`).
- `limit_complexity`, `limit_depth`, `limit_recursive_depth` (parser recursion), `limit_directives` (per field), `limit_aliases` (8.0-rc.5).
- `validation_mode(ValidationMode::Strict | Fast)`.
- `extension(...)`, `data(...)`, `directive(...)`.
- `enable_federation`, `enable_subscription_in_federation`.
- `override_input_type_description`, `override_output_type_description`.
- `disable_suggestions` ("did you mean" in errors), `with_sorted_fields`, `with_sorted_enums`.
- `Schema::build_with_ignore_name_conflicts` (allow duplicate type names).
- `Schema::sdl()`, `sdl_with_options(SDLExportOptions)`: `sorted_fields`, `sorted_arguments`, `sorted_enum_items`, `federation`, `prefer_single_line_descriptions`, `include_specified_by`, `compose_directive`, `use_space_ident`, `indent_width`.
- `Schema::names()`: all type, field, arg and directive names (for building compression dictionaries).

## Validation and input validators

- All standard spec validation rules plus `UploadFile` (an `Upload` variable is only allowed in mutations).
- No public API to add custom validation rules. I did not find one.
- Built-in validators: `maximum`, `minimum`, `multiple_of`, `max_items`, `min_items`, `max_length`, `min_length`, `chars_max_length`, `chars_min_length`, `regex`, `custom = "expr"` (`CustomValidator<T>` trait), `list` (apply to each list item).
- Object-level `InputObject` validator.
- `process_with` for post-parse normalization.
- Removed in 8.0: `email`, `url`, `ip`, `uuid` validators.

## Guards (authorization)

- `Guard` trait (`async fn check(&self, ctx) -> Result<()>`). `GuardExt::and`, `GuardExt::or`.
- `guard = "Expr"` on types, fields, `ComplexObject`, `Subscription`. Guard expressions can use resolver argument values.
- Open bugs: guards not applied on interface fields (#1826). Guard on nullable field returns null instead of bubbling (PR #1820).

## Visibility

- `visible = false` or `visible = "fn"` on types, fields, args, enum items, input fields. Hides from introspection and SDL per request. I think hidden fields are still executable. The book only says "hide in introspection".

## Errors

- `Error` (`message`, `source`, `extensions`). `Error::new`, `new_with_source`.
- `ErrorExtensions` trait (`extend`, `extend_with(|err, e| e.set(...))`). `ResultExt::extend_err`.
- `ErrorExtensionValues::set`, `unset`, `get`.
- `ServerError` (message, source, locations, path, extensions). `InputValueError` (`custom`, `expected_type`, `propagate`).
- `Context::add_error` for non-fatal errors. Response keeps `errors` before `data` (8.0).
- No built-in error codes, masking or error formatter hook. Extensions can rewrite responses.

## Cache control

- `cache_control(max_age, public, private, no_cache)` on types and fields. Merged per response (min max_age, private wins).
- `Response::cache_control`, `CacheControl::value()` returns the `Cache-Control` header value.

## Pagination (`types::connection`)

- `Connection<Cursor, Node, ConnectionFields, EdgeFields, ConnectionName, EdgeName, NodesField>`, `Edge`, `PageInfo`.
- `connection::query(after, before, first, last, |...| async {})`, `query_with` (custom cursor type).
- `CursorType` trait, `OpaqueCursor<T>` (serde-encoded cursor).
- `EnableNodesField` / `DisableNodesField` (shortcut `nodes` field). `ConnectionNameType` / `EdgeNameType` for custom type names. Additional fields on connection and edge.
- No Relay `Node` interface or global ID helpers. I did not find any.

## DataLoader (`dataloader` feature)

- `Loader<K>` trait (`async fn load(&self, keys) -> Result<HashMap<K, V>, E>`). One loader can implement several key types.
- `DataLoader::new(loader, spawner, timer)`, `with_cache(..., cache_factory)`, `delay`, `max_batch_size` (default 1000), `enable_all_cache`, `enable_cache`.
- `load_one`, `load_many`, `feed_one`, `feed_many` (prime cache), `clear`, `clear_one` (8.0).
- Caches: `NoCache` (default), `HashMapCache`, `LruCache`. Custom through `CacheFactory` / `CacheStorage`.
- Not request scoped by default. Put it in schema data (global) or request data.

## Custom directives

- Executable: `CustomDirective` trait (`resolve_field(ctx, resolve_fut)`), `#[Directive]` factory. Only `FIELD` location supported.
- Type system: `#[TypeDirective]` on `ArgumentDefinition`, `Enum`, `EnumValue`, `FieldDefinition`, `InputFieldDefinition`, `Object`, `InputObject`, `Interface`. Only printed in SDL. No runtime behavior.
- Built in: `@skip`, `@include`, `@deprecated` (also on args and input fields), `@specifiedBy`, `@oneOf`.

## Extensions (`Extension` trait)

- Hooks (middleware style with `next.run`): `request`, `subscribe`, `prepare_request`, `parse_query`, `validation`, `execute`, `resolve`.
- `ExtensionFactory::create` per request. `ExtensionContext`: `data`, `sdl`, `sdl_with_options`, `stringify_execute_doc` (with secrets redacted). `ResolveInfo`: `path_node`, `parent_type`, `return_type`, `name`, `alias`, `is_for_introspection`, `field`.
- `NextExecute::run_with_data` (attach data before execution).
- Built in: `Analyzer` (adds `complexity` and `depth` to response extensions), `ApolloTracing` (feature `apollo_tracing`, deprecated Apollo spec), `ApolloPersistedQueries<T>` (feature `apollo_persisted_queries`, `CacheStorage` trait, `LruCacheStorage`), `Logger` (feature `log`), `Tracing` (feature `tracing`, `TracingConfig::with_trace_scalars`).
- Extras crate: `OpenTelemetry<T>` (feature `opentelemetry`, `with_trace_scalars`).
- External: Apollo Studio extension (`async_graphql_apollo_studio_extension`, separate repo).

## Subscriptions

- `#[Subscription]` streams. `MergedSubscription`.
- `http::WebSocket` with both `graphql-transport-ws` and legacy `graphql-ws` (`ALL_WEBSOCKET_PROTOCOLS`, `Protocols`). `on_connection_init`, `on_ping`, `keepalive_timeout`, `connection_data`, `from_message_stream`.
- `multipart/mixed` subscriptions over HTTP (Apollo Router protocol): `create_multipart_mixed_stream`, `is_accept_multipart_mixed`. Used by axum, actix and poem `GraphQL` services.
- No SSE transport. I did not find one.
- I think subscription items resolve one at a time. PR #1833 adds configurable concurrent resolution.

## HTTP layer (`http` module)

- `receive_body`, `receive_batch_body`, `receive_json`, `receive_batch_json`, `parse_query_string` (GET).
- Multipart upload spec: `MultipartOptions::max_file_size`, `max_num_files`. `Upload::value(ctx)` gives `UploadValue` (`filename`, `content_type`, `content`, `size`, `into_async_read`, `try_clone`). Temp files with `tempfile` feature.
- `GraphiQLSource::build()`: `endpoint`, `subscription_endpoint`, `header`, `version`, `ws_connection_param`, `title`, `credentials` (feature `graphiql`, default on). GraphiQL v5.
- GraphQL Playground and Altair removed in 8.0.
- I did not find CSRF protection or a block on mutations over GET.

## Federation

- Federation v2 (`@link` to `federation/v2.5`). Auto on when any `entity` resolver exists, or `enable_federation()`.
- Adds `_service`, `_entities`, `_Any`, `_Entity`.
- Entity resolvers: `#[graphql(entity)]` on Query methods. Key from arg names, `#[graphql(key)]` marks key args, others are `@requires` inputs. Nested keys through `InputObject`. Multiple `@key`s per type.
- Directives: `@key`, `@shareable`, `@inaccessible`, `@override(from)`, `@external`, `@provides`, `@requires`, `@tag`, `@composeDirective`, `@interfaceObject`, `@requiresScopes`, `@key(resolvable: false)` (`unresolvable`), `@extends`.
- `enable_subscription_in_federation`.
- Not supported: `@authenticated`, `@policy`, `@cost`, `@listSize`, `@context`, `@fromContext`, `@override(label)`. Apollo federated tracing (ftv1) not in core.
- Dynamic schema supports federation too (`entity_resolver`, `key`, `unresolvable`).

## Dynamic schema (`dynamic` module, default feature `dynamic-schema`)

- Runtime schema building: `dynamic::Schema::build(query, mutation, subscription)`, `register`, `finish() -> Result<_, SchemaError>`.
- Types: `Object`, `Field` (`FieldFuture`, `FieldValue` with `with_type`, `owned_any`, `borrowed_any`, `list`), `InputObject`, `InputValue`, `Interface`, `InterfaceField`, `Union`, `Enum`, `EnumItem`, `Scalar` (`validator`), `Subscription`, `SubscriptionField`, `Directive`, `TypeRef`.
- `ResolverContext` with `ValueAccessor`, `ObjectAccessor`, `ListAccessor`. `DynamicRequestExt::root_value`.
- Builder: `data`, `extension`, `limit_*`, `validation_mode`, `disable_introspection`, `introspection_only`, `disable_suggestions`, `enable_federation`, `enable_uploading`, `sdl`.
- Setters: description, deprecation, federation attributes, type directives.
- No guards, input validators, complexity attrs or cache control in dynamic schema. I did not find them.
- Book does not cover dynamic schema. Only rustdoc.

## Integrations (separate crates, all `8.0.0-rc.5`)

- `async-graphql-axum`: `GraphQL` (tower service, HTTP plus multipart/mixed), `GraphQLRequest`, `GraphQLBatchRequest`, `GraphQLResponse`, `GraphQLSubscription`, `GraphQLWebSocket`, `GraphQLProtocol`, `rejection`. Works on wasm without subscriptions.
- `async-graphql-actix-web`: `GraphQL` handler, `GraphQLRequest`, `GraphQLBatchRequest`, `GraphQLResponse`, `GraphQLSubscription` (on `actix-ws` since 8.0). Feature `http2`.
- `async-graphql-poem`: `GraphQL` endpoint, `GraphQLRequest`, `GraphQLBatchRequest`, `GraphQLResponse`, `GraphQLBatchResponse`, `GraphQLSubscription`, `GraphQLWebSocket`, `GraphQLProtocol`.
- `async-graphql-rocket`: `GraphQLRequest`, `GraphQLBatchRequest`, `GraphQLQuery` (GET), `GraphQLResponse`. No WebSocket subscriptions.
- `async-graphql-warp`: filters `graphql`, `graphql_opts`, `graphql_batch`, `graphql_batch_opts`, `graphql_subscription`, `graphql_protocol`, `GraphQLWebSocket`, `GraphQLBadRequest`.
- All HTTP integrations accept GET query-string requests.
- Removed: `tide` (8.0). No ORM integration (Diesel, SeaORM, sqlx) in this repo. SeaORM has its own `seaography` project outside this repo.

## Cargo features (core crate)

- Default: `dynamic-schema`, `tempfile`, `graphiql`.
- `apollo_persisted_queries`, `apollo_tracing`, `dataloader`, `log`, `tracing`.
- Scalars: `chrono`, `chrono-duration`, `chrono-tz` (implicit from optional dep), `decimal`, `jiff`, `time`, `url`, `uuid`, `secrecy`, `string_number`.
- `tokio` (Tokio spawner and timer in `runtime`), `raw_value` (serde_json raw values), `boxed-trait` (use `async-trait` boxing for all traits).
- Extras crate features: `email-address` (default), `opentelemetry`.

## Not supported or not in scope

- `@defer` and `@stream`. No incremental delivery in the code. `multipart/mixed` is only used for subscriptions.
- SSE transport. Trusted documents or operation allow-lists (only Apollo APQ). Query cost per argument beyond `complexity` expressions.
- Relay `Node` interface and global IDs.
- Custom validation rules. Custom executable directives on locations other than `FIELD`.
- Schema-first (SDL to Rust) code generation. Client code generation (separate projects like `graphql_client`, `cynic`).
- ORM integration, filtering and ordering generation.
- Schema stitching or gateway. Only subgraph federation.
- Semantic non-null (PR #1638 open). Error propagation control (PR #1837 `@experimental_disableErrorPropagation` open).
- `?Send` futures (PRs #1122, #1372 open for years).

## Upcoming and unreleased work

- 8.0.0 final not released. Branch `aw/remove-features` and others exist.
- Open PRs: `SignedDuration` for jiff (#1843), merge repeated sub-selections on nested lists (#1841), parser enum values starting with `true`/`false`/`null` (#1838), `@experimental_disableErrorPropagation` (#1837), `arbitrary_precision` numbers (#1834), concurrent subscription items (#1833), `directive` on `#[Scalar]` (#1828), `@skip`/`@include` with defaulted variables (#1827), `directive()` on dynamic `SchemaBuilder` (#1825), guard bubbling fix (#1820), `dyn ContainerType` for faster compile (#1754), `semanticNonNull` (#1638), `nullable-result` feature (#1637), deprecate `data_unchecked` / `data_opt` (#1616), dynamic schema subtypes (#1697), `tracing-otel` span names (#1700).
- Recent issues: huge inlined `resolve_field` future causes OOM on wide objects (#1842), federation `extends` with docs gives invalid schema (#1823), `Vec<T>` input does not propagate `federation_fields` (#1824).

## Docs and code disagree

- `define_complex_object.md` says "A resolver function has to be asynchronous". The code allows sync resolvers. Only `entity` resolvers must be async.
- `input_value_validators.md` lists `email`, `url`, `ip`, `uuid` validators. They are removed in 8.0 (no code in `src/validators` or `derive/src/validators.rs`).
- `dataloader.md` shows `DataLoader::new(loader, spawn)` with two args. Code requires three (`spawner`, `timer`).
- `custom_directive.md` says type directives only support `FieldDefinition` and `Object`. Code supports 8 locations.
- `apollo_federation.md` says "supports all the functionality of Apollo Federation v2". SDL links `federation/v2.5`. Directives from v2.6+ (`@authenticated`, `@policy`, `@cost`, `@listSize`, `@context`) are missing.
- `quickstart.md` uses `async-graphql = "4.0"`. `cache_control.md` mentions `QueryResponse` (now `Response`).
- `define_one_of_object.md` says OneOf is still an RFC.
- `lib.rs` crate docs feature table lists `fast_chemail`, `opentelemetry`, `unblock`, `rawvalue`. These do not exist in `Cargo.toml` (`raw_value` is the real name). It omits `chrono-duration` and `tokio`. It says no feature is on by default. `dynamic-schema`, `tempfile` and `graphiql` are default. It says MSRV 1.56.1. `Cargo.toml` says 1.89.
- `integrations_to_poem.md` mounts the query endpoint at `/ws`. Minor.
- `extensions_available.md` lists OpenTelemetry under extras (correct for 8.0), but docs.rs `latest` (7.2.1) still has it in core.
- Features in code but not in the book: dynamic schema, `limit_aliases`, `limit_directives`, `limit_recursive_depth`, `disable_suggestions`, `with_sorted_*`, `SDLExportOptions`, `Schema::names`, `process_with`, `serial`, `owned`, `use_type_description`, `NewType`, `Description`, `MaybeUndefined`, `Json`, `Upload` and `MultipartOptions`, `GraphiQLSource`, multipart/mixed subscriptions, WebSocket callbacks, `requires_scopes`, `interface_object`, `IntrospectionMode`, `ValidationMode`, `Request::set_parsed_query`, `Context::add_error`, rocket and axum integration pages (only listed).

## Sources

- Book: https://async-graphql.github.io/async-graphql/en/index.html. Source in repo `docs/en/src/` (all pages read): `introduction`, `quickstart`, `define_*`, `context`, `error_handling`, `merging_objects`, `derived_fields`, `default_value`, `generic`, `query_and_mutation`, `subscription`, `sdl_export`, `field_guard`, `input_value_validators`, `cache_control`, `cursor_connections`, `error_extensions`, `apollo_tracing`, `depth_and_complexity`, `visibility`, `extensions_*`, `integrations*`, `custom_scalars`, `dataloader`, `custom_directive`, `apollo_federation`.
- API docs: https://docs.rs/async-graphql/latest/async_graphql/ (shows 7.2.1). https://docs.rs/async-graphql/8.0.0-rc.5/async_graphql/. Rustdoc source in `src/docs/*.md` and `src/lib.rs`.
- Repo: https://github.com/async-graphql/async-graphql (shallow clone `82cd1f1`). Code read in `derive/src/args.rs`, `derive/src/validators.rs`, `src/schema.rs`, `src/context.rs`, `src/extensions/`, `src/http/`, `src/dataloader/`, `src/dynamic/`, `src/types/`, `src/registry/export_sdl.rs`, `src/validation/rules/`, `integrations/*/src`, `extras/src`.
- Changelog: https://github.com/async-graphql/async-graphql/blob/master/CHANGELOG.md
- crates.io: https://crates.io/crates/async-graphql
- PRs and issues: https://github.com/async-graphql/async-graphql/pulls, https://github.com/async-graphql/async-graphql/issues, PR #1822 https://github.com/async-graphql/async-graphql/pull/1822
- Extras: https://github.com/async-graphql/async-graphql/tree/master/extras
- llms.txt: https://async-graphql.github.io/llms.txt (404).
