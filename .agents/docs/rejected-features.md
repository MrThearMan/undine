# Rejected features

Features that were considered for Undine and rejected, with the reason and what covers the need instead.
The list comes from a comparison of 47 GraphQL frameworks (November 2026).
Accepted features are GitHub issues. `just issues-ready` lists the issues that can be worked on.

Check this list before you propose a feature.
A rejected feature comes back only with a new reason, for example a new use case or a finished spec.
When a feature is rejected, add it here under its area, in the same format.

Format: **Feature** (where it was seen): reason. What covers the need, if anything.

## Schema and types

- **Multiple schemas in one project** (hot-chocolate): visibility hooks, or two services with different `SCHEMA` settings. FAQ entry exists.
- **Static schema variants** (pothos sub-graphs, strawberry `get_fields`): a build-time filter over every element is large, and visibility covers the common case.
- **Extend a type from other apps** (nexus `extendType`, wpgraphql): rare in Django projects. Subclassing covers own apps, #189 merges root types.
- **Create types at runtime** (strawberry `create_type`): Python `type()` already does it.
- **Replace default attribute resolver** (strawberry, graphene): fields are model based. `@<field>.resolve` covers single fields.
- **Custom naming rules** (strawberry `NameConverter`, PostGraphile inflection): `CAMEL_CASE_SCHEMA_FIELDS` and `schema_name` cover the common needs.
- **Namespaced root fields** (`mutation { blog { createPost } }`): nested mutation fields do not run in order. Known anti-pattern.
- **Generic object types** (`Page[T]`): Undine builds its own wrappers (`Connection`, `OffsetPagination`).
- **Dynamic field** (graphene `Dynamic`): a class body can use `if apps.is_installed(...)`.
- **Default nullability setting** (pothos): nullability comes from the model, and `nullable=` covers single fields. A global switch makes schemas hard to read.
- **Rich schema build errors** (strawberry code frames): `UndineErrorGroup` lists all build errors.
- **Plugin modules that add schema parts** (tartiflette): Django apps are the module system.
- **SDL-first schema definition** (ariadne, gqlgen): against Undine's code-first, model-centric design.
- **Import external GraphQL types** (pothos): `Field(<graphql-core type>)` accepts a raw type.
- **Schema hot swap at runtime** (mercurius, hot-chocolate): Django processes restart on deploy.
- **Remove or report unreachable types** (hot-chocolate): types are built from references, so unreachable types are rare.
- **Extra types not reachable from roots** (saleor `types=`): no Undine case needs it. Federation entities and interface implementers come through references.
- **Warm up at startup** (hot-chocolate): the caches are in-process LRUs, so only the first requests gain.
- **Schema export for older tools** (`--spec-version`): niche.
- **Semantic non-null schema variant** (hot-chocolate): depends on client adoption. `@semanticNonNull` exists.
- **Schema transformation hooks** (graphql-java `SchemaTransformer`, pothos): `Directive.__connected__` (#237) covers changes for each element.
- **SDL printer options** (graphql-java): the `SDL_PRINTER` setting allows a custom printer.
- **Per-operation root value and context** (graphql-php): the context is the request, and lifecycle hooks can add to it.
- **Argument mapper** (graphql-php): `TypedDict` arguments, and dataclass inputs in #241.
- **Lazy type loading** (graphql-php): the schema is built once for each process.
- **Resolve object by URL** (wpgraphql `nodeByUri`): a function entrypoint with Django's `resolve()`.
- **Typed raw SQL entrypoint** (Hasura native queries): a function entrypoint can call `raw()` and return a `TypedDict`.
- **Version notes in descriptions** (saleor): docstrings cover it.
- **Graph usable without GraphQL** (graphlayer): out of scope. #188 runs operations in process.
- **Resolver dependency injection** (graphlayer, typegraphql): Django code uses `info.context` and imports.
- **Model property field** (strawberry-django `model_property`): properties cause hidden N+1 queries. FAQ entry exists. The django-lookup-property integration is #193.
- **Abstract base type** (graphene-sqlalchemy): a plain mixin with hooks already works. No docs note wanted.
- **Scoped context for child fields** (graphql-java `localContext`): resolvers can attach data to the returned object.
- **Non-ORM data providers and cross-source relations** (graphweaver): Undine is Django-first.
- **Relations without foreign keys** (PostGraphile `@ref`): `Field(Subquery(...))` and function fields.
- **Auto-map reachable related models** (strawberry-sqlalchemy): explicit `QueryType`s are clearer.
- **Type description from model docstring** (strawberry-django): model docstrings are rarely written for API users.
- **First-or-default list field** (hot-chocolate): a custom resolver covers it.
- **Distinct on** (Hasura `distinct_on`): PostgreSQL only, interacts with ordering. `Filter(distinct=True)` covers the server side.
- **Global feature toggles** (PostGraphile behaviors): Undine is explicit for each class.
- **Nullability guard** (nexus): hides bugs. `@semanticNonNull` is the modern approach.
- **Runtime non-null per request** (gqlgen): niche.
- **Return pre-built JSON** (graphql-ruby `raw_value`): niche.
- **Vector similarity queries** (dgraph): pgvector expressions already work in `Field` and `Order`.
- **Write-only password field** (dgraph `@secret`): Django auth handles passwords. `Input(input_only=True)` with `@<input>.convert`.
- **JSON path argument on JSON fields**: hard to validate and can expose unplanned keys. #199 covers JSON with a known shape.
- **Required but nullable input**: GraphQL cannot express it. With `UNSET` (#213), a function can enforce it.
- **Pydantic models as types**: a second validation system. It can live outside Undine. Revisit on demand. Dataclasses are #241.
- **File output object** (size, dimensions): reads the storage backend for each row. Docs recipe "Reading file data" in `docs/file-upload.md`.
- **Pluggable global ID format** (graphene, pothos): clients store global IDs long-term, and they must be deterministic, so a codec change or key rotation breaks them. Add a `GLOBAL_ID_CODEC` setting only on request.
- **Auto ID as global ID** (strawberry-django): `Node` on a `QueryType` gives `id: ID!`.
- **Type-restricted node field** (graphene): `GlobalID[TaskType]` arguments (#220).
- **Check all nodes are resolvable** (hot-chocolate): every `QueryType` with `Node` can be refetched.
- **Filter interface results by concrete type** (neo4j-graphql): each implementation has its own filter arguments.
- **Custom selection directives** (tartiflette `on_field_collection`): responses would depend on hidden rules. Visibility hides fields.
- **Directive on output coercion** (tartiflette): resolver wrappers (#237).
- **Internal directives** (hot-chocolate): #249 makes the SDL printer follow visibility.
- **Opt-in features, deprecated object types, directive introspection** (hot-chocolate): proposal or RFC stage. Revisit when they are in the spec.
- **Flatten input object argument** (gqlgen `@inlineArguments`): `TypedDict` arguments.
- **Cascade directive** (dgraph `@cascade`): drops nodes after fetching, which breaks prefetches and pagination counts.
- **More built-in scalars** (graphql-java extended scalars): 19 scalars exist. `ScalarType` covers the rest. Add more on request.
- **Range and regex scalar helpers** (hot-chocolate): `ScalarType`.
- **Choice enum naming and sharing** (graphene-django): #238, #239, #240 and `TextChoicesField`.
- **Rows of a table as an enum** (Hasura `is_enum`): rows change at runtime, so the schema would change.
- **ISO 8601 duration** (gqlgen): `Duration` uses seconds, and a format change is breaking.
- **DateTime precision options** (hot-chocolate): no need found.
- **Dictionary as key-value list** (hot-chocolate): the `JSON` scalar.
- **Scalar overrides** (strawberry `scalar_map`): converters and `parse`/`serialize` can be re-registered.
- **Image thumbnail field** (saleor): app-specific.

## Mutations

- **Django Form mutations** (graphene-django): duplicates `MutationType` with fewer features (no nesting, no bulk) and a different save path (`Model.save()`). No docs recipe.
- **DRF serializer mutations** (graphene-django): same reasons. The output would skip the `QueryType`, or the serializer would only validate, which `__validate__` does.
- **Through model data for many-to-many**: a related `MutationType` on the through model works. Docs section "Many-to-many through models".
- **Atomic number and JSON update operators** (Hasura `_inc`): a custom mutation with `QuerySet.update(F(...))`.
- **Soft delete** (lighthouse): `__mutate__` and `__filter_queryset__`.
- **Affected row counts** (Hasura `affected_rows`): #200 and #215 return the objects, so the client can count.
- **Many different updates in one call** (Hasura `update_many`): bulk update with a list, and aliases.
- **full_clean options** (strawberry-django): `MUTATION_FULL_CLEAN` and `__validate__`.
- **Full replace update** (graphene-django-cud): `Input(required=True)`.
- **ID suffix input names** (`ownerId`): `Input(schema_name=...)`.
- **Input type override per field** (graphene-django-cud): an explicit `Input(<type>)`.
- **Relay clientMutationId**: old convention. Modern Relay does not need it.
- **Mutation payload convention** (hot-chocolate): style choice.
- **Input object from resolver arguments** (strawberry): `TypedDict` arguments.
- **Queued background mutation** (lighthouse `@async`): a function entrypoint can start a Django or Celery task.
- **Input and output DTOs** (api-platform): the `custom` kind, function entrypoints and #241.
- **Built-in input sanitizers** (lighthouse `@trim`): `@<input>.convert`.
- **Replace explicit null with default** (graphql-ruby): `@<input>.convert`.
- **Changed-field tracking** (saleor): django-dirtyfields, and `__before__` (#210) sees the input data.
- **Audit trail** (graphweaver): django-simple-history and django-auditlog. #211 adds mutation signals.
- **Client-generated primary keys** (graphweaver): an explicit `Input("pk")` on a create mutation.
- **Reusable argument maps** (pothos): Python covers it.
- **Bulk size limit per mutation** (saleor): `MUTATION_INSTANCE_LIMIT`.
- **Reorder helper, translate mutations** (saleor): app-specific. The modeltranslation integration covers translated fields.
- **Input validation webhook** (Hasura): Python validation hooks.
- **Post-mutation row check** (Hasura `check`): `__validate__` before the save, and `@atomic` rolls back on an error in `__after__`. Documented in the `__after__` section.

## Filtering and ordering

- **Limit filter operations per request**: exists as `MAX_FILTERS_PER_TYPE`, which counts inside `NOT`, `AND`, `OR` and `XOR`.
- **Disable logical operators** (hot-chocolate): small gain. `MAX_FILTERS_PER_TYPE` limits use.
- **Custom function ordering**: no function interface on purpose. The optimizer must add ordering at the right point, so the queryset is not exposed. `@<order>.aliases` gets `info`.
- **Autogenerate orders only for indexed columns**: replaced by the index system check (#225).
- **Filter field that is not applied** (strawberry-django `skip_queryset_filter`): a function `Filter` decides the `Q` itself.
- **Client DISTINCT flag**: `Filter(distinct=True)` on the server is safer, because the server knows which joins duplicate rows.
- **django-filter integration** (graphene-django): only helps migration. `FilterSet` covers the same features.
- **Explicit null filter semantics** (saleor): the `isnull` lookup.
- **JSON key filtering** (saleor metadata): a path filter like `Filter("extra_data__color")` covers known keys. Free-form keys are app-specific.
- **Filter conventions** (hot-chocolate): converters cover renaming and type binding.
- **Column to column comparison** (Hasura `_ceq`): a function filter returning `Q(a=F("b"))`.
- **ltree operators** (Hasura): needs a third-party Django field.
- **Client-chosen null placement** (strawberry-django, Hasura): doubles the enum values. `Order(null_placement=...)`.
- **Nested relation ordering input** (strawberry-django): `Order("color__name")`.
- **Order by aggregate of related rows** (Hasura): `Order(Count(...))`.
- **Input object ordering shape** (Hasura, Prisma `orderBy: [{ name: asc }]`): the enum list keeps key order and supports deprecation for each `Order`. An `Order` has only two directions, so nothing needs grouping like #306 does for filters.

## Pagination

- **`nodes` shortcut on connections**: small gain over `edges { node }`.
- **Custom connection and edge fields**: edge data muddies model access. Use a `QueryType` for the through model. Revisit with another use case.
- **Strict (non-null) connection types**: the Relay spec allows both. Connections use the common nullable style, plain lists stay strict. Changing either breaks clients.
- **Page-number pagination**: with #184, pages are client math (`offset = (page - 1) * limit`).
- **Default list arguments per type**: filters and ordering are already per type. A pagination default makes field types implicit. `LIST_ENTRYPOINT_LIMIT` covers unbounded lists.
- **Require first or last** (graphene-django): the default page size limits every query.
- **Offset argument on cursor connections**: `OffsetPagination` exists, and keyset cursors are better.
- **Custom connection type names** (nexus), **shared connection interfaces** (wpgraphql), **relative cursors for page bars** (hot-chocolate): no need found.
- **Simple limit on nested lists** (saleor): `OffsetPagination` on a `Field`.

## Performance

- **Static N+1 system check**: too difficult, and a simpler version would mislead. The runtime detector is #231.
- **Operation plan cache**: most of the plan depends on the request (arguments, `optimize` hooks, visibility), and the gain is not measured. Revisit if a profile shows the optimizer is a real cost.
- **Optimizer skips deferred fragments**: the incremental delivery spec is not finished. Notes are on #46.
- **Field-level optimizer hints as arguments** (strawberry-django): `@<field>.optimize` and `__optimize__`.
- **Disable optimizer per field** (strawberry-django): a custom resolver skips the optimizer.
- **Batched fallback load** (pothos): fix misses with `@<field>.optimize`. #231 finds them.
- **Subquery-based child loading** (graphjoiner): small gain over `prefetch_related`.
- **Plan-based execution** (Grafast): an execution engine rewrite.
- **Resolver concurrency control** (tartiflette, gqlgen): `sync_to_async` already runs ORM calls one after another.

## DataLoaders

- **Batch field resolver**: a sync DataLoader (#233) does everything a batch resolver does. `resolve_batch` sugar may come later.
- **graphql-sync-dataloaders as a dependency**: last release September 2022, before graphql-core 3.3. Used as a reference only for #233.
- **Cross-request DataLoader cache** (strawberry): `load_fn` can use the Django cache. Documented.
- **Built-in model loaders** (graphql-ruby): the optimizer covers model data.
- **Field-bound loaders** (pothos): a function field calls the loader in one line.
- **Parameterized loader instances** (graphql-ruby): separate `DataLoader`s or tuple keys.
- **Lookups for extra cache keys** (hot-chocolate): `prime` and `prime_many`.
- **Batched pagination in loaders** (hot-chocolate): the optimizer paginates nested model lists.
- **Per-key load context** (java-dataloader): `info` in `load` (#181) and tuple keys.
- **Streaming batch results, max concurrent batches** (java-dataloader, sangria): niche.
- **DataLoader spans** (saleor): #259 adds a batch size metric.
- **Toggle exception caching** (java-dataloader): after #181, cached failures live for one operation.
- **Batch delay** (async-graphql): batching for each event loop tick collects one execution level.

## Permissions and visibility

- **Enforced federation auth directives**: they stay metadata, enforced by the router. An enforcing directive is a wrapper. Example in #237.
- **Object permission library integration** (django-guardian, django-rules): they plug into `has_perm`, so `HasObjectPerm` (#185) works. A guardian list filter is a small subclass with `object_permission_filter` (#246).
- **Session auth mutations**: Django `authenticate()`, `login()` and `logout()` work in function entrypoints. Docs page `docs/authentication.md`.
- **JWT, refresh tokens, cookie tokens, auth signals** (django-graphql-jwt): auth packages set `request.user`. Undine ships no token handling.
- **Per-argument credentials** (`JWT_ALLOW_ARGUMENT`): one subtree as another user is hard to reason about.
- **Skip authentication for some root fields**: `AllowAny()` (#245).
- **Step-up multi-factor checks** (graphweaver): auth packages, and a permission class (#185) can check a session flag.
- **Permissions shown in the schema** (strawberry-django): `@requiresPermissions` (#247) is printed. Permission classes have no data to print.
- **Type-level permission before every field** (pothos): `QueryType.__permissions__` and #185.
- **Argument-level authorization** (graphql-ruby): `Input() < ...` (#185), and function bodies or `@<name>.permissions`.
- **Superuser bypass** (graphweaver): `user.has_perm` is `True` for active superusers.
- **Granted scopes along a path** (pothos): niche.
- **Disable auth in tests** (pothos): log in a user or mock the permission.
- **Per-role schema, backend-only mutations** (Hasura): visibility hooks, #185 and #249.
- **Named visibility profiles** (graphql-ruby): `VISIBILITY_CACHE_EXTRA_CONTEXT` caches by role.
- **Schema versioning by release date** (graphql-ruby): visibility hooks can read a version header.
- **Several definitions with one name** (graphql-ruby): one name for each type keeps the schema simple.
- **Run a request against a narrower SDL** (graphjoiner): visibility hooks.

## Security and limits

- **Query depth limit**: `MaxComplexityRule` counts every relation and `MaxListNestingDepthRule` limits to-many nesting. Parser recursion is #250.
- **Cost analysis with list multipliers**: a second cost system, and plain lists have no known size. Routers enforce `CostDirective` and `ListSizeDirective`.
- **Cost report in response**: complexity is fixed for each document, and the over-limit error shows the number.
- **Field count limit**: graphql-core deduplicates fragments and has a comparison budget. The exponential optimizer walk is #255.
- **Root field count limit**: root fields must be different entrypoints, and `MAX_ALLOWED_ALIASES` counts root aliases.
- **django-ratelimit as a dependency**: last release July 2023, sync only. #254 builds on the Django cache.
- **Separate cache for invalid documents** (mercurius): `ValidationCacheHook` stores only valid documents.
- **Skip or disable validation** (strawberry, apollo-server): unsafe. The validation cache gives the speed.
- **Remove spec validation rules** (gqlgen): spec rules always run.
- **Allowed operation types** (envelop): transport settings, or a short rule in `ADDITIONAL_VALIDATION_RULES`.
- **Execute-time validation rules** (envelop): custom rules read `self.context.request` and `self.context.variables` (#251, #252).
- **Field cycle depth** (hot-chocolate): complexity and list nesting rules.
- **Fragment visit and field merge limits** (hot-chocolate): graphql-core's budget and #255.
- **Introspection depth limit** (hot-chocolate): introspection is off by default, and #253 limits it to chosen users.
- **Parser limits** (hot-chocolate): `MAX_TOKENS` and #250.
- **Validation timeout** (graphql-ruby): token, depth and error limits bound the work.
- **Concurrency gate** (hot-chocolate): the ASGI or WSGI server.
- **Operation name length limit** (cosmo): #288 and #289 cut or hash client values.
- **Require variables instead of inline arguments** (cosmo): #289 removes literals before hashing.
- **Resolver count limit** (AppSync): complexity and page sizes.
- **Upload validation** (saleor): model field validators and Pillow. Content sniffing belongs to the project.

## Subscriptions

- **NATS and Kafka brokers**: PostgreSQL (#270) and Redis (#271) cover a setup without Channels.
- **Event-keeping broker for resumption** (Hot Chocolate `@eventCursor`): needs a broker that stores events. Left for later in #314.
- **Subscription lifecycle hooks** (mercurius): generator `finally`, and #273.
- **Overflow policy** (hot-chocolate): a full buffer ends the stream with `GraphQLSubscriptionBacklogFullError`. Silent drops would hide lost data.
- **Subscriptions from mutation results** (AppSync): signal subscriptions, #211 and #267.
- **Hosted push transports** (Pusher, Ably): proprietary. A custom broker can wrap one.
- **Per-event context** (gqlgen): #181 resets DataLoader state for each event.
- **Exclude the sender** (lighthouse): put a sender ID in the payload (#267) and skip it in the generator.
- **Skip empty results** (Hasura): a generator skips by not yielding. `SkipItem` in #244.
- **Previous state in update events** (neo4j-graphql): needs a `pre_save` query for every save.
- **Webhooks from subscription documents** (saleor): large and app-specific.
- **Webhooks as subscription events** (graphql-mesh): a Django view calls `publish` (#267).

## Caching

- **HTTP conditional requests**: Django's `ConditionalGetMiddleware` gives `ETag` and `304` for GET queries. Documented in `docs/caching.md`.
- **Cache debug metadata** (yoga, cosmo): the `Age` header exists.
- **Stale-while-revalidate on the server** (mercurius): complex. The CDN header is a comment on #276.
- **Concurrent request deduplication** (mercurius, apollo-router): async only, and it must respect per-user data.
- **Shared parse and validation cache** (strawberry-django): parsing costs less than a cache round trip.
- **Introspection result cache** (saleor): the visibility cache and #253.
- **Client-requested caching** (Hasura `@cached`), **client `Cache-Control` header** (cosmo): cache rules belong to the server. Any client could force full runs. `REQUEST_CACHE_READ_PREDICATE` exists.
- **Entity-level response cache, Cache-Control on entity responses** (apollo-router): gateway features.

## Persisted documents

- **Operation store per client with usage** (graphql-ruby Pro, cosmo): #288, #262 and #283 give the data.
- **Allow lists per role** (Hasura): #279 and `PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`.
- **Other document stores** (hot-chocolate Redis): the model is swappable (`UNDINE_PERSISTED_DOCUMENTS_MODEL`).
- **Document aliases and per-document settings** (wpgraphql): a swappable model can add fields.
- **Client sync tool with signed requests** (graphql-ruby): #280, and the permission callback can check a signature.

## Federation

- **Fetch reasons** (cosmo): cosmo-only directive.
- **Request signature check** (hive-gateway HMAC): network rules or Django middleware.
- **Forwarded JWT claims** (hive-gateway): Django authentication middleware.
- **Federation 1**: old. Routers support Federation 2.
- **Composite schemas spec** (hot-chocolate): still an RFC. Revisit when it is finished.

## Errors

- **Shared error types for errors as data**: every error type implements `FieldError { message }`, and the registry reuses one type for each exception class. `code` is not needed, because `__typename` identifies the error.
- **Per-item errors in lists**: a function list returning an exception item already gives `null` with an indexed error path. Bulk mutations are #216.
- **Add errors without failing the field**: graphql-core treats an error at a path as a nulled position. Use nullable fields, errors as data or a warnings field.
- **Client-chosen error mode** (`onError`): still a spec proposal. `@experimental_disableErrorPropagation` exists. Revisit when it is in the spec.
- **Error schema coordinate** (yoga): `path`, or the #301 formatter.
- **Standard error taxonomy** (netflix-dgs): `error_code` and `status_code`.
- **Separate loggers for handled and unhandled errors** (saleor): #302 and Django logging config.
- **Reusable named error union, several success types, direct result** (pothos): rare needs. `UnionType` and the `Value` wrapper cover them.

## HTTP and transports

- **SDL endpoint**: `print_schema` and introspection cover it. An endpoint needs its own access rules and visibility support.
- **Query batching**: a workaround for HTTP/1.1, with no gain on HTTP/2 or HTTP/3, and it needs extra limits. FAQ entry exists.
- **Incremental delivery over SSE, JSON Lines and WebSocket**: the spec is not finished. Notes are on #46.
- **Legacy incremental payload format** (graphql-js): two formats of a changing spec.
- **Defer limits** (lighthouse): `MAX_ALLOWED_DIRECTIVES` limits `@defer` and `@stream`.
- **HTTP status from execution errors** (yoga): the GraphQL over HTTP spec keeps 200. Request errors are #182.
- **Legacy subscriptions-transport-ws**: deprecated protocol.
- **Custom JSON serializer** (apollo-server): helps only very large responses. Add on request.
- **Response formatter hook** (tartiflette): lifecycle hooks, `request.response_headers` and #301.
- **Set response headers from resolvers** (AppSync): write `info.context.request.response_headers`.
- **Variable batching, `@export`, HTTP 294** (hot-chocolate, sangria, spring-graphql): draft or experimental specs.
- **Response deduplication** (graphene `deflate`): needs a client helper.
- **Health check endpoint, maintenance mode, OPTIONS handling**: Django projects and middleware (django-cors-headers).
- **Pretty JSON output** (graphene-django): browser tools and GraphiQL format JSON.
- **Pluggable subscription transport** (ariadne): WebSocket, SSE and multipart cover the specs.
- **Serverless handler** (ariadne-lambda): Mangum or apig-wsgi.
- **Custom request body parser, transport version selection, SSE minimum event interval**: no need found.
- **Cancel execution on client disconnect** (yoga): Django's ASGI handler cancels the view task. Not tested. MCP is #294.

## Observability and hooks

- **Response extensions from resolvers, debug messages in extensions** (gqlgen, wpgraphql): works with `info.context` and a hook. Niche, so no docs recipe.
- **Root field interceptor** (gqlgen): the `resolve` hook, and wrappers (#237).
- **Hook for invalid HTTP requests** (apollo-server): `graphql_errors_hook` and #301.
- **Server start and stop hooks** (apollo-server): `AppConfig.ready`.
- **Per-request hooks** (ariadne): a hook can check the request and do nothing.
- **Operation logging**: #284, or a small hook.
- **SQL and timing in extensions** (graphene-django), **profiler** (strawberry): Debug Toolbar, tracing and #290.
- **Apollo Tracing extension**: deprecated. OpenTelemetry covers it.
- **Diagnostic event listeners** (hot-chocolate): hooks and #259.
- **Skip middleware for simple fields, per-request tracing switch**: tracing skip predicates and sampling.
- **Context update between mutations** (sangria), **preload asset hints** (envelop): niche.
- **Compiled execution** (envelop): no Python equivalent.
- **Other APM traces** (New Relic, X-Ray), **sampled detailed traces**: OpenTelemetry and sampling.
- **Usage and schema reporting** (GraphOS, Hive): proprietary. Rover with `print_schema`, and #258 data.
- **Traffic-based breaking change check** (cosmo): needs stored #258 data, which belongs to the project.
- **Postgres row-level security bridge** (PostGraphile): a hook can `SET LOCAL`. Niche for Django.

## Tooling and integrations

- **Alternative GraphQL IDEs** (Apollo Sandbox, Altair): standalone apps.
- **GraphiQL plugins** (mercurius, cosmo): override the template.
- **GraphiQL schema hot reload** (PostGraphile): `runserver` restarts.
- **Remote schema stitching** (ariadne-graphql-proxy, Hasura): federation.
- **Webhook-backed fields, REST endpoints as GraphQL** (Hasura, caliban-tapir): function entrypoints.
- **JSON:API endpoint, shared REST resource** (Hasura DDN, api-platform): out of scope. REST from documents is #291.
- **Event and scheduled triggers** (Hasura): signals and task queues.
- **Schema lint rules, record and replay traffic** (cosmo, apollo-router): external tools and gateways.
- **Generated admin UI** (graphweaver): Django admin.
- **Test client login, unittest helpers, permission grants** (strawberry-django, graphene-django, saleor): the test clients subclass Django's clients, so `force_login` and `TestCase` work.
- **Introspection JSON export, typed client codegen, schema from introspection, SDL to code** (graphene-django, ariadne-codegen, strawberry): SDL-based tools.
- **Schema mocking** (apollo-server): clients mock.
- **Write SDL file automatically** (nexus): `print_schema --check` in CI.
- **Validate documents without executing** (juniper): graphql-eslint, graphql-inspector, and #280 `--check`.
- **Resolver mocking** (lighthouse): `unittest.mock`.
- **Path-based response assertions** (spring-graphql): the response helpers.
- **GraphQL-level backtrace** (graphql-ruby): `path` and `INCLUDE_ERROR_TRACEBACK`.
- **Document formatter** (absinthe): Prettier.
- **Project template, agent skills** (hot-chocolate): `example_project/` and `llms.txt`.
- **Markdown docs from schema** (netflix-dgs): SpectaQL and similar.
- **Upgrade codemods** (strawberry): migration notes.
- **Locate definition, run one field in tests, introspection test helpers, test documents from files, scaffolding, query anonymizer, query generator, schema name constants**: no need found.
