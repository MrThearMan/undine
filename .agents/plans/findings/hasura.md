# Hasura findings

Versions checked: v2 `graphql-engine` latest release `v2.50.3` (2026-09-09). Repo `hasura/graphql-engine` default branch at `ed6ea94` (last commit 2026-10-07). The v2 docs source is in the same repo under `docs/docs/` (about 700 `.mdx` pages). The v3 / DDN engine is also in the same repo under `v3/` (Rust). The DDN docs are in a separate repo `hasura/ddn-docs` (checked at `d2ca0f4`, 2026-05-12).
Hasura v2 is a Haskell server that generates a GraphQL API from database tables, plus actions, remote schemas and events. Configuration is "metadata" (YAML/JSON via the Metadata API, CLI or Console). No code-first schema. Apache-2.0 for the community edition (CE). Enterprise features (EE) are in the same binary and need a license key.

Paid badges in the docs: "Cloud Free", "Cloud Professional", "Cloud Enterprise", "Self-hosted Enterprise". In this file: `[Cloud/EE]` means not in the free community edition.

## Maintenance status

- Very active for v2 maintenance. 32k stars. About 2400 open issues plus PRs. Not archived. Apache-2.0.
- Recent v2 releases: v2.50.3 (2026-09-09), v2.50.1 (2026-08-18), v2.50.0 (2026-08-05), v2.49.0 (2026-05-28), v2.48.0 (2025-05-20). Older lines (v2.45.x) still get patch releases.
- `CHANGELOG.md` in the repo stops at v2.11. Newer notes are only on GitHub releases and https://hasura.io/changelog.
- v3 engine (`v3/changelog.md`) uses date versions. Latest `v2026.07.15`. `[Unreleased]` has small fixes. v3 releases are mostly infra and auth tweaks in 2026.
- https://hasura.io/docs/llms.txt returns the DDN HTML page, not a text file. https://hasura.io/docs/2.0/llms.txt is 404.
- Recent v2 changes: Relay API promoted to stable `/v1/relay` (2.49). `--enable-relay` flag (default off on Cloud). `HASURA_GRAPHQL_DISABLE_EVENTING` (2.49). `--disable-admin-secret` (2.50). `cascade` on `remove_remote_schema` (2.50). `HASURA_GRAPHQL_PRESERVE_401_ERRORS` and `HASURA_GRAPHQL_SERVER_TIMEOUT` (2.48). Query tag format `standard_prepended` (2.48). Bounded websocket queues `HASURA_GRAPHQL_WEBSOCKET_QUEUE_SIZE` (2.50.x). Naming convention Sep-2023 is opt-in via `HASURA_FF_NAMING_CONVENTION_SEP_2023` (2.50).
- 2.50.0 fixed an MSSQL bug that let users see data they were not authorized for.

## v2 schema generation (general)

- Tables, views and SQL functions are "tracked" in metadata. Each tracked table gets root fields. Untracked objects are hidden.
- Backends: Postgres (and flavours: Citus, CockroachDB, AlloyDB, Neon, Yugabyte, Aurora, Timescale), MS SQL Server, BigQuery. Through Data Connectors (`dc-agents`, "Super Connector") `[Cloud/EE]`: Snowflake, MySQL, MariaDB, Oracle, MongoDB, Athena, Redshift, ClickHouse and others.
- Operator and feature sets differ per backend. Postgres has the most. This file describes Postgres unless noted.
- Default query root fields per table: `<table>`, `<table>_by_pk`, `<table>_aggregate`, `<table>_stream` (subscription only). Relay endpoint adds `<table>_connection`.
- Default mutation root fields per table: `insert_<table>`, `insert_<table>_one`, `update_<table>`, `update_<table>_by_pk`, `update_<table>_many`, `delete_<table>`, `delete_<table>_by_pk`.
- Tables outside the `public` schema get a `<schema>_<table>` prefix. `custom_root_fields`, `custom_name`, `custom_column_names` (now `column_config`) rename things per table. Per-source `customization` adds `root_fields.namespace`, `prefix`, `suffix` and `type_names` prefixes/suffixes.
- Naming conventions: `hasura-default` (snake_case) and `graphql-default` (camelCase fields, PascalCase types, UPPER enum values). Docs say it needs the `naming_convention` experimental feature, but the code no longer checks that flag (see "Docs and code disagree"). Set per source or globally via `HASURA_GRAPHQL_DEFAULT_NAMING_CONVENTION`.
- Postgres enum tables: a table with a single-column text PK can be marked `is_enum: true` and becomes a GraphQL enum. Native Postgres `ENUM` types are mapped as scalars.
- Custom SQL functions (`track_function`) become query or mutation root fields with `args: {...}`. They accept the same `where`/`order_by`/`limit`/`offset`/`distinct_on` as tables. `<function>_aggregate` also. Session argument (`session_argument`) passes `hasura_session` JSON into the function. `exposed_as: mutation` makes a volatile function a mutation.
- Computed fields: SQL functions attached to a table. Scalar computed fields and table-returning computed fields. Can take extra arguments (`args`). Session argument supported.
- Logical models and native queries: typed result shapes (`track_logical_model`) and raw SQL with `{{arg}}` parameters (`track_native_query`). Native queries on BigQuery, MSSQL and Snowflake are `[Cloud/EE]`. Postgres native queries are free.
- Stored procedures on MS SQL Server (`track_stored_procedure`) `[Cloud/EE]`.
- Relationships: object (`object_relationship`) and array (`array_relationship`). Defined by `foreign_key_constraint_on` or `manual_configuration` (`remote_table`, `column_mapping`, `insertion_order: before_parent | after_parent`). Relationships on views and to native queries are also allowed.
- Postgres default values can be set via column presets or DB defaults. `column_config` also renames columns. Column comments become GraphQL descriptions. `comment` on tables, relationships and functions in metadata overrides the description.
- `HASURA_GRAPHQL_STRINGIFY_NUMERIC_TYPES` returns `numeric`/`bigint` as strings. `bigquery_string_numeric_input` experimental feature.
- Relay API (`/v1/relay`, stable since 2.49): `<table>_connection` with `first`/`last`/`after`/`before`, `edges`/`node`/`cursor`, `pageInfo`, global `id` and `node(id:)` root field. Flag `--enable-relay` (`HASURA_GRAPHQL_ENABLE_RELAY`). Default on for CE/EE, off on Cloud. Mutations on Relay return the same shapes as normal mutations.
- Apollo Federation v1 subgraph support (experimental, `apollo_federation`). Per table `apollo_federation_config: {enable: v1}` adds `@key(fields: "<pk>")` and `_entities`/`_service`.

## v2 query grammar (Postgres)

- Root list field: `<table>(where:, order_by:, limit:, offset:, distinct_on:)`. All arguments are optional.
- `<table>_by_pk(<pk_col>: value, ...)`. Composite PKs take one argument per column. Returns a nullable object.
- JSON/JSONB columns take a `path: String` argument on output (JSONPath subset, `$.` is optional, `[0]`, `['key']`).
- Nested relationships take the same arguments as root fields: `articles(where:, order_by:, limit:, offset:, distinct_on:)`. Object relationships take no arguments.
- `distinct_on: [<table>_select_column!]`. Maps to Postgres `DISTINCT ON`. Needs `order_by` to start with the same columns (Postgres rule).
- Pagination: `limit: Int`, `offset: Int`. Keyset pagination is done by hand with `where` and `order_by`. Relay cursor pagination is only on the Relay endpoint.
- Select permissions can set a role-level `limit`. A query `limit` above it is clamped.
- Directives: only standard `@include` and `@skip`. Plus Hasura `@cached(ttl:, refresh:)` `[Cloud/EE]`. No `@defer`/`@stream`.
- Multiple root fields in one query are run in parallel. Every database root field becomes one SQL query (JSON aggregated in Postgres). No N+1. Remote joins are batched.

### `where` (`<table>_bool_exp`)

- Logical: `_and: [bool_exp!]`, `_or: [bool_exp!]`, `_not: bool_exp`. Empty object `{}` is TRUE.
- Implicit AND: several keys in one object are ANDed. Several operators in one column object are ANDed.
- Passing an object to `_or` (not a list) is coerced to a one-item list. The docs warn this becomes AND behaviour.
- Column filter: `{<column>: <type>_comparison_exp}`.
- Relationship filter: `{<object_rel>: <target>_bool_exp}`. For array relationships it means "any related row matches" (EXISTS). "All" is written as `_not: {rel: {col: {_neq: v}}}`. "None" is `_not: {rel: {...}}`. "Exists" is `{rel: {}}`.
- Relationship filters only work for local relationships. Remote relationships are not filterable.
- Aggregation predicates: `{<array_rel>_aggregate: {<fn>: {arguments:, distinct: Boolean, filter: bool_exp, predicate: <type>_comparison_exp}}}`. Postgres functions in source: `count` (arguments: list of columns or none), `avg`, `max`, `min`, `sum`, `bool_and`, `bool_or`, `stddev_samp`, `var_samp`, `corr`, `covar_samp` (the last two take named arguments `X`, `Y`). One function per `_aggregate` object. Hide with experimental `hide_aggregation_predicates`.
- Doc/code mismatch: the API reference and the filter page examples use `average: {...}`. The Postgres source names the function `avg` (`Hasura/Backends/Postgres/Instances/Schema.hs`). I think `average` fails on Postgres.
- Computed field filter: `{<computed_field>: <comparison_exp>}` for scalar, `{<computed_field>: <table>_bool_exp}` for set-returning ("any"). Computed fields with extra arguments cannot be used in `where`.
- `_exists` (permissions only, not in client `where`): `{_exists: {_table: {schema, name}, _where: bool_exp}}` for unrelated tables.
- Column comparison operators (permissions only): `_ceq`, `_cne`, `_cgt`, `_clt`, `_cgte`, `_clte`. Compare to another column, or with `["$", "col"]` to a root table column.
- `null` in a comparison (`{_eq: null}`) is an error since v2.0. `HASURA_GRAPHQL_V1_BOOLEAN_NULL_COLLAPSE=true` restores v1 behaviour (reduce to `{}`). `_eq`/`_neq` never match NULL rows.

### Comparison operators (`<type>_comparison_exp`)

- All types: `_eq`, `_neq`, `_gt`, `_lt`, `_gte`, `_lte`, `_in: [T!]`, `_nin: [T!]`, `_is_null: Boolean`. `json` type has no equality.
- Text-like: `_like`, `_nlike`, `_ilike`, `_nilike`, `_similar`, `_nsimilar`, `_regex`, `_nregex`, `_iregex`, `_niregex` (regex since v2.0).
- Postgres arrays (`<type>_array_comparison_exp`): `_contains`, `_contained_in`, plus the common ops. Experimental `disable_postgres_arrays` turns array types into strings.
- JSONB: `_contains`, `_contained_in`, `_has_key`, `_has_keys_any`, `_has_keys_all`, `_jsonb_path_exists`, `_jsonb_path_match`.
- `_cast`: `{_cast: {String: {...}}}` casts `jsonb` to `String`. `{_cast: {geography: {...}}}` and `{_cast: {geometry: {...}}}` cast between PostGIS types.
- PostGIS geometry/geography: `_st_contains`, `_st_crosses`, `_st_equals`, `_st_intersects`, `_st_3d_intersects`, `_st_overlaps`, `_st_touches`, `_st_within`, `_st_d_within: {distance, from, use_spheroid}`, `_st_3d_d_within`. Raster: `_st_intersects_rast`, `_st_intersects_nband_geom: {nband, geommin}`, `_st_intersects_geom_nband: {geommin, nband}`.
- `ltree`: `_ancestor`, `_ancestor_any`, `_descendant`, `_descendant_any`, `_matches` (`lquery`), `_matches_any` (`[lquery]`), `_matches_fulltext` (`ltxtquery`).
- No full-text search operator for `tsvector`. Docs point to custom SQL functions for that.
- MS SQL Server: common ops, `_like`, `_nlike`, and spatial `_st_contains`, `_st_crosses`, `_st_equals`, `_st_intersects`, `_st_overlaps`, `_st_touches`, `_st_within`.
- BigQuery: common ops, `_like`, `_nlike`, `_ilike`, `_nilike`, and `_st_d_within` and other `_st_*` geography ops.

### `order_by` (`[<table>_order_by!]`)

- `order_by: {col: asc}` or a list `order_by: [{a: desc}, {b: asc}]`. Key order in one object is not kept since v2.0. Docs say: one key per object.
- `order_by` enum values: `asc` (nulls last), `asc_nulls_first`, `asc_nulls_last`, `desc` (nulls first), `desc_nulls_first`, `desc_nulls_last`.
- Object relationship: `{author: {name: asc}}`.
- Array relationship: by aggregate only. `{articles_aggregate: {count: desc}}` or `{articles_aggregate: {max: {rating: asc}}}`. Aggregate order ops: `count`, `sum`, `avg`, `max`, `min`, `stddev`, `stddev_samp`, `stddev_pop`, `variance`, `var_samp`, `var_pop`.
- Computed fields (v2.0.2+): scalar computed fields directly, set-returning computed fields by aggregate (`{get_articles_aggregate: {count: asc}}`). Only computed fields without extra arguments.
- `<table>_aggregate` also supports `order_by` on aggregate output (`TableAggOpOrderBy`).
- No ordering by remote relationship fields.

### Aggregates

- `<table>_aggregate(where:, order_by:, limit:, offset:, distinct_on:) { aggregate { ... } nodes { ... } }`. Also `<array_rel>_aggregate` as a nested field.
- `aggregate` fields: `count(columns: [select_column!], distinct: Boolean)`, `sum`, `avg`, `max`, `min`, `stddev`, `stddev_samp`, `stddev_pop`, `variance`, `var_samp`, `var_pop`. Each numeric op returns an object with a field per numeric column. `max`/`min` also work on text and dates.
- Aggregate access needs `allow_aggregations: true` in the role's select permission.
- Undocumented: `group_by` on `<table>_aggregate` behind experimental feature `group_by_aggregations` (Postgres only, in source `Hasura/GraphQL/Schema/Select.hs`). Shape: `group_by(keys: [<table>_group_by_key!]!) { group_key { ... } aggregate { ... } }`. The key input is `{column: <table>_select_column}`. Not in the docs and not in the flags reference list.
- No `HAVING`. No grouping in GA v2 except the experimental `group_by`. Docs point to views and SQL functions for advanced aggregation.

## v2 mutations

- `insert_<table>(objects: [<table>_insert_input!]!, on_conflict: <table>_on_conflict) { affected_rows returning { ... } }`.
- `insert_<table>_one(object: <table>_insert_input!, on_conflict:)` returns the row. Needs select permission.
- Nested inserts: `{author: {data: {...}, on_conflict: ...}}` for object relationships, `{articles: {data: [...], on_conflict: ...}}` for array relationships. Many-to-many goes through the bridge table. `insertion_order` on manual relationships controls parent/child order.
- Upsert (Postgres): `on_conflict: {constraint: <table>_constraint!, update_columns: [<table>_update_column!]!, where: <table>_bool_exp}`. Empty `update_columns` means "do nothing". Partial unique indexes cannot be used. Needs update permission on the table.
- Upsert (MS SQL Server): `if_matched: {match_columns, update_columns, where}`. Uses `MERGE`.
- `update_<table>(where: bool_exp!, _set:, _inc:, _append:, _prepend:, _delete_key:, _delete_elem:, _delete_at_path:) { affected_rows returning }`. At least one operator is required.
- `update_<table>_by_pk(pk_columns: {...}, _set:, ...)` returns the row.
- `update_<table>_many(updates: [{where:, _set:, _inc:, ...}])` (v2.10+). Results in order. All in one transaction. Hide with experimental `hide_update_many_fields`.
- JSONB update ops: `_append`, `_prepend`, `_delete_key: {col: "key"}`, `_delete_elem: {col: index}`, `_delete_at_path: {col: ["path"]}`. `_inc` for numeric columns.
- `delete_<table>(where: bool_exp!) { affected_rows returning }`. `delete_<table>_by_pk(<pk>: value)`.
- `where` is required on bulk update and delete. `{}` deletes or updates all rows the role can see.
- No nested updates or nested deletes (GitHub issue #1573 is open).
- Multiple top-level mutations in one request run in sequence in one transaction (Postgres and MSSQL). If a remote schema or action field is in the same request, there is no rollback for it.
- Insert/update validation: permission `check` (post-insert/update row check), column presets, Postgres constraints and triggers. Input validation webhook `validate_input` (v2.29+): `{type: http, definition: {url, headers, forward_client_headers, timeout}}` on insert/update/delete permissions. It runs before the mutation and can reject it with a message.
- `no_null_unbound_variable_default`: experimental. Unbound nullable variables are omitted instead of set to NULL.
- Backend-specific: BigQuery has no mutations. MSSQL has `if_matched`. Data connectors support mutations per agent capability.

## v2 authentication

- No built-in user store, login or token issuing. Hasura only verifies and maps identity.
- Session variables: headers/claims named `x-hasura-*` (case-insensitive). `x-hasura-role` picks the role. `x-hasura-user-id` is the common one. Any custom `x-hasura-*` value can be used in permissions and presets.
- Admin secret: `HASURA_GRAPHQL_ADMIN_SECRET`, sent as `x-hasura-admin-secret`. With it, the request can pick any role with `x-hasura-role` and pass any session variables. `--disable-admin-secret` (2.50) turns header auth off. Multiple admin secrets for rotation: `HASURA_GRAPHQL_ADMIN_SECRETS` `[Cloud/EE]`.
- JWT mode: `HASURA_GRAPHQL_JWT_SECRET` JSON config. Fields: `type` (HS256/384/512, RS256/384/512, Ed25519, ES256/384/512), `key`, `jwk_url` (JWKS with refresh by `Cache-Control`/`Expires`), `claims_namespace`, `claims_namespace_path`, `claims_format` (`json` or `stringified_json`), `audience`, `issuer`, `extra_required_claims`, `claims_map` (JSONPath into the token with defaults), `allowed_skew`, `header` (`{type: Authorization}` or `{type: Cookie, name}`). Claims: `x-hasura-allowed-roles`, `x-hasura-default-role`, `x-hasura-*`. Multiple JWT secrets: `HASURA_GRAPHQL_JWT_SECRETS` `[Cloud/EE]`.
- Webhook mode: `HASURA_GRAPHQL_AUTH_HOOK`, `HASURA_GRAPHQL_AUTH_HOOK_MODE` (`GET` or `POST`). The hook returns 200 with session variables or 401. `Cache-Control`/`Expires` in the response. Webhook result caching is `[Cloud/EE]`. `HASURA_GRAPHQL_AUTH_HOOK_SEND_REQUEST_BODY`. The `x-hasura-role` header can be forwarded to the hook. Websocket connections are closed when the session expires.
- Unauthenticated role: `HASURA_GRAPHQL_UNAUTHORIZED_ROLE` for requests without credentials.
- `HASURA_GRAPHQL_PRESERVE_401_ERRORS` (2.48) returns HTTP 401 instead of 200 for auth errors.
- Only one auth mode at a time (JWT or webhook), plus admin secret.

## v2 authorization (permissions)

- Role based. Permissions are per table, per role, per operation: `select`, `insert`, `update`, `delete`. Defined in metadata (`pg_create_select_permission` and similar, or `create_select_permission` per backend). The `admin` role bypasses all.
- Each role gets its own generated GraphQL schema. Fields, types and root fields the role cannot use are not in its schema or introspection.
- Row-level (`filter`): a boolean expression in the same grammar as `where`. Values can be static or session variables (`"X-Hasura-User-Id"`). Session variables that hold arrays work with `_in`, `_nin`, `_has_keys_any`, `_has_keys_all`.
- Row filters can traverse relationships (`{author: {id: {_eq: "X-Hasura-User-Id"}}}`), array relationships ("any"), and remote source relationships (v2.33+, with limits).
- `_exists: {_table: {schema, name}, _where: ...}` checks unrelated tables or views.
- Column comparison operators `_ceq`, `_cne`, `_cgt`, `_clt`, `_cgte`, `_clte` compare two columns. `["$", "col"]` references the root table from inside a relationship filter.
- Undocumented aliases in the Postgres permission parser (`Hasura/Backends/Postgres/DDL/BoolExp.hs`): every operator also has a Mongo-style `$` form (`$eq`, `$in`, `$ceq`, ...). `_ne` and `_neq` both work. `_cneq` is an alias for `_cne`. The docs list `_ne` in the permissions page but `_neq` in the query reference.
- Column-level (`columns`): list of columns per role per operation. `"*"` means all. Also `computed_fields` for select.
- Insert permission: `check` (row check on the new row), `columns`, `set` (column presets), `backend_only`, `validate_input`.
- Update permission: `filter` (pre-update), `check` (post-update), `columns`, `set`, `backend_only`, `validate_input`.
- Delete permission: `filter`, `backend_only`, `validate_input`.
- Select permission: `filter`, `columns`, `computed_fields`, `limit` (row fetch limit), `allow_aggregations`, `query_root_fields`, `subscription_root_fields` (root field visibility, v2.8+).
- Root field visibility: `query_root_fields: ["select", "select_by_pk", "select_aggregate"]`, `subscription_root_fields: [..., "select_stream"]`. Empty list hides the table at root. It stays reachable through relationships.
- Column presets (`set`): fill columns from session variables or static values on insert/update. Preset columns are removed from the role's input types.
- Backend-only mutations: `backend_only: true` on insert/update/delete. Visible only with admin secret and `x-hasura-use-backend-only-permissions: true`. Update/delete support since v2.8.
- Inherited roles: `add_inherited_role {role_name, role_set: [...]}`. Select permissions are combined: rows are ORed, columns become cell-level (null where the row's role does not grant the column), limit is the max, aggregation is allowed if any role allows it. Mutation and remote schema permissions are only inherited when all roles agree. Explicit permissions override. No cycles.
- `optimize_permission_filters` experimental feature: deduplicates permission filters in SQL.
- Function permissions: `pg_create_function_permission`. By default functions inherit table select permissions (`HASURA_GRAPHQL_INFER_FUNCTION_PERMISSIONS`, default true).
- Remote schema permissions: per-role SDL subset with `@preset(value:, static:)` argument presets (`add_remote_schema_permissions`). Needs `HASURA_GRAPHQL_ENABLE_REMOTE_SCHEMA_PERMISSIONS`.
- Action permissions: per-role allow list (`create_action_permission`).
- Not supported: field-level custom logic in permissions (no code). Attribute or policy engines are not built in. Permission checks on remote relationship fields are limited.

## v2 subscriptions

- Any query becomes a subscription by changing `query` to `subscription`. Same arguments and permissions. Only one root field per subscription.
- Transport: WebSocket only, at `/v1/graphql`. Both `subscriptions-transport-ws` (default) and `graphql-ws` (`graphql-transport-ws`) protocols. Chosen by `Sec-WebSocket-Protocol`. No SSE. No HTTP multipart subscriptions.
- Headers go in `connectionParams` (`connection_init` payload). Cookies are read on the WebSocket handshake under CORS rules. `HASURA_GRAPHQL_WS_READ_COOKIE` forces cookie reading.
- Live queries: poll-based, not WAL/trigger-based. The full result is re-run every `HASURA_GRAPHQL_LIVE_QUERIES_MULTIPLEXED_REFETCH_INTERVAL` (default 1000 ms). A response is sent only if the result hash changed.
- Multiplexing: subscriptions with the same role, same query shape and only different variable values are batched into one SQL query using a `VALUES` list of variables. Batch size `HASURA_GRAPHQL_LIVE_QUERIES_MULTIPLEXED_BATCH_SIZE` (default 100). Aliases or different input object keys stop multiplexing.
- Cohorts: subscribers with the same variables and session variables share one result row.
- Streaming subscriptions (v2.7+, `<table>_stream`): `<table>_stream(batch_size: Int!, cursor: [<table>_stream_cursor_input]!, where: <table>_bool_exp)`. Cursor input: `{initial_value: {<col>: value}, ordering: ASC | DESC}`. Server keeps the cursor per subscriber. No sticky sessions needed. Config: `HASURA_GRAPHQL_STREAMING_QUERIES_MULTIPLEXED_BATCH_SIZE`, `HASURA_GRAPHQL_STREAMING_QUERIES_MULTIPLEXED_REFETCH_INTERVAL`. Non-unique cursor columns can give larger batches (`WITH TIES`) or skipped rows on CockroachDB. Hide with experimental `hide_stream_fields`.
- `remove_empty_subscription_responses` experimental: do not send `null`/`[]` results.
- Backend support: live queries on Postgres, Citus, CockroachDB, MSSQL (no row updates subscription on MSSQL per the feature table). No subscriptions on BigQuery. Streaming only on Postgres-like backends.
- Subscriptions on actions: only async actions (`<action>` result via subscription). Subscriptions on remote schemas are not supported. Subscriptions with remote relationships are supported (I think since v2.0, via remote joins on each poll).
- Bounded websocket send queues: `HASURA_GRAPHQL_WEBSOCKET_QUEUE_SIZE` (2.50.x). Over capacity cancels the subscription with an error.
- `HASURA_GRAPHQL_WEBSOCKET_KEEPALIVE`, `HASURA_GRAPHQL_WEBSOCKET_CONNECTION_INIT_TIMEOUT`.
- Subscription metrics and worker views `[Cloud/EE]`.
- No event-based (pub/sub) subscriptions for arbitrary custom events. No subscription filtering beyond `where`.

## v2 actions (custom business logic)

- Actions add custom query or mutation root fields backed by an HTTP webhook. Defined in SDL (`metadata/actions.graphql`) plus `actions.yaml` (`create_action`).
- `ActionDefinition`: `arguments`, `output_type` (object or list of objects, or scalar list), `kind: synchronous | asynchronous`, `type: mutation | query`, `handler` (URL, env templating `{{ACTION_BASE_ENDPOINT}}/path`), `headers` (`value` or `value_from_env`), `forward_client_headers`, `ignored_client_headers`, `timeout` (default 30 s), `request_transform`, `response_transform`, `comment`.
- Custom types (`set_custom_types`): object, input object, scalar, enum. Nested objects since v2.2. No interfaces or unions in custom types.
- Handler request payload: `{action: {name}, input: {...}, session_variables: {...}, request_query}`. Session variable keys are lowercase. Success is 2xx with the output type. Error is 4xx with `{message, extensions: {code, ...}}`.
- Header precedence: client headers > session `x-hasura-*` > configured headers. A flag can flip this order. Handlers are secured by an "action secret" header pattern (no built-in signing).
- Async actions: only for mutations. The mutation returns an `action_id` (UUID). The result is fetched with a generated query or subscription `<action>(id: uuid!)` that returns `{id, created_at, errors, output}`. Logs in `hdb_catalog.hdb_action_log`. Manual cleanup. Async actions keep the trace context since 2.50 `[Cloud/EE]`.
- Action permissions: `create_action_permission {action, role}`. Plain allow per role. No row logic.
- Action relationships: from action output types to Postgres tables (`relationships` on custom object types: `type: object | array`, `remote_table`, `field_mapping`). Not to remote schemas. Only non-list scalar fields can be join keys.
- REST connectors (request/response transforms, v2.1+): Kriti templating language. Transforms `method`, `url`, `query_params`, `request_headers` (`add_headers`, `remove_headers`), `body` (`action: transform | remove | x_www_form_urlencoded`, `template`, `form_template`). Response body transform. Context variables `$body`, `$session_variables`, `$base_url`, `$query_params`.
- Derive actions: Console generates action types and handler code from an existing mutation, so validation can wrap a generated mutation.
- Import action from OpenAPI spec (Console).
- Action codegen: Console/CLI generate handler boilerplate (`hasura actions codegen`) for frameworks like `nodejs-express`, `typescript-zeit`, `python-flask` and more.
- Mutations with actions and DB fields in one request are not one transaction.
- Kriti templating (`api-reference/kriti-templating.mdx`): `{{ }}` expressions, `if`/`else`, `range` loops, functions `empty`, `size`, `inverse`, `head`, `tail`, `toCaseFold`, `toLower`, `toUpper`, `toTitle`, `fromPairs`, `toPairs`, `removeNulls`, `concat`, plus `escapeUri` and `getSessionVariable` in REST connectors. Optional chaining `?.`. Also used in event triggers, scheduled triggers and remote schema customizations.

## v2 remote schemas (schema stitching)

- `add_remote_schema {name, definition: {url | url_from_env, headers, forward_client_headers, timeout_seconds, customization}, comment}`. The remote root fields are merged into the Hasura schema.
- Customization: `root_fields_namespace` (nest under one field), `type_names: {prefix, suffix, mapping}`, `field_names: [{parent_type, prefix, suffix, mapping}]`.
- Schema is cached. Refresh only by `reload_remote_schema` or Console "Reload". No automatic polling.
- Top-level field names must be unique across sources. Types with the same name and structure are merged. Same name with a different structure is an error.
- Not supported: subscriptions on remote schemas. Remote schemas are not on the Relay endpoint.
- Remote schema permissions: per-role restricted SDL (`add_remote_schema_permissions`). Can drop object/interface/input fields, union members, enum values and arguments. `@preset(value: ..., static: Boolean)` injects argument values from session variables (`x-hasura-*`) or static values. Preset arguments leave the role's schema. Needs `HASURA_GRAPHQL_ENABLE_REMOTE_SCHEMA_PERMISSIONS=true`. Without it, every role gets the full remote schema.
- Auth forwarding: `forward_client_headers`, `x-hasura-*` session headers are sent. Remote `Set-Cookie` can pass back to the client.
- `remove_remote_schema` has `cascade` since 2.50.

## v2 remote joins / data federation

- Remote relationships join across sources at the Hasura layer. Types: DB to DB (`to_source`, different databases), DB to remote schema (`to_remote_schema`), remote schema to DB, remote schema to remote schema (GraphQL joins), action to DB.
- `create_remote_relationship {table, name, definition: {to_source: {relationship_type: object | array, source, table, field_mapping}}}` or `{to_remote_schema: {remote_schema, lhs_fields, remote_field: {field: {arguments: {id: "$col"}}}}}`. Remote schema relationships use `create_remote_schema_remote_relationship`.
- Joins are batched: one request per remote source per level.
- Not supported: filtering, ordering or aggregating by remote relationship fields in `where`/`order_by`. Remote relationship predicates are allowed in permissions (v2.33+, data connector backends, limited template).
- Apollo Federation subgraph (v2.10+, experimental `apollo_federation`): tables can be entity types with `@key` on the PK. Action and remote schema types cannot be extended. Federation v1 only. Hasura cannot act as a federation gateway (supergraph router) itself, it composes through remote schemas instead.
- Schema registry: tracks schema diffs per role on each metadata change. Breaking, dangerous and safe change classes. Email and Slack alerts `[Cloud only]`.

## v2 event triggers

- Database change data capture to webhooks. Postgres and MS SQL Server only. Uses DB triggers that write to `hdb_catalog.event_log`, then Hasura polls and delivers.
- `pg_create_event_trigger {name, table, source, webhook | webhook_from_env, insert: {columns}, update: {columns}, delete: {columns}, enable_manual, retry_conf, headers, replace, request_transform, response_transform, cleanup_config, trigger_on_replication}`. MSSQL uses `mssql_create_event_trigger`.
- `OperationSpec`: `columns` (which columns to listen to on update, or `"*"`) and `payload` (which columns to send).
- Delivery: at least once, may be out of order. HTTP `POST`. `2xx` is success. `Retry-After` header on a non-2xx response schedules one more try.
- `retry_conf`: `num_retries` (default 0), `interval_sec` (default 10), `timeout_sec` (default 60).
- Payload: `{id, created_at, trigger: {name}, table: {schema, name}, event: {op: INSERT | UPDATE | DELETE | MANUAL, data: {old, new}, session_variables, trace_context}, delivery_info: {current_retry, max_retries}}`. UPDATE fires only if the row changed. Computed fields are not in the payload. Session variables only on Postgres.
- Manual invoke: `enable_manual: true` plus `pg_invoke_event_trigger` API or the Console button.
- Redeliver failed events: `pg_redeliver_event`. Fetch logs: `pg_get_event_logs`, `pg_get_event_invocation_logs`, `pg_get_event_by_id`.
- Auto cleanup of event logs (v2.13+) `[Cloud/EE]`: `cleanup_config {schedule (cron), clear_older_than (hours), batch_size, timeout, clean_invocation_logs, paused}`. Manual APIs `cleanup_event_trigger_logs`, `pause_event_trigger_cleanups`, `resume_event_trigger_cleanups`.
- Request/response transforms with Kriti (same as actions).
- Tuning: `HASURA_GRAPHQL_EVENTS_HTTP_POOL_SIZE`, `HASURA_GRAPHQL_EVENTS_FETCH_BATCH_SIZE`, `HASURA_GRAPHQL_EVENTS_FETCH_INTERVAL`. Redact payloads in logs: `HASURA_GRAPHQL_REDACT_EVENT_TRIGGER_LOGS`. Disable all eventing: `HASURA_GRAPHQL_DISABLE_EVENTING` (2.49).
- Observability of event triggers (metrics, Prometheus) `[EE]`.
- Not supported: events for BigQuery and data connectors. No exactly-once delivery. No ordering guarantee.

## v2 scheduled triggers (cron and one-off)

- Cron triggers: `create_cron_trigger {name, webhook, schedule (cron, UTC), payload, headers, retry_conf, include_in_metadata, comment, request_transform, response_transform, replace}`. `retry_conf` adds `tolerance_seconds` (default 6 hours) for missed events. `delete_cron_trigger`, `get_cron_triggers`.
- One-off scheduled events: `create_scheduled_event {webhook, schedule_at (ISO timestamp), payload, headers, retry_conf, comment}`. `delete_scheduled_event`, `get_scheduled_events`, `get_scheduled_event_invocations`.
- Delivery has about 10 seconds jitter (polled). Logs in `hdb_catalog.hdb_cron_events`, `hdb_cron_event_invocation_logs`, `hdb_scheduled_events`, `hdb_scheduled_event_invocation_logs`. Cleanup is manual SQL.
- I think the webhook payload is `{scheduled_time, payload, name, id, comment}`. I did not check this.
- Cron triggers can be created from the Console without being part of metadata (`include_in_metadata: false`).

## v2 caching `[Cloud/EE]`

- Response cache via `@cached(ttl: Int = 60, refresh: Boolean = false)` query directive. Max TTL 300 s on Cloud. Self-hosted EE uses Redis (`HASURA_GRAPHQL_REDIS_URL`) and `HASURA_GRAPHQL_CACHE_MAX_ENTRY_TTL`.
- Cache key: hash of query text (whitespace ignored), operation name, variables, role and only the session variables used by the query's permissions, plus headers for actions/remote schemas with `forward_client_headers`.
- Works for DB queries, actions and remote schemas.
- Response headers: `X-Hasura-Query-Cache-Key`, `X-Hasura-Query-Family-Cache-Key`, `Cache-Control: max-age=N`.
- Invalidation only by TTL or manual clear: `POST /pro/cache/clear`, `?key=`, `?family=` (all variables). No mutation-based invalidation.
- Cache writes are rate-limited (token bucket, `HASURA_GRAPHQL_CACHE_BUCKET_RATE`, `HASURA_GRAPHQL_CACHE_BUCKET_SIZE`). `HASURA_GRAPHQL_CACHE_MAX_ENTRY_SIZE`. Cache metrics in Prometheus.
- Query plan caching exists internally in CE. Separate from response caching.
- Automated Persisted Queries (Apollo APQ): `HASURA_GRAPHQL_ENABLE_PERSISTED_QUERIES` and a TTL flag `[EE]`. Only in the flags reference. Not described elsewhere in the docs.

## v2 security and API limits

- Allow list: `HASURA_GRAPHQL_ENABLE_ALLOWLIST`. Only operations stored in query collections that are added to the allow list can run. Admin role is exempt. Field order is compared strictly. `__typename` is ignored. Introspection must be added explicitly. Query collections API: `create_query_collection`, `add_query_to_collection`, `add_collection_to_allowlist {collection, scope: {global, roles}}`. Role-based allow list (`scope.roles`) is `[Cloud/EE]`. In OSS role-based entries are ignored.
- API limits `[Cloud/EE]` (`set_api_limits`): `rate_limit` (`max_reqs_per_min`, `unique_params: "IP" | [session vars]`, Redis backed), `depth_limit`, `node_limit`, `time_limit` (seconds, cancels Postgres queries), `batch_limit` (operations per batched request). Each has `global` and `per_role`. `disabled: Boolean`. Admin is exempt. Depth limit skips introspection.
- No cost or complexity analysis. Depth and node limits are the only static checks.
- Disable introspection per role: `set_graphql_schema_introspection_options {disabled_for_roles: [...]}`. Free in CE.
- Maintenance mode `HASURA_GRAPHQL_ENABLE_MAINTENANCE_MODE`, `HASURA_GRAPHQL_ENABLED_APIS` (turn off metadata, graphql, pgdump, config, metrics APIs), CORS (`HASURA_GRAPHQL_CORS_DOMAIN`, `HASURA_GRAPHQL_DISABLE_CORS`), `HASURA_GRAPHQL_ADMIN_INTERNAL_ERRORS`, dev mode (`HASURA_GRAPHQL_DEV_MODE`) adds internal error details.
- Dynamic secrets: DB URLs read from files (`dynamic-from-file:///path`), `HASURA_GRAPHQL_DYNAMIC_SECRETS_ALLOWED_PATH_PREFIX`. Template variables in connection strings.
- `HASURA_GRAPHQL_LOG_MASKED_VARIABLES`: mask variables in query logs. `HASURA_GRAPHQL_REDACT_*_LOGS` for events, scheduled triggers and action handlers.
- Max header size `HASURA_GRAPHQL_MAX_TOTAL_HEADER_LENGTH`. Request timeout `HASURA_GRAPHQL_SERVER_TIMEOUT` (2.48).
- SSO for the Console (`HASURA_GRAPHQL_SSO_PROVIDERS`) `[EE]`.

## v2 RESTified endpoints

- `create_rest_endpoint {name, url, methods: [GET | POST | PUT | PATCH | DELETE], definition: {query: {query_name, collection_name}}, comment}`. A saved GraphQL operation is served at `/api/rest/<url>`.
- URL path variables `:id` map to GraphQL variables. Query string and JSON body also map to variables.
- Console can create CRUD endpoints for a table in one step (`READ`, `READ ALL`, `CREATE`, `UPDATE`, `DELETE`).
- OpenAPI 3 spec export at `/api/swagger/json`, admin only (Console "Export OpenAPI Spec").
- Not supported: subscriptions as REST endpoints.
- `@cached` works on RESTified endpoints and adds HTTP cache headers.

## v2 transport, API surface and operations

- Endpoints: `/v1/graphql` (POST, and WebSocket), `/v1/relay`, `/v1/metadata` (metadata API), `/v2/query` (schema API: `run_sql`), `/v1/graphql/explain` (Explain API, admin only, returns SQL plans for a query and role), `/api/rest/*`, `/v1/version`, `/healthz`, `/hasura/healthz?strict=true`, `/v1/config`, `/v1alpha1/pg_dump`, `/v1/metrics` (Prometheus) `[EE]`, `/v1alpha1/graphql` (legacy, returns 4xx/5xx on errors).
- `/v1/graphql` always returns HTTP 200, also on errors. `HASURA_GRAPHQL_PRESERVE_401_ERRORS` changes this for 401.
- Batched requests: a JSON array of operations in one POST. Limited by `batch_limit` `[Cloud/EE]`.
- Error format: `{errors: [{message, extensions: {path, code, internal?}}]}`. Codes (from `lib/hasura-base/src/Hasura/Base/Error.hs`) include `validation-failed`, `constraint-violation`, `constraint-error`, `data-exception`, `permission-error`, `permission-denied`, `access-denied`, `invalid-jwt`, `jwt-invalid-claims`, `jwt-missing-role-claims`, `invalid-headers`, `parse-failed`, `not-supported`, `not-found`, `remote-schema-error`, `postgres-error`, `unexpected-payload`, `concurrent-update`. The error code list is not documented as a stable list. Internal details only for admin (`HASURA_GRAPHQL_ADMIN_INTERNAL_ERRORS`) or in dev mode.
- Not supported: `@defer`, `@stream`, file uploads (multipart), query cost analysis, custom directives on the generated schema, `@oneOf`.
- `GET /v1/graphql` exists only for APQ. In CE the handler always throws `PersistedQueryNotSupported` (`server/src-lib/Hasura/App.hs`). APQ is implemented only in the EE build.
- Metadata: everything is metadata (JSON/YAML). Managed by the Metadata API (`export_metadata`, `replace_metadata`, `reload_metadata`, `get_inconsistent_metadata`, `drop_inconsistent_metadata`, `bulk`, `bulk_atomic`, `bulk_keep_going`, `test_webhook_transform`), the CLI (`hasura metadata apply/export/diff`, `hasura migrate create/apply/squash/status`, `hasura seed`, `hasura console`, `hasura deploy`, `hasura actions codegen`, `hasura scripts`), and the Console UI.
- Metadata inconsistency handling: inconsistent objects are reported and dropped from the schema instead of failing startup. `--disallow-inconsistent-metadata` on apply.
- Migrations: SQL up/down files, generated by the Console. Seeds. `cli-migrations` Docker image auto-applies on start.
- Multi-instance sync: `HASURA_GRAPHQL_SCHEMA_SYNC_POLL_INTERVAL`. Websockets close on metadata change by default (`HASURA_GRAPHQL_CLOSE_WEBSOCKETS_ON_METADATA_CHANGE`).
- Database config: multiple sources, connection pool settings, `isolation_level`, `use_prepared_statements`, SSL certs, `extensions_schema`. Read replicas `[Cloud/EE]`. Dynamic routing via `connection_set` and a Kriti `connection_template` (per role, header or tenant) `[Cloud/EE]`. Cloud connection pooling `[Cloud]`.
- Observability: structured JSON logs with log types (`http-log`, `websocket-log`, `query-log`, `livequery-poller-log`, `event-trigger`, ...). Query tags as SQL comments (`standard`, `standard_prepended`, `sqlcommenter` formats, `set_query_tags`) `[Cloud/EE]`. OpenTelemetry traces (v2.18+), metrics (v2.31+), logs (v2.35+) `[Cloud/EE]`. Prometheus metrics and Grafana dashboards `[EE]`. Cloud monitoring UI with operations, errors, websockets, subscription workers, usage, alerting `[Cloud]`. Datadog, New Relic, Azure Monitor integrations `[Cloud]`.
- Health: source health checks `[Cloud/EE]`. `/healthz`.
- Query collections, RESTified endpoints and allow lists share the same stored operations.
- Cloud-only tooling: preview apps, GitHub integration, regression tests (replay captured operations against a new schema), one-click deploy, schema registry, environments, SSO, VPC peering, high availability `[Cloud]`.
- `hasura` CLI gateway plugin (alpha) `[Cloud]` checks and publishes metadata of child Hasura instances in a federated setup.
- Console: database browser, SQL runner, permission builder, GraphiQL with explorer and query analyzer ("Analyze" shows SQL), data modelling UI.

## v2 data sources and backend features

- `pg_add_source`, `mssql_add_source`, `bigquery_add_source`, data connector sources (`<agent>_add_source`). `dc_add_agent` registers a custom data connector agent (HTTP). Data Connector agent spec is in `dc-agents/` (TypeScript reference agent, SQLite agent).
- Native queries on Postgres are free. Snowflake, MySQL, MariaDB, Oracle, MongoDB, ClickHouse, Athena, Redshift and BigQuery native queries are behind `[Cloud/EE]` badges. I think the Super Connector (JDBC) is EE only.
- Postgres views (with `update` permissions if updatable). Postgres functions as root fields and computed fields. Enum tables.
- Vector databases (Weaviate) via data connectors (docs `databases/vector-databases`).
- Feature matrix per backend in `databases/feature-support.mdx`.

- Postgres-compatible backends: Citus, CockroachDB, Cosmos DB for Postgres, AlloyDB, Aurora, Neon, Supabase, Timescale, Yugabyte. Each has a compatibility page with gaps.
- Feature gaps by backend (from `databases/feature-support.mdx`): BigQuery has no mutations, no subscriptions, no event triggers, no enums, no custom functions, no Relay. SQL Server has no custom functions, no computed fields, no Relay, no naming conventions, no multiple mutations per request, no streaming subscriptions and no "updates to rows" live queries. CockroachDB has no `distinct_on`, no functions, no event triggers, no remote relationships. Citus has no computed fields and no event triggers.
- Naming conventions (`graphql-default` with camelCase fields and PascalCase types, or `hasura-default` snake_case) are only for Postgres. Set per source (`customization.naming_convention`) or globally with `HASURA_GRAPHQL_DEFAULT_NAMING_CONVENTION`. The docs say the experimental flag `naming_convention` is needed. The code ignores it.
- Database-to-database remote joins: only Postgres to Postgres is fully supported. Other pairs are marked partial.

## v3 / DDN engine (Rust, `v3/` in the same repo)

Hasura DDN ("Data Delivery Network") is the v3 product. The engine is Rust, Apache-2.0 (`v3/Cargo.toml`), and is in `v3/crates/`. Data access goes through NDC data connectors (separate HTTP services). Configuration is "OpenDD" metadata in `.hml` YAML files, authored with the `ddn` CLI and the VS Code extension. There is no Console-driven setup as in v2. Docs: https://hasura.io/docs/3.0/. Versions are dates (latest `v2026.07.15`).

Plans: "DDN Free", "DDN Base", "DDN Advanced", plus Enterprise contracts. In this section `[DDN Base]`, `[DDN Advanced]` and `[Enterprise]` mark paid features. Self-hosting the engine and connectors with Docker or Kubernetes is documented. I think plain Docker self-hosting is free, and the Kubernetes guide is tagged "enterprise ddn".

### Metadata objects (OpenDD)

- `DataConnectorLink` (connector URL, schema, `argumentPresets`, header forwarding), `ScalarType`, `ObjectType` (with `dataConnectorTypeMapping`), `BooleanExpressionType`, `OrderByExpression`, `AggregateExpression`, `Model` (v1, v2), `Command`, `Relationship`, `TypePermissions`, `ModelPermissions`, `CommandPermissions`, `AuthConfig` (v1 to v4), `GraphqlConfig`, `CompatibilityConfig`, `LifecyclePluginHook`, `View` (SQL view definition), `PromptQlConfig` (v1, v2).
- Supergraph and subgraphs: metadata is split into subgraphs (modules owned by teams). Cross-subgraph relationships. Multi-repo subgraphs and subgraph roles `[DDN Advanced]`.
- Builds are immutable. `ddn supergraph build create`, `ddn supergraph build apply`. Incremental builds. Schema diff between builds in the Console.
- `CompatibilityConfig` date pins behaviour flags (for example `disallow_order_by_fields_with_field_arguments`, `disallow_literals_as_boolean_expression_arguments`, `fix_exists_in_nested_arrays`). New behaviour is opt-in by date.
- Model = a collection (table, view, native query, or connector function with arguments). Command = a function (query root) or procedure (mutation root).
- Field arguments on object type fields. Model arguments (`args` input). Global ID source per model (`globalIdSource`).
- Native queries and native mutations are defined in the connector configuration (Postgres, MongoDB, ClickHouse, and others). Native mutations exist in DDN but not in v2.

### GraphQL API grammar (differences from v2)

- Root fields are named in metadata (`selectMany.queryRootField`, `selectUniques[].queryRootField` with `uniqueIdentifier`, `aggregate.queryRootField`). CLI defaults are camelCase: `authors`, `authorsById`, `authorsAggregate`. v2 uses snake_case `authors`, `authors_by_pk`, `authors_aggregate` by default.
- Argument names come from `GraphqlConfig`: `where`, `order_by`, `limit`, `offset`, `args`, and operator names `_and`, `_or`, `_not`, `_is_null`. They are configurable. In v2 they are fixed.
- Filter (`where`): the `BooleanExpressionType` decides which fields, relationships and operators exist (`comparableFields`, `comparableRelationships`, `logicalOperators.enable`, `isNull.enable`). Scalar operators come from the connector (`_eq`, `_neq`, `_gt`, `_lt`, `_gte`, `_lte`, `_in`, `_like`, `_ilike`, ...). `dataConnectorOperatorMapping` renames them. No v2-style fixed operator list. No `_cast`, no JSONB or PostGIS operator set unless the connector provides it.
- Filter on nested object fields and on relationships (object and array). Remote relationships in predicates (filtering across connectors) are resolved by the engine.
- Aggregation predicates in filters (`objectAggregate` / `scalarAggregate` operands, filter by `_count` of a relationship) exist in code. They need the engine flag `--unstable-feature enable-aggregation-predicates` (`v3/crates/engine/src/internal_flags.rs`).
- Order by: `order_by: [<Model>_order_by!]`, values `Asc` and `Desc` (enum names configurable). No `asc_nulls_first` / `desc_nulls_last` variants. Order by relationship fields and nested object fields. `OrderByExpression` restricts orderable fields and directions per type (for example only `Asc`).
- No `distinct_on` in the GraphQL schema.
- Pagination: `limit` and `offset` only. No cursor pagination and no Relay connections.
- Aggregates: a separate root field (`<model>Aggregate`) and relationship aggregate fields. Input is `filter_input: {where, order_by, limit, offset}` (name configurable). Output is `_count`, `_count_distinct`, and per field functions defined by the connector (`_sum`, `_avg`, `_min`, `_max`, ...). v2 uses `<table>_aggregate { aggregate { count sum { col } } nodes }`. DDN has no `nodes` field.
- Group by: not in the GraphQL API. `Model.uniqueIdentifiers` (v2026.03.25) is for "grouping operations" on other interfaces.
- Mutations: no generic insert/update/delete grammar in the engine. Mutations are commands (procedures). Some connectors (Postgres) auto-generate procedures such as `insertUsers(objects: [...])`, `updateUsersById(keyId: ..., updateColumns: {age: {set: ...}})`, `deletePostsById(keyId: ...)`, with `affectedRows` and `returning`. Other mutations come from native mutations or lambda connectors. No upsert `on_conflict` grammar, no nested inserts and no `_inc` / `_append` operators in the engine itself.
- Remote joins also run from mutation (procedure) results.
- Global IDs: `id` field and `node(id:)` root field. This is the only Relay part. Full Relay API is "WIP".
- Apollo Federation: `_entities` and `_service` root fields (`GraphqlConfig.apolloFederation.enableRootFields`, per-model `apolloFederation.entitySource`). DDN can be an Apollo subgraph.
- `@deprecated` on root fields, fields and relationships via metadata `deprecated`.

### v3 subscriptions

- Subscriptions are in beta (free during beta). Live queries by polling only (`subscription.pollingIntervalMs`, default 1000 ms). Available on select many, select unique and aggregate root fields.
- `allowSubscriptions` in `ModelPermissions.select` per role.
- WebSocket protocol is `graphql-transport-ws` only (`v3/crates/graphql/graphql-ws`). v2 also supports the old `graphql-ws` (Apollo) protocol.
- No streaming subscriptions (WIP per docs).

### v3 authentication and authorization

- `AuthConfig` v4 modes: `jwt`, `webhook` (GET or POST), `noAuth` (fixed role and session variables). `alternativeModes` lets one project accept several modes. `sessionVariableToTraceAttributeMap` adds session values to OpenTelemetry traces.
- No admin secret in DDN. Roles come from JWT claims or the webhook. Optional `x-hasura-role` header picks a role (v2026.03.25).
- `TypePermissions`: per role output field allow list and `input.fieldPresets` (preset input fields from session variables).
- `ModelPermissions`: per role `select.filter` (a predicate tree with `fieldComparison`, `fieldIsNull`, `nestedField`, `relationship`, `and`, `or`, `not`), `argumentPresets`, `allowSubscriptions`. `relationalInsert`, `relationalUpdate`, `relationalDelete` are permission slots for the relational (SQL) API.
- `CommandPermissions`: per role `allowExecution` and `argumentPresets`. Argument presets can inject a boolean expression into a command argument.
- Rules-based permissions (`TypePermissions` / `ModelPermissions` / `CommandPermissions` version `v2` with `permissions.rulesBased`) exist in code (`v3/crates/open-dds/src/authorization.rs`, `v3/crates/auth/authorization-rules`). Rules are `allowFields` / `denyFields`, `allow` / `deny`, presets, each with a `condition` (`and`, `or`, `not`, `equal`, `contains`, `greaterThan`, `lessThan`, `isNull`, ...) on session variables and literals.
- No column-level insert or update check grammar as in v2 (`check`, `set`, `columns` per operation). Mutation authorization is done in connector code, argument presets and command permissions.

### v3 other APIs and operations

- `POST /graphql`, `GET /graphql` for WebSockets, `POST /v1/explain` (query plan), `GET /health`, `/metadata` and `/metadata-hash` (dev).
- JSON:API (`/v1/jsonapi`, alias of the older `/v1/rest`) is in alpha. It is generated from models. Query parameters: `filter={"field":{"$eq":5}}` with `$and` / `$or`, `sort=-field`, `page[limit]` / `page[offset]`, `include=rel.path`, sparse `fields[...]`. OpenAPI schema at `/__schema`.
- SQL interface (`/v1/sql`) is mentioned in `v3/CLAUDE.md` and the changelog. Its code is in `crates/cloud/`, which is not in the public repo. I think it is a Cloud or PromptQL-only feature.
- Engine plugins (HTTP hooks) via `LifecyclePluginHook`: `pre-parse`, `pre-response`, `pre-route`, `pre-ndc-request`, `pre-ndc-response`. Plugins can rewrite the request, short-circuit with a response, or fail gracefully (`onPluginFailure`). Multiple HTTP status codes in plugin responses.
- Allow list, caching (Redis), rate limit and RESTified endpoints are separate open-source plugin services (`hasura/engine-plugin-*`), not engine features. v2 has them built in.
- Business logic: lambda connectors in TypeScript (`ndc-nodejs-lambda`), Python and Go. Functions become commands. The OpenAPI connector and the GraphQL connector replace v2 actions and remote schemas.
- Request limits: `REQUEST_BODY_LIMIT` (default 10 MB). Connector response limit `NDC_RESPONSE_SIZE_LIMIT` (default 30 MB). No depth or node limits (docs: API limits not supported).
- CORS config with wildcard subdomains. OpenTelemetry traces. Query usage analytics (`v3/crates/query-usage-analytics`).
- Observability in the DDN Console: traces, model analytics, API usage trends `[DDN Base]`. Team analytics `[DDN Advanced]`.
- Private DDN (dedicated or BYOC data planes, private endpoints) `[Enterprise]`.
- PromptQL (natural language to query plans over the supergraph) is "contact us" `[Enterprise]` in the docs. `PromptQlConfig` is in the metadata.
- Not in DDN (docs "feature availability" page): cron triggers, admin secret, event triggers (WIP), streaming subscriptions (WIP), API limits (WIP), full Relay API (WIP).

## Not supported

v2:
- Code-first schema or in-process resolvers. All custom logic is outside the engine: actions (webhooks), remote schemas, SQL functions, event triggers.
- `@defer`, `@stream`, `@oneOf`, file uploads (multipart). Custom directives on the generated schema (only built-in `@cached`, `@preset` in remote schema permissions, `@include`/`@skip`).
- Query cost or complexity analysis in CE. Depth and node limits are `[Cloud/EE]`.
- GA `GROUP BY` and `HAVING`. Only the hidden `group_by_aggregations` experiment.
- Cursor pagination outside the Relay endpoint. `distinct_on` on SQL Server and CockroachDB is partial or missing.
- Interfaces and unions in generated table types and in action custom types. They exist only through remote schemas.
- Filtering, ordering or aggregating on remote relationship fields in user `where` / `order_by`.
- Subscriptions on remote schemas and on sync actions. SSE transport. Mutations, subscriptions and events on BigQuery.
- Exactly-once or ordered event delivery.
- Apollo Federation v2 directives. Hasura is a v1 subgraph only and cannot be a federation gateway.
- Built-in policy engines (ABAC with external policy), and code in permission rules.
- Translations / i18n of schema descriptions.

v3 / DDN (from the feature-availability page and the engine code):
- Cron triggers. Admin secret.
- Event triggers, streaming subscriptions, API limits (depth, node, rate in engine), and Relay cursor connections are "WIP".
- `distinct_on`, `asc_nulls_first`-style ordering, cursor pagination, GraphQL group by.
- Generic insert/update/delete/upsert grammar in the engine. It depends on the connector.
- Built-in allow list, caching, rate limits and RESTified endpoints. These are external plugins.
- `graphql-ws` (Apollo legacy) WebSocket protocol. Only `graphql-transport-ws`.
- `@defer`, `@stream`, file uploads.

## Upcoming and unreleased work

- v2 is in maintenance. Most 2026 releases are fixes, security and performance. `v2.50` is the newest LTS line ("Planned LTS support is through December 2028", `policies/versioning.mdx`). `v2.45` LTS until December 2027. LTS lines are for Enterprise customers `[EE]`.
- v2 open PRs (2026): "server: interpret writer effects with the CPS writer" (#10885, internal refactor), console RegExp escaping fix (#10871), "Remove __typename from inline fragments in allowlist normalization" (#10769), "Improve relationship nullability and joins without LATERAL" (#10712, open since 2025-03).
- v3 `[Unreleased]` in `v3/changelog.md`: artifact client auth with Kubernetes service-account tokens (`ARTIFACTS_AUTH_TOKEN_FILE`), models with arguments exposed as table-valued functions in the SQL schema, dependency security bumps.
- v3 unstable feature in code: `--unstable-feature enable-aggregation-predicates` (filter by aggregates of related rows).
- v3 rules-based permissions (`permissions.rulesBased`, `Condition` trees) are in code and changelog fixes (v2026.04.23), but not in the published docs. Open RFC PR "[RFC][v3] Authorization Rules in V3" (#10237).
- Open v3 RFC PRs (old, not merged): "REST API output on Hasura v3" (#10475), "Supergraph Client RFC" (#10311), "Presets in Permissions" (#10112), "allow adding description to metadata objects" (#10102). RFCs in repo: `v3/rfcs/aggregations.md`, `multiple-frontends.md`, `open-dd-boolean-expression-types.md`, `support-for-multiple-auth-configs.md`.
- DDN docs mark as WIP: event triggers ("plugin support"), streaming subscriptions, API limits, Relay cursor connections. Relationships from nested object filters to commands are "coming soon" (`graphql-api/queries/filters/nested-objects.mdx`).
- Public roadmap: https://github.com/orgs/hasura/projects/201 (linked from the DDN docs). I did not read it.
- Most v3 changelog entries in 2026 are about PromptQL, auth, tracing and Cloud infrastructure. I think new GraphQL API features in v3 have slowed.

## Docs and code disagree

- v2 `HASURA_GRAPHQL_EXPERIMENTAL_FEATURES`: docs list `inherited_roles`, `naming_convention` and `streaming_subscriptions` as flags, and say the flag is required (`schema/postgres/naming-convention.mdx`, and the WebSocket queue part of `deployment/graphql-engine-flags/reference.mdx` for streaming). The code parses these flags but never checks them (`EFInheritedRoles`, `EFNamingConventions`, `EFStreamingSubscriptions` have no use outside `server/src-lib/Hasura/Server/Types.hs`). These features are always on.
- v2 `group_by_aggregations` experimental feature exists in code (`EFGroupByAggregations`) but is not in the flag docs or any docs page.
- v2 `CHANGELOG.md` in the repo ends at v2.11. Newer release notes are only on GitHub releases.
- v2 `--experimental-features` CLI help text in `Serve.hs` lists only five features ("inherited_roles,optimize_permission_filters and naming_convention, streaming_subscriptions, apollo_federation"). The code accepts 13.
- v2 APQ: `GET /v1/graphql` is routed in CE, but the CE handler always fails with `PersistedQueryNotSupported`. Only the EE build implements it.
- v3 docs (`graphql-api/response-size-limit.mdx`) say the connector response limit is a fixed 30 MB and to contact support to raise it. The engine has `NDC_RESPONSE_SIZE_LIMIT` (default 30 MB) to set it (`v3/crates/engine/bin/engine/main.rs`).
- v3 rules-based permissions (`TypePermissions` / `ModelPermissions` / `CommandPermissions` `v2`) are in the code. The metadata reference documents only `v1`. The JSON schema title of `TypePermissionsV2` is `"TypePermissionsV1"` in `v3/crates/open-dds/src/permissions.rs`.
- v3 aggregation predicates (`objectAggregate` / `scalarAggregate` boolean expression operands) are in the code behind an unstable flag. The docs do not mention them.
- v3 docs `upgrade/feature-availability/api-features.mdx`: the table says "API Limits: WIP", the text says "not supported". The same page says lambda business logic is TypeScript and Python. `business-logic/overview.mdx` says TypeScript, Python and Go.
- v3 docs table says "Relay API: WIP". The engine has global IDs and the `node` root field. Only cursor connections are missing.
- The DDN docs repo was last updated 2026-05-12. Engine changes after that (for example the unreleased SQL table-valued functions) are not in the docs.

## Sources

Repos (clones in `/tmp`):
- https://github.com/hasura/graphql-engine (`/tmp/hasura-graphql-engine`, default branch at `ed6ea94`, 2026-10-07). Paths used: `server/src-lib/Hasura/Server/Types.hs`, `server/src-lib/Hasura/Server/Init/Arg/Command/Serve.hs`, `server/src-lib/Hasura/GraphQL/Schema/NamingCase.hs`, `server/src-lib/Hasura/App.hs`, `lib/hasura-base/src/Hasura/Base/Error.hs`, `docs/docs/` (v2 docs source), `v3/changelog.md`, `v3/CLAUDE.md`, `v3/rfcs/`, `v3/crates/engine/`, `v3/crates/engine/bin/engine/main.rs`, `v3/crates/engine/src/internal_flags.rs`, `v3/crates/graphql/schema/src/`, `v3/crates/graphql/graphql-ws/`, `v3/crates/open-dds/src/` (`permissions.rs`, `authorization.rs`, `boolean_expression.rs`, `plugins.rs`, `views.rs`), `v3/crates/auth/`, `v3/crates/jsonapi/src/endpoint.rs`.
- https://github.com/hasura/ddn-docs (`/tmp/hasura-ddn-docs`, `d2ca0f4`, 2026-05-12). Paths used: `docs/graphql-api/`, `docs/json-api/`, `docs/reference/metadata-reference/` (`models.mdx`, `graphql-config.mdx`, `aggregate-expressions.mdx`, `orderby-expressions.mdx`, `permissions.mdx`, `auth-config.mdx`), `docs/upgrade/feature-availability/api-features.mdx`, `docs/plugins/`, `docs/reference/pricing.mdx`, `docs/private-ddn/overview.mdx`, `docs/deployment/self-hosted/`, `docs/ai/overview.mdx`, `docs/business-logic/overview.mdx`.
- GitHub releases and PRs via `gh`: https://github.com/hasura/graphql-engine/releases (v2.49.0, v2.50.0, v2.50.1, v2.50.3), https://github.com/hasura/graphql-engine/pulls.

v2 docs (https://hasura.io/docs/2.0/, read from `docs/docs/` in the repo):
- https://hasura.io/docs/2.0/databases/feature-support/
- https://hasura.io/docs/2.0/schema/postgres/naming-convention/
- https://hasura.io/docs/2.0/deployment/graphql-engine-flags/reference/
- https://hasura.io/docs/2.0/policies/versioning/
- https://hasura.io/docs/2.0/api-reference/general-info/
- Other v2 pages used by the earlier sections: `queries/`, `mutations/`, `subscriptions/`, `auth/`, `actions/`, `remote-schemas/`, `event-triggers/`, `scheduled-triggers/`, `caching/`, `security/`, `restified/`, `observability/`, `databases/`, `schema/`, `api-reference/` under https://hasura.io/docs/2.0/.

v3 / DDN docs (https://hasura.io/docs/3.0/):
- https://hasura.io/docs/3.0/graphql-api/overview/
- https://hasura.io/docs/3.0/graphql-api/queries/filters/
- https://hasura.io/docs/3.0/graphql-api/queries/sorting/
- https://hasura.io/docs/3.0/graphql-api/queries/pagination/
- https://hasura.io/docs/3.0/graphql-api/queries/aggregation-queries/
- https://hasura.io/docs/3.0/graphql-api/mutations/
- https://hasura.io/docs/3.0/graphql-api/subscriptions/
- https://hasura.io/docs/3.0/graphql-api/global-ids/
- https://hasura.io/docs/3.0/graphql-api/apollo-federation/
- https://hasura.io/docs/3.0/graphql-api/response-size-limit/
- https://hasura.io/docs/3.0/json-api/overview/
- https://hasura.io/docs/3.0/plugins/overview/
- https://hasura.io/docs/3.0/reference/metadata-reference/
- https://hasura.io/docs/3.0/upgrade/feature-availability/api-features/
- https://hasura.io/docs/3.0/reference/pricing/
- https://hasura.io/docs/3.0/private-ddn/overview/
- Changelog: https://hasura.io/changelog
