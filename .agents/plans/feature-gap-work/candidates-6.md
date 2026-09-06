# Candidates batch 6

Findings files: hasura, postgraphile-grafast, pg_graphql, dgraph, neo4j-graphql, apollo-router-federation, wundergraph-cosmo, graphql-mesh-hive-gateway, aws-appsync.

Many of these are databases, hosted services or gateways. For gateway features, Notes say "server" when one Django server could offer it itself, or "subgraph" when Undine would only need to support it as a subgraph.

## Progress

- [x] hasura
- [x] postgraphile-grafast
- [x] pg_graphql
- [x] dgraph
- [x] neo4j-graphql
- [x] apollo-router-federation
- [x] wundergraph-cosmo
- [x] graphql-mesh-hive-gateway
- [x] aws-appsync

## 1. Schema, root types and entrypoints

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Fetch by unique field or composite key | Single-object entrypoint takes one argument per key column, or any unique column. | hasura: `<table>_by_pk(<pk_col>:, ...)`, DDN `selectUniques[].uniqueIdentifier`. postgraphile: `userBy<Key>` per unique constraint (`rowByUnique` inflector). pg_graphql: `<type>ByPk(<pk columns>)` | partial: `Entrypoint(QueryType)` fetches by `pk` only | medium | I think Django 5.2 `CompositePrimaryKey` is not handled. No grep hits for it in undine/. |
| Root field namespace and type prefix | Puts all root fields of a source under one namespace field, or adds a prefix or suffix to type names. | hasura: source `customization.root_fields.namespace`, `type_names.prefix`/`suffix` | missing | low | Useful when many apps share one schema. `schema_name` covers single renames. |
| Rows of a table as an enum | A lookup table's rows become GraphQL enum values. | hasura: `is_enum: true` table | partial: `choices` and `TextChoices` become enums | low | Rows can change at runtime, so the schema would change. Weak fit. |
| Typed raw SQL entrypoint | Exposes a raw SQL query with parameters and a declared result shape as a root field. | hasura: `track_native_query`, `track_logical_model`, `track_function` | partial: function `Entrypoint` with a `TypedDict` return | low | Django users can call `raw()` in a function entrypoint. |
| Multiple schemas in one project | Serves different schemas at different endpoints (for example public and admin). | postgraphile: one `postgraphile()` instance per schema, `multiple-schemas.md`. dgraph: one schema per namespace (multi-tenancy) | missing | medium | Views read one `SCHEMA` setting. `graphql_view_sync(request)` takes no schema argument. I checked `undine/http/views.py`. |
| In-process execution API | Runs a GraphQL operation from Python code without an HTTP request. | hive-gateway: `runtime.sdkRequester`, `getExecutorForUnifiedGraph`. graphql-mesh: in-context SDK | partial: `execute_graphql_http_sync(params, request)` needs a request | low | Useful for tasks and tests. The test client covers tests. |

## 2. Query types and fields

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| JSON path argument on JSON fields | A JSON field takes a `path` argument and returns only that part. | hasura: JSON/JSONB column `path: String` argument | missing | medium | Could map to Django `KeyTextTransform` or `KT()`. No grep hits for json path in undine/. |
| Distinct on | Client picks columns for `DISTINCT ON`. | hasura: `distinct_on: [<table>_select_column!]` | partial: `Filter(distinct=True)` is server side, no column list | low | Postgres only. Interacts with ordering. |
| Big integer scalar | Returns 64-bit integers without overflow, often as strings. | hasura: `HASURA_GRAPHQL_STRINGIFY_NUMERIC_TYPES`. pg_graphql: `BigInt` (`int8`) and `BigFloat` (`numeric`) as JSON strings | missing | high | `BigIntegerField` subclasses `IntegerField` and maps to `GraphQLInt` (32-bit) in `undine/converters/impl/convert_to_graphql_type.py`. Large values fail to serialize. I checked the converter. |
| Single-table polymorphism | One table with a type column maps to an interface with several concrete types. | postgraphile: `@interface mode:single type:<col>` and `@type VALUE name:X` | missing | medium | Undine matches concrete types by exact model class. Django proxy models are the usual way. |
| Relations without foreign keys | Declares a relation between tables through any column route. | postgraphile: `@ref name to:Type via:(cols)->table(cols)`, `@refVia` | partial: `Field(Subquery(...))` and function fields | low | Django needs a relation field for joins. |
| Soft-delete hiding | Hides archived rows by default with an opt-in argument to show them. | postgraphile: `@graphile-contrib/pg-omit-archived` | partial: `__filter_queryset__` | low | No built-in "include archived" argument. |
| Global feature toggles | One setting turns off generated lists, connections, mutations or filters across the schema. | postgraphile: behaviors (`schema.defaultBehavior: "-connection +list"`, `@behavior`) | partial: `auto`, `exclude` and `AUTOGENERATION` | low | Undine is explicit per class. |
| Custom naming rules | Replaces how type and field names are generated. | postgraphile: inflection (`inflection.replace.<name>`) | partial: `schema_name` and `CAMEL_CASE_SCHEMA_FIELDS` | low | A naming hook could rename generated types like `<Type>Connection`. |
| Vector similarity queries | Finds the nearest rows to a vector or to another row, with a distance field. | dgraph: `querySimilar<T>ByEmbedding(by:, topK:, vector:)`, `querySimilar<T>ById`, `@embedding`, `vector_distance` | missing | low | Possible with pgvector expressions in `Field` and `Order`. A built-in helper is not needed now. |
| Write-only password field with check | A password input is hashed on write, never returned, and checked by a query. | dgraph: `@secret(field:)`, `check<T>Password` | partial: `Input(input_only=True)` and `@<input>.convert` | low | Django auth handles passwords. |

## 3. Mutations and inputs

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Upsert on conflict | Inserts, or updates chosen columns when a unique constraint conflicts. | hasura: `on_conflict: {constraint, update_columns, where}`, MSSQL `if_matched`. dgraph: `addT(input:, upsert: true)` by `@id` field | partial: `custom` kind acts as create or update by `pk` | high | Django has `bulk_create(update_conflicts=True, unique_fields=, update_fields=)` and `update_or_create`. Internal bulk upsert code exists in `undine/utils/model_utils.py`. |
| Filtered bulk update and delete | Updates or deletes every row that matches a filter. | hasura: `update_<table>(where:, _set:)`, `delete_<table>(where:)`. pg_graphql: `update<Type>Collection(set:, filter:, atMost:)`, `deleteFrom<Type>Collection(filter:, atMost:)`. dgraph: `updateT(input: {filter, set, remove})`, `deleteT(filter:)`. neo4j-graphql: `updateMovies(where:, update:)`, `deleteMovies(where:, delete:)` | missing | medium | Undine bulk mutations take a list of inputs with `pk`. Could reuse the FilterSet as the `where` input. pg_graphql `atMost` (default 1) is a good safety limit. |
| Many different updates in one call | A list of `(where, set)` pairs run in order in one transaction. | hasura: `update_<table>_many(updates: [...])` | partial: bulk update with a list of inputs by `pk` | low | Only matters together with filtered updates. |
| Atomic increment and JSON update operators | Updates a value relative to the current value in the database. | hasura: `_inc`, `_append`, `_prepend`, `_delete_key`, `_delete_elem`, `_delete_at_path`. neo4j-graphql: `add`, `subtract`, `multiply`, `divide`, list `push`, `pop` | missing | medium | Maps to Django `F("x") + n`. Avoids lost updates. |
| Affected rows count in mutation output | Returns how many rows the mutation changed, next to the returned rows. | hasura: `{ affected_rows returning { ... } }`. pg_graphql: `affectedCount`, `records`. dgraph: `numUids`. neo4j-graphql: `info { nodesCreated relationshipsCreated nodesDeleted }` | partial: output type returns objects. Delete returns `pk` | low | Only useful with filtered bulk mutations. |
| Post-mutation row check | Checks the row after the write and rolls back if it fails. | hasura: insert and update permission `check` | partial: `__after__` can raise inside `transaction.atomic` | low | I think raising in `__after__` rolls back. Not verified. |
| Input validation webhook | Calls an external HTTP service to accept or reject a mutation input. | hasura: `validate_input: {type: http, definition: {url, ...}}` | partial: `__validate__` and `@<input>.validate` in Python | low | Python hooks are the Django way. |
| Async mutation with job result | A mutation returns a job id. The client fetches or subscribes to the result later. | hasura: async actions (`kind: asynchronous`, `<action>(id:)`) | missing | low | Would need a task queue (Django tasks, Celery). Users can build it. |
| Relay mutation payload extras | Mutation output includes `clientMutationId`, a `query` field and an edge for the new row. | postgraphile: payload `clientMutationId`, `query`, `<record>Edge(orderBy:)` | missing | low | Relay clients use the edge to update connections. Legacy pattern. |
| Delete returns deleted objects | Delete mutation returns the full objects as they were before deletion. | dgraph: `DeleteTPayload { t { ... } msg }` | partial: delete returns `<SchemaName>Output { pk }` | medium | Clients often need more than the pk to update caches. |
| Optimistic concurrency control | Updates carry a version and fail on conflict. | aws-appsync: versioned data sources, `_version`, `conflictHandler: OPTIMISTIC_CONCURRENCY` | missing | medium | Common need for forms edited by many users. No grep hits for optimistic or version checks in undine/. |
| Declarative input validators | Short validators like min length or regex on input fields. | aws-appsync (Amplify Gen 2): `.validate(v => v.minLength(n))` | partial: `@<input>.validate` and Django model validators with `MUTATION_FULL_CLEAN` | low | Django validators already cover it. |

## 4. Filtering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Relation "any", "all", "none", "exists" filters | Filters by a nested condition on related rows with clear quantifiers. | hasura: `{<array_rel>: <target>_bool_exp}`, `_not`, `{rel: {}}`. neo4j-graphql: `<rel>: { all, none, single, some }` | partial: relation path filters like `Filter("tasks__name")` and `NOT` | medium | No nested related FilterSet input and no explicit "all" quantifier. |
| Filter by aggregate of related rows | Filters by `count`, `sum`, `avg` and so on of related rows. | hasura: `{<array_rel>_aggregate: {count: {predicate: ...}}}`. DDN: aggregation predicates (unstable). neo4j-graphql: `<rel>Connection: { aggregate: { count, node: { <f>: { average, min, max, sum } } } }` | partial: `Filter(Count(...))` expression reference | medium | Works per declared filter. No generic aggregate predicate input. |
| Column to column comparison | Compares two columns of the same row. | hasura: `_ceq`, `_cne`, `_cgt`, `_clt` (permissions only) | partial: function filter can return `Q(a=F("b"))` | low | Possible by hand. |
| PostGIS spatial operators | Spatial filters like intersects and within distance. | hasura: `_st_contains`, `_st_intersects`, `_st_d_within`, ... dgraph: `PointGeoFilter` `near`, `within`, `PolygonGeoFilter` `contains`, `intersects` | missing | low | No GeoDjango support in Undine. |
| ltree operators | Ancestor, descendant and lquery match filters. | hasura: `_ancestor`, `_descendant`, `_matches` | missing | low | Needs a third-party Django ltree field. |
| Filter by global ID | A list filter accepts a global ID and rejects IDs of other types. | pg_graphql: `filter: {nodeId: {eq: "..."}}` | missing | low | I think Undine filters only take raw pks. Not verified. |
| Full-text search with relevance score | A search root field returns rows with a score and can filter and sort by it. | neo4j-graphql: `@fulltext(indexes: [...])`, `edges { score node }`, `score: { min, max }` | partial: `PostgresFTS` filter reference (undocumented) | medium | No score output or rank ordering. Django has `SearchRank`. |

## 5. Ordering

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Client chooses null placement | Ordering enum values include nulls first and nulls last. | hasura: `asc_nulls_first`, `asc_nulls_last`, `desc_nulls_first`, `desc_nulls_last` | partial: `Order(null_placement=...)` server side | low | Server-side choice is usually enough. |
| Order by aggregate of to-many relation | Orders by `count` or `max` of related rows. | hasura: `{articles_aggregate: {count: desc}}` | partial: `Order(Count(...))` expression reference | low | Works per declared order. |

## 6. Pagination and connections

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Connection nodes shortcut | Connection has a `nodes` list next to `edges`. | postgraphile: connection `nodes` | missing | medium | Inventory lists it as missing. Simpler client code. |
| Offset argument on cursor connections | Connections take `offset` next to `first` and `after`. | postgraphile: `offset` on connection fields | missing | low | Undine has a separate `OffsetPagination`. |
| Through-model fields on connection edges | Edges of a many-to-many connection expose fields of the through row. Clients can filter and sort by them. | neo4j-graphql: `MovieActorsRelationship { properties }`, connection `where: { edge: ... }`, `sort: { edge: ... }` | missing | medium | Common Django need (for example role on a membership). I think Undine edges only have `cursor` and `node`. |

## 7. Global object IDs (Relay Node)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Configurable global ID format | Lets the user change how global IDs encode and decode. | postgraphile: `schema.defaultNodeIdCodec`, `@nodeIdCodec`, `NodeIdCodec { encode, decode }` | partial: fixed `to_global_id` and `from_global_id` | low | A setting with a dotted path would do it. |

## 8. Query optimizer (N+1 and over-fetching)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Operation plan cache | Caches the data-fetching plan per operation shape and reuses it across requests. | postgraphile: Grafast operation plan cache (`operationsCacheMaxLength`), plan constraints | missing | medium | I think the optimizer walks the AST on every request. Only parse and validation are cached. I found no cache in `undine/optimizer/`. |
| Plan-based batched execution | Every field is planned as a batched step. No DataLoader needed. | postgraphile: Grafast plan resolvers, `loadOne`, `loadMany` | partial: optimizer plus `DataLoader` (async only) | low | Big engine change. Listed for completeness. |

## 10. Interfaces

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Relation fields on interfaces | Interfaces declare relation fields that each implementer maps to its own relation. | neo4j-graphql: `@declareRelationship` | partial: `InterfaceField` must map to a model field with the same output type | medium | Inventory says no computed interface fields. |
| Filter interface results by concrete type | Interface list takes a filter on `__typename`. | neo4j-graphql: `typename: [Movie]` in the interface `where` | missing | low | Per-implementation filter args exist. |

## 13. Scalars and type conversion

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Phone and timestamp scalars | Phone number and epoch timestamp scalars. | aws-appsync: `AWSPhone`, `AWSTimestamp` | missing | low | Users can define them with `ScalarType`. |

## 14. Permissions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Declarative row filter per role | Row access rules as data (filter expressions with session values). | hasura: select permission `filter`, `_exists`. DDN: `ModelPermissions.select.filter`, rules-based permissions. dgraph: `@auth(query:, add:, update:, delete:)` with JWT claim rules and graph traversal rules. aws-appsync (Amplify): `@auth(rules: [{allow: owner}, {allow: groups}])` | partial: `QueryType.__filter_queryset__` in Python | low | Python hooks are more flexible. |
| Per-role schema | Each role gets its own schema and introspection. | hasura: role-based schema generation | partial: visibility hooks (not a security boundary) | low | Visibility already gives per-request schemas. |
| Inherited roles with cell-level nulls | Combines roles. Columns not allowed for a row return null. | hasura: `add_inherited_role` | missing | low | Field permissions raise instead of nulling. |
| Backend-only mutations | Mutations only callable by trusted backends. | hasura: `backend_only: true` | partial: visibility and permission hooks | low | Possible with hooks. |
| Auth directives enforced by the server | `@authenticated`, `@requiresScopes` and `@policy` hide or null unauthorized fields. | apollo-router: `authorization.directives`, `reject_unauthorized`, `UNAUTHORIZED_FIELD_OR_TYPE`. hive-gateway: `genericAuth` with `@authenticated`, `@requiresScopes`, `@policy` | partial: `AuthenticatedDirective`, `RequiresScopesDirective`, `PolicyDirective` are federation metadata. Python permission hooks | medium | Server feature. Undine could enforce them itself with Django auth and permissions, also outside federation. |
| Require authentication for all requests | Rejects every unauthenticated request. | apollo-router: `authorization.require_authentication`. dgraph: `ClosedByDefault: true`. hive-gateway: `genericAuth` mode `protect-all` with `@skipAuth` | missing | low | Server feature. Django middleware or `login_required` covers it. |

## 15. Visibility (per-request schema hiding)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Schema contracts by tag | Builds filtered schema variants by including or excluding `@tag` values. | cosmo: `wgc contract create --include/--exclude`. apollo-router: contracts with `@tag` | partial: visibility hooks and `TagDirective` metadata | medium | Server feature. Undine could print or serve a schema variant filtered by tags, for example a public API. |
| Schema variant by request header | A header or cookie picks a schema variant per request. | cosmo: `X-Feature-Flag` header, feature flags | partial: visibility hooks get the request | low | Visibility can read headers. A doc example would cover it. |

## 16. Validation rules and operation limits

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query depth limit | Rejects operations nested deeper than N. | hasura: `set_api_limits` `depth_limit`. pg_graphql: fixed `MAX_SELECTION_DEPTH` 32. apollo-router: `limits.router.max_depth`. cosmo: `security.complexity_limits.depth`. hive-gateway: armor `maxDepth` (default 6). aws-appsync: `queryDepthLimit` (1 to 75) | partial: `MaxListNestingDepthRule` counts only to-many nesting | medium | Plain depth limit is a common checklist item. |
| Node count limit | Rejects operations with more than N selected fields. | hasura: `node_limit`. apollo-router: `limits.router.max_height` (unique fields). cosmo: `security.complexity_limits.total_fields` | missing | medium | Cheap validation rule. |
| Rate limiting | Limits requests per minute per IP or per user. | hasura: `rate_limit: {max_reqs_per_min, unique_params}`. apollo-router: `traffic_shaping.router.global_rate_limit`. hive-gateway: `rateLimiting` and `@rateLimit` directive per type or field with `identifier` | missing | medium | Could use Django cache. Inventory lists it as missing. Server feature. A per-field rule (for example login mutation) fits Undine well. |
| Per-role limits | Different limits for different users or roles. | hasura: `set_api_limits` `per_role` | missing | low | Settings are global. Could be a callback. |
| Row fetch limit per role | Caps rows returned for a role. | hasura: select permission `limit` | partial: `LIST_ENTRYPOINT_LIMIT` global and `Entrypoint(limit=...)` | low | Per user cap is missing. |
| Introspection off per role | Disables introspection for chosen users only. | hasura: `set_graphql_schema_introspection_options {disabled_for_roles}`. pg_graphql: per schema `{"introspection": true}` comment directive | partial: `ALLOW_INTROSPECTION_QUERIES` global setting | medium | Common need: introspection only for staff. A predicate setting would do it. |
| Sync execution timeout | Cancels long queries also in sync mode. | hasura: `time_limit` (cancels Postgres queries) | partial: `EXECUTION_TIMEOUT_SECONDS` async only | low | Postgres `statement_timeout` is an option. |
| Root field count limit | Rejects operations with more than N root fields. | apollo-router: `limits.router.max_root_fields`. cosmo: `complexity_limits.root_fields`, `root_field_aliases` | missing | medium | Server feature. Simple validation rule. |
| Recursive selection limit | Rejects operations with too many recursive fragment selections. | apollo-router: `limits.router.max_recursive_selections` | missing | low | Server feature. graphql-core already rejects fragment cycles. |
| Warn-only mode for limits | Logs limit violations without rejecting the request. | apollo-router: `limits.router.warn_only`, `demand_control.mode: measure`. cosmo: `complexity_limits.mode: measure`, `cost_control.mode: measure` | missing | medium | Server feature. Helps roll out new limits safely. |
| Cost analysis with list sizes | Estimates cost from per-field weights and assumed list sizes, and compares estimate with actual cost. | apollo-router: `demand_control` with `@cost(weight:)`, `@listSize(assumedSize:, slicingArguments:)`, `cost.estimated`, `cost.actual`. cosmo: `security.cost_control`, `X-WG-Cost-Estimated` and `X-WG-Cost-Actual` headers. hive-gateway: `demandControl` (`maxCost`, `listSize`, `fieldCost`) | partial: `MaxComplexityRule` counts database queries. `CostDirective` and `ListSizeDirective` exist only as federation metadata | medium | Server feature. Undine could read its own `@cost` and `@listSize` and use `page_size` as the slicing size. |
| Read-only switch | Rejects all mutations with one setting. | apollo-router: `forbid_mutations: true`. cosmo: `security.block_mutations`, `block_subscriptions` with expression `condition` | missing | low | Server feature. Useful for read replicas or maintenance. |
| Skip limits for persisted documents | Trusted persisted documents bypass complexity and depth limits. | cosmo: `complexity_limits.*.ignore_persisted_operations` | missing | medium | Server feature. Lets staff tools run heavy known queries. |
| Operation name length limit | Rejects very long operation names. | cosmo: `security.operation_name_length_limit` | missing | low | Server feature. Names go to logs and traces. |
| Require variables instead of inline arguments | Warns about or rejects literal argument values in operations. | cosmo: `engine.validate_inline_arguments` (`permissive`, `strict`) | missing | low | Server feature. Improves cache hit rates and log redaction. |
| Resolver count limit | Stops execution after N resolver calls in one request. | aws-appsync: `resolverCountLimit` (default 10,000), `ResolverExecutionLimitReached` | missing | low | Server feature. A field middleware could count calls. |

## 17. Subscriptions

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Live queries | Any query can be a subscription. The server re-runs it and sends the result when it changes. | hasura: live queries (`HASURA_GRAPHQL_LIVE_QUERIES_MULTIPLEXED_REFETCH_INTERVAL`). DDN: `subscription.pollingIntervalMs`, `allowSubscriptions`. dgraph: `@withSubscription` (poll every `--graphql poll-interval`, shared poller per identical query). graphql-mesh: `@live` with `invalidations: [{ field: Mutation.addTodo, invalidate: [Query.todos] }]` | partial: model signal subscriptions (`ModelUpdateSubscription`) | medium | Polling and hash compare is simple to build. Signals miss bulk updates. |
| Cursor-based table stream subscription | Streams new rows in batches from a cursor column. | hasura: `<table>_stream(batch_size:, cursor:, where:)` | missing | medium | Survives reconnect if the client sends the last cursor. Inventory lists "no missed-event replay". |
| Legacy WebSocket protocol | Supports the old `subscriptions-transport-ws` protocol. | hasura: both `graphql-ws` and `graphql-transport-ws`. dgraph: only legacy `graphql-ws`. cosmo: `subscriptions-transport-ws` and Absinthe protocol | missing | low | The old protocol is deprecated. Inventory lists it as not supported. |
| Skip empty subscription results | Does not send null or empty results. | hasura: `remove_empty_subscription_responses` | missing | low | Users can filter in the generator. |
| Bounded send queue | Cancels a subscription when the client is too slow. | hasura: `HASURA_GRAPHQL_WEBSOCKET_QUEUE_SIZE` | partial: `max_backlog` on signal subscriptions | low | |
| Postgres LISTEN/NOTIFY broker | Delivers subscription events across processes with Postgres notifications. | postgraphile: `pgSubscriber` (`makePgService({pubsub: true})`), `listen()` step | partial: `ChannelLayerSubscriptionBroker` needs channels | medium | No extra service for Postgres users. Fits the `SubscriptionBroker` interface. |
| Client filter on model subscriptions | Client passes a `where` filter to a created, updated or deleted subscription. | neo4j-graphql: `movieCreated(where: MovieSubscriptionWhere)`. cosmo: `@openfed__subscriptionFilter(condition:)` with `{{ args.x }}`. aws-appsync: subscription arguments as equality filters, `extensions.setSubscriptionFilter` with `ctx.identity` | partial: `SignalSubscription.filter` is server side | medium | Could reuse the QueryType FilterSet. |
| Previous state in update events | Update events carry the old values next to the new ones. | neo4j-graphql: `MovieUpdatedEvent { updatedMovie previousState }` | missing | low | Needs a `pre_save` read. Costs a query. |
| HTTP callback subscription protocol | Subgraph posts subscription events to a router callback URL instead of keeping a WebSocket. | apollo-router: `subscription.mode.callback` (`callbackUrl`, `subscriptionId`, `verifier`, `check`, `next`, `complete`) | missing | medium | Subgraph. Works without channels. Needs a background task to post events. |
| Subscription limits | Caps open subscriptions and subscription lifetime. | apollo-router: `max_opened_subscriptions`, `max_lifetime`, `queue_capacity`. aws-appsync: 200 subscriptions per connection, 24 h connection limit | partial: `max_backlog` on signal subscriptions | medium | Server feature. Protects workers from too many long connections. |
| Shared upstream for identical subscriptions | Identical subscriptions share one source stream. | apollo-router: subscription `deduplication` | partial: broker fan-out per topic | low | Server feature. |
| Server-side subscription invalidation | A mutation closes matching active subscriptions, for example when a user loses access. | aws-appsync: `extensions.invalidateSubscriptions`, `setSubscriptionInvalidationFilter` | missing | medium | Undine checks permissions per yielded value. A way to close streams early is missing. |
| Subscriptions linked to mutation results | A subscription fires with the result of named mutations. | aws-appsync: `@aws_subscribe(mutations: [...])` | partial: `ModelSaveSubscription` and other signal subscriptions | low | Model signal subscriptions cover most uses. |

## 19. Caching

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Client-requested caching | A query directive asks for a cached result with a TTL or a forced refresh. | hasura: `@cached(ttl:, refresh:)`. dgraph: `@cacheControl(maxAge:)` on the operation (HTTP header only) | partial: server-side `cache_time` and `@cacheRules` | low | Client-set TTL can be abused. `refresh` is the useful part. |
| Manual cache clear | API to clear cached responses by key or by operation family. | hasura: `POST /pro/cache/clear`, `?key=`, `?family=`, `X-Hasura-Query-Cache-Key` header. apollo-router: `/invalidation` endpoint with `kind: subgraph \| type \| cache_tag` | missing | medium | Inventory says no invalidation. A Python helper to clear by operation would help. |
| Cache tags and tag invalidation | Tags cached responses by type, entity or custom tag and purges by tag. | apollo-router: `@cacheTag(format:)`, `apolloCacheTags` and `apolloEntityCacheTags` extensions, response cache invalidation | partial: `CacheTagDirective` is federation metadata only | medium | Server and subgraph. Undine could tag its response cache by QueryType and model, and clear tags from model signals. |
| CDN cache tag header | Sends a `Cache-Tag` or `Surrogate-Key` header so CDNs can purge by tag. | apollo-router: `Cache-Tag` response header with `subgraph-*`, `type-*` and `@cacheTag` values | missing | medium | Server feature. Fits the existing `Cache-Control` support. |
| Entity-level response cache | Caches each federation entity apart, so different operations reuse them. | apollo-router: `response_cache` per `_entities` item | missing | low | Gateway feature. A subgraph only needs to send correct `Cache-Control`. |
| Cache-Control on subgraph entity responses | Subgraph sends `Cache-Control` with the minimum TTL of returned entities. | apollo-router: reads subgraph `Cache-Control` (`max-age`, `private`) | partial: `Cache-Control` and `Age` headers from cache rules | low | Subgraph. I think Undine sends the header only when the response cache is active. Not verified. |
| Client Cache-Control request header | Client `Cache-Control: no-cache` skips the cache read and `no-store` skips the write. | cosmo: response cache honors client `no-cache` and `no-store` | partial: `REQUEST_CACHE_READ_PREDICATE` and `REQUEST_CACHE_WRITE_PREDICATE` | low | Server feature. Default predicates could read the header. |
| Cache status debug headers | Response headers show hit or miss for each cache. | cosmo: `engine.debug.enable_cache_response_headers` (`X-WG-Execution-Plan-Cache`, ...) | partial: `Age` header on cached responses | low | Server feature. Dev aid. |
| Response cache invalidation on mutations | Mutations evict cached responses that contain the changed entities. | hive-gateway: `responseCaching` invalidation by entity identity (Yoga response cache). aws-appsync: `extensions.evictFromApiCache(typeName, fieldName, keys)` from mutations | missing | high | Inventory says time-based only. Undine knows the model of each QueryType, so it could tag entries by model and pk and clear them from signals. |
| Per-field result cache | Caches one field's resolver result with chosen cache keys, not the whole response. | aws-appsync: `PER_RESOLVER_CACHING`, `cachingConfig { ttl, cachingKeys }` | missing | medium | Inventory says no partial result caching. Useful for slow function fields. |

## 21. Persisted documents and APQ

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Allow list per role | Persisted-only mode where the allowed set depends on the role. | hasura: `add_collection_to_allowlist {scope: {roles}}` | partial: `PERSISTED_DOCUMENTS_ONLY` is global | low | |
| Admin exemption from allow list | Admin users can run any operation in allow-list mode. | hasura: admin role is exempt from the allow list. postgraphile: `@grafserv/persisted` `allowUnpersistedOperation` (bool or callback). cosmo: `security.block_non_persisted_operations.condition` expression. hive-gateway: `allowArbitraryDocuments` (bool or function) | missing | medium | Useful for staff tools. I think `PERSISTED_DOCUMENTS_ONLY` has no predicate. Not verified. |
| Persisted documents from files | Loads trusted documents from a directory or manifest at deploy time. | postgraphile: `@grafserv/persisted` `persistedOperationsDirectory`, `persistedOperationsGetter`. apollo-router: `persisted_queries.local_manifests` (`apollo-persisted-query-manifest` JSON) | partial: database model and registration view | medium | A management command or file loader would fit CI workflows. |
| Audit mode for persisted documents | Logs operations that are not in the persisted list before enforcing the list. | apollo-router: `persisted_queries.log_unknown`, safelist rollout. cosmo: `persisted_operations.log_unknown` | missing | medium | Server feature. Makes it safe to turn on `PERSISTED_DOCUMENTS_ONLY`. |
| Warm caches from persisted documents | Parses and validates persisted documents at startup. | apollo-router: `experimental_prewarm_query_plan_cache.on_startup` | missing | low | Server feature. Parse and validation caches are in-process LRU. |
| Custom persisted document IDs and manifest formats | Accepts non-hash IDs and imports Relay or Apollo manifests. | cosmo: custom IDs (1 to 250 chars), Relay query map, Apollo persisted query manifest, `wgc operations push` | partial: sha256 IDs from `PersistedDocumentsView` | medium | Server feature. Relay compiler emits its own IDs. |
| Persisted documents per client | Stores and allows documents per client name. | cosmo: operations pushed per `graphql-client-name`. hive-gateway: Hive App Deployments (document sets per client version) | missing | low | Server feature. |

## 22. Lifecycle hooks (middleware / extensions)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cost and tracing data in response extensions | Adds per-resolver timings or touched-row counts to `extensions`. | dgraph: `extensions.touched_uids`, `extensions.tracing` (Apollo Tracing format). cosmo: Advanced Request Tracing (`X-WG-Trace: true`, `extensions.trace`) | partial: hooks can add `extensions`. Docs show timing examples | low | Apollo Tracing format is deprecated. A query count in extensions could help in dev. |

## 24. Integrations

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| REST endpoints from saved operations | Serves a stored GraphQL operation at a REST URL. Path and query params become variables. | hasura: `create_rest_endpoint`, `/api/rest/<url>`. cosmo: ConnectRPC (`connect_rpc`, one RPC per trusted operation, OpenAPI via Buf) | missing | medium | Could reuse persisted documents. Good for webhooks and simple clients. |
| OpenAPI export of REST endpoints | Generates an OpenAPI spec for the REST endpoints. | hasura: `/api/swagger/json` | missing | low | Only with REST endpoints. |
| JSON:API endpoint | Generates a JSON:API REST interface from the same models. | hasura DDN: `/v1/jsonapi` | missing | low | Out of scope for a GraphQL library. |
| Explain endpoint | Returns the SQL and plan for a GraphQL query. | hasura: `/v1/graphql/explain`. Console "Analyze". postgraphile: `grafast.explain: ["plan","sql"]`, `X-GraphQL-Explain` header, Ruru plan diagrams. apollo-router: `Apollo-Expose-Query-Plan: true \| dry-run` header | partial: debug toolbar and `pytest_undine` query log | medium | A GraphiQL panel or command that shows SQL would help debugging. |
| SQL query tags | Adds operation name and other data to SQL as comments. | hasura: `set_query_tags` (`standard`, `sqlcommenter`) | missing | medium | Helps match slow SQL to GraphQL operations. Django has `connection.execute_wrapper`. No grep hits for sqlcommenter. |
| Prometheus metrics | Exposes request, error and subscription metrics. | hasura: `/v1/metrics`. apollo-router: Prometheus exporter, `apollo.router.*` instruments. hive-gateway: `prometheus` plugin | missing | medium | Inventory lists it as missing. |
| Event triggers to webhooks | Sends row changes to an HTTP endpoint with retries. | hasura: `pg_create_event_trigger`. dgraph: `@lambdaOnMutate(add:, update:, delete:)` | missing | low | Django signals and task queues cover it. Not GraphQL. |
| Scheduled triggers | Cron and one-off webhook calls. | hasura: `create_cron_trigger`, `create_scheduled_event` | missing | low | Out of scope. |
| Log masking of variables | Masks variables in logs. | hasura: `HASURA_GRAPHQL_LOG_MASKED_VARIABLES` | partial: tracing integrations redact documents and variables | low | |
| Remote schema stitching | Merges another GraphQL API into the schema. | hasura: `add_remote_schema` with `customization`. graphql-mesh: source handlers for GraphQL, OpenAPI, gRPC, SOAP, OData, MySQL | missing | low | Server feature. Federation covers most needs. |
| Remote relationships | Joins a local type to a field in a remote GraphQL or REST API. | hasura: `create_remote_relationship` (`to_remote_schema`, `to_source`) | partial: function `Field` can call any API | low | Server feature. |
| Webhook-backed fields | A root field forwards to an HTTP handler with request and response transforms. | hasura: actions (`handler`, `request_transform`, Kriti). dgraph: `@custom(http: {url, method, body, graphql, mode: BATCH})`, `@lambda`. apollo-router: connectors `@connect`, `@source` | partial: function `Entrypoint` | low | Python code covers it. |
| Postgres row-level security bridge | Passes the request user to Postgres session settings so RLS policies apply. | postgraphile: `pgSettings`, `set_config(k, v, true)` per transaction | missing | low | Niche for Django. Would need a transaction per request. |
| Schema hot reload in GraphiQL | GraphiQL refreshes the schema when the server schema changes. | postgraphile: watch mode, `X-GraphQL-Event-Stream`, Ruru | missing | low | Django runserver reloads. The browser keeps the old schema until refresh. |
| Usage reporting to schema registries | Sends operation signatures and field usage to Apollo GraphOS or Hive Console. | apollo-router: GraphOS usage reporting, extended references. hive-gateway: `reporting` (`type: 'hive'` or `'graphos'`) | missing | medium | Subgraph usage is reported by the router. A monolith Undine server would need it. Hive has no Python usage client (console issue #508), so this is an open gap. |
| Client name and version awareness | Reads client name and version headers and adds them to traces and metrics. | apollo-router: `apollographql-client-name`, `apollographql-client-version`, `enhanced_client_awareness`. cosmo: `client_header.name`, `client_header.version` (`graphql-client-name`) | missing | medium | Server feature. Cheap to add to the tracing hooks. |
| Record and replay traffic | Records requests to replay against a new version. | apollo-router: `experimental.record` | missing | low | Server feature. Testing aid. |
| Coalesce identical in-flight requests | Runs one execution for identical concurrent queries and shares the result. | apollo-router: `traffic_shaping.deduplicate_query`. cosmo: `enable_inbound_request_deduplication`. hive-gateway: `inboundInflightRequestDeduplication` | missing | low | Server feature. Only for async mode. Must respect per-user data. |
| Subgraph compatibility listing | Library is listed in Apollo's subgraph compatibility table. | apollo-router: `apollo-federation-subgraph-compatibility` repo, Python entries for Ariadne, Graphene, Strawberry | partial: Undine passes the harness locally (`tests/test_federation/compatibility/`) | medium | Subgraph. Not a code feature. A PR to the compatibility repo makes Undine visible to federation users. |
| MCP server from persisted documents | Exposes trusted operations as MCP tools for AI agents, with schema and auth scopes. | cosmo: router `mcp` block, `execute_operation_<name>` tools, `get_schema`, `mcp.oauth`. hive-gateway: `@graphql-hive/plugin-mcp` (`useMCP`, `@mcpTool`, `@mcpHeader`) | missing | medium | Server feature. Persisted documents already give a safe operation list. |
| Field usage tracking | Records which fields and arguments clients use, for deprecation and pruning. | cosmo: `graphql_metrics` schema usage export, graph pruning (`UNUSED_FIELDS`, `DEPRECATED_FIELDS`) | missing | medium | Server feature. Could be a lifecycle hook writing counters. |
| Traffic-based breaking change check | Checks a schema change against operations seen in real traffic. | cosmo: `subgraph check` operation checks, check overrides | partial: `check_schema_changes` compares SDL only | low | Needs field usage data first. |
| Schema lint rules | Checks naming, descriptions and deprecation rules in the schema. | cosmo: lint policy (`FIELD_NAMES_SHOULD_BE_CAMEL_CASE`, `ALL_TYPES_REQUIRE_DESCRIPTION`, `REQUIRE_DEPRECATION_REASON`, ...) | missing | low | Server feature. Could be a management command. |
| Message broker subscriptions | Subscription fields read from Kafka, NATS or Redis topics, with topic templates from arguments. | cosmo: Cosmo Streams `@edfs__kafkaSubscribe(topics:)`, `@edfs__natsSubscribe(subjects:)`, `@edfs__redisSubscribe(channels:)` | partial: `SubscriptionBroker` with in-memory and channel layer brokers | low | Server feature. A Redis broker without channels could be useful. |
| GraphiQL pre-request scripts | Runs a script before each request in the IDE, for example to fetch a token. | cosmo: Studio playground pre-flight and pre/post-operation scripts | missing | low | GraphiQL plugin work. |
| Fetch reasons for subgraphs | Router tells the subgraph why each field was fetched (client, key or `@requires`). | cosmo: `@openfed__requireFetchReasons`, `extensions.fetch_reasons` | missing | low | Subgraph. Could skip permission checks for router-only fields. |
| Subgraph request signature check | Subgraph verifies an HMAC signature that the gateway adds to each request. | hive-gateway: `hmacSignature`, `useHmacSignatureValidation` | missing | low | Subgraph. Protects a subgraph that is reachable outside the gateway. |
| Forwarded JWT claims from gateway | Subgraph reads verified claims that the gateway puts in `extensions.jwt`. | hive-gateway: `jwt.forward`, `useForwardedJWT` | missing | low | Subgraph. Django auth usually reads its own headers. |
| Request ID propagation | Generates or forwards `x-request-id` and adds it to logs and traces. | hive-gateway: `requestId` (on by default). aws-appsync: `x-amzn-RequestId` on every response and log event | missing | low | Server feature. Django middleware can do it. |
| Schema mocking | Returns fake data for the schema for frontend work. | hive-gateway: `useMock` (`MockStore`) | missing | low | Server feature. Dev aid. |
| Webhooks as subscription events | An incoming webhook HTTP call publishes an event to a subscription topic. | graphql-mesh: `@resolveTo(pubsubTopic: "webhook:post:/path")`, gateway `webhooks: true` | partial: custom `SignalSubscription` plus a Django view that sends a signal | low | Server feature. |
| Semantic introspection for agents | Adds search and definition lookups to the schema for AI agents. | hive-gateway: `@graphql-hive/semantic-introspection` (`__search`, `__definitions`, open PR) | missing | low | Server feature. Unreleased upstream. |

## 26. Transports and HTTP

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Query batching | Many operations in one HTTP request as a JSON array. | hasura: batched requests, `batch_limit`. apollo-router: `batching` (`batch_http_link`, `maximum_size`). cosmo: `batching` (`max_concurrency`, `max_entries_per_batch`). hive-gateway: `batching: true \| { limit }` | missing | medium | Inventory lists it as missing. Needs a batch size limit. |
| HTTP 401 for auth errors | Returns HTTP 401 instead of 200 for auth failures. | hasura: `HASURA_GRAPHQL_PRESERVE_401_ERRORS` | partial: errors carry `status_code` | low | I think Undine already uses status codes with `application/graphql-response+json`. Not verified. |
| Maintenance mode | Turns the API off with a clear response. | hasura: `HASURA_GRAPHQL_ENABLE_MAINTENANCE_MODE` | missing | low | Django middleware covers it. |
| Health endpoint | Simple health check path. | hasura: `/healthz`. apollo-router: `health_check` (`/health?ready`, `?live`). hive-gateway: `healthCheckEndpoint`, `readinessCheckEndpoint` | missing | low | Not GraphQL specific. |
| CSRF prevention by preflight header | Rejects simple requests unless a custom header forces a CORS preflight. | apollo-router: `csrf.required_headers` (`apollo-require-preflight`, `x-apollo-operation-name`) | partial: Django `CsrfViewMiddleware` | low | Server feature. Useful when the API uses token auth and is CSRF exempt. |
| Set response headers from resolvers | Resolvers add HTTP response headers. | aws-appsync: `util.http.addResponseHeader(name, value)` | partial: `request.response_headers` exists and the cache hook uses it | low | Not documented in docs/. I think resolvers can write `info.context.response_headers`. Not verified. |

## 27. Errors and error handling

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| onError request parameter | Client chooses error behavior per request: propagate, null or halt. | postgraphile: `onError: "PROPAGATE" \| "NULL" \| "HALT"` read from the request body | partial: `@experimental_disableErrorPropagation` directive | medium | This follows the newer error behavior RFC. No grep hits for `onError` in undine/. |

## 28. Async

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cancel execution on client disconnect | Stops resolver work when the client goes away. | hive-gateway: `executionCancellation`, `upstreamCancellation`. apollo-router: `supergraph.early_cancel` | missing | low | Server feature. I think the async view does not watch for disconnects. Not verified. |

## Aggregation (new area)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Aggregate root and nested fields | Returns `count`, `sum`, `avg`, `min`, `max` and statistics for a filtered set, with optional `nodes`. | hasura: `<table>_aggregate { aggregate { count sum { col } } nodes }`, `<array_rel>_aggregate`. DDN: `<model>Aggregate`, `_count`, `_count_distinct`. pg_graphql: `aggregate { count sum avg min max }` on connections (opt in per table). neo4j-graphql: `<plural>Connection { aggregate { count node { <f> { min max average sum shortest longest } } } }` | missing | high | No grep hits for aggregate in undine/. `totalCount` on connections is the only count. Maps well to Django `aggregate()`. |
| Group by | Groups rows by keys and returns aggregates per group. | hasura: `group_by(keys:) { group_key aggregate }` (experimental `group_by_aggregations`). neo4j-graphql: `@groupBy`, `groupBy(fields:)` on connections | missing | medium | Maps to `values().annotate()`. |

## Executable directives (new area)

| Feature | What it does | Seen in (real API name) | Undine today | Fit | Notes |
|---|---|---|---|---|---|
| Cascade directive | Drops result nodes that miss any selected field or the listed fields. | dgraph: `@cascade`, `@cascade(fields: [...])` | missing | low | Acts like an inner join on nested filters. Hard to map to Django prefetches. |
