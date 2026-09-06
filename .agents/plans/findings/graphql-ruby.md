# graphql-ruby findings

Versions checked: `graphql` gem 2.6.11 (RubyGems, 2026-09-21). Repo `master` at `6484df1` (2026-10-01, commit `pro-1.30.4`). `graphql-c_parser` 1.1.4 (2026-08-03). npm `graphql-ruby-client` 1.16.0 (2026-08-26). Paid gems from the changelogs: `graphql-pro` 1.30.4 (2026-10-01), `graphql-enterprise` 1.7.0 (2026-04-24).
graphql-ruby is a code-first, class-based GraphQL server library for Ruby. It has its own parser, validator, analyzer and executor (it does not wrap a reference implementation). Schema is a Ruby class (`class MySchema < GraphQL::Schema`). Types are Ruby classes. Rails integration is optional (generators, Railtie, Dashboard engine). Works with any Rack app. MIT. Ruby `>= 2.7.0`.
Two paid add-ons: GraphQL-Pro ($1100/year) and GraphQL-Enterprise ($2400/year, includes Pro). Their source is closed. Their docs are on graphql-ruby.org. Paid features are marked **[Pro]** or **[Enterprise]** below. Everything not marked is free in the `graphql` gem.

## Maintenance status

- Very active. Single main maintainer (Robert Mosolgo, rmosolgo), plus Shopify contributors (`Execution::Next` is based on Shopify's breadth-first work). Last commit on `master`: 2026-10-01. GitHub `pushed_at` 2026-10-01. 5444 stars. 68 open issues plus PRs. Not archived.
- Releases: 2.6.11 (2026-09-21), 2.6.10 (2026-08-27), 2.6.9 (2026-08-17, security), 2.6.8 (2026-08-13), 2.6.7 (2026-07-28), 2.6.6 (2026-07-21, security), 2.6.5 (2026-07-06), 2.6.4 (yanked), 2.6.3 (2026-05-26), 2.6.0 (2026-04-24). Roughly one patch release every two to three weeks.
- Versioning is not semver. The `development.md` guide says MINOR may contain small breaking changes.
- Changelogs in the repo: `CHANGELOG.md`, `CHANGELOG-pro.md`, `CHANGELOG-enterprise.md`, `CHANGELOG-relay.md` (old).
- 33 commits on `master` after the 2.6.11 tag, not released yet (see "Upcoming").
- Docs site https://graphql-ruby.org/ is Jekyll, built from `guides/` in the main repo (124 `.md` files, about 72k words). API docs are generated YARD docs. `/llms.txt` returns 404. `Accept: text/markdown` returns HTML.

## Schema definition

- `class MySchema < GraphQL::Schema` with `query(...)`, `mutation(...)`, `subscription(...)`. Root types can be given in a block (`query { Types::Query }`) for lazy loading.
- `Schema.orphan_types`, `Schema.extra_types` (types printed and introspectable but not reachable).
- `Schema.use(plugin, **opts)` is the plugin mechanism. Plugins implement `.use(schema, **kwargs)`. `Schema.plugins` lists them.
- Code-first type classes: `GraphQL::Schema::Object`, `Interface` (a module), `Union`, `Enum`, `InputObject`, `Scalar`, `Directive`. Base classes are normal Ruby inheritance. All config is inherited by subclasses.
- Customizable member classes: `field_class`, `argument_class`, `enum_value_class`, `connection_type_class`, `edge_type_class`, `type_membership_class`, `object_class`, `input_object_class`. This is how users add custom keyword options to `field`/`argument`/`value`.
- `graphql_name`, `description`, `comment` (printed as `# ...` SDL comment above the definition), `deprecation_reason` on fields, arguments, enum values and resolvers (`Resolver.deprecation_reason` since 2.5.2).
- Automatic camelCase of field and argument names. Opt out with `camelize: false`. Already-camelCased names stay camelCased in GraphQL but are passed snake_cased to resolvers.
- `Schema.from_definition(path_or_string, default_resolve:, using:)` builds a runnable schema from SDL. `default_resolve:` takes an implementation object (`#call`, `#resolve_type`, `#coerce_input`, `#coerce_result`) or an implementation hash. `using:` installs plugins. SDL directives are available as `.ast_node.directives`.
- `Schema.from_introspection(introspection_result)` builds a schema from an introspection JSON result. Source only (`GraphQL::Schema::Loader`).
- `Schema.to_definition(context:)` prints SDL. `Schema.to_document`. `Schema.to_json` / `Schema.as_json` dump introspection JSON. `GraphQL::Schema::Printer` for custom printing. Source only for the printer class.
- `Schema.find("Type.field.argument")` finds a schema member by path. Source only.
- `Schema.get_type`, `Schema.get_field`, `Schema.possible_types`, `Schema.references_to`, `Schema.union_memberships` (the last two do not work with `Schema::Visibility`).
- Lazy type loading in development: needs `use GraphQL::Schema::Visibility` and root types and field types in blocks (`field :posts do type([Types::Post]) end`).
- `GraphQL.eager_load!` for production boot. Rails calls it automatically.
- `Schema.freeze_schema` and `GraphQL::Schema::RactorShareable` for minimal Ractor support (2.5.10). Source only.
- `Schema.did_you_mean(...)`: uses Ruby `DidYouMean` for "did you mean" suggestions in errors. Return `nil` to turn off. Source only.
- Pattern matching on non-null and list type definitions (2.6.6).
- RuboCop cops shipped in the gem (`require "graphql/rubocop"`): `GraphQL/DefaultNullTrue`, `GraphQL/DefaultRequiredTrue`, `GraphQL/FieldTypeInBlock`, `GraphQL/RootTypesInBlock`.

## Object types and fields

- `field :name, Type, "desc", null:, ...`. Fields default to `null: true`. Arguments default to `required: true`.
- Field options from `Schema::Field#initialize`: `method:`, `hash_key:`, `dig: [...]`, `resolver_method:`, `fallback_value:`, `connection:`, `max_page_size:`, `default_page_size:`, `scope:`, `camelize:`, `trace:` (per-field tracing opt in or out), `complexity:`, `dataload:`, `extras:`, `extensions:`, `resolver:`/`mutation:`/`subscription:`, `subscription_scope:`, `broadcastable:`, `directives:`, `validates:`, `method_conflict_warning:`, `resolve_static:`/`resolve_each:`/`resolve_batch:`/`resolve_legacy_instance_method:`, `relay_node_field:`, `relay_nodes_field:`, `dynamic_introspection:`.
- Default resolution: call method on the type class instance, then the underlying object method, then hash key (symbol or string), then `fallback_value:`. `method: :itself` passes the object through.
- Resolver methods are instance methods on the type class with `object` and `context` helpers. Arguments become Ruby keyword args.
- `extras: [...]` injects runtime metadata into the resolver: `:ast_node`, `:graphql_name`, `:owner`, `:lookahead`, `:execution_errors`, `:argument_details`, `:parent`. Any method on a custom field class can be used as a custom extra.
- Fields can be redefined for different viewers with `visible?` (two definitions with the same name, one hidden). See Visibility.
- `Types::BaseObject.fields(context)` and `.get_field(name, context)` can be overridden to return a dynamic field set per request.
- `field ... do ... end` block form for description, arguments, complexity, extensions, validates.

## Arguments and input objects

- `argument :name, Type, required:, default_value:, as:, prepare:, loads:, validates:, deprecation_reason:, replace_null_with_default:, camelize:, directives:, comment:`.
- `required: :nullable` means the argument must be passed but `null` is accepted.
- `replace_null_with_default: true` uses `default_value:` when the client sends `null`.
- `as: :other_name` renames the Ruby keyword.
- `prepare: ->(value, ctx) { ... }` or a method name. Can transform the value or raise `GraphQL::ExecutionError`.
- `loads: Types::Thing` turns an `ID` argument into an application object via `Schema.object_from_id`, checks the type via `Schema.resolve_type`, runs `.authorized?`, and strips the `_id`/`_ids` suffix from the keyword name. Works with lists of IDs and with interfaces and unions. `def load_#{arg}(id)` overrides loading per resolver. `load_application_object_failed(error)` and `unauthorized_object(error)` customize failures. Error class `GraphQL::LoadApplicationObjectFailedError`.
- Argument `#authorized?(object, arg_value, context)` and `#visible?(context)`.
- Argument deprecation is marked "Experimental" in the docs.
- `GraphQL::Schema::InputObject` with `argument(...)`. Values are input object instances. Access by method (`attrs.full_text`) or by `#[]` with camel-cased key. `#to_h`. `@arguments` and `@context` available. Custom methods allowed.
- `InputObject#prepare` converts the whole input object to another Ruby value (for example a `Range`).
- `one_of` on an input object implements `@oneOf` (spec September 2025). Introspection `isOneOf`. Validation rule `OneOfInputObjectsAreValid`.
- Argument validation with `validates:` (see Validation).

## Validation (argument validators)

- `validates: { ... }` on arguments, or `validates ...` inside a field block, input object or resolver.
- Built-in validators: `length:` (`maximum`, `minimum`, `is`, `within`), `format:` (`with`, `without`), `numericality:` (`greater_than`, `greater_than_or_equal_to`, `less_than`, `less_than_or_equal_to`, `other_than`, `odd`, `even`), `inclusion: { in: }`, `exclusion: { in: }`, `required: { one_of: [...] }` (exactly one argument from a set, can be nested lists for groups), `allow_blank:`, `allow_null:`, `all: { ... }` (apply to each list item).
- Custom messages per validator.
- Validator options can be procs evaluated at runtime (2.6.3).
- Custom validators subclass `GraphQL::Schema::Validator` and implement `validate(object, context, value)`. Return a message string or array of strings. Register with `GraphQL::Schema::Validator.install(:keyword, Klass)` or pass the class directly.
- `required:` validator raises a developer error when all `one_of:` options are hidden. `allow_all_hidden: true` permits it (2.5.15).
- Validation errors go to the top-level `"errors"` array.

## Scalars and enums

- Built-in scalars: `String`, `Int`/`Integer`, `Float`, `Boolean`, `ID`.
- Extra scalars in the gem (opt in by referencing them): `GraphQL::Types::ISO8601DateTime`, `ISO8601Date`, `ISO8601Duration` (needs `ActiveSupport::Duration`), `JSON` (untyped), `BigInt`.
- Custom scalars: subclass `GraphQL::Schema::Scalar`, implement `self.coerce_input(value, ctx)` and `self.coerce_result(value, ctx)`. Raise `GraphQL::CoercionError` for bad input.
- `@specifiedBy` directive (`GraphQL::Schema::Directive::SpecifiedBy`, `specified_by_url`). Source only.
- `Float` rejects non-finite values (2.6.10).
- Enums: `value "NAME", "desc", value: ruby_value, deprecation_reason:, comment:, value_method:`. Generates class methods like `Types::MediaCategory.audio # => "AUDIO"`. `value_method: false` skips that.
- Dynamic enum values per request: override `self.enum_values(context)`.
- Enum value `#authorized?(context)` and `#visible?(context)`. Unauthorized input raises `GraphQL::UnauthorizedEnumValueError` (goes to `Schema.unauthorized_object`). Unauthorized output raises `GraphQL::Schema::Enum::UnresolvedValueError` (crashes the query).

## Interfaces and unions

- Interfaces are Ruby modules that `include GraphQL::Schema::Interface`. Objects use `implements Types::Iface`. Interfaces can implement interfaces.
- Interfaces can provide default field implementations as instance methods.
- `definition_methods do ... end` adds inherited class methods to interfaces (like `ActiveSupport::Concern#class_methods`).
- `resolver_methods do ... end` copies class methods into implementing objects for `Execution::Next`.
- `resolve_type(object, context)` on the interface, the union, or `Schema.resolve_type(abstract_type, obj, ctx)`. Can return `[Type, unwrapped_object]` to swap the runtime object.
- `orphan_types` on an interface or on the schema.
- Unions: `possible_types A, B`.
- Since 2.6.0, SDL must list all transitively implemented interfaces (spec fix, breaking).

## Resolvers, mutations

- `GraphQL::Schema::Resolver`: reusable class with `type`, `argument`, `def resolve(**args)`, `extension`, `extras`, `null`, `description`, `deprecation_reason`. Attach with `field :x, resolver: Klass`. String type names (`type "[Types::Task]"`) break load cycles.
- `GraphQL::Schema::Mutation`: Resolver subclass for mutation fields. `field ...` in the class builds a generated payload type. `null(false)` makes the payload non-null.
- `GraphQL::Schema::RelayClassicMutation`: generates a single `input:` input object and a payload type, with `clientMutationId`. `GraphQL::Schema::HasSingleInputArgument` is the mixin behind it (source only).
- Mutation lifecycle: `self.authorized?(obj, ctx)` (class) then `#ready?(**args)` (before loads) then argument `loads:` then `#authorized?(**args)` (after loads) then `#resolve`. `ready?` and `authorized?` may return `false, { errors: [...] }` to return errors as data, or raise `GraphQL::ExecutionError`.
- Root mutation fields run serially (spec).
- "Errors as data" pattern documented: `errors` field with a user error type. Docs recommend nullable payload fields for this.
- No built-in model-driven create/update/delete mutations. Rails generators can scaffold them (`graphql:mutation_create`, `_update`, `_delete`).

## Authorization

Three layers: visibility (schema shape per request), authorization (per object/field at runtime), scoping (filter lists).

- Type `.authorized?(object, context)`. Called for every object returned from a field. `false` replaces the object with `nil` by default.
- Field `#authorized?(object, args, context)`. Argument `#authorized?(object, arg_value, context)`. Resolver/Mutation `.authorized?(obj, ctx)` and `#authorized?(**args)`. Enum value `#authorized?(context)`.
- `authorized?` may return a lazy value (Dataloader or promise).
- `Schema.unauthorized_object(error)` and `Schema.unauthorized_field(error)` hooks. Raise `GraphQL::ExecutionError`, return a replacement object, or return `nil`.
- Errors: `GraphQL::UnauthorizedError`, `GraphQL::UnauthorizedFieldError`.
- Scoping: field `scope: true|false` (default `true` for list and connection fields). Type `self.scope_items(items, context)` filters lists. `reauthorize_scoped_objects(false)` skips per-item `.authorized?` after scoping.
- No built-in authentication. Docs say: authenticate in the controller and put the user in `context`.
- **[Pro]** `GraphQL::Pro::PunditIntegration`: `ObjectIntegration`, `FieldIntegration`, `ArgumentIntegration`, `MutationIntegration`, `ResolverIntegration`, `UnionIntegration`, `InterfaceIntegration`. `pundit_role :name` (calls `#name?` on the policy), `pundit_role nil` to bypass, `pundit_policy_class`, Pundit scopes applied to lists and connections (crashes if a scope is missing), `scope: false` bypass. Custom hooks `pundit_policy_class_for`, `pundit_role_for`, `scope_by_pundit_policy`. `unauthorized_by_pundit(owner, value)` for mutations (can return errors as data). Custom user via `Context#pundit_user`. Generator `rails generate graphql:pundit:install`.
- **[Pro]** `GraphQL::Pro::CanCanIntegration`: same module set. `can_can_action :read`, `can_can_attribute:` (CanCan 3 attribute rules), `can_can_subject:` for root fields with no object, `.accessible_by` for relation scoping, `select` for arrays, `unauthorized_by_can_can(owner, value)`, custom ability via `context[:can_can_ability]`. Generator `rails generate graphql:cancan:install`. Also supports Mongoid criteria scoping (changelog).

## Visibility (per-request schema)

- `use GraphQL::Schema::Visibility` (the new implementation). Legacy `GraphQL::Schema::Warden` is still the fallback. Docs say Visibility "will be the default in a future version".
- `visible?(context)` on types (class method), fields, arguments, enum values (instance methods), mutations and resolvers. Hidden members do not exist for that query: they disappear from introspection and cause validation errors when queried.
- Hiding cascades: a field whose return type is hidden is hidden. An argument whose input type is hidden is hidden. Interfaces and unions must be hidden manually when all members are hidden (differs from Warden).
- Multiple definitions with the same name are allowed if only one is visible per request. Used to migrate a type (for example scalar `Money` to object `Money`) or to give staff a different field implementation.
- Visibility profiles: `use GraphQL::Schema::Visibility, profiles: { public: {...}, beta: {...} }`. Query picks one with `context[:visibility_profile]`. Profiles are cached and frozen. `preload:` defaults to true in Rails production and staging. `dynamic: true` permits queries without a profile.
- `migration_errors: true` runs Visibility and Warden side by side and raises on differences. Context flags `visibility_migration_running`, `visibility_migration_warden_running`, `skip_migration_error`.
- `use GraphQL::Schema::AlwaysVisible` turns all checks off for speed.
- `Schema.to_definition(context: {...})` dumps the schema as seen by a given context.
- `GraphQL::Schema::Directive::Flagged`: example schema directive that hides members unless `context[:flags]` contains a flag.
- Introspection entry points can be disabled: `disable_introspection_entry_points`, `disable_schema_introspection_entry_point`, `disable_type_introspection_entry_point`.

## Query execution API

- `MySchema.execute(query_string, variables:, context:, root_value:, operation_name:, document:, validate:, max_depth:, max_complexity:, visibility_profile:, static_validator:)`. Returns `GraphQL::Query::Result` (hash-like, has `.context`, `.query`, `.subscription?`).
- `MySchema.multiplex([{query:, variables:, context:, operation_name:}, ...], context:)`. Every query runs inside a multiplex (single query = multiplex of one). Results keep request order. Used for Apollo batched HTTP.
- `MySchema.validate(query_string)` returns validation errors only.
- `GraphQL::Query.new(...)` with `#result`, `#fingerprint`, `#query_fingerprint`, `#variables_fingerprint`, `#sanitized_query_string`, `#selected_operation_name`, `#mutation?`, `#subscription_update?`.
- `Query#run_partials` and `GraphQL::Query::Partial`: run a sub-tree (path or fragment) of an already valid query with a given object (2.5.6, 2.5.8). Used internally by the new `@defer`.
- `GraphQL::Query::Context`: wraps the user hash. `context[:key]`, `scoped_set!`, `scoped_merge!`, `context.scoped` (scoped context visible only to the current field and children), `response_extensions[...]` (adds to top-level `"extensions"`), `add_error`, `skip` (returns a skip marker), `raw_value(...)` (return pre-built JSON without further resolution), `current_path`, `dataloader`, `logger`, `namespace(:key)`, `backtrace`.
- `Schema.context_class(...)` and `Schema.query_class(...)` plug in custom subclasses.
- Root value `root_value:` is the `object` for root fields.
- `GraphQL::Current`: fiber-local `GraphQL::Current.operation_name`, `.field`, `.dataloader_source_class`, `.dataloader_source`. Used for `ActiveRecord::QueryLogs` tags.
- `Schema.lazy_resolve(LazyClass, :method)`: register promise-like classes for lazy execution (used by GraphQL-Batch).
- Phases: lex, parse, validate, analyze, execute, respond.
- Non-null error propagation per spec. `Schema.type_error(err, ctx)` customizes invalid null and unresolved type handling.
- `Schema.error_bubbling` exists but is deprecated (will be removed in 3.0). Source only.

## Execution::Next (new breadth-first engine)

- `use GraphQL::Execution::Next`, then `MySchema.execute_next(...)` and `MySchema.multiplex_next(...)`. `as_default: true` makes `execute` use it. `execute_legacy` runs the old engine.
- Breadth-first ("execution batching"), based on Shopify's GraphQL Cardinal / `graphql-breadth-exec`. Docs claim up to 15x faster and 75% less memory on list-heavy responses.
- Resolvers become class methods. Field configs: `resolve_each: true|:method` (per object, `def self.f(object, context, **args)`), `resolve_static:` (one result for all objects, `def self.f(context, **args)`), `resolve_batch:` (`def self.f(objects, context, **args)`, returns an array), `resolve_legacy_instance_method:` (compat, slow), `method:`, `hash_key:` (no fallback between symbol and string keys).
- `dataload:` shorthand on fields: `dataload: Sources::X`, `dataload: { with:, using:, by:, method: }`, `dataload: { association: true|:name, method: }` (uses `ActiveRecordAssociationSource`), `dataload: { model: Post, using: :post_id, find_by:, method: }` (uses `ActiveRecordSource`).
- Field extensions receive `objects:` and `values:` arrays.
- Not supported in Next: `current_path`, scoped context, `fallback_value:`, `extras: [:current_path]`, `extras: [:execution_errors]`, `context.add_error`, returning arrays of `ExecutionError`, custom `load_*` methods, `GraphQL::Backtrace`. Custom runtime directives are "not stable". Query-level directives are "not implemented yet".
- Argument `#authorized?` is called even when only a default value applies.
- Helper tool `graphql_migrate_execution` (separate project, https://rmosolgo.github.io/graphql_migrate_execution/) rewrites resolvers.
- Docs recommend feature flags and dual-run experiments (compare `execute` and `execute_next` results) for migration.
- Pro 1.30.0 and Enterprise 1.7.0 added support for Next.

## Dataloader (batching)

- `use GraphQL::Dataloader`. Fiber-based. One Dataloader per query or multiplex.
- Sources: subclass `GraphQL::Dataloader::Source`, implement `fetch(keys)` returning one value per key in order. Batch parameters via `initialize(...)` and `dataloader.with(SourceClass, *params)`. Source instances are deduplicated per batch key (`Source.batch_key_for`).
- `dataloader.with(...).load(key)`, `.load_all(keys)`, `.request(key)` / `.request_all(keys)` then `.load` (non-blocking registration).
- `Source#merge({key => value})` prefills the cache. `result_key_for(key)` customizes cache keys and deduplication.
- `dataloader.yield` inside `fetch` for manual parallelism (Rails `load_async`, `async_count`, `Concurrent::Future`, threads).
- `GraphQL::Dataloader::AsyncDataloader`: uses the `async` gem. Runs `fetch` calls in parallel with `Fiber.scheduler`. Needs Rails 7.1+ and `isolation_level = :fiber` on Rails.
- Fiber lifecycle hooks on a Dataloader subclass: `get_fiber_variables`, `set_fiber_variables`, `cleanup_fiber` (used for ActiveRecord connection handling and `connected_to` roles and shards).
- Built-in sources: `GraphQL::Dataloader::ActiveRecordSource` (by primary key or `find_by:`, supports composite keys) and `GraphQL::Dataloader::ActiveRecordAssociationSource` (belongs_to and has_many, with scopes).
- Shortcuts on objects, resolvers and `context` (`Schema::Member::HasDataloader`): `dataload(Source, *args, key)`, `dataload_all`, `dataload_record(Model, id, find_by:)`, `dataload_all_records`, `dataload_association(:name, scope:)`, `dataload_all_associations`.
- `GraphQL::Dataloader.with_dataloading { |dl| ... }` runs sources outside a query (used for tests).
- `GraphQL::Dataloader::NullDataloader` is used when Dataloader is not installed. Source only.
- `Schema.object_from_id` can use `ctx.dataloader`, so `loads:` and `node(id:)` get batched.
- GraphQL-Batch (Shopify, promise-based) is supported via `lazy_resolve`. Generator `graphql:loader` scaffolds GraphQL-Batch loaders.

## Lookahead

- `extras: [:lookahead]` injects `GraphQL::Execution::Lookahead`.
- `lookahead.selects?(:field, arguments: ...)`, `.selection(:field)` (chainable, returns a null lookahead when absent), `.selections`, `.selects_alias?("alias")`, `.alias_selection("alias")`, `.arguments`, `.name`, `.field`, `.owner_type`.
- Docs warn to check both `edges { node }` and `nodes` on connections.
- No automatic ORM query optimization (no select-related or prefetch planner). Lookahead plus Dataloader is the documented way.

## Pagination (connections)

- Relay connections built in: `Types::Post.connection_type`. Fields whose type name ends in `Connection` get `connection: true` automatically. Adds `first`, `last`, `after`, `before`.
- Connection wrappers: `GraphQL::Pagination::ArrayConnection`, `ActiveRecordRelationConnection`, `SequelDatasetConnection`, `MongoidRelationConnection`. All offset-based cursors.
- `Schema.connections.add(AppListClass, MyConnectionWrapper)` maps any list class to a custom wrapper. Or return `MyConnection.new(items, max_page_size:, default_page_size:)` from a resolver.
- Custom wrapper subclasses `GraphQL::Pagination::Connection` and implements `nodes`, `has_next_page`, `has_previous_page`, `cursor_for(item)`.
- `Schema.default_max_page_size`, `Schema.default_page_size`, field `max_page_size:` and `default_page_size:`. `nil` removes the limit. `default_page_size` is clamped to `max_page_size`.
- Connection types: `GraphQL::Types::Relay::BaseConnection`, `BaseEdge`, `PageInfo`, mixins `ConnectionBehaviors`, `EdgeBehaviors`, `PageInfoBehaviors`. Options `edges_nullable`, `edge_nullable`, `node_nullable`, `has_nodes_field` (adds `nodes` shortcut). Custom edge fields for relationship metadata.
- `Schema.cursor_encoder(obj)` with `.encode(str, nonce:)` and `.decode(str, nonce:)`. Default Base64.
- Connection field is implemented as a field extension (`GraphQL::Schema::Field::ConnectionExtension`).
- No `totalCount` by default. Docs show adding it in a custom connection.
- `GraphQL::Relay::RangeAdd` helper for Relay `RANGE_ADD` mutation payloads.
- **[Pro]** Stable (keyset, value-based) cursors for ActiveRecord: `GraphQL::Pro::PostgresStableRelationConnection`, `MySQLStableRelationConnection`, `SqliteStableRelationConnection`. Database-specific NULL ordering. Adds primary key to ordering. Supports grouped relations (must include a unique column), Arel `NullsFirst`/`NullsLast`, ordering by joined fields. Accepts old offset cursors and upgrades them. Raises `GraphQL::Pro::RelationConnection::InvalidRelationError` for unordered grouped relations.
- **[Pro]** Encrypted, versioned cursors and IDs: `GraphQL::Pro::Encoder` with `key(...)`, `tag(...)`, `encoder(...)` (byte-to-string layer). AES-128-GCM, authenticated, nonces for cursors. `GraphQL::Pro::Encoder.versioned(New, Old, Legacy)` decodes with any, encodes with the first. `decode_versioned` returns `[data, encoder]`.

## Object identification (Relay)

- `Schema.object_from_id(id, ctx)`, `Schema.id_from_object(obj, type, ctx)`, `Schema.resolve_type`.
- `implements GraphQL::Types::Relay::Node` adds global `id`.
- `include GraphQL::Types::Relay::HasNodeField` (`node(id:)`) and `HasNodesField` (`nodes(ids:)`).
- `GraphQL::Schema::UniqueWithinType.encode(type_name, id)` / `.decode` helper for Base64 global IDs. Source only.
- Used by `loads:`, `node`, and ObjectCache.

## Query analysis, limits and security

- Ahead-of-time analysis: subclass `GraphQL::Analysis::Analyzer`, implement `on_enter_*` / `on_leave_*` visitor hooks and `result`. Register with `Schema.query_analyzer` or `Schema.multiplex_analyzer`. `analyze?` for conditional analysis. Return `GraphQL::AnalysisError` to reject the query. `visitor.query.arguments_for(node, field_def)` gives coerced arguments. `visitor.skipping?`, `visitor.visiting_fragment_definition?`.
- Built-in analyzers: `GraphQL::Analysis::QueryDepth`, `QueryComplexity`, `MaxQueryDepth`, `MaxQueryComplexity`, `FieldUsage` (lists used fields, deprecated fields, deprecated arguments, deprecated enum values; source only).
- `Schema.max_depth(n, count_introspection_fields:)` and per-query `max_depth:`. Introspection counted by default.
- `Schema.max_complexity(n, count_introspection_fields:)` and per-query `max_complexity:`. Field `complexity:` as a number or `->(ctx, args, child_complexity) { ... }`. Field `#calculate_complexity(query:, nodes:, child_complexity:)` override. Default connection cost multiplies child cost by `first`/`last` or page size settings, adds 1 for `pageInfo` and `totalCount`.
- Complexity algorithm merges selections per possible type and takes the max across abstract type branches (documented in detail).
- `Schema.complexity_cost_calculation_mode(:legacy | :future | :compare)`, `complexity_cost_calculation_mode_for(multiplex_context)`, `legacy_complexity_cost_calculation_mismatch(...)` for migrating off older buggy complexity scoring (2.5.3). Not in the guides.
- `Schema.max_query_string_tokens(n)`: reject large query strings at the lexer. Comments count (2.6.1).
- `Schema.validate_timeout(seconds)` for validation and analysis. Default 3 seconds. `nil` turns off. Uses Ruby `Timeout`.
- `Schema.validate_max_errors(n)` stops validation after n errors.
- `use GraphQL::Schema::Timeout, max_seconds: 2` for execution. Stops resolving new fields after the limit and adds errors. Does not interrupt running fields. Subclass and override `max_seconds(query)` and `handle_timeout(error, query)`. Can be disabled during a query (2.5.8).
- `validate: false` per query skips static validation. `static_validator:` per query accepts a custom `GraphQL::StaticValidation::Validator.new(schema:, rules:)`, so custom validation rule sets are possible. Not in the guides.
- Legacy non-spec validation behaviors with migration hooks: `Schema.allow_legacy_invalid_return_type_conflicts`, `legacy_invalid_return_type_conflicts(...)`, `allow_legacy_invalid_empty_selections_on_union`, `legacy_invalid_empty_selections_on_union(_with_type)`.
- Subscriptions are validated to have a single root field (2.5.0).
- No built-in alias limit, directive count limit or field-duplication limit beyond depth, complexity and tokens.
- **[Enterprise]** Rate limiters, see below.

## Errors

- `raise GraphQL::ExecutionError.new(msg, extensions: {...})` adds a top-level error with `locations` and `path`. Subclass and override `#to_h` for custom JSON.
- `Schema.rescue_from(ErrorClass) { |err, obj, args, ctx, field| ... }` maps application exceptions. Handler can raise `ExecutionError`, re-raise, or return a replacement value. Also covers errors during batch loading.
- `Schema.type_error(err, ctx)` for `InvalidNullError` and `UnresolvedTypeError` (and scalar encoding errors).
- `Schema.parse_error(err, ctx)` and `Schema.query_stack_error(query, err)` hooks for bug trackers.
- `GraphQL::Backtrace`: `context[:backtrace] = true` or `use GraphQL::Backtrace` wraps unhandled errors in `GraphQL::Backtrace::TracedError` with a GraphQL-level backtrace table (location, field, object, arguments, partial result). `context.backtrace` prints it during execution.
- `GraphQL::CoercionError` for scalar input errors.
- Unhandled exceptions crash the query and propagate to the caller (controller).
- Error classes include `ParseError`, `AnalysisError`, `UnauthorizedError`, `UnauthorizedFieldError`, `UnauthorizedEnumValueError`, `LoadApplicationObjectFailedError`, `InvalidNullError`, `UnresolvedTypeError`, `IntegerEncodingError`, `FloatEncodingError`, `StringEncodingError`, `DateEncodingError`, `DurationEncodingError`, `IntegerDecodingError`, `FloatDecodingError`.

## Directives

- Built-in: `@skip`, `@include`, `@deprecated`, `@oneOf`, `@specifiedBy`.
- Custom directives subclass `GraphQL::Schema::Directive` with `locations(...)`, `argument(...)`, `graphql_name`, `repeatable`. Register with `Schema.directive(...)`.
- Runtime hooks: `self.include?(obj, args, ctx)` (skip nodes) and `self.resolve(obj, args, ctx) { yield }` (wrap resolution). Also `resolve_each` for list items (source).
- Schema directives: `directive Directives::X, arg: ...` on types, `directives: { X => {...} }` on fields and arguments. `.directives` returns instances. Printed by `to_definition`. Parsed by `from_definition`.
- Example directives shipped: `GraphQL::Schema::Directive::Feature` (client-side feature flag, `.enabled?`), `Transform` (`@transform(by: "upcase")`), `Flagged` (server-side visibility flags).
- `@defer` and `@stream` are not in the free gem. See Pro.

## Field extensions

- `GraphQL::Schema::FieldExtension` with `apply` (modify field config at definition time), `after_define`, `resolve(object:, arguments:, context:) { yield(object, arguments, memo) }`, `after_resolve(value:, memo:, ...)`. Extensions are frozen. `default_argument(...)` adds an argument unless the field defines it. `extras [...]` per extension. Options via `extension(Klass, opt: 1)` or `extensions: [Klass => {...}]`.
- Resolvers can declare `extension Klass, **opts`.
- Connections and subscriptions are implemented as built-in field extensions.

## Introspection

- Custom introspection system: `Schema.introspection(MyModule)` where the module defines `SchemaType`, `TypeType`, `FieldType`, `DirectiveType`, `EnumValueType`, `InputValueType`, `TypeKindType`, `DirectiveLocationType`, `EntryPoints` (add root introspection fields), `DynamicFields` (fields available on every type, like `__typename`).
- `GraphQL::Introspection::INTROSPECTION_QUERY`. `GraphQL::Introspection.query(include_is_one_of:, include_deprecated_args:, ...)` options.

## Subscriptions

- `GraphQL::Schema::Subscription` (a Resolver subclass). Generated payload type from `field`s, or `payload_type Type`.
- Lifecycle: `#authorized?(**args)` (before subscribe and before each update, unsubscribes on failure), `#subscribe(**args)` (return initial value or `:no_response`, the default), `#update(**args)` (return value, `super`, or `NO_UPDATE` to skip this subscriber), `unsubscribe(final_value)`.
- `loads:` on subscription arguments. Missing object auto-unsubscribes.
- `subscription_scope :context_key`: implicit routing key. `trigger(..., scope: value)` must match.
- `MySchema.subscriptions.trigger(:field, args, object, scope:)`.
- `extras [:lookahead, :ast_node]` on subscription classes.
- `use ..., validate_update: false` skips re-validation on each update.
- Broadcasts: `use ..., broadcast: true, default_broadcastable: true|false` plus field `broadcastable: true|false`. A subscription whose fields are all broadcastable runs once and is delivered to all matching subscribers (same query string, variables, args, scope). `Subscriptions#broadcastable?(query_string)` for tests. `default_broadcastable(true)` on connection and edge types.
- `GraphQL::Subscriptions` base class to implement a custom backend: `execute_all`, `deliver`, `write_subscription`, `read_subscription`, `delete_subscription`, `build_id`, `execute_update`, `normalize_name`.
- `GraphQL::Subscriptions::ActionCableSubscriptions` (free): Rails ActionCable transport. Options `serializer:` (`.dump`/`.load(string, context)`), `namespace:`, `action_cable:`, `action_cable_coder:`.
- `GraphQL::Subscriptions::Serialize` dumps and loads context and objects (GlobalID-aware).
- `GraphQL::Testing::MockActionCable` for tests (2.5.15).
- Multi-tenant guide: tenant-based `subscription_scope`, a trace module around `execute_multiplex` to select the tenant, a tenant-aware `serializer:`.
- No built-in `graphql-ws` / `graphql-transport-ws` protocol, no SSE, no generic WebSocket server. Transport is ActionCable (free) or Pusher/Ably (Pro).
- **[Pro]** `GraphQL::Pro::PusherSubscriptions`: Redis state plus Pusher delivery. Subscription is created over HTTP POST. Response header `X-Subscription-ID` is the channel. Pusher webhook (`MySchema.pusher_webhooks_client` Rack app) removes closed subscriptions. Options `redis:` or `connection_pool:`, `stale_ttl_s:`, `cleanup_delay_s:`, `batch_size:` (batched Pusher triggers), `extra_webhook_tokens:` (key rotation). `context[:channel_prefix]` for private channels. `context[:compress_pusher_payload]` gzips payloads (`compressed_result`). Broadcasts over one channel. `broadcast_subscription_id?` for auth endpoints. `dump_context` / `load_context` overrides. `MySchema.subscriptions.clear`. `read_subscription_failed_error` hook.
- **[Pro]** `GraphQL::Pro::AblySubscriptions`: same model with Ably. Ably presence webhooks (`MySchema.ably_webhooks_client`). Token auth. End-to-end encryption with `cipher_base:` (per-subscription key returned in `X-Subscription-Key`). Broadcast namespace `gqlbdcst:`.
- **[Pro]** Subscriptions dashboard: topics, subscribers, `last_triggered_at`, broadcast subscriber counts, reset button.
- JS client (`graphql-ruby-client`, free, npm): `ActionCableLink`, `PusherLink`, `AblyLink` (Apollo Link 2/3), `addGraphQLSubscriptions` (Apollo 1), `createRelaySubscriptionHandler` (Relay Modern, plus `createLegacyRelaySubscriptionHandler` for Relay < 11), `SubscriptionExchange` (urql), `createActionCableFetcher`, `createPusherFetcher`, `createAblyFetcher` (GraphiQL). `decompress:` option for compressed Pusher payloads.

## Incremental delivery (@defer, @stream)

- **[Pro]** `use GraphQL::Pro::Defer` adds `@defer(if:, label:)`. `context[:defer]` enumerates deferrals (the initial result is the first one). Deferral `.to_h`, `.path`, `.data`, `.errors`, `.to_http_multipart(incremental: true)`. `deferred.stream_http_multipart(response, incremental: true)` for Rails `ActionController::Live`. Supports the proposed `incremental:` payload format and Apollo Client's format. Works with GraphQL-Batch via a custom subclass.
- **[Pro]** `use GraphQL::Pro::Stream` adds `@stream(if:, label:, initialCount:)`. Ignored on non-list fields. `GraphQL::Pro::FutureStream` (undocumented) streams lazy enumerators. With `Execution::Next`, `Stream` streams enumerators lazily.
- Defer is single-threaded: deferred fields run sequentially after the initial chunk.
- With `Execution::Next`, deferred branches run as new `GraphQL::Query::Partial` instances with a copied context.
- Docs include a GraphiQL fetcher example using `meros`.

## Persisted queries

- Free gem has no persisted query or APQ support. Third-party `graphql-ruby-persisted_queries` implements Apollo APQ.
- **[Pro]** `GraphQL::Pro::OperationStore`: server-side, normalized, deduplicated, immutable store of operations per client. Backends: ActiveRecord (generator `rails generate graphql:operation_store:create`, tables `graphql_clients`, `graphql_operations`, `graphql_client_operations`, `graphql_index_entries`, `graphql_index_references`), Redis (`redis:`), or `backend_class:`.
- **[Pro]** Clients send `operationId: "client-name/operation-alias"` (put it in `context[:operation_id]`). Supports Relay persisted output, Apollo Link `extensions.operationId`, Apollo persisted query manifests (`sha256Hash`), Apollo Android `OperationOutput.json`, Apollo codegen JSON.
- **[Pro]** Sync API Rack app `MySchema.operation_store_sync` (HMAC-SHA256 auth header `GraphQL::Pro #{client} #{hmac}`). `operation_store_sync(visibility_profile:)` binds synced operations to a visibility profile. `GraphQL::Pro::Routes::Lazy` for lazy route loading.
- **[Pro]** `last_used_at` tracking (`update_last_used_at_every:`, `default_touch_last_used_at:`, `context[:operation_store_touch_last_used_at]`), archive and unarchive, delete, usage index of types, fields and arguments across stored operations.
- **[Pro]** Rejecting arbitrary queries is done in the controller by passing `nil` as the query string.
- JS `graphql-ruby-client sync` CLI: `--url`, `--path`, `--relay-persisted-output`, `--apollo-codegen-json-output`, `--apollo-android-operation-output`, `--apollo-persisted-query-manifest`, `--client`, `--secret`, `--outfile`, `--outfile-type js|json`, `--header`, `--add-typename`, `--changeset-version`, `--dump-payload`, `--verbose`. Generates `OperationStoreClient` with `getOperationId`, `apolloMiddleware`, `apolloLink`.
- Deprecated older Pro feature `GraphQL::Pro::Repository` (static persisted queries).

## Caching

- Free gem has no response or field cache. Third-party `graphql-ruby-fragment_cache` and `graphql-cache`.
- `GraphQL::Language::Cache`: parser cache for parsed `.graphql` files (`config.graphql.parser_cache = true` in Rails). Signed entries with `secret:` (security fix 2.6.9).
- **[Enterprise]** `GraphQL::Enterprise::ObjectCache`: whole-response cache keyed by query fingerprint plus context fingerprint. Stores the IDs and fingerprints of every object visited. Serves a cached response only if all object fingerprints still match and objects pass `.authorized?` again.
- **[Enterprise]** Config: `ObjectIntegration` and `FieldIntegration`, `cacheable(true|false)`, `cacheable(public: true|false)`, `cacheable(ttl: seconds)`, field `cacheable: { ttl: 60 }`. Only queries are cached.
- **[Enterprise]** Hooks: `Schema.private_context_fingerprint_for(ctx)`, `Schema.object_fingerprint_for(obj)` (default `cache_key_with_version`, then `to_param`, `nil` = do not cache), `Schema.fingerprint` (bump to expire everything), `Type.cache_dependencies_for(obj, ctx)`, `Type.cacheable_object(obj, ctx)`.
- **[Enterprise]** `GraphQL::Enterprise::ObjectCache::CacheableRelation` for top-level relations without a parent object.
- **[Enterprise]** `cache_introspection: { public:, ttl: } | false`. `reauthorize_cached_objects: false` (global or per query). Context flags `skip_object_cache`, `refresh_object_cache`. Metrics in `context[:object_cache]` (`key`, `write`, `hit`, `ttl`, `public`, `messages`, `objects`, `uncacheable`).
- **[Enterprise]** Backends: Redis (`redis:`, `redis_cluster:`, `connection_pool:`), Memcached via Dalli (`dalli:`).
- No HTTP cache headers or `@cacheControl` directive.

## Rate limiting

- **[Enterprise]** `GraphQL::Enterprise::ActiveOperationLimiter`: limits concurrent operations per `context[:limiter_key]`. `limit:`, `stale_request_seconds:`.
- **[Enterprise]** `GraphQL::Enterprise::RuntimeLimiter`: token bucket on processing time per client. `limit_ms:`, `window_ms:` (default 60000). Stops resolving new fields when over limit. Checks only at query start and end.
- **[Enterprise]** `MutationLimiter` exists (changelog 1.1.12, dashboard code references `enterprise_mutation_limiter`). There is no guide page. I could not see its API.
- **[Enterprise]** Shared hooks: `limiter_key(query)`, `limit_for(key, query)`, `soft_limit?(key, query)`, `handle_redis_error(err)`. Soft mode (count but do not block) is the default and is toggled in the dashboard or with `set_soft_limit(false)`. Metrics in `context[:active_operation_limiter]` and `context[:runtime_limiter]`. Options `dashboard_charts:`, `assign_as:`, `context_key:`, `redis_cluster:`, `connection_pool:`.

## Schema versioning (Changesets)

- **[Enterprise]** `GraphQL::Enterprise::Changeset` subclasses with `release "2020-12-01"`. Members get `added_in: Changeset` and `removed_in: Changeset`. Works on fields, arguments, enum values, union `possible_types`, `implements`, and whole types (two types with the same `graphql_name`).
- **[Enterprise]** Integrations: `ArgumentIntegration`, `FieldIntegration`, `EnumValueIntegration`, `TypeMembershipIntegration`.
- **[Enterprise]** Client picks a version through `context[:changeset_version]` (for example from an `API-Version` header). `nil` means no changesets apply.
- **[Enterprise]** `use GraphQL::Enterprise::Changeset::Release, changesets_dir: "app/graphql/changesets"` or `changesets: [...]`. `Changeset.active?(context)` at runtime. `Schema.changesets`, `Changeset.changes` (`.member`, `.type` = `:addition`/`:removal`). `to_definition(context: { changeset_version: ... })` previews a version.
- Built on top of the free Visibility system.

## Tracing and observability

- `Schema.trace_with(Module, **options)`: trace modules override hook methods and call `super`. Hooks include `parse`, `lex`, `validate`, `analyze_query`, `analyze_multiplex`, `execute_multiplex`, `execute_query`, `execute_query_lazy`, `execute_field`, `execute_field_lazy`, `begin_execute_field`/`end_execute_field`, `authorized`, `begin_authorized`/`end_authorized`, `resolve_type`, `begin_resolve_type`/`end_resolve_type`, `dataloader_fiber_yield`/`resume`, `begin_dataloader_source`/`end_dataloader_source` (see `GraphQL::Tracing::Trace`).
- `context[:trace]` accepts a trace instance. `GraphQL.parse(..., trace:)`.
- Trace modes: `Schema.trace_mode(:name, TraceClass)`, `default_trace_mode`, `context[:trace_mode]`. Source only.
- Field `trace: true|false` toggles per-field tracing.
- Built-in platform traces: `ActiveSupportNotificationsTrace`, `AppsignalTrace`, `DataDogTrace`, `NewRelicTrace`, `PrometheusTrace`, `ScoutTrace`, `SentryTrace` (`data_collection` config, 2.6.11), `StatsdTrace`, `AppOpticsTrace`. Based on `GraphQL::Tracing::MonitorTrace` (options `set_transaction_name`, `trace_scalars`, `trace_authorized`, `trace_resolve_type`).
- `GraphQL::Tracing::PerfettoTrace`: Perfetto (ui.perfetto.dev) trace files with per-fiber spans and links between fields and Dataloader sources.
- `GraphQL::Tracing::DetailedTrace`: samples production queries via `Schema.detailed_trace?(query)`, stores Perfetto profiles in ActiveRecord (generator `rails generate graphql:detailed_trace`), Redis, or memory. `limit:`, `debug: false`, `context[:detailed_trace_debug]`, `inspect_object` override.
- `Schema.default_logger`, `context[:logger]`. Debug logs only.
- `Query#sanitized_query_string` via `GraphQL::Language::SanitizedPrinter`: prints the query with variables inlined and string values redacted. Source mostly.
- `Query#fingerprint` (`query_fingerprint`, `variables_fingerprint`): opaque, stable hashes for logging and caching.
- `ActiveRecord::QueryLogs` integration via `GraphQL::Current` (set up by the install generator).
- Legacy `instrument(...)` and `tracer(...)` APIs still exist with compat shims.
- Old Pro feature `GraphQL::Pro::Monitoring` is deprecated in favor of tracing.

## Dashboard

- `GraphQL::Dashboard` (free, in the main gem. I think it arrived in the 2.4.x series): Rails engine. `mount GraphQL::Dashboard, at: "graphql_dashboard", schema: "MySchema"` (or an array of schemas). Pages for detailed traces, OperationStore (Pro), subscriptions (Pro), limiters (Enterprise). Auth via `GraphQL::Dashboard.middleware.use(...)` or `ActiveSupport.on_load(:graphql_dashboard_application_controller)`. Not in the guides. Source only.
- **[Pro]** `MySchema.dashboard` Rack app (the older documented entry point), `GraphQL::Pro::Routes::Lazy`. Docs recommend Rails route constraints or `Rack::Auth::Basic`.

## Language tools

- `GraphQL.parse(string)`, `GraphQL.parse_file(path)`, `GraphQL.default_parser`. Immutable, persistent AST (`GraphQL::Language::Nodes::*`) with `.merge(attrs)` and `.add_{child}(attrs)`.
- `GraphQL::Language::Visitor` (modifying, `DELETE_NODE`) and `GraphQL::Language::StaticVisitor`.
- `GraphQL::Language::Printer` (subclass to customize). `node.to_query_string`.
- `GraphQL::Language::DefinitionSlice`: extracts one operation with the fragments it needs. Source only.
- `GraphQL::Language::DocumentFromSchemaDefinition`: schema to AST.
- `graphql-c_parser` gem: C extension parser, drop-in, installed as `GraphQL.default_parser` when required. `GraphQL.scan_with_c`, `GraphQL.parse_with_c`.

## Rails generators and tooling

- `rails g graphql:install` with `--directory`, `--schema`, `--skip-graphiql`, `--skip-mutation-root-type`, `--skip-query-logs`, `--relay`, `--batch`, `--playground`, `--api`. Adds controller, route, base classes, `graphiql-rails`, QueryLogs.
- Type generators: `graphql:object`, `graphql:input` (both read ActiveRecord columns and nullability), `graphql:interface`, `graphql:union`, `graphql:enum`, `graphql:scalar`, `graphql:relay`. `--namespaced-types`.
- Mutation generators: `graphql:mutation`, `graphql:mutation_create`, `graphql:mutation_update`, `graphql:mutation_delete` (Relay Classic, per model). Filtered parameters are skipped (2.6.5).
- `graphql:loader` (GraphQL-Batch loader), `graphql:detailed_trace`.
- `GraphQL::RakeTask.new(schema_name:, load_schema:, load_context:, directory:, idl_outfile:, json_outfile:, include_is_one_of:, ...)`: `rake graphql:schema:dump`, `graphql:schema:idl`, `graphql:schema:json`.
- `GraphQL::Railtie`: `config.graphql.parser_cache`, eager-load namespace.
- **[Pro]** `rake graphql:pro:validate[version]` checks the downloaded gem checksum against published checksums.

## Testing

- `include GraphQL::Testing::Helpers.for(MySchema)` gives `run_graphql_field("Type.field", object, arguments:, context:, visibility_profile:)`. Runs visibility, authorization, argument preparation, extensions and Dataloader for one field without a full query.
- `with_resolution_context(type:, object:, context:) { |rc| rc.run_graphql_field("title") }`.
- `GraphQL::Dataloader.with_dataloading` for source tests.
- `GraphQL::Testing::MockActionCable` for subscription tests.
- Guides recommend a checked-in `schema.graphql` dump, `GraphQL::SchemaComparator` (third party) for breaking change checks, and `schema.validate(query)` against a stored query list.
- Profiling guide: StackProf and MemoryProfiler.

## HTTP and transport

- No HTTP server, view or request parser in the gem. The user writes a controller (the install generator creates `GraphqlController#execute`).
- GraphiQL comes from the separate `graphiql-rails` gem. `graphql_playground-rails` is an install option.
- Apollo-style batching is documented as `params[:_json]` mapped to `Schema.multiplex`.
- No file upload support. Third-party `apollo_upload_server-ruby` is listed.
- No CSRF handling in the gem. Rails handles it.

## Documented FAQ items

- Route URL helpers in types via `context[:request]`.
- ActiveStorage blob URLs via `ActiveStorage::SetCurrent`.

## Not supported or not in scope

- Federation: no built-in support. Third-party `apollo-federation-ruby` (Gusto). Schema stitching via third-party `graphql-stitching-ruby`.
- No model-driven type generation at runtime (only Rails generators that write code). No automatic filtering or ordering arguments from models. Third-party `graphql-filters`, `search_object_graphql`, `graphql-groups`.
- No automatic query optimizer or N+1 planner. Users combine Lookahead and Dataloader.
- No persisted queries, APQ, response cache, `@defer` or `@stream` in the free gem (Pro or Enterprise only, or third party).
- No `graphql-ws`, `graphql-transport-ws` or SSE subscriptions. No GraphQL over HTTP spec server.
- No file uploads.
- No codegen for clients in the gem (only the JS sync tool for persisted queries).
- No built-in authentication. JWT and Devise integrations are third party (`graphql-devise`).
- No HTTP caching (`@cacheControl`, ETag).
- No schema diffing in the gem (third-party `graphql-schema_comparator`).
- No alias count or directive count limits.

## Upcoming and unreleased work

- `Execution::Next` is in "heavy development". Open gaps: query-level directives, stable custom runtime directives, `current_path`, scoped context, `fallback_value:`, several `GraphQL::Current` values. Changelog shows steady compatibility fixes in every 2.6.x release.
- `Schema::Visibility` is planned to replace `Warden` as the default.
- `error_bubbling` and legacy complexity mode are scheduled for removal in 3.0. A `3.0-dev` branch exists but is stale (last commit 2024-11-18).
- Unreleased on `master` after 2.6.11: argument and field-name preloading for Visibility profiles, defaults for omitted non-null variables, list error propagation through non-null items, invalid RelationConnection cursor rejection, per-fiber runtime state for nested Dataloader fibers, `current_field` for list-item Dataloader fibers.
- Open PRs: Sorbet type signatures (#5746), migrate docs to rdoc (#5689), single-pass input coercion (#5730), complexity caching PoC (#5638), spec-compliant scalar result coercion (#5306), subscription initial response `nil` (#5489), free `hasNextPage` query in relation pagination (#4908), paginate duplicate connection items by position (#5755).
- Branches of note: `spec-compliant-data-response`, `spec-compliant-scalar-coercion`, `single-pass-input-values`, `stream-lazy-enumerator`, `add-sorbet`, `exec-next-subscriptions`.

## Docs and code disagree

- `dataloader/adopting.md` says Dataloader cannot be used outside GraphQL. `dataloader/testing.md` and the code have `GraphQL::Dataloader.with_dataloading`, which runs sources outside a query.
- `errors/overview.md` says the validation rules cannot be customized except with `validate: false`. The code accepts `static_validator:` on queries and `GraphQL::StaticValidation::Validator.new(schema:, rules:)`, so a custom rule list is possible.
- `errors/type_errors.md` lists two type errors handled by `Schema.type_error`. The code also routes `StringEncodingError`, `FloatEncodingError`, `IntegerEncodingError` (raised) and `FloatDecodingError`, `IntegerDecodingError` (return `nil`) through it.
- `authorization/visibility.md` says profiles preload when `Rails.env.production?`. The code also preloads in `Rails.env.staging?`.
- `queries/ast_analysis.md` mentions `AST::MaxQueryDepth`. The class in code is `GraphQL::Analysis::MaxQueryDepth`.
- The free `GraphQL::Dashboard` Rails engine (with detailed traces) is not described anywhere in the guides. Only the Pro `MySchema.dashboard` is.
- `GraphQL::Analysis::FieldUsage`, `Query#run_partials`, `Schema.from_introspection`, `Schema.complexity_cost_calculation_mode`, `Schema.trace_mode`, `Schema.freeze_schema` and the RuboCop cops `DefaultNullTrue`/`DefaultRequiredTrue` exist in code but have no guide.
- The Enterprise limiter class name is written both `ActiveOperationLimiter` and `ActiveOperationsLimiter` in the guides. I could not check which one the closed-source gem uses.
- `object_cache/memcached.md` shows `use GraphQL::Enterprise::OperationStore, dalli: ...`. I think it should be `ObjectCache` (OperationStore is a Pro class with no `dalli:` option in its docs).
- The Dashboard limiter page links to `http://graphql-ruby.org/limiters/mutations`, which returns 404. `MutationLimiter` has no guide.
- `fields/validation.md` example `validates :title, String, validates: {...}` is a typo for `argument :title, ...`.
- `fields/arguments.md` marks argument deprecation as "Experimental". It is part of the current GraphQL spec and printed in SDL.

## Sources

Repo (shallow clone in `/tmp/graphql-ruby/`):
- https://github.com/rmosolgo/graphql-ruby (`master` at `6484df1`, 2026-10-01)

Docs read (repo source of https://graphql-ruby.org/, all 124 guide files under `guides/` read):
- `authorization/*` (overview, visibility, authorization, scoping, pundit_integration, can_can_integration), `changesets/*`, `dataloader/*`, `defer/*`, `errors/*`, `execution/next.md`, `execution/migration.md`, `fields/*`, `javascript_client/*`, `language_tools/*`, `limiters/*`, `mutations/*`, `object_cache/*`, `operation_store/*`, `pagination/*`, `pro/*`, `queries/*`, `relay/range_add.md`, `schema/*`, `subscriptions/*`, `testing/*`, `type_definitions/*`, `getting_started.md`, `faq.md`, `development.md`, `related_projects.md`.
- https://graphql.pro and https://graphql.pro/enterprise (feature and price pages).
- https://graphql-ruby.org/llms.txt returns 404.

Changelogs:
- `CHANGELOG.md` (2.4.16 to 2.6.11 read in full, older skimmed), `CHANGELOG-pro.md`, `CHANGELOG-enterprise.md`.
- GitHub compare API `v2.6.11...master` for unreleased commits. `gh pr list` for open PRs. `git ls-remote` for branches. GitHub repo API for stars and activity.
- RubyGems API for `graphql` and `graphql-c_parser` versions. npm registry for `graphql-ruby-client`.

Source files checked:
- `lib/graphql.rb`, `lib/graphql/schema.rb` (class method list, `type_error`, `validate_timeout`, `error_bubbling`, `complexity_cost_calculation_mode`, trace modes), `lib/graphql/schema/field.rb` and `argument.rb` and `enum_value.rb` (option lists), `lib/graphql/schema/visibility.rb`, `lib/graphql/schema/directive/*`, `lib/graphql/schema/ractor_shareable.rb`, `lib/graphql/schema/unique_within_type.rb`, `lib/graphql/query.rb`, `lib/graphql/query/partial.rb`, `lib/graphql/query/context.rb`, `lib/graphql/query/fingerprint.rb`, `lib/graphql/analysis/field_usage.rb`, `lib/graphql/dataloader.rb`, `lib/graphql/schema/member/has_dataloader.rb`, `lib/graphql/current.rb`, `lib/graphql/subscriptions.rb`, `lib/graphql/subscriptions/action_cable_subscriptions.rb`, `lib/graphql/testing/mock_action_cable.rb`, `lib/graphql/dashboard.rb`, `lib/graphql/dashboard/limiters.rb`, `lib/graphql/tracing/detailed_trace.rb`, `lib/graphql/tracing/monitor_trace.rb`, `lib/graphql/language/cache.rb`, `lib/graphql/language/sanitized_printer.rb`, `lib/graphql/rake_task.rb`, `lib/graphql/static_validation/validator.rb`, `lib/generators/graphql/*` (file list), `javascript_client/src/*` (file list), `graphql.gemspec`.
