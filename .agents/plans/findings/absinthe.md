# Absinthe findings

Versions checked: `absinthe` 1.12.0 (Hex, 2026-09-02). Repo `main` at `1372ceb` (2026-09-02, commit "chore(main): release 1.12.0"). Companions: `absinthe_plug` 1.5.10 (2026-05-16), `absinthe_phoenix` 2.0.5 (2026-05-05), `absinthe_relay` 1.6.0 (2025-11-06), `dataloader` 2.0.2 (Hex, 2024-12-19).
Absinthe is the GraphQL toolkit for Elixir. It has its own lexer (`nimble_parsec`), parser, validator and executor. Code-first: schemas are Elixir modules built with macros from `Absinthe.Schema.Notation`. SDL-first is also possible with `import_sdl` plus a `hydrate/2` callback. The core package does not know about HTTP. HTTP is in `absinthe_plug`. WebSocket subscriptions are in `absinthe_phoenix`. MIT. Elixir `~> 1.17`. Optional deps: `dataloader`, `decimal`, `opentelemetry_process_propagator`.
Key design: the schema is compiled at compile time through a pipeline of phases over `%Absinthe.Blueprint{}` structs. Schema errors fail compilation. Documents run through the same kind of phase pipeline. Users can insert, replace or remove phases in both pipelines.

## Maintenance status

- Active, small team. Last commit on `main`: 2026-09-02. GitHub `pushed_at` 2026-09-02. 4398 stars. 71 open issues plus PRs. Not archived.
- Releases: 1.12.0 (2026-09-02), 1.11.0 (2026-06-04), 1.10.2 (2026-05-08, CVE patch), 1.10.1/1.10.0 (2026-04-03), 1.9.0 (2025-11-21), 1.8.0 (2025-11-05), 1.7.11 (2025-10-29). About one minor release every two to three months in 2025-2026. Before that, 1.7.x patch releases for several years.
- Release process uses release-please (conventional commits). `CHANGELOG.md` in the repo.
- Hex recent downloads: absinthe 872k, absinthe_plug 771k, dataloader 541k, absinthe_phoenix 496k, absinthe_relay 341k.
- Docs at https://hexdocs.pm/absinthe/ (redirects to `absinthe.hexdocs.pm`). ExDoc built from `guides/` in the main repo (36 `.md` files, about 19k words) plus module docs. `/llms.txt` gives 404. `.md` URLs give 404. No `Accept: text/markdown` support.
- Several guides are thin. `guides/errors.md` has a banner "This guide could use some improvement". `Absinthe.Subscription` moduledoc still talks about the "beta release" and "Before the final version of 1.4.0".

## Schema definition

- `use Absinthe.Schema` in the schema module. `use Absinthe.Schema.Notation` in type modules.
- Root types: `query do ... end`, `mutation do ... end`, `subscription do ... end`. Default names `RootQueryType`, `RootMutationType`, `RootSubscriptionType`. Root types can only be defined in the schema module.
- Optional `schema do ... end` declaration, used to apply directives to the schema itself.
- Type macros: `object`, `input_object`, `interface`, `union`, `enum`, `scalar`, `directive`.
- Wrappers: `non_null(type)`, `list_of(type)`.
- Types are referenced by atom identifier (`:item`). GraphQL names are derived (`:item` becomes `Item`). Override with `name: "..."`.
- `@desc "..."` attribute or `description "..."` macro or `description:` option.
- `field :name, :type, opts` or block form. Field options: `name:` (skips camelCase conversion), `description:`, `deprecate:`, `resolve:`, `complexity:`, `default_value:` (input fields only), `meta:`, `args:`.
- `arg :name, :type, default_value:, description:, deprecate:` on fields and directives.
- `resolve fn args, resolution -> ... end` (arity 2) or `fn parent, args, resolution -> ... end` (arity 3) or `{Module, :fun}`.
- Default resolver is `Absinthe.Middleware.MapGet` (`Map.get(parent, field_identifier)`). Atom keys only. Replace globally with `Absinthe.Schema.replace_default/4` (for example for string keys).
- `interfaces [:a, :b]` on objects and on interfaces (interfaces implementing interfaces). `is_type_of fn ... end` on objects. `resolve_type fn value, resolution -> :type end` on interfaces and unions.
- `union :name do types [:a, :b]; resolve_type ... end`.
- `enum :color do value :red, as: "r", description:, deprecate: end`. Also `values [:a, :b]`. Internal values are atoms by default.
- `extend object :user do ... end`. Extendable: `enum`, `input_object`, `interface`, `object`, `scalar`, `union`, `schema`.
- `import_types Module`, `import_types Mod.{A, B}`, with `only:` / `except:`. Only allowed in the schema module.
- `import_fields :object_identifier` copies fields from another object. Cycles are a compile error (`NoCircularFieldImports`).
- `import_directives Module` and `import_type_extensions Module`, both with `only:` / `except:`.
- `import_sdl "type Query {...}"` or `import_sdl path: "schema.graphql"` (recompiles when the file changes). Resolvers and other logic are attached with the `hydrate/2` callback.
- `hydrate(node, ancestors)` callback on the schema returns hydrations: `{:resolve, fun}`, `{:description, text}`, `{:middleware, ...}`, `{:complexity, ...}`, `{:resolve_type, fun}`, `{:is_type_of, fun}`, `{:parse, fun}`, `{:serialize, fun}`, `{:as, value}`, `{:meta, kw}`, `:halt`. Works for macro-defined schemas too.
- `meta :key, value` or `meta key: value` stores custom metadata on types and fields. Read with `Absinthe.Type.meta/2`. Meant for libraries that extend Absinthe.
- `private(owner, key, value)` is a `@doc false` macro for library-private data on definitions (used by `absinthe_relay`). Source only.
- `__absinthe_blueprint__()` on any schema or type module returns the blueprint tree.
- Introspection helpers on the compiled schema: `Absinthe.Schema.lookup_type/3`, `lookup_directive/2`, `types/1`, `used_types/1`, `referenced_types/1`, `implementors/2`, `concrete_types/2`, `directives/1`, `introspection_types/1`, `schema_declaration/1`.
- `Absinthe.Schema.to_sdl/1` prints SDL. `Absinthe.Schema.introspect/2` runs the full introspection query.
- `use Absinthe.Schema, use_spec_compliant_int_scalar: true` swaps `Int` for a 32-bit spec-compliant version. The default `Int` accepts values up to `2^53 - 1`, which breaks the spec.

## Compile-time schema verification

- The schema is built and validated in `__after_compile__`. Any error raises `Absinthe.Schema.Error` and stops compilation.
- Schema validation phases (`Absinthe.Phase.Schema.Validation.*`): `TypeNamesAreUnique`, `TypeReferencesExist`, `TypeNamesAreReserved` (no `__` prefix), `NoCircularFieldImports`, `KnownDirectives`, `DefaultEnumValuePresent`, `DirectivesMustBeValid`, `ObjectMustDefineFields`, `InputOutputTypesCorrectlyPlaced`, `InterfacesMustResolveTypes`, `ObjectInterfacesMustBeValid`, `ObjectMustImplementInterfaces`, `NoInterfaceCycles`, `QueryTypeMustBeObject`, `NamesMustBeValid`, `UniqueFieldNames`, `OneOfDirective`. Also `KnownArgumentNames` and `RepeatableDirectives` reused from the document phases.
- Schema pipeline hook: `@pipeline_modifier MyModule` (accumulates) in the schema module. The module implements `pipeline/1` or `pipeline/2` and can insert custom phases with `Absinthe.Pipeline.insert_after/3`, `insert_before/3`, `replace/3`, `without/2`, `upto/2`, `from/2`, `before/2`, `reject/2`. A custom phase implements `run(blueprint, opts)`.
- Schema storage backends (`@schema_provider`): `Absinthe.Schema.Compiled` (default, a generated `MySchema.Compiled` module) and `Absinthe.Schema.PersistentTerm` (marked "Experimental", stores the schema in `:persistent_term`, needs `{Absinthe.Schema, MySchema}` in the supervision tree). Behaviour `Absinthe.Schema.Provider` is "Experimental" and "may change significantly in patch releases".
- `Absinthe.Schema.Hydrator` behaviour for a custom hydrator via the `:hydrator` schema pipeline option. Source only.

## Scalars

- Built-in: `:string`, `:integer` (`Int`), `:float`, `:boolean`, `:id`.
- `Absinthe.Type.Custom` (opt-in with `import_types Absinthe.Type.Custom`): `:datetime` (`DateTime`, UTC only, non-zero offset rejected), `:naive_datetime`, `:date`, `:time`, `:decimal` (only if `decimal` is installed).
- Custom scalars: `scalar :name do parse fn %Absinthe.Blueprint.Input.String{value: v} -> ... end; serialize fn v -> ... end end`. `parse` gets the typed input AST node, not a raw value. It must handle `%Absinthe.Blueprint.Input.Null{}` itself. Return `{:ok, value}`, `:error` or `{:error, reason}`.
- `@specifiedBy` via `directive :specified_by, url: "..."` in a scalar block.
- No JSON, UUID, URL, BigInt or Upload scalar in core. The wiki has "Scalar Recipes". `:upload` is in `absinthe_plug`.

## Input objects and arguments

- `input_object :name do field ... end`. Input fields support `default_value:` and `deprecate:`.
- `@oneOf` input objects via `directive :one_of` in the `input_object` block (since 1.8.0). Compile-time checks: more than one field and all fields nullable. Runtime check `Absinthe.Phase.Document.Validation.OneOfDirective`. Introspection `isOneOf` since 1.12.0.
- Argument and input field deprecation (`@deprecated` on `ARGUMENT_DEFINITION` and `INPUT_FIELD_DEFINITION`).
- Arguments arrive in resolvers as a map with atom keys (snake_case).
- No built-in argument validation DSL (no length, format or range validators). Users write middleware or check in resolvers.
- No built-in input-to-struct mapping. Enums map to atoms or to the `as:` value.

## Name conversion (adapters)

- `Absinthe.Adapter` behaviour with `to_internal_name/2` and `to_external_name/2`. Set per request with the `adapter:` run option. So one schema can serve different naming conventions to different clients.
- `Absinthe.Adapter.LanguageConventions` (default): snake_case in Elixir, camelCase in documents and results.
- `Absinthe.Adapter.StrictLanguageConventions`: same, but rejects snake_case names in incoming documents. Not in the guide. Source only.
- `Absinthe.Adapter.Underscore`: converts incoming names to snake_case, leaves output as is.
- `Absinthe.Adapter.Passthrough`: no conversion.

## Directives

- Executable: `@skip`, `@include`.
- Type system: `@deprecated`, `@specifiedBy`, `@oneOf`.
- Custom executable directives: `directive :name do arg ...; on [:field, :fragment_spread, :inline_fragment]; expand fn args, node -> ... end end`. `expand` changes the blueprint node, for example with `Absinthe.Blueprint.put_flag(node, :skip, __MODULE__)`.
- `repeatable true` in a directive definition. Validation `RepeatableDirectives`.
- Custom type system directives are defined in a prototype schema: `use Absinthe.Schema.Prototype` and `@prototype_schema MyPrototype` in the schema. Apply with `directive :feature, name: "..."` inside types, fields, args, enum values, scalars, unions, interfaces, input objects or the `schema` block. The `expand` function can change the schema blueprint at compile time. Applied directives show up in SDL and in `import_sdl`.
- `@defer` and `@stream` are not supported on `main` (see "Upcoming").

## Resolution, middleware and plugins

- Each field has a middleware list. The resolver is one middleware (`{Absinthe.Resolution, :call}`).
- `Absinthe.Middleware` behaviour: `call(%Absinthe.Resolution{}, opts)`. Middleware can also be a function `fn res, opts -> res end` or `{Module, opts}` or `{{Module, :fun}, opts}`.
- Placement: `middleware Mod, opts` inside a field (before or after `resolve`), or the schema callback `middleware(middleware, field, object)` to add middleware by object or field (for example all mutations), or a resolver can return `{:middleware, Mod, opts}`.
- `Absinthe.Resolution` struct fields: `adapter`, `definition`, `context`, `root_value`, `parent_type`, `schema`, `source`, `arguments`, `errors`, `value`, `state` (`:unresolved`, `:resolved`, `:suspended`), `middleware`, `acc` (shared across all fields, for plugins), `private`, `extensions`, `path`, `fragments`, `fields_cache`.
- `Absinthe.Resolution.put_result/2` to short-circuit with `{:ok, v}` or `{:error, e}`. Setting `state: :resolved` skips the rest.
- `Absinthe.Resolution.path/1`, `path_string/1`.
- `Absinthe.Resolution.project/1,2` returns the selected child fields for the current field (look-ahead). Handles fragments and abstract types.
- `Absinthe.Plugin` behaviour: `before_resolution/1`, `after_resolution/1`, `pipeline/2`. Plugins can add another resolution pass. This is how batching works. Schema callback `plugins/0`. Defaults: `Absinthe.Plugin.defaults()` = `[Absinthe.Middleware.Batch, Absinthe.Middleware.Async]`.
- Built-in middleware: `Absinthe.Middleware.Async` (helper `async(fun, timeout: 30_000)`), `Absinthe.Middleware.Batch` (helper `batch({Mod, :fun, arg}, key, callback, timeout: 5_000)`), `Absinthe.Middleware.Dataloader`, `Absinthe.Middleware.MapGet`, `Absinthe.Middleware.PassParent` (default subscription resolver), `Absinthe.Middleware.Telemetry`.
- `Absinthe.Middleware.shim/unshim` exist for compiled middleware. Source only.
- Schema `context/1` callback can add values to the context for every run (used for the dataloader instance).
- Context can be changed by middleware and the change carries over to later fields (see "Docs and code disagree").
- Resolver results: `{:ok, value}`, `{:error, value}`, `{:middleware, mod, opts}`.

## Batching and N+1

- `Absinthe.Middleware.Batch` with `batch/3,4`. Batch function gets the aggregated keys and returns a map. Runs in tasks. Telemetry events `[:absinthe, :middleware, :batch, :start | :stop | :exception | :timeout]`.
- Dataloader integration: `import Absinthe.Resolution.Helpers` then `dataloader(Source)`, `dataloader(Source, :resource)`, `dataloader(Source, opts)` or `dataloader(Source, fn parent, args, res -> {resource, args} end)`. Options: `args:`, `use_parent:`, `callback:`. `on_load(loader, fun)` for manual control.
- No automatic query planning or ORM projection. N+1 is solved only by batching (Batch or Dataloader). `Ecto.assoc` preloading is manual.
- If `opentelemetry_process_propagator` is installed, Async and Batch use its `Task.async/1` so OTel context crosses into tasks.

## Errors

- `{:error, "msg"}`, `{:error, %{message: "...", code: 1}}`, `{:error, message: "...", extra: ...}`, lists of these, or any value with `to_string/1`.
- Extra keys are merged into the top level of the error object by default, next to `message`, `locations`, `path`. This is not spec style.
- `spec_compliant_errors: true` on the `Absinthe.Phase.Document.Result` phase puts extra keys under `extensions`. Set through `pipeline_modifier` or `absinthe_plug` `:pipeline`. Not in the guides. Only in tests and the 1.7.9 changelog.
- "Did you mean" suggestions for unknown fields and types (`FieldsOnCorrectType`). No option to turn them off (open PR #1393).
- No built-in error masking of exceptions. I think a raised exception in a resolver crashes the request (not verified). Changeset formatting is left to `absinthe_error_payload` (third party).
- Error results for an unresolved field are `nil` with propagation to the nearest nullable parent.

## Document execution

- `Absinthe.run(document, schema, opts)` and `Absinthe.run!/3`. Document can be a string, `Absinthe.Language.Source` or a parsed `Absinthe.Language.Document`.
- Run options: `:adapter`, `:operation_name`, `:variables`, `:context`, `:root_value`, `:analyze_complexity`, `:max_complexity`, `:token_limit`, `:pipeline_modifier` (function `(pipeline, opts) -> pipeline`). Pipeline options also include `:jump_phases`, `:result_phase`, `:validation_result_phase`. Source only for the last three.
- `Absinthe.Pipeline.for_document(schema, opts)` returns the full phase list. `Absinthe.Pipeline.run/2` runs any pipeline. Users can run partial pipelines (for example parse and validate only with `upto/2`).
- Document validation phases: `ExecutableDefinitions`, `ProvidedAnOperation`, `NoFragmentCycles`, `LoneAnonymousOperation`, `SelectedCurrentOperation`, `KnownFragmentNames`, `NoUndefinedVariables`, `NoUnusedVariables`, `NoUnusedFragments`, `UniqueFragmentNames`, `UniqueOperationNames`, `UniqueVariableNames`, `ProvidedNonNullVariables`, `KnownTypeNames`, `VariableTypesMatch`, `KnownDirectives`, `RepeatableDirectives`, `ScalarLeafs`, `VariablesAreInputTypes`, `ArgumentsOfCorrectType`, `KnownArgumentNames`, `ProvidedNonNullArguments`, `UniqueArgumentNames`, `UniqueInputFieldNames`, `FieldsOnCorrectType`, `OneOfDirective`, `OnlyOneSubscription`.
- Not implemented: `OverlappingFieldsCanBeMerged` and `PossibleFragmentSpreads`. I found no file or test for either.
- Descriptions on operations and fragments are parsed (since 1.11.0, September 2025 spec).
- Introspection: `__schema`, `__type`, `__typename`. Deprecated items hidden by default. App config `config :absinthe, include_deprecated: true` changes the default of `includeDeprecated` for `args`, `inputFields` and `enumValues`. No built-in switch to turn introspection off. Users remove it with a custom phase.

## Safety limits

- Complexity analysis: `analyze_complexity: true, max_complexity: n`. Per field `complexity 10` or `complexity fn args, child_complexity -> ... end` or a 3-arity function that also gets `%Absinthe.Complexity{context, root_value, schema, definition}`, or `{Mod, :fun}`. Default per field cost is `1 + child_complexity`. Error lists the actual and max complexity.
- Token limit: `token_limit: n` (default `:infinity`). Lexer stops with "Token limit exceeded".
- No query depth limit. No alias count limit. No rate limiting. No timeout per request.

## Subscriptions

- Transport-agnostic core in `Absinthe.Subscription`. Pubsub behaviour `Absinthe.Subscription.Pubsub` (`subscribe/1`, `node_name/0`, `publish_mutation/3`, `publish_subscription/2`, optional `run_docset/3`). `absinthe_phoenix` implements it on `Phoenix.Endpoint` / `Phoenix.PubSub`.
- Supervisor: `{Absinthe.Subscription, pubsub: MyAppWeb.Endpoint, pool_size:, compress_registry?:, async:, registry_partition_strategy:}`. `pool_size` must be equal on all nodes. `async` (default `true`) and `registry_partition_strategy` (`:pid` or `:key`, Elixir 1.19+) are only in the changelog and source.
- Field config: `config fn args, resolution -> {:ok, topic: "..."} end`. Topic can be a list. Can return `{:error, ...}` to reject (authorization).
- `context_id:` in the config result de-duplicates resolution. Subscribers with the same document and same `context_id` share one resolution per publish.
- Triggers: `trigger :mutation_name, topic: fn result -> topic end` or `trigger [:m1, :m2], topic: ...`. Publishes automatically after the mutation resolves.
- Manual publish: `Absinthe.Subscription.publish(pubsub, value, field: topic)`.
- In-process subscription: `Absinthe.run(sub_doc, schema, context: %{pubsub: Endpoint})` returns `{:ok, %{"subscribed" => topic}}`.
- `Absinthe.Subscription.unsubscribe/2`.
- Subscription docs triggered by a mutation run inside the mutation process (back pressure, from the moduledoc). `Absinthe.Subscription.Local` resolves all docs for a publish together with `Absinthe.Pipeline.BatchResolver`, so batching and dataloader work across subscribers. Cross-node fan-out goes through `Absinthe.Subscription.Proxy` processes with a `PartitionSupervisor` of tasks (since 1.11.0).
- Document ids are a SHA-256 of the document, variables and context id.
- Telemetry `[:absinthe, :subscription, :publish, :start | :stop]`.
- No subscription filtering beyond topics. No catch-up or priming of initial state (open PR #1168).

## Telemetry and logging

- Events: `[:absinthe, :execute, :operation, :start | :stop]`, `[:absinthe, :resolve, :field, :start | :stop]`, `[:absinthe, :subscription, :publish, :start | :stop]`, batch events above.
- No built-in tracing format (no Apollo tracing). OpenTelemetry is through the third-party `opentelemetry_absinthe` (I think, not verified here).
- `Absinthe.Logger`: `config :absinthe, Absinthe.Logger, filter_variables: ["token", "password"], pipeline: true`. `config :absinthe, log: false`. Variable values matching the terms are logged as `"[FILTERED]"`. Called by `absinthe_plug`.

## Tooling

- `mix absinthe.schema.sdl [--schema Mod] [file]` writes `schema.graphql`.
- `mix absinthe.schema.json [--schema Mod] [--json-codec Mod] [--pretty] [file]` writes introspection JSON.
- `Absinthe.Formatter`: formats `.graphql` / `.gql` files. Works as a `mix format` plugin (`plugins: [Absinthe.Formatter]`).
- `~GQL` sigil (`Absinthe.Sigil`, since 1.9.0): parses at compile time, prints parse errors to stderr, and lets `mix format` format the embedded GraphQL.
- `Absinthe.Test.prime(MySchema)`: runs introspection once to load code before timing-sensitive tests.
- No codegen for clients or types. No schema diff or breaking change check.

## absinthe_plug (1.5.10, last commit 2026-05-15)

- `plug Absinthe.Plug, schema: ...`. `Absinthe.Plug.Parser` for `application/graphql` bodies. GET with `query`, `variables`, `operationName`. POST JSON, form, multipart. Mutations over GET are rejected (`Absinthe.Validation.HTTPMethod`).
- Options: `:schema`, `:adapter`, `:context`, `:json_codec`, `:serializer` (for example MessagePack), `:content_type`, `:pipeline` (`{Mod, :fun}` to build the pipeline), `:document_providers`, `:no_query_message`, `:before_send` (change the conn after execution, for example set a cookie), `:log_level`, `:pubsub`, `:analyze_complexity`, `:max_complexity`, `:token_limit`, `:transport_batch_payload_key`, `:standard_sse`.
- `Absinthe.Plug.put_options(conn, context: ...)` and `assign_context/2` set per-request options from earlier plugs.
- Transport batching: a JSON array of operations in one request (`Absinthe.Plug.Batch.Runner`). Results returned in order. Batched queries are resolved together by `Absinthe.Pipeline.BatchResolver`, so batching and dataloader work across them.
- Persisted documents: `Absinthe.Plug.DocumentProvider` behaviour. `Absinthe.Plug.DocumentProvider.Compiled` with `provide "id", "query ..."` or `provide %{...}` and `key_param:` (default `"id"`). Documents are parsed and validated at compile time. Can load Apollo `persistgraphql` output. No Apollo APQ hash protocol built in.
- File uploads: `import_types Absinthe.Plug.Types` gives `:upload`. The argument value names a multipart part. Value is `%Plug.Upload{}`. This is not the `graphql-multipart-request-spec`. Clients need `apollo-absinthe-upload-link`.
- Subscriptions over HTTP as SSE (`text/event-stream`) when a pubsub is configured. `standard_sse: true` follows the `graphql-sse` `next` event format. Otherwise subscriptions over HTTP are rejected.
- `Absinthe.Plug.GraphiQL` with `interface: :advanced` (GraphiQL Workspace, default), `:simple` (GraphiQL 3.8.3), `:playground` (GraphQL Playground). Options `default_headers`, `default_url`, `socket_url`, `socket`, `default_query`. `mix absinthe.plug.graphiql.assets.download` and `.remove` to self-host assets.

## absinthe_phoenix (2.0.5, last commit 2026-05-05)

- `use Absinthe.Phoenix.Endpoint`, `use Absinthe.Phoenix.Socket, schema:, pipeline:, gc_interval:`. `Absinthe.Phoenix.Socket.put_options(socket, context: ...)` in `connect/2`.
- Protocol: a Phoenix channel `__absinthe__:control` with `doc` and `unsubscribe` events. Clients need `@absinthe/socket` and `@absinthe/socket-apollo-link` (or the Relay variant). It does not speak `graphql-ws` or `graphql-transport-ws`. I found no reference to either in the source.
- I think queries and mutations can also run over the socket (the `doc` event takes any document). Not verified.
- `gc_interval:` runs periodic garbage collection on the channel process (memory bloat workaround).
- `Absinthe.Phoenix.Controller`: `use Absinthe.Phoenix.Controller, schema:, action: [mode: :internal]` and a `@graphql "..."` attribute per action. Params become variables. Results replace params. Internal mode allows object fields without a selection set (returns the whole struct). Useful for server-rendered views.
- `Absinthe.Phoenix.SubscriptionTest` helpers for channel tests (`join_absinthe/1`, `push_doc/3`).

## absinthe_relay (1.6.0, last commit 2025-11-06)

- `use Absinthe.Relay.Schema, :modern` (or `:classic`). `use Absinthe.Relay.Schema.Notation, :modern` in type modules.
- Nodes: `node interface do resolve_type ... end`, `node field do resolve fn %{type: t, id: id}, _ -> ... end end`, `node object :thing, id_fetcher: fun do ... end`. `id_type:` option (for example `:uuid`). Global IDs are Base64 of `Type:id` by default. Custom `Absinthe.Relay.Node.IDTranslator` via `global_id_translator:` option or app config.
- `Absinthe.Relay.Node.to_global_id/3`, `from_global_id/2`. `Absinthe.Relay.Node.ParseIDs` middleware (`parse_id`) decodes global IDs in arguments and nested inputs, with type checks.
- Connections: `connection node_type: :pet do field ...; edge do field ... end end` and `connection field :pets, node_type: :pet, paginate: :forward | :backward | :both`. Helpers `Connection.from_list/3`, `from_slice/3`, `from_query/4` (Ecto, `max:` option), `offset_and_limit_for_query/2`, `cursor_to_offset/1`, `offset_to_cursor/1`. Edge extra fields via `{node, edge_attrs}` tuples. Cursors are offset based. No keyset pagination. No `totalCount` built in (users add it as a custom connection field).
- Mutations (modern): `payload field :name do input do ... end; output do ... end; resolve ... end`. Adds `input` argument and `clientMutationId`.

## dataloader (Hex 2.0.2 on 2024-12-19, repo last commit 2025-11-18)

- `Dataloader.new(get_policy:, timeout:)`, `add_source/3`, `load/4`, `load_many/4`, `run/1`, `get/4`, `get_many/4`, `put/5`, `pending_batches?/1`.
- `get_policy`: `:raise_on_error` (default), `:return_nil_on_error`, `:tuples`.
- `Dataloader.Ecto.new(Repo, query: fun, run_batch: fun, repo_opts:, timeout:, max_concurrency:, async?:)`. Loads associations by name (including `has_many :through`), or `{:one | :many, Queryable}` with column filters. `query/2` hook per queryable for scoping (soft delete, permissions). Queries with `limit` or `offset` use a `LATERAL` join, so per-parent limits work. Lateral handling is source only.
- `Dataloader.KV.new(load_fun, max_concurrency:, timeout:, async?:)` for any key-value backend.
- `Dataloader.Source` protocol for custom sources. Since 2.0 it needs an `async?/1` function.
- `mix.exs` on `main` says 2.0.1 and the changelog has 2.0.2 changes as "Unreleased", but Hex has 2.0.2.

## Not supported (core and official companions)

- `@defer` / `@stream` on released code.
- `OverlappingFieldsCanBeMerged` and `PossibleFragmentSpreads` validation.
- Query depth limit, alias limit, per-request timeout.
- `graphql-ws` / `graphql-transport-ws` WebSocket protocols.
- Federation (Apollo subgraph). Only third-party packages exist.
- Built-in authorization or permissions DSL. Done with middleware.
- Argument validation DSL.
- Schema visibility or per-viewer schema hiding.
- Automatic ORM types, filters, ordering or projection from Ecto schemas. Types are written by hand.
- APQ (hash-based automatic persisted queries).
- Response or field caching.
- Client codegen.
- Error masking.

## Upcoming and unreleased work

- `defer-stream-wip` branch (2026-02-09, 1 commit ahead, 34 behind `main`): "Implement @defer and @stream directives for incremental delivery (#1377)". Adds `Absinthe.Incremental.*`, `Absinthe.Streaming.*`, `Absinthe.Middleware.AutoDeferStream`, `Absinthe.Middleware.IncrementalComplexity`, `Absinthe.Pipeline.Incremental`, built-in `@defer`/`@stream` directives, a `guides/incremental-delivery.md` guide with transports `:auto | :sse | :websocket`, and telemetry `[:absinthe, :incremental, ...]`.
- `cschiewek/schema-coordinates` branch (2025-11-21): schema coordinates for types, fields, args and enum values.
- Open PRs: LeafList optimization for nullable scalar lists (#1451), operation `:exception` telemetry event when a phase raises (#1443), configurable `Task` implementation for async (#1349), disable field suggestions on errors (#1393), `DigitAwareLanguageConventions` adapter (#1417), subscription priming / ordinals for catch-up state (#1168, absinthe part, open since years and updated 2026-09-07), eliminate bare atom identifiers (#1198), Sobelow security scanning in CI (#1440), reject integers with no finite float form (#1457), Unicode surrogate escapes in strings (#1460), keep comments when formatting (#1428).
- 1.12.0 (2026-09-02) was mostly performance: faster suspended fields (Dataloader, Batch) and less memory for lists of scalars.

## Docs and code disagree

- `guides/context-and-authentication.md` says the context "cannot be modified over the course of a given execution". The code carries context changes from middleware to later fields (`update_persisted_fields` in `Absinthe.Phase.Document.Execution.Resolution`). The `Absinthe.Resolution` moduledoc also says you can update it.
- `guides/complexity-analysis.md` says a 3-arity complexity function gets an `%Absinthe.Resolution{}`. The code passes `%Absinthe.Complexity{}` (`context`, `root_value`, `schema`, `definition`). The `Absinthe.Type.Field` docs are correct.
- `guides/introspection.md` shows `include_deprecated: true` changing `__Type.fields`. In the code, `fields` has a fixed `default_value: false`. The config only changes `args`, `inputFields` and `enumValues`.
- `CHANGELOG.md` 1.7.10 says "Set include_deprecated default value to true for backwards compatibility". The code default is `false` (`Application.get_env(:absinthe, :include_deprecated, false)`).
- `guides/adapters.md` says Absinthe "ships with two adapters" and then lists three. The code has four (`StrictLanguageConventions` is not mentioned).
- `Absinthe.run/3` docs list only six options. The code also accepts `:token_limit` and `:pipeline_modifier` (in the typespec) and pipeline options like `:result_phase`.
- `Absinthe.Subscription.child_spec/1` docs and `@type opt` list `:pubsub`, `:compress_registry?`, `:pool_size`. The code also reads `:async` and `:registry_partition_strategy`.
- `Absinthe.Subscription` moduledoc describes a "beta release" and says "database batching does not happen across the set of subscription docs". The code batches them with `Absinthe.Pipeline.BatchResolver` in `Absinthe.Subscription.Local`.
- `guides/client/relay.md` says `:modern` "will be the default option in v1.5". `absinthe_relay` is at 1.6.0.
- `CHANGELOG.md` has two `1.12.0` headings, one dated 2026-09-02 and one "(Pending)".
- `dataloader` Hex release 2.0.2 exists, but `mix.exs` on `main` is 2.0.1 and the changelog marks the change as "Unreleased".

## Sources

Repos (shallow clones in `/tmp/abs-*`):
- https://github.com/absinthe-graphql/absinthe (`main` at `1372ceb`, 2026-09-02)
- https://github.com/absinthe-graphql/absinthe_plug (`a20146e`, 2026-05-15)
- https://github.com/absinthe-graphql/absinthe_phoenix (`95e6b97`, 2026-05-05)
- https://github.com/absinthe-graphql/absinthe_relay (`344ad76`, 2025-11-06)
- https://github.com/absinthe-graphql/dataloader (`9af722c`, 2025-11-18)

Docs read (repo source of https://hexdocs.pm/absinthe/overview.html):
- All of `guides/*.md`: `introduction/overview.md`, `schemas.md`, `middleware-and-plugins.md`, `errors.md`, `context-and-authentication.md`, `complexity-analysis.md`, `directives.md`, `subscriptions.md`, `batching.md`, `dataloader.md`, `custom-scalars.md`, `introspection.md`, `importing-types.md`, `importing-fields.md`, `adapters.md`, `variables.md`, `testing.md`, `telemetry.md`, `file-uploads.md`, `plug-phoenix.md`, `client/apollo.md`, `client/javascript.md`, `client/relay.md`. Tutorial and upgrade guides skimmed.
- Module docs read in source: `Absinthe`, `Absinthe.Schema`, `Absinthe.Schema.Notation`, `Absinthe.Schema.Prototype`, `Absinthe.Schema.PersistentTerm`, `Absinthe.Schema.Provider`, `Absinthe.Pipeline`, `Absinthe.Resolution`, `Absinthe.Resolution.Helpers`, `Absinthe.Middleware*`, `Absinthe.Plugin`, `Absinthe.Subscription*`, `Absinthe.Type.*`, `Absinthe.Complexity`, `Absinthe.Logger`, `Absinthe.Formatter`, `Absinthe.Sigil`, `Absinthe.Test`, `Absinthe.Adapter.*`, mix tasks.
- Companion module docs: `Absinthe.Plug`, `Absinthe.Plug.GraphiQL`, `Absinthe.Plug.DocumentProvider*`, `Absinthe.Plug.Types`, `Absinthe.Phoenix.Socket`, `Absinthe.Phoenix.Controller`, `Absinthe.Relay.Connection`, `Absinthe.Relay.Node*`, `Absinthe.Relay.Mutation.Notation.Modern`, `Dataloader`, `Dataloader.Ecto`, `Dataloader.KV`.
- https://hexdocs.pm/absinthe/llms.txt returns 404. `.md` page URLs return 404.

Changelogs and status:
- `CHANGELOG.md` of all five repos.
- Hex API (`https://hex.pm/api/packages/<name>`) for versions, dates and downloads.
- `gh release list`, `gh pr list`, `gh api repos/.../branches/<name>` and `compare/main...defer-stream-wip` for branches and open PRs.

Source files checked:
- `lib/absinthe.ex`, `lib/absinthe/pipeline.ex`, `lib/absinthe/schema.ex`, `lib/absinthe/schema/notation.ex`, `lib/absinthe/phase/document/result.ex`, `lib/absinthe/phase/document/complexity/analysis.ex`, `lib/absinthe/phase/document/execution/resolution.ex`, `lib/absinthe/phase/schema/hydrate.ex`, `lib/absinthe/phase/schema/spec_compliant_int.ex`, `lib/absinthe/type/built_ins/introspection.ex`, `lib/absinthe/subscription.ex`, `lib/absinthe/subscription/supervisor.ex`, `lib/absinthe/subscription/pubsub.ex`, `lib/absinthe/lexer.ex`, validation phase directory listings.
- `absinthe_plug/lib/absinthe/plug.ex`, `plug/graphiql.ex`, `validation/no_subscription_on_http.ex`, `plug/batch/runner.ex`.
- `absinthe_phoenix/lib/absinthe/phoenix/socket.ex`, `channel.ex`, `controller.ex`.
- `dataloader/lib/dataloader.ex`, `dataloader/ecto.ex`.
