# Juniper findings

Versions checked: `juniper 0.17.1` (latest on crates.io, 2026-01-26). `juniper_codegen 0.17.0` and all integration crates last released 2025-09-08. Repo `master` at `65cbce2` (last commit 2026-08-30). Docs source is in the repo (`book/src/`, mdBook, about 4700 lines). All book pages read. Codegen rustdoc (`juniper_codegen/src/lib.rs`) and attribute parsers read. Core, http, executor, schema and integration crates spot-checked.
Juniper is a Rust GraphQL server library. BSD-2-Clause. Code-first through procedural macros. Own parser, own validator, own executor. Edition 2024, MSRV 1.85. Pre-1.0. The book says "some API instability should be expected".

## Maintenance status

- Active, slow releases. 5970 stars. Not archived. 108 open issues plus PRs. Last push 2026-09-30.
- Milestone `0.18.0`: 3 open, 24 closed. Milestone `next major`: 12 open.
- Releases are batched. 0.16.0 (2024-03-20), 0.16.1 (2024-04-04), 0.16.2 (2025-06-25), 0.17.0 (2025-09-08), 0.17.1 (2026-01-26, macro fix only).
- `master` has a large unreleased section (September 2025 spec work). Not on crates.io yet.
- Many old PRs (tracing, serde_json, fuzzing, custom directives, core trait rework) were touched on 2026-02-10 but are not merged.
- https://graphql-rust.github.io/juniper/llms.txt and https://graphql-rust.github.io/llms.txt return 404. `Accept: text/markdown` returns HTML.

## Big changes in recent releases

- 0.16.0 (2024-03-20): October 2021 spec. `rename` attribute renamed to `rename_all`. `#[graphql_interface]` redesign (value enum, `for`/`impl`). `#[derive(GraphQLInterface)]` (struct as interface). `#[graphql_scalar]` redesign. `graphql_input_value!`, `graphql_vars!`. `time`, `bigdecimal`, `rust_decimal`, `anyhow`/`backtrace` integrations. `js` feature (wasm). Look-ahead rework (`applies_for`, `field_original_name`, `field_alias`). `RootNode::disable_introspection()`. `FromInputValue` fallible. `schema-language` feature merges `graphql-parser`. `as_schema_language()` renamed to `as_sdl()`. `bson`, `url`, `uuid`, `schema-language` off by default. GraphiQL 3 (needs `graphql-transport-ws`).
- 0.17.0 (2025-09-08): `jiff` integration. Scalars renamed to graphql-scalars.dev names (`URL`, `UUID`, `ObjectID`, `LocalDate`, `LocalDateTime`, `DateTime`). Schema internals use `arcstr` (no lifetimes on meta types). `ScalarValue` rework (`TryToPrimitive`, `FromScalarValue`, `ToScalarValue`, `IntoValue`, `IntoInputValue`). `#[graphql_scalar]` `from_input` takes concrete types and non-`Result` returns. `to_output` can return `impl Display`. `GraphQLResponse::into_result()`. `String` scalar for `ArcStr` and `CompactString`. GraphiQL 5.2. Fix for error propagation inside fragments.
- 0.17.1 (2026-01-26): less code from `macros::reflect`.

## Macros (schema definition)

- `#[derive(GraphQLObject)]` on structs. Fields become output fields.
- `#[graphql_object]` on `impl` blocks. Each method is a field. Methods can be sync or `async`. `self` is optional (static fields allowed). Return `T`, `Option<T>`, `Result<T, E: IntoFieldError>`.
- `#[derive(GraphQLInterface)]` on a struct, or `#[graphql_interface]` on a trait (needed when fields have arguments). Both only describe fields. The macro generates a value enum (`CharacterValue` by default) used for dispatch and as return type.
- `#[derive(GraphQLUnion)]` on enums (newtype variants). `#[graphql_union]` on traits (methods return `Option<&T>`), lightly documented.
- `#[derive(GraphQLEnum)]` on fieldless enums. Generic enums allowed if non-unit variants are ignored.
- `#[derive(GraphQLInputObject)]` on structs. On enums (master, unreleased) it creates a `@oneOf` input object. Each variant is one nullable field.
- `#[derive(GraphQLScalar)]` on local types. `#[graphql_scalar]` on type aliases (foreign types) or local types.
- `#[graphql_subscription]` on `impl` blocks. All methods must be `async` and return a `Stream`.
- `#[derive(ScalarValue)]` with `#[value(...)]`: builds a custom `ScalarValue` enum (the set of scalar representations the whole schema uses).
- Doc comments become descriptions. `description`/`desc` overrides them. Rust `#[deprecated]` maps to GraphQL deprecation.
- Interface implementation is checked at compile time (missing `for`/`impl`, wrong subtypes, extra non-null arguments). Errors appear as const-eval panics.
- `macros::reflect` holds the compile-time assertion macros (`assert_implemented_for!`, `assert_interfaces_impls!`, `assert_subtype!`, `assert_field_args!` and others). Used by generated code.

## Macro attributes

Type-level `#[graphql(...)]` (from the codegen parsers):
- Object (`GraphQLObject`, `graphql_object`): `name`, `desc`/`description`, `context`/`ctx`/`Context`, `scalar`/`Scalar`/`ScalarValue` (type, or generic `S: ScalarValue`), `impl`/`implements`/`interfaces`, `rename_all`, `internal`.
- Interface: `name`, `desc`, `context`, `scalar`, `for`/`implementers`, `impl`/`implements` (interfaces implementing interfaces), `enum` (rename the value enum), `async` (force `async_trait` transform), `rename_all`, `internal`.
- Union: `name`, `desc`, `context`, `scalar`, `on Type = path::to::fn` (external resolver for a member type), `internal`. Variant-level: `ignore`/`skip`, `with = fn` (external resolver).
- Enum: `name`, `desc`, `context`, `scalar`, `rename_all`, `internal`. Variant-level: `name`, `desc`, `deprecated`, `ignore`/`skip`.
- Input object: `name`, `desc`, `context`, `scalar`, `rename_all`, `internal`. Field-level: `name`, `default` / `default = expr`, `desc`, `deprecated`, `ignore`/`skip` (needs `Default` or `default = expr`).
- Scalar: `name`, `desc`, `specified_by_url`, `scalar`, `transparent` (newtype delegation), `to_output_with = fn`, `from_input_with = fn`, `parse_token_with = fn`, `parse_token(Type1, Type2)`, `with = module or Self`, `where(bounds)`.
- `ScalarValue` derive: `#[value(to_int)]`, `to_float`, `to_bool`, `to_string`, `as_str`, top-level `from_displayable_with`, `from_displayable_non_static_with`.
- Rename policies: `camelCase` (fields default), `SCREAMING_SNAKE_CASE` (enum values default), `snake_case` (master only), `none`.

Field-level (output): `name`, `desc`/`description`, `deprecated` / `deprecated = "reason"` (default reason "No longer supported"), `ignore`/`skip`.

Argument-level: `name`, `desc`, `deprecated` (master only, needs nullable or `default`), `default` / `default = expr` (any Rust expression), `context`/`ctx` (inject context), `executor`/`exec` (inject `&Executor`). Arguments named `context`, `ctx`, `_context`, `_ctx` are context by name. `executor`, `_executor` are executor by name.

Not present: guards, permissions, complexity, cache control, visibility, validators, `flatten`, `complex` (mixing derive and impl), field-level directives, federation keys.

## Type mapping and scalars

- Non-null by default. `Vec<T>` is `[T!]!`. Use `Option` for nullable. `Nullable<T>` distinguishes explicit `null` from omitted (`Nullable::ExplicitNull`, `ImplicitNull`, `Some`, `.explicit()`).
- Built-in: `bool` `Boolean`, `i32` `Int`, `f64` `Float`, `String`/`&str`/`Cow<str>`/`ArcStr`/`CompactString` `String`, `juniper::ID`. Lists from `Vec`, slices, arrays. `Box`, `Arc`, references are transparent.
- No built-in `i64`, `u64` or other integers. User must define a custom scalar.
- Optional scalars by feature: `bigdecimal` (`BigDecimal`), `bson` (`ObjectID`, `DateTime`), `chrono` (`LocalDate`, `LocalTime`, `LocalDateTime`, `DateTime`), `chrono-tz` (`TimeZone`), `jiff` (`LocalDate`, `LocalTime`, `LocalDateTime`, `DateTime`, `ZonedDateTime`, `TimeZoneOrUtcOffset`, `TimeZone`, `UtcOffset`, `Duration`), `ruint` (`U8` to `U256`, master only, plus `integrations::ruint::unit_scalar`), `rust_decimal` (`Decimal`), `time` (`LocalDate`, `LocalTime`, `LocalDateTime`, `DateTime`, `UtcOffset`), `url` (`URL`), `uuid` (`UUID`).
- Scalar names follow graphql-scalars.dev specs. `specifiedByURL` is set.
- Custom `ScalarValue`: the whole schema is generic over `S: ScalarValue`. `DefaultScalarValue` has `Int`, `Float`, `String`, `Boolean`. A custom one can add e.g. `i64`. Needed for scalars on foreign types (orphan rule).
- Generics: no generic GraphQL types. Each concrete instantiation needs its own `#[graphql_object]` impl with a `name`.

## Resolvers, Context and execution

- `Context` marker trait (`impl juniper::Context for MyCtx {}`). One context type per GraphQL type, set with `#[graphql(context = ...)]`. Context is immutable. Interior mutability is the documented pattern.
- `FromContext<T>` trait converts between context types, so sub-trees can use a narrower context. `()` converts from any context. Not in the book.
- Context switching: a resolver can return `(&NewCtx, T)` or `FieldResult<(&NewCtx, T)>` (`IntoResolvable`). `Executor::replaced_context`, `resolve_with_ctx`. Not in the book.
- `Executor` methods: `context()`, `schema()`, `current_type()`, `variables()`, `fragment_by_name()`, `location()`, `push_error()`, `push_error_at()`, `new_error()`, `take_errors()`, `look_ahead()`, `as_owned_executor()` (`OwnedExecutor`), `field_sub_executor`, `type_sub_executor`, `resolve*`.
- Entry points: `juniper::execute` (async), `execute_sync`, `resolve_into_stream` (subscriptions), `introspect(schema, ctx, IntrospectionFormat::{All, WithoutDescriptions})`.
- `GraphQLError` variants: `ParseError`, `ValidationError(Vec<RuleError>)`, `NoOperationProvided`, `MultipleOperationsProvided`, `UnknownOperationName`, `IsSubscription`, `NotSubscription`, `NotSupported` (master).
- Async fields of one selection set run concurrently. Mutation root fields also run concurrently (spec violation, issue #1398, fix in PR #1399, open).
- Null returned by a custom resolver for a non-null field bubbles up without an error entry (PR #1397, open).
- Lower-level traits for manual impls: `GraphQLType`, `GraphQLValue`, `GraphQLValueAsync`, `GraphQLTypeAsync`, `GraphQLSubscriptionType`, `Registry` (`field`, `arg`, `arg_with_default`, `build_object_type`, `build_enum_type` and others), `meta::*` types.
- Runtime-defined types: `GraphQLType::TypeInfo` plus `RootNode::new_with_info(query, mutation, subscription, query_info, mutation_info, subscription_info)`. Lets one Rust type produce types with names and fields chosen at runtime (`tests/type_info_tests.rs`). Not in the book. No builder-style dynamic schema API.

## Schema (`RootNode`)

- `RootNode::new(query, mutation, subscription)`, `new_with_scalar_value`, `new_with_info`.
- `EmptyMutation<Ctx>`, `EmptySubscription<Ctx>` stubs.
- Only reachable types are registered. No way to add orphan types by hand, I think.
- `RootNode::disable_introspection()` adds a validation rule. `__schema`/`__type` become validation errors. `enable_introspection()` reverts. No per-request or per-user introspection control.
- `RootNode::as_sdl()` and `RootNode::as_document()` (graphql-parser `Document`) need the `schema-language` feature.
- `SchemaType` API: `set_description`, `add_directive`, `type_by_name`, `concrete_type_list`, `directive_list`, `possible_types`, `is_subtype` and others.
- Schema description is supported (the September 2025 tracking issue says "already possible").

## Validation

- Built-in spec rules in `validation::rules` (26 rule modules): `arguments_of_correct_type`, `default_values_of_correct_type`, `fields_on_correct_type`, `known_directives`, `no_fragment_cycles`, `overlapping_fields_can_be_merged`, `variables_in_allowed_position`, and the other spec rules. Plus `disable_introspection`.
- `validation` module is public (`ValidatorContext`, `Visitor`, `visit_all_rules`, `RuleError`). There is no hook to add custom rules to `execute`, I think. A user must call parse and validate by hand.
- Not supported: depth limit, complexity or cost analysis, alias limit, token limit, recursion limit setting.
- `parse_and_validate()` (validate without executing, returns `OperationType`) is in open PR #1392.

## Errors

- `FieldError::new(message, extensions_value)`, `FieldResult<T, S>`, `IntoFieldError` trait for custom error types. `FieldError::map_message`, `map_scalar_value`.
- Any `E: Display` converts to `FieldError` (so `?` works on most errors).
- Response errors have `message`, `locations`, `path`, optional `extensions`.
- `anyhow` feature: `anyhow::Error` into `FieldError`. `backtrace` feature puts the backtrace into `extensions.backtrace`.
- Panics in resolvers are not caught by core. `juniper_graphql_ws` (master) has `PanicHandler`.
- Book documents "errors as schema types" (unions of result and error objects) as a pattern. No library helpers for it.
- No error masking or error formatter hook.

## Look-ahead

- `Executor::look_ahead()` returns `LookAheadSelection`: `field_name`, `field_original_name`, `field_alias`, `arguments`, `argument(name)`, `has_arguments`, `children()`, `children_for_explicit_type(type)`, `applies_for()`.
- `LookAheadChildren`: `names()`, `select(name)`, `has_child(name)`, `iter()`, `len()`. `LookAheadArgument` and `LookAheadValue` give argument values with variables resolved.
- `@skip`/`@include` are applied in look-ahead.
- Book uses it to batch-load relations manually (N+1). No ORM integration.

## N+1 and data loading

- No built-in DataLoader. The book points to the third-party `dataloader` crate (`Loader`, `BatchFn`, `with_yield_count`).
- Eager loading: third-party `juniper-eager-loading` crate (requires `juniper-from-schema`). The book has a TODO saying it does not support the latest juniper.
- No ORM integration of any kind. No query planning or projection.

## Directives

- Built-in: `@skip`, `@include`, `@deprecated`, `@specifiedBy`, `@oneOf` (master).
- Not supported: custom executable directives, custom schema directives in macros. Issues #156 (2018) and #894 open. PR #1314 (schema with custom directives) open.
- `SchemaType::add_directive` exists, but execution only handles `skip`/`include`.

## Subscriptions

- `#[graphql_subscription]` resolvers return `Stream<Item = T>` or `Stream<Item = Result<T, E>>`. Can return `Result<Stream, E>`.
- `SubscriptionCoordinator` and `SubscriptionConnection` traits. `juniper_subscriptions::Coordinator` is the default impl. `Coordinator::subscribe(&req, &ctx)` returns a `Connection` stream.
- Transports: WebSocket only (`juniper_graphql_ws`). No SSE. No multipart subscriptions.
- `juniper_graphql_ws`: both `graphql-ws` (legacy) and `graphql-transport-ws` protocols (Cargo features `graphql-ws`, `graphql-transport-ws`). `ConnectionConfig::new(ctx)`, `with_max_in_flight_operations`, `with_keep_alive_interval`, `with_keep_alive_timeout`, `with_panic_handler` (master). `Init` trait or closure builds `ConnectionConfig` from the `connection_init` payload (auth hook). `Schema` trait and `ArcSchema`.
- Master: context is cloned per operation (needs `Clone`). Keep-alive timeout closes the connection.

## HTTP layer (`juniper::http`)

- `GraphQLRequest { query, operation_name, variables }`. No `extensions` field. So no persisted queries and no APQ. PR #1356 adds `extensions` (open).
- `GraphQLBatchRequest` (single or batch array), `GraphQLBatchResponse`, `GraphQLResponse` (`from_result`, `into_result`, `error`, `is_ok`).
- Batching (JSON array of requests) is supported by all integrations. Documented in the book.
- `graphiql::graphiql_source(url, subscriptions_url)` (GraphiQL 5.3 on master). `playground::playground_source(url, subscriptions_url)` (GraphQL Playground 1.7.28).
- `http::tests::run_http_test_suite` and `WsIntegration` for testing an integration.
- Not supported: GraphQL over HTTP spec compliance (`application/graphql-response+json`, status codes). PR #1226 open. File uploads (multipart) not supported. No CSRF protection. No response caching, no cache control.

## Integrations (separate crates)

- `juniper_axum 0.3.0`: `graphql` handler, `extract::JuniperRequest` (GET, POST JSON, POST `application/graphql`), `response::JuniperResponse`, `graphiql`, `playground`. Feature `subscriptions`: `ws` (auto-negotiates protocol), `graphql_ws`, `graphql_transport_ws`, `subscriptions::serve_ws` and friends.
- `juniper_actix 0.7.0`: `graphql_handler`, `get_graphql_handler`, `post_graphql_handler`, `graphiql_handler`, `playground_handler`. Feature `subscriptions`: `ws_handler` (auto), `graphql_ws_handler`, `graphql_transport_ws_handler`.
- `juniper_warp 0.9.0`: `make_graphql_filter`, `make_graphql_filter_sync`, `graphiql_filter`, `playground_filter`. Feature `subscriptions`: `make_ws_filter`, `serve_graphql_ws`, `serve_graphql_transport_ws`.
- `juniper_hyper 0.10.0`: `graphql`, `graphql_sync`, `graphiql`, `playground`. No WebSocket.
- `juniper_rocket 0.10.0`: `GraphQLRequest`, `GraphQLResponse` (`error`, `custom(status, json)`), `graphiql_source`, `playground_source`. No WebSocket.
- `juniper_graphql_ws 0.5.0` and `juniper_subscriptions 0.18.0`: see Subscriptions.
- Third party: `juniper-from-schema` (schema-first, SDL to Rust traits), `juniper-eager-loading`. I think both are not maintained for 0.17.

## Cargo features (core crate)

- No default features.
- `anyhow`, `backtrace`, `bigdecimal`, `bson`, `chrono`, `chrono-clock`, `chrono-tz`, `jiff`, `rust_decimal`, `ruint` (master), `time`, `url`, `uuid`: type integrations.
- `schema-language`: SDL export (`as_sdl`, `as_document`) through `graphql-parser`.
- `js`: wasm32 support (`chrono/wasmbind`, `time/wasm-bindgen`, `uuid/js`).
- `expose-test-schema`: exposes `juniper::tests` (Star Wars fixture schema, SDL file).
- Helper macros (no feature): `graphql_value!`, `graphql_input_value!`, `graphql_vars!` (JSON-like literals for `Value`, `InputValue`, `Variables`).

## Not supported or not in scope

- Federation (issue #376 open since 2019).
- `@defer`/`@stream` (issue #734 open since 2020).
- Persisted queries and APQ (issue #843).
- Custom directives (issue #156).
- Query depth, complexity and cost limits.
- Built-in DataLoader, Relay connections and pagination, `Node` interface helpers, global IDs.
- Filtering, ordering, ORM integration, mutations from models.
- Guards, permissions, field visibility per request.
- Middleware, extensions, plugin or tracing hooks. No Apollo tracing, no OpenTelemetry. Tracing PRs #720 and #972 are open.
- File uploads.
- SSE and multipart subscription transports.
- Schema-first SDL loading in core (only through third-party `juniper-from-schema`).
- Response cache, cache control hints.
- Validating a query without executing it (PR #1392 open).
- Schema coordinates.

## Upcoming and unreleased work

- `master` (milestone 0.18.0): September 2025 spec. `@oneOf` input objects through `#[derive(GraphQLInputObject)]` on enums, `__Type.isOneOf`. Deprecation of arguments and input fields. New `__DirectiveLocation` values. Block strings. Full Unicode. Descriptions on operations, fragments and variable definitions. Non-null `includeDeprecated` and `@deprecated(reason:)`. `rename_all = "snake_case"`. `ruint` scalars. GraphiQL 5.3. `GraphQLError::NotSupported` instead of panic. Fixes: `specifiedByURL` name, missing `@specifiedBy` in SDL, subscription macro memory leak, default values on non-null variables.
- Open PRs: serial mutation execution (#1399), null-in-non-null errors (#1397), `parse_and_validate` (#1392), `extensions` in requests (#1356), GraphQL over HTTP (#1226), custom directives (#1314), core trait rework (#1072), `HashSet` as list (#1070), fuzzing and `arbitrary` (#1033, #1032), `serde_json::Value` integration (#975, #325), tracing (#972, #720), public parsing (#776).

## Docs and code disagree

- `introduction.md` says Juniper supports the October 2021 spec. That is correct for 0.17.1. `master` already implements most of September 2025.
- `serve/index.md` says all integrations expose GraphiQL "and/or GraphQL Playground" and recommends both. GraphQL Playground is still bundled at 1.7.28. I think upstream Playground is retired.
- `serve/index.md` says "most" integrations do WebSocket. Code: axum, actix and warp do. hyper and rocket do not.
- `types/index.md` links `objects/Context.md`. The file is `objects/context.md`.
- `eager_loading.md` has a TODO that `juniper-eager-loading` does not support the latest juniper. The page still presents it as the eager loading solution.
- Book Tip lists rename policies including `snake_case`. On 0.17.1 `snake_case` is not accepted. It is added on `master` (#1354). The book is built from `master`.
- Features in code but not in the book: `#[graphql_union]` on traits, union external resolvers (`with`, `on Type = fn`), interface `async` and `enum` args (`enum` shown once), `#[graphql(executor)]` argument injection, `FromContext`, context switching with `(&Ctx, T)`, `TypeInfo` with `RootNode::new_with_info`, `#[derive(ScalarValue)]`, `graphql_value!`/`graphql_vars!`/`graphql_input_value!`, `Executor::push_error`, `OwnedExecutor`, `RootNode::as_document`, `SchemaType::add_directive`, `IntrospectionFormat::WithoutDescriptions`, `juniper_graphql_ws::ConnectionConfig` options and `Init`, `http::tests` integration test suite, `expose-test-schema`, `anyhow` backtrace in extensions.

## Sources

- Book: https://graphql-rust.github.io/juniper/. Source in repo `book/src/` (all pages read): `introduction`, `quickstart`, `types/objects/{index,complex_fields,context,generics}`, `types/objects/error/{index,field,schema}`, `types/{interfaces,unions,enums,input_objects,scalars}`, `schema/{index,subscriptions,introspection}`, `serve/{index,batching}`, `advanced/{implicit_and_explicit_null,n_plus_1,dataloader,lookahead,eager_loading}`.
- API docs: https://docs.rs/juniper/latest/juniper/ (source read locally in `juniper_codegen/src/lib.rs` and `juniper/src/`).
- Repo: https://github.com/graphql-rust/juniper (shallow clone `65cbce2`). Code read in `juniper_codegen/src/*/mod.rs`, `juniper_codegen/src/common/`, `juniper/src/lib.rs`, `juniper/src/schema/model.rs`, `juniper/src/executor/`, `juniper/src/http/`, `juniper/src/validation/`, `juniper/src/integrations/`, `juniper/src/tests/type_info_tests.rs`, `juniper_*/src`.
- Changelogs: https://github.com/graphql-rust/juniper/blob/master/juniper/CHANGELOG.md, https://github.com/graphql-rust/juniper/blob/master/juniper_axum/CHANGELOG.md, https://github.com/graphql-rust/juniper/blob/master/juniper_graphql_ws/CHANGELOG.md
- crates.io: https://crates.io/crates/juniper (and `juniper_axum`, `juniper_actix`, `juniper_warp`, `juniper_hyper`, `juniper_rocket`, `juniper_graphql_ws`, `juniper_subscriptions`, `juniper_codegen`).
- Issues and PRs: https://github.com/graphql-rust/juniper/issues/1347 (September 2025 spec), https://github.com/graphql-rust/juniper/issues/1398, https://github.com/graphql-rust/juniper/pull/1399, https://github.com/graphql-rust/juniper/pull/1397, https://github.com/graphql-rust/juniper/pull/1392, https://github.com/graphql-rust/juniper/pull/1356, https://github.com/graphql-rust/juniper/pull/1314, https://github.com/graphql-rust/juniper/issues/376, https://github.com/graphql-rust/juniper/issues/734, https://github.com/graphql-rust/juniper/issues/843, https://github.com/graphql-rust/juniper/issues/156
- llms.txt: https://graphql-rust.github.io/juniper/llms.txt (404).
