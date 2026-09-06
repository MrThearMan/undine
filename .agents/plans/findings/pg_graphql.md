# pg_graphql findings

Versions checked: `Cargo.toml` version `1.6.2`. Repo `supabase/pg_graphql` default branch `master` at `51dbdc9` (last commit 2026-10-03). Docs source is in the same repo under `docs/` (mkdocs, 16 pages). Built with pgrx `0.19.2`.
pg_graphql is a Postgres extension written in Rust (pgrx). It reflects a GraphQL schema from the SQL catalog and exposes one SQL function, `graphql.resolve(...)`. There is no HTTP server. Any client that can call SQL can run GraphQL. Configuration is done with SQL: grants, RLS, `search_path` and JSON "comment directives" on SQL objects. Apache-2.0.

## Maintenance status

- Active but slow. 3358 stars. 52 open issues plus PRs. Not archived. Maintained by Supabase staff.
- Recent releases: v1.6.2 (2026-08-26, chores only: pgrx bump, pinned actions), v1.6.1 (2026-05-07), v1.6.0 (2026-04-30), v1.5.12 (2026-01-23), v1.5.11 (2025-02-20), v1.5.9 (2024-10-16).
- `docs/changelog.md` stops at 1.6.1. The `## master` section is empty. 1.6.2 is only on GitHub releases.
- Postgres 14 to 18 supported (cargo features `pg14` ... `pg18`, default `pg18`).
- No `llms.txt` on https://supabase.github.io/pg_graphql/llms.txt (404). Supabase's own docs have https://supabase.com/llms.txt and a markdown page https://supabase.com/docs/guides/graphql.md. That page is a copy of `docs/supabase.md`.

## Architecture: one SQL statement per root field

- Entry: `graphql.resolve(query text, variables jsonb default '{}', "operationName" text default null, extensions jsonb default null) returns jsonb`. It is a plpgsql wrapper around the Rust function `graphql._internal_resolve`. The wrapper catches any SQL exception and returns `{"data": null, "errors": [{"message": ...}]}`.
- Steps inside `_internal_resolve` (`src/lib.rs`): parse with `graphql_parser`. Load config (`search_path`, `current_role`, schema version). Load the SQL context. Build a `__Schema`. Run `resolve_inner`.
- SQL context: one big catalog query `sql/load_sql_context.sql` returns all schemas, tables, columns, types, enums, foreign keys, functions and their privileges as one JSONB. The result is cached in process memory (`cached::SizedCache`, size 250). The cache key is a hash of `search_path` + `current_role` + schema version.
- Schema version: a sequence `graphql.seq_schema_version`. Event triggers `graphql_watch_ddl` (on `ddl_command_end`) and `graphql_watch_drop` (on `sql_drop`) increment it on every DDL. So DDL changes invalidate the cache. Comment changes are DDL too.
- The GraphQL schema is per role and per `search_path`. Different roles see different schemas.
- Each query root field is transpiled to one SQL statement that returns JSONB (`src/transpile.rs`). Root fields in one query run as separate statements, one after the other. Nested relationships and nested connections are correlated subqueries inside the parent `jsonb_build_object(...)`. So one root field, however deep, is one SQL round trip. No N+1. No dataloader.
- Connection SQL shape (`ConnectionBuilder::to_sql`): CTEs `__records` (the page, with filter, cursor clause, `order by`, `limit`, `offset`), `__total_count` (`count(*)` over the filter), `__has_next_page` (fetch `limit + 1`), `__has_previous_page` (checks one row before the page), `__has_records`, `__aggregates`, `__base_object`. Then `jsonb_build_object` builds edges, nodes, pageInfo and aggregates.
- `hasNextPage` and `hasPreviousPage` queries are only built when requested. Otherwise `select null`.
- I think the `__total_count` CTE is always part of the SQL, even when `totalCount` is not selected or not enabled. It is cross joined into `__base_object`. I did not run EXPLAIN to confirm Postgres executes it.
- Variables and literals are passed as SPI parameters (`ParamContext.clause_for`) and cast to the column type. Identifiers are quoted with `quote_ident`. Block aliases are random names (`rand_block_name`).
- Mutations: all mutation root fields in one request run in one `Spi::connect_mut` session, in order. Each mutation field is one SQL statement (CTE `with impacted as (insert/update/delete ... returning ...)`). Any error raises a Postgres `ERROR`. The plpgsql wrapper catches it, so the whole request rolls back (subtransaction). Mutations are atomic per request.
- Queries: errors are per root field. Other root fields still return data. If every field failed, `data` is `null`.
- The request runs inside the caller's transaction and role. Row Level Security and grants apply as normal SQL.
- Error objects only have `message`. No `locations`, `path` or `extensions`.
- The `extensions` argument of `graphql.resolve` is accepted but unused (`#[allow(unused_variables)]` in `src/lib.rs`).
- Safety limits in code (not documented): max selection depth 32 (`MAX_SELECTION_DEPTH`, fragments count towards it). Fragment cycle detection with stack limit 50 (`STACK_DEPTH_LIMIT`). Collections clamp `first`/`last` to `max_rows` (default 30).

## Schema reflection

- Exposed schemas are the schemas on the current role's `search_path` where the role has `USAGE`. No other config.
- Reflected relation kinds: tables, partitioned tables, views, materialized views, foreign tables (`relkind in r, t, v, m, f, p`).
- A primary key is required. Tables without one are not exposed. Views, materialized views and foreign tables need a fake key via the `primary_key_columns` directive.
- Grants shape the schema. No `SELECT` on a table removes the type. Column-level `SELECT` removes the field. No `INSERT`/`UPDATE`/`DELETE` removes the matching mutation field. Column-level `INSERT`/`UPDATE` removes the field from the insert/update input. Functions need `EXECUTE`. Types need `USAGE`.
- Updatable views get the same mutations as tables. Non-updatable views are read only.
- View columns are always nullable in GraphQL. Open PR #619 adds a `not_null` directive for view columns.
- Relationships come from foreign keys. Many-to-one gives an object field. One-to-many gives a `<type>Collection` connection field with full collection arguments. A unique FK gives one-to-one (object fields both ways).
- Foreign keys on non-null columns give non-null relationship fields. Exception: if the referenced table has RLS, the field is nullable (1.5.7).
- Relationship field names: if the FK has one column ending in `Id` (no inflection) or `_id` (inflection), the suffix is stripped (`account_id` -> `account`). Otherwise the target type name in lower camel case. Reverse side is `<type>Collection` unless the FK is unique.
- Root query fields per table: `<type>Collection(...)`, `<type>ByPk(<pk cols>)` (1.6.0). Plus a global `node(nodeId: ID!): Node`.
- Root mutation fields per table: `insertInto<Type>Collection`, `update<Type>Collection`, `deleteFrom<Type>Collection`.
- Every table type implements `Node` and has `nodeId: ID!`. `nodeId` is base64 of a JSON array `[schema, table, pk values...]`. Example: `WyJwdWJsaWMiLCAiYmxvZyIsIDFd` = `["public", "blog", 1]`.
- Postgres enums become GraphQL enums. Enums not on the role's `search_path` are excluded.
- Column comments without a directive are not used as descriptions. Only the `description` directive sets descriptions.
- Names that are not valid GraphQL names are omitted (test `omit_weird_names`). Enum values can be remapped with `mappings`.
- Composite-type columns are omitted entirely. JSON/JSONB columns are exposed but cannot be filtered or ordered. Array columns cannot be ordered.
- Generated columns are reflected like normal columns (preferred way to add computed values).
- No subscriptions. `subscription` operations return `Subscriptions are not supported`.
- No Relay `Node` for functions returning scalars. No interfaces or unions other than `Node`.

## Scalars

- `ID`, `Int` (`int2`, `int4`), `Float` (`float4`, `float8`), `String` (`text`, `varchar`, `char`, `bpchar`, `name`, `citext`), `Boolean`, `Date`, `Time` (`time`), `Datetime` (`timestamp`, `timestamptz`), `UUID`, `JSON`, `BigInt` (`int8`), `BigFloat` (`numeric`), `Cursor`, `Opaque`.
- `BigInt` and `BigFloat` are serialized as JSON strings.
- `JSON` is serialized as a JSON string, not an object. Inputs must also be JSON strings.
- `Opaque` is every unknown type. Serialized with `to_json`. Filter ops: `eq`, `is`.
- `varchar(n)` length is kept as type info. Since 1.2.0 it no longer truncates input.

## Query grammar: collections

- Collection arguments: `first: Int`, `last: Int`, `before: Cursor`, `after: Cursor`, `offset: Int`, `filter: <Type>Filter`, `orderBy: [<Type>OrderBy!]`.
- Connection type `<Type>Connection`: `edges: [<Type>Edge!]!`, `pageInfo: PageInfo!`, `totalCount: Int!` (opt in), `aggregate: <Type>Aggregate` (opt in).
- Edge type: `cursor: String!`, `node: <Type>`.
- `PageInfo`: `startCursor: String`, `endCursor: String`, `hasNextPage: Boolean!`, `hasPreviousPage: Boolean!`.

### Pagination

- Keyset (Relay) pagination with `first`+`after` and `last`+`before`.
- Validation errors in code: `only one of "first" and "last" may be provided`, `only one of "before" and "after" may be provided`, `"first" may only be used with "after"`, `"last" may only be used with "before"`, `"offset" may only be used with "first" and "after"`.
- Offset pagination: `first` + `offset` (1.5.0). `offset` can also combine with `after`. No backward offset.
- Page size: `limit = min(first or last or max_rows, max_rows)`. Default `max_rows` is 30. Asking for more silently returns fewer.
- Cursor: base64 of the JSON array of the row's `orderBy` column values (`translate(encode(convert_to(jsonb_build_array(...)::text,'utf-8'),'base64'), ...)`). Example `WzFd` = `[1]`. Cursors are not opaque or signed. A cursor is only valid for the same `orderBy`.
- The primary key columns are always appended to the `orderBy` (ascending, nulls last) for stable keyset pagination.
- Backward pagination reverses the order in SQL and flips `hasNextPage` and `hasPreviousPage`.

### Filtering (`filter: <Type>Filter`)

- Entity filter fields: one per selectable, non-composite, non-JSON column. Plus `nodeId: IDFilter`. Plus `and: [<Type>Filter!]`, `or: [<Type>Filter!]`, `not: <Type>Filter` (1.3.0).
- If a column is named `and`, `or` or `not`, that logical operator is dropped.
- Several keys in one object are ANDed. Several ops in one column filter are ANDed. Empty objects are ignored.
- Passing an object to `or` instead of a list is coerced to a one-item list, so it behaves like AND. Docs warn about this.
- `not` with a list input is rejected: `Only and and or filters are allowed to take an array as input.`
- No relationship filters. You cannot filter by a related table, by EXISTS, or by computed fields. Use a view or a set-returning function instead.
- Operators per filter type (from `FilterTypeType::input_fields` in `src/graphql.rs`):
  - `IDFilter`: `eq`.
  - `UUIDFilter`: `eq`, `neq`, `in`, `is`.
  - `BooleanFilter`: `eq`, `is`.
  - `IntFilter`, `FloatFilter`, `BigIntFilter`, `BigFloatFilter`, `DateFilter`, `TimeFilter`, `DatetimeFilter`: `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `in`, `is`.
  - `StringFilter`: the above plus `startsWith`, `like`, `ilike`, `regex`, `iregex`.
  - `OpaqueFilter`: `eq`, `is`.
  - `<Enum>Filter`: `eq`, `neq`, `in`, `is`.
  - `<Scalar>ListFilter` (array columns, 1.5.6): `contains`, `containedBy`, `eq`, `overlaps`, `is`. `contains` and `containedBy` also accept a single scalar.
- `is: FilterIs` takes `NULL` or `NOT_NULL`.
- `in` takes `[T!]`.
- Filters also work on `update` and `delete` mutations.

### Ordering (`orderBy: [<Type>OrderBy!]`)

- One input field per orderable column (not arrays, composites or JSON).
- `OrderByDirection`: `AscNullsFirst`, `AscNullsLast`, `DescNullsFirst`, `DescNullsLast`.
- Only one key per list element. `[{name: AscNullsLast}, {id: DescNullsFirst}]` is valid. Two keys in one element is an error.
- Default order is the primary key ascending.
- No ordering by related fields, by aggregates or by computed fields.

### Aggregates (1.5.12)

- Opt in per table with `@graphql({"aggregate": {"enabled": true}})`. Field `aggregate: <Type>Aggregate` on the connection.
- `<Type>Aggregate` fields: `count: Int!`, `sum: <Type>SumAggregateResult`, `avg: <Type>AvgAggregateResult`, `min: <Type>MinAggregateResult`, `max: <Type>MaxAggregateResult`.
- `sum`/`avg`: numeric columns (`int2`, `int4`, `int8`, `float4`, `float8`, `numeric`, `decimal`, `money`). `sum` of int types is `BigInt`, others `BigFloat`. `avg` is always `BigFloat`.
- `min`/`max`: numeric, string, date/time and boolean columns.
- Aggregates use the same `filter` and relationship join but ignore pagination (`first`, `after`, ...).
- Aggregates also work on nested relationship connections, since they are on the connection type.
- No `groupBy`. No `count(distinct)`. No aggregate filters (HAVING). No ordering by aggregates. No aggregates on arrays.
- Open PR #653: aggregate result types ignore column-level `SELECT` grants. I think this only exposes column names in the schema, and a query would then fail with a Postgres permission error. Not verified.

### totalCount

- Opt in per table with `@graphql({"totalCount": {"enabled": true}})`. Counts all rows matching `filter`, ignoring pagination.

### Single record queries

- `<type>ByPk(<pk columns as arguments>)` (1.6.0). Composite primary keys take one argument per column. All must be given. Returns null when no row matches.
- `node(nodeId: ID!)`: global lookup by `nodeId`. Use inline fragments for type fields.
- Filter by `nodeId` inside a collection: `filter: {nodeId: {eq: "..."}}`. A `nodeId` from another table gives `nodeId belongs to a different collection`.

## Mutations

- `insertInto<Type>Collection(objects: [<Type>InsertInput!]!): <Type>InsertResponse`. Bulk insert. Empty list is an error (`At least one record must be provided to objects`).
- `update<Type>Collection(set: <Type>UpdateInput!, filter: <Type>Filter, atMost: Int! = 1): <Type>UpdateResponse!`. `set` needs at least one key. Same values for all matched rows.
- `deleteFrom<Type>Collection(filter: <Type>Filter, atMost: Int! = 1): <Type>DeleteResponse!`.
- `atMost` is a safety limit. If more rows match, the SQL raises `update impacts too many records` / `delete impacts too many records` and the whole request rolls back. Default 1.
- Responses: `affectedCount: Int!`, `records: [<Type>!]!`. `records` can select relationships too.
- Insert input fields are the insertable columns. Update input fields are the updatable columns.
- No upsert (`on conflict`). WIP PR #503 and branch `feat/on-conflict` (last touched 2024-2025) add `onConflict` with `<Type>OnConflictConstraint` and `<Type>Field` enums. Not merged.
- No nested inserts or updates through relationships. No per-row different updates. No increment or expression updates. No returning of a single object. No `deleteByPk` or `updateByPk`.
- Volatile SQL functions are exposed as mutation fields (see "Functions").
- Mutations can use fragments (test `fragment_on_mutation`).

## Functions (user defined, 1.4.0)

- Functions on the `search_path` with `EXECUTE` are exposed as root fields.
- `immutable` or `stable` functions go on `Query`. `volatile` functions go on `Mutation`.
- Arguments: built-in and custom scalars, and arrays of non-composite types (1.4.3). Arguments without a SQL default are required (non-null). A `default null` makes them optional.
- Return types: scalars, a table or view row (implements `Node`), `setof <table/view>` (exposed as a full collection with pagination, filter and orderBy).
- A function returning a row where all columns are null returns `null` (Postgres treats an all-null row as null).
- Not supported (function is hidden): overloaded functions, nameless arguments, `void` returns, variadic, arrays of composite types, enum args or returns, functions taking a table row type (those become computed fields instead), trigger functions.
- `name` and `description` directives work on functions.

## Computed fields and computed relationships

- Computed field: a function `f(rec <table>) returns <scalar>` adds a field to the table type. A leading `_` in the function name is stripped (`_full_name` -> `fullName` with inflection).
- Computed fields take only the row argument. No extra arguments.
- Computed to-one relationship: `f(rec <table>) returns setof <entity> rows 1`.
- Computed to-many relationship: `f(rec <table>) returns setof <entity>`. Exposed as a collection with full arguments.
- Computed fields cannot be used in `filter` or `orderBy`.
- Docs note: function volatility affects freshness of data returned in mutation `records`.
- Composite-returning computed fields work since 1.5.3.

## Comment directives

Format: `comment on <object> is e'@graphql(<JSON>)'`. Parsed by `graphql.comment_directive` with regex `@graphql\((.+)\)`. Other comment text is ignored. Keys read in `sql/load_sql_context.sql`:

- Schema: `inflect_names` (bool, default false). `max_rows` (int, default 30). `introspection` (bool, default false, 1.6.0).
- Table / view / materialized view / foreign table: `name`, `description`, `totalCount: {"enabled": bool}`, `aggregate: {"enabled": bool}`, `primary_key_columns: [..]`, `foreign_keys: [{local_name, local_columns, foreign_name, foreign_schema, foreign_table, foreign_columns}]`, `max_rows`.
- Column: `name`, `description`.
- Foreign key constraint: `local_name` (reverse field name), `foreign_name` (forward field name).
- Function: `name`, `description`.
- Type (enum): `name`, `mappings: {"sql-value": "GRAPHQL_VALUE"}`.
- `max_rows` falls back from table to schema to 30. A view's parent is its schema, not the base table.
- Inflection: `snake_case` -> `PascalCase` for types, `camelCase` for fields. Without it, SQL names are used as is. Inflection is per schema.
- No directive to hide a table or column. Hiding is done with grants.
- No global config file, no GUCs. All config is in comments, grants and `search_path`.

## Introspection and security

- Introspection (`__schema`, `__type`) is off by default since 1.6.0 (breaking). Opt in per schema with `{"introspection": true}`.
- If no exposed schema has it on, `__schema`/`__type` give `Unknown field "__schema" on type Query`. Other root fields in the same query still resolve.
- If some schemas have it on, types from the others are hidden from `__schema` and `__type` returns `null` for them. Their data is still queryable.
- Disabling introspection does not restrict data access. Grants and RLS do.
- Security model: Postgres roles, grants, column grants and RLS policies. No GraphQL-level permission rules.
- No query cost analysis, no rate limiting, no persisted queries, no allow lists. Only the depth limit of 32 and `max_rows`.

## GraphQL language support

- Supported: queries, mutations, variables (with defaults), named operations with `operationName`, aliases, fragments, inline fragments, `__typename`, `@skip`, `@include`, field merging.
- Errors: `Anonymous operations must be the only defined operation`, `Operation names must be unique`, `Operation not found`, `variables must be an object`.
- Not supported: subscriptions, `@defer`, `@stream`, custom directives, file uploads, batching (multiple operations in one call), `@oneOf`, `@specifiedBy` (open PR #644 for `specifiedByURL` in introspection).
- Open PR #647: selecting a composite field without subfields returns `{}` instead of an error (issue #412).

## How Supabase exposes it

- Endpoint `https://<PROJECT_REF>.supabase.co/graphql/v1`. No trailing `/`. Local dev: `http://localhost:54321/graphql/v1` from `supabase start`.
- Headers: `apiKey: <API_KEY>` always. `Authorization: Bearer <JWT>` for a logged-in user. The JWT role (`anon`, `authenticated`, `service_role`) becomes the Postgres role, so RLS applies.
- Wiring (from `supabase/supabase` `docker/volumes/api/kong.yml`): Kong routes `/graphql/v1` to PostgREST `http://rest:3000/rpc/graphql` with header `Content-Profile: graphql_public`. So the HTTP layer is PostgREST calling an RPC function.
- `graphql_public.graphql("operationName", query, variables, extensions)` is a SQL wrapper that calls `graphql.resolve`. It is created by the event trigger function `extensions.grant_pg_graphql_access()` when the extension is created (from `supabase/postgres` `migrations/schema-17.sql`).
- If the extension is dropped, the event trigger `issue_graphql_placeholder` installs a stub `graphql_public.graphql` that returns the error `pg_graphql extension is not enabled.`.
- Exposed schemas: by default `public`. To add more, add the schema to the API "Extra search path" setting and grant usage and privileges to `anon`, `authenticated`, `service_role`.
- I think only `POST` works, because PostgREST only allows `GET` for stable functions and the wrapper is volatile. Not verified.
- Clients: Supabase Studio has a built-in GraphiQL (`API Docs > GraphQL > GraphiQL`). It needs introspection enabled since 1.6.0. `supabase-js` has no GraphQL client. Docs have guides for Apollo Client (codegen scalar map, `dataIdFromObject` with `nodeId`, `typePolicies` for `node`) and Relay (`nodeInterfaceIdField: 'nodeId'`, `getDataID: node => node.nodeId`, custom scalars).
- Upgrades: `drop extension pg_graphql; create extension pg_graphql;` for zero-downtime upgrades.
- Local demo in repo: `docker-compose up` starts Postgres, PostgREST v10 and GraphiQL at `http://localhost:4000/`. The demo GraphiQL posts to `/rpc/graphql`.

## Not supported

- Subscriptions and realtime.
- Relationship filters, filters on computed fields, JSON/JSONB filters and path access.
- Ordering by relationships, aggregates, computed fields, arrays or JSON.
- Group by, distinct, `count(distinct)`, HAVING-like aggregate filters.
- Upsert, nested mutations, per-row update values, by-PK mutations.
- Composite type columns and composite inputs.
- Functions: overloads, variadic, void, enums, composite arrays, extra arguments on computed fields.
- Tables without a primary key.
- Custom resolvers, remote schemas, federation, schema stitching.
- `@defer`, `@stream`, persisted queries, query cost limits, file uploads.
- Custom scalars defined by the user. Unknown types are `Opaque`.
- GraphQL-level auth or permissions (only Postgres roles and RLS).
- Error `path`, `locations`, `extensions`.
- An HTTP server. HTTP comes from PostgREST (Supabase) or user code.

## Upcoming and unreleased work

- `master` has no unreleased changelog entries.
- Open PRs: #653 aggregate result types respect column `SELECT` grants (2026-09-17). #652 do not fail when `search_path` is empty (2026-09-03). #647 reject composite fields without subselection (2026-08-19). #644 `specifiedByURL` on `__Type` (2026-06-29). #619 `not_null` directive for view columns (2026-01-20). #503 WIP `onConflict` upsert for inserts (2024-03-29).
- Branches: `feat/on-conflict` (10 commits ahead, 265 behind, last 2024-08-26).

## Docs and code disagree

- API docs say `UUIDFilter` only supports `eq` and `neq`. Code gives `eq`, `neq`, `in`, `is`.
- API docs say `min`/`max` result types "match the original field types". Code maps `float4`/`float8`/`numeric` to `BigFloat` (column type is `Float` for floats) and `money` to `Opaque` (`sql_type_to_scalar` in `src/graphql.rs`).
- `docs/sql_interface.md` shows the function as `strict volatile parallel safe`. `sql/resolve.sql` declares none of these (plain `language plpgsql`).
- `docs/sql_interface.md` shows `"errors": []` in a success response. Code omits the `errors` key when there are none (`Omit::Omitted`).
- `docs/configuration.md` computed field rename example creates `"_fullName"` but comments on `public._full_name`.
- `extensions` argument is documented in the signature but ignored by the code.
- `docs/changelog.md` has no 1.6.2 entry.
- Undocumented in user docs: selection depth limit 32, fragment cycle limit 50, PK appended to every `orderBy`, cursor format, error messages for pagination argument combinations.

## Sources

- https://github.com/supabase/pg_graphql (cloned at `51dbdc9`, `docs/`, `src/`, `sql/`, `test/`)
- https://supabase.github.io/pg_graphql/
- https://supabase.github.io/pg_graphql/api/
- https://supabase.github.io/pg_graphql/configuration/
- https://supabase.github.io/pg_graphql/views/
- https://supabase.github.io/pg_graphql/functions/
- https://supabase.github.io/pg_graphql/computed_fields/
- https://supabase.github.io/pg_graphql/security/
- https://supabase.github.io/pg_graphql/sql_interface/
- https://supabase.github.io/pg_graphql/supabase/
- https://supabase.github.io/pg_graphql/changelog/
- https://github.com/supabase/pg_graphql/releases
- https://github.com/supabase/pg_graphql/pulls
- https://supabase.com/docs/guides/graphql.md
- https://raw.githubusercontent.com/supabase/postgres/develop/migrations/schema-17.sql
- https://raw.githubusercontent.com/supabase/supabase/master/docker/volumes/api/kong.yml
