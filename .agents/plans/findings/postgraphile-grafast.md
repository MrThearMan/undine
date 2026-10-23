# PostGraphile / Grafast findings

Versions checked: `postgraphile@5.1.5`, `graphile-build-pg@5.1.5`, `grafast@1.1.4`, `grafserv@1.0.2`, `@dataplan/pg@1.1.2`, `graphile-config@1.1.1`, `ruru@2.0.2`. Repo `graphile/crystal` `main` at `65f5704` (2026-10-05). Unreleased `next` branch at `41063eb` (2026-10-09).
The repo is a monorepo. It holds PostGraphile V5, Grafast (engine), Grafserv (server), Ruru (GraphiQL), `@dataplan/pg` and `@dataplan/json` (step libraries), Graphile Build (plugin schema builder), `graphile-build-pg`, `graphile-utils`, `graphile-config`, `graphile-export`, `pg-sql2`, `pg-introspection`, `tamedevil`, `@graphile/lru`. Docs source is in the same repo: `postgraphile/website/`, `grafast/website/`, `graphile-build/website/`, `utils/website/` (Docusaurus).
PostGraphile generates a GraphQL API from a PostgreSQL schema by introspection. Grafast replaces GraphQL.js execution with a plan-based engine. Grafast can be used without PostGraphile. Node.js, TypeScript. MIT license (some sponsor-only extras, see below).

## Maintenance status

- Very active. 12.9k stars. 168 open issues plus PRs. Not archived. MIT. Last push 2026-10-09.
- PostGraphile V5.0.0 and Grafast 1.0.0 released 2026-03-24 after years of alpha/beta/rc. `postgraphile@5.1.0` on 2026-07-13. Latest `postgraphile@5.1.5` (2026-09-04), `graphile-build-pg@5.1.5` and `grafast@1.1.4` (2026-10-02).
- V4 is in maintenance on the `v4` / `legacy` branches. Docs keep V4 pages under https://postgraphile.org/postgraphile/4/.
- Per-package `CHANGELOG.md` files (for example `postgraphile/postgraphile/CHANGELOG.md`, `grafast/grafast/CHANGELOG.md`). Releases use changesets. GitHub releases are per package (`postgraphile@5.1.5`).
- https://postgraphile.org/llms.txt and https://grafast.org/llms.txt return 404. No markdown variants of doc pages.
- Docs versions: `/postgraphile/5/` is the released V5 docs. `/postgraphile/next/` is the `current` docs from `main`. `/postgraphile/4/` is V4.
- Repo has an `AGENTS.md` for code assistants.
- Supports `graphql@^16.9.0`. Node.js only for the main stack.

## Upcoming and unreleased work

`next` branch, held in PR #3127 "next: PostGraphile v5.2". Changesets in `.changeset/`:

- Grafast `prepare()`: does operation planning without execution. For warming the operation plan cache at server start.
- Grafast flag handling overhaul. Fixes how `sideEffect()`, `trap()`, `inhibitOnNull()` combine through implicit dependencies.
- Grafast experimental `fieldNodes` on `FieldInfo`.
- `@dataplan/pg` `PgSelectStep.setInliningStrategy()` (`preferLeftJoin`, `preferSubquery`, `auto`, `forbidden`) and `setChildInliningStrategy()`. `auto` now caps at about 7 joins and uses subqueries for children that have their own joins.
- `PgSelectStep` and `PgUnionStep` use a materialized CTE lateral join instead of a subquery lateral join.
- `PgExecutor` groups similar queries and runs them on the same connection. Fewer transaction handshakes.
- Query deduplication inside `pgSelect`. Automatic skip of fetches for `WHERE col = null`.
- Experimental "wrap" on `PgInsertSingleStep`, `PgUpdateSingleStep`, `PgDeleteSingleStep`. Runs logic before and after a CRUD mutation inside the same transaction (validation, coercion, auditing, rollback).
- `PgClassSingleStep.toSelectSingle()`. `PgUpdateSingleStep` with no values is a no-op instead of an error.
- Empty ranges supported on input and output.
- `pgSettings` passed to Postgres via `unnest()` instead of `json_array_elements()`.
- `addPgTableCondition()` and `addPgTableOrderBy()` accept a string match (`"my_schema.my_table"`).
- `extendSchema()` and `wrapPlans()` declare `provides` for plugin ordering.
- `@returnType` fixed for `setof` functions.
- Stable ordering of schema construction (changes schema print order).
- Better TypeScript types for codecs and resources. "PostGraphile Pro (V5)" type generation plugin: generates typed registry, plan resolver and smart tag types. On npm, `@graphile/pro@2.1.1` still peers on `postgraphile@^4`.

Open PRs on `main` (2026-10):
- #3124 PostgreSQL `PROCEDURE` support (CALL-based mutations). New `PgCallStep` / `pgCall()` and `PgProceduresPlugin`. Not merged.
- #3168 `@argNdescription` smart tag to document function arguments.
- #3082 [WIP] progressive introspection.
- #2997 overloaded computed column functions.
- #3066 better smart tags for polymorphic types.
- #2842 Elysia adapter for Grafserv.
- #3204 / #2820 rewrite `json_array_elements` to `json_to_recordset` (performance).
- #3184 / #3183 performance of the behavior system and of `graphile-export`.
- #2553 ability to disable polymorphic partitioning. #2391 replace the `nullableBoundary` layer plan with executable boundaries.
- Branches hint at more work: `batch-plan-resolver`, `runtime-condition`, `runtime-pagination-planning`, `dataplan-graphql`, `generated-types`, `input-planning-overhaul`.


## Grafast planning model (how it works)

- Grafast is a GraphQL execution engine. It replaces the resolver-per-field model of graphql-js. It uses graphql-js only for parsing, validation and types.
- Two phases. Planning is synchronous and runs once per operation shape. Execution is asynchronous and runs the plan for each request. Plan resolvers never see runtime data.
- Plan resolver: each field has `plan($parent, fieldArgs, info) => Step` instead of a resolver. It describes what data is needed. It does not fetch data. Stored in `field.extensions.grafast.plan`.
- Step: a node in a data-flow graph. A step has dependencies on other steps. At run time a step gets a batch of values for each dependency and returns a batch of results. So every step is batched by design. There is no DataLoader. Batching is a property of the plan, not something the user adds.
- Operation plan (`OperationPlan`): the result of planning a whole operation. Grafast walks the operation breadth-first. For each field it calls the plan resolver, then argument `applyPlan`s, then deduplicates new steps. Then: tree shake, `optimize` (leaves to root), tree shake again, `finalize`, output plan finalize.
- Deduplication: `step.deduplicate(peers)` merges equal steps from different fields. Two fields that need the same row share one step.
- Optimize: `step.optimize()` lets a step rewrite itself or merge with its parent. Example: `@dataplan/pg` `PgSelectStep` inlines child selects into the parent SQL query as joins or subqueries. A whole GraphQL tree can become one SQL query. `$pgSelect.setInliningForbidden()` turns this off per step.
- Finalize: `step.finalize()` builds the final work, for example the SQL text. This happens once per plan, not per request.
- Layer plans (buckets): the plan is split into layers. Reasons: `root`, `nullableBoundary`, `listItem`, `subscription`, `mutationField`, `defer`, `polymorphic`, `polymorphicPartition`, `subroutine`, `combined`. A bucket is the run-time batch store for one layer plan. All list items of a list field are run as one batch.
- Output plan: synchronous. It shapes data into the GraphQL response. It can write a JSON string directly (`outputDataAsString`, `stringifyPayload`).
- Plan diagrams: `grafast.explain: ["plan"]` returns the plan as JSON in `extensions.explain`. `planToMermaid()` (`grafast/mermaid`) draws it. Ruru shows it.
- Plan caching: the parse cache (`schema.extensions.grafast.queryCacheMaxLength`, about 50 MB heuristic). The operation plan cache is keyed by the operation AST node object. LRU of `operationsCacheMaxLength` (default 500) operations. Each operation keeps up to `operationOperationPlansCacheMaxLength` (default 50) plan variants. All three have no docs.
- Plan constraints: a cached plan is reused only if its constraints match the new request's `variableValues`, `context`, `rootValue` and `onError`. Constraint kinds: `value`, `equal`, `exists`, `keys`, `length`, `isEmpty` (`grafast/grafast/src/constraints.ts`). Plan resolvers create them with `eval()`, `evalIs()`, `evalHas()`, `evalKeys()`, `evalLength()`, `evalIsEmpty()`. No docs. `@skip`/`@include` and null-vs-undefined variables use this. Each variable combination gets its own plan.
- Docs advice: use static documents and cache parsing. A new document text means new planning.
- Cache is in memory only. Serializable, shared or build-time plans are "future".
- Traditional resolvers still work. `graphqlResolver` / `GraphQLResolverStep` emulates them. Limits: no `info.path`, context must be an object, `resolveType`/`isTypeOf` must return a string.
- Grafast is usable without PostGraphile. Use `makeGrafastSchema` or add plans to an existing graphql-js schema (`getting-started/existing-schema.md`).

## Grafast plan resolvers and schema API

- `makeGrafastSchema({ typeDefs, objects, interfaces, unions, inputObjects, scalars, enums, extensions, enableDeferStream })`. Per field: `objects[Type].plans[field]`. `enableDeferStream` (default false) has no docs.
- Deprecated: top-level `plans` key and `__assertStep` / `__planType` keys.
- `defaultPlanResolver`: `get($source, info.fieldName)`.
- `FieldArgs`: `$argName` shortcuts (nested `$filter.$author` works), `getRaw(path)`, `getBaked(path)`, `apply($target, path?, getTargetFromParent?)`, `autoApply($target)`. `typeAt(path)` has no docs. `fieldArgs.get` is removed ("use bakedInput()").
- `FieldInfo`: `fieldName`, `field`, `schema`. `parentType` has no docs. Experimental `fieldNodes` is on the `next` branch.
- Argument plans: `applyPlan($parent, $target, val)`, `applySubscribePlan`. Legacy `inputPlan`, `autoApplyAfterParentPlan`, `autoApplyAfterParentSubscribePlan` are typed `never`.
- Input objects: input fields use `apply`. Input object types use `baked`. `bakedInput()` / `applyInput()` helpers. `applyScope()` on inputs, enums and scalars is EXPERIMENTAL. Enum value `apply` is EXPERIMENTAL.
- Scalars: `plan` for output, `inputPlan` for input, `idempotent` flag.
- Object types: `assertStep` (class or assertion function), `planType($specifier)`, `isTypeOf`.
- Schema builder helpers with no docs: `newObjectTypeBuilder`, `objectSpec` and similar.

## Grafast steps (user API)

- Base class `Step` (old alias `ExecutableStep`). Do not subclass other step classes. `__` names are reserved. Convention: a lowercase step function builds each step.
- `execute({ count, values, indexMap, indexForEach, stream, extra })`. `values[i]` has `.at(i)`, `.isBatch`, `.unaryValue()`. Must return a list of length `count`. A throw fails the whole batch. `flagError(e)` fails one entry.
- `extra.stopTime` (steps must honour the execution timeout), `extra.meta` (via `metaKey`), `extra.eventEmitter`.
- `UnbatchedStep` (`unbatchedExecute(extra, ...values)`, alias `UnbatchedExecutableStep`). No docs. `isSyncAndSafe = true` is the sync fast path.
- Dependencies: `addDependency` (returns index), `addUnaryDependency` (throws at plan time if not unary), `addRef` / `getRef`, `getDep(i)`. No docs: `addDataDependency`, `addStrongDependency`, `AddDependencyOptions` (`onReject`, accept flags). `getDepDeep` is EXPERIMENTAL.
- Lifecycle hooks: `deduplicate(peers)`, `deduplicatedWith(replacement)`, `optimize({ stream, meta })`, `finalize()` (must call `super.finalize()`). Flags: `allowMultipleOptimizations`, `metaKey` and `optimizeMetaKey` (both EXPERIMENTAL), `hasSideEffects`, `isSyncAndSafe`.
- Method conventions: `get(key)`, `at(i)`, `items()`, `apply($cb)`, `listItem($item)` (ListCapableStep), `toTypename()`, `toSpecifier()`, `toRecord()`. `__inferGet` type helper.
- No docs: `cloneStreams`, `peerKey`, `planJSONExtra()`.
- Request steps: `context()`, `rootValue()`, `variableValues()` (unary, root bucket). `constant(value)`. `operationPlan()` at plan time. `rootValue`, `variableValues`, `operationPlan` have no docs.
- `$$` symbols: `$$inhibit`, `$$idempotent`, `$$verbatim`, `$$bypassGraphQL`, `$$eventEmitter`, `$$extensions`.
- Basic standard steps: `lambda($in, cb, isSyncAndSafe?)` (unbatched escape hatch), `object`, `list` (`.at`, `.first`, `.last`), `remapKeys`, `first($l, arrayOnly?)`, `last`, `reverse` / `reverseArray`, `filter`, `groupBy`, `each($list, $item => ...)`, `applyTransforms`, `coalesce`, `condition(op, ...)`, `multistep`, `access($s, path)`, `get($s, key)`.
- No docs: `listTransform`, `partitionByIndex`, `setter` / `Setter` / `createObjectAndApplyChildren`, `proxy` (@experimental), `error` / `ErrorStep`.
- Utility exports with no docs: `arraysMatch`, `stepADependsOnStepB` and more.

## Grafast data loading (plan-level batching for non-SQL sources)

- `loadOne($lookup | multistep, loader)` and `loadMany(...)`. `loader` is a function or `{ load, name?, shared?, ioEquivalence?, paginationSupport? }` (`paginationSupport` on `loadMany` only). A third argument throws "signature of loadOne has changed".
- Callback: `load(lookups, { shared, attributes, params })`. `info.unary` is a deprecated alias of `shared`.
- `$rec.get(attr)` adds to `attributes`, so the loader knows which columns to fetch. `$rec.setParam(key, $unary)` sets `params`.
- `ioEquivalence` (string, array or object map) lets a child fetch run in parallel with its parent.
- Lookups are deduplicated with `===`. `multistep` tuple and object forms keep values stable.
- `loadMany` steps that share the same `load` merge their `attributes`.
- `loadMany` with `paginationSupport` gets `params.limit`, `offset`, `after`, `reverse` from `connection()`.
- Typing helpers with no docs: `loadOneCallback`, `loadOneLoader`, `loadManyCallback`, `loadManyLoader`. `LoadedRecordStep` is plan-only.

## Grafast pagination and node IDs

- `connection($list, { fieldArgs, edgeDataPlan })` returns `ConnectionStep` with `EdgeStep`. Methods `setFirst`, `setLast`, `setBefore`, `setAfter`, `setOffset`.
- Step pagination contract: a step declares `paginationSupport { offset, cursor, reverse, full }` and implements `applyPagination($params)`. With `cursor` it implements `cursorForItem($item)`. Optional `nodeForItem`, `edgeForItem`, `connectionClone()`.
- Without pagination support, `connection()` fetches the full list and uses numeric cursors.
- No `node()` step. Helpers: `specFromNodeId(handler, $id)`, `nodeIdFromNode(handler, $node)`. `NodeIdHandler { typeName, codec, match, getIdentifiers, getSpec, get, plan, deprecationReason? }`. `NodeIdCodec { name, encode, decode }`. `makeDecodeNodeId`, `makeDecodeNodeIdRuntime` have no docs.

## Grafast polymorphism

- Interfaces and unions use `planType($specifier, info)`. It returns `{ $__typename, planForType?(objectType) }`. `toSpecifier` on the abstract type is optional. Fallback: `$step.toSpecifier()`, then `$step.toRecord()`, then the step. `info.$original`, `info.abstractType`.
- Grafast calls `planForType` for every possible type. Types that give equal steps are grouped into `polymorphicPartition`s. It fans in (`combined`) before it fans out again. Branching grows as P*D, not P^D.
- `defaultPlanType`: `$step.toTypename()` or `get($step, "__typename")`.
- Lazy (on-demand) polymorphic planning is only "might add".

## Grafast errors, flow control, side effects

- `flagError(err)`, `SafeError(message, extensions?, options?)`, `isSafeError`, `error(err)` / `ErrorStep`.
- Entry flags: error, null, inhibited, polymorphic-skipped, stopped. Errored and inhibited entries are filtered out of later batches by default.
- `inhibitOnNull`, `inhibitIf($step, $cond)`, `inhibitOnEmpty`, `assertNotNull($step, msg)` (raises `SafeError`). Docs: inhibition is "not a security boundary".
- `trap($step, TRAP_ERROR | TRAP_INHIBITED | TRAP_ERROR_OR_INHIBITED, { valueForError, valueForInhibited: "PASS_THROUGH" | "NULL" | "EMPTY_LIST", if })`. Uses `__FlagStep` inside.
- No `try`/`catch` in plan resolvers. Use `maskError` or flow steps.
- `onError: "PROPAGATE" | "NULL" | "HALT"` (error behavior RFC) on `grafast()` and `execute()`. Grafserv reads `onError` from the request body. No docs.
- `sideEffect($in, cb)` (not batched). Any step can set `hasSideEffects = true`. Later steps depend on the latest side-effect step. Side effects are expected only in root mutation fields.
- Each root mutation field gets its own `mutationField` layer plan. They run in sequence.

## Grafast subscriptions and incremental delivery

- Subscription field: `subscribePlan` returns a stream step. `plan` maps each event (`$source` is the event). `subscribePlan` is not in the website docs.
- `listen(pubsubOrStep, topicOrStep, itemPlan?, $initialEvent?)`, `ListenStep`. `GrafastSubscriber { subscribe(topic): AsyncIterator, release?() }`. Any pubsub backend works via this interface.
- `subscribe()` is exported. Each event is a new execution pass. Timeouts apply per event.
- `@defer` / `@stream`: `defer` layer plan, `GraphQLDeferDirective`, `GraphQLStreamDirective`, `graphqlHasStreamDefer`, `details.stream.initialCount`. Implements an old draft (`hasNext`). Needs `enableDeferStream`. The code says "incremental delivery is going to be fully rewritten ... we recommend you avoid using it for now" (`grafast/grafast/src/prepare.ts:1032`).

## Grafast entry points, config and debugging

- `grafast(args)` (parses and validates with a cache), `grafastSync`, `execute(args)`, `subscribe(args)`. Args: graphql-js args plus `resolvedPreset`, `requestContext`, `middleware`, `outputDataAsString`, `onError`. Preset as 2nd/3rd positional argument is deprecated.
- `hookArgs(args)` (@experimental): applies preset middleware and `grafast.context`.
- Grafast does not validate documents itself. It expects a validated document.
- Preset `grafast.*`: `context` (object or `(requestContext, args) => obj`), `explain` (`true` or `["plan","sql"]`), `maxPlanningDepth` (default 100, limits planning layers not query depth), `timeouts { planning, execution }` (default no limit), `distributorPauseDuration`, `distributorTargetBufferSize`, `distributorTargetBufferSizeIncrement`.
- Planning timeout is checked at some stages only. The first plans get a 5x allowance that drops by 0.5 per plan. Execution timeout is checked only before async steps.
- Middleware (`plugin.grafast.middleware`): `validateSchema`, `parseAndValidate`, `prepareArgs`, `execute`, `subscribe`, `establishOperationPlan`, `executeStep`. Only the Grafserv plugins page mentions it.
- Debug: `debugPlans()`, `inspect()`. `isDev` reads `GRAPHILE_ENV`, then `NODE_ENV` (`development`/`test`). Warns when neither is set. Dev mode adds slower checks.
- Envelop: `useGrafast({ explainAllowed })`, `useMoreDetailedErrors` (`grafast/envelop`). Reads the `x-graphql-explain` header.
- `prepare()` (plan without execution, for cache warming) is on the `next` branch.

## @dataplan/pg (Postgres step library)

- Registry: `makeRegistryBuilder()` with `addCodec`, `addResource`, `addRelation`, `getRegistryConfig`. `makeRegistry(config)`. `PgRegistry.pgCodecs`, `pgResources`, `pgRelations`. PostGraphile builds it from introspection.
- Codecs: `TYPES`, `recordCodec(config)`, `listOfCodec(inner)`, `rangeOfCodec(inner, name, identifier)`, custom scalar codecs.
- `pgResource.get(spec)`, `find(spec)`, `execute()`.
- `pgSelect`: `.alias`, `.single()`, `.singleAsRecord()`, `.row($row)`, `.orderBy(spec)`, `.setOrderIsUnique()`, `.where(condition)`, `.placeholder($step, codec)`, `.singleRelation(name)`, `.apply($step)`, `.setFirst/.setLast/.setOffset`, `.groupBy(spec)`, `.having(condition)`, `.setUnique()`, `.setInliningForbidden()`, `.setTrusted()`.
- `pgSelectSingle`: `.get(attr)`, `.select(fragment, codec)`, `.placeholder`, `.singleRelation`, `.manyRelation`, `.record()`, `.cursor()`, `.getClassStep()`. `pgSelectFromRecords`, `pgSelectFromRecord`, `pgSelectSingleFromRecord`.
- `pgCondition`: `.orPlan()`, `.andPlan()`, `.notPlan()`, `.existsPlan(options)`, `.where()`, `.having()`. `sqlValueWithCodec(value, codec)`.
- `pgUnionAll`: polymorphic select across several resources with conditions, ordering and pagination.
- Mutations: `pgInsertSingle`, `pgUpdateSingle`, `pgDeleteSingle`. `pgClassExpression`.
- Raw client: `loadOneWithPgClient`, `loadManyWithPgClient`, `sideEffectWithPgClient`, `sideEffectWithPgClientTransaction`. Adaptor `@dataplan/pg/adaptors/pg` with `createWithPgClient`, `PgSubscriber`.
- No docs: `PgTempTable`, `pgFromExpression`, `sqlFromArgDigests`, `PgCursorStep`, `pgValidateParsedCursor`, `domainOfCodec`, `enumCodec`.
- `@dataplan/json`: `jsonParse` is the only documented step.
- On-demand transactions, no savepoints. Mutations do not use `RETURNING *`.

## Grafserv (HTTP server)

- Adapters: `grafserv/node`, `grafserv/express/v4`, `grafserv/koa/v2` (`koa/v3` alias), `grafserv/fastify/v4`, `grafserv/fastify/v5`, `grafserv/h3/v1`, `grafserv/hono/v4`, `grafserv/lambda/v1` (API Gateway v2), `grafserv/whatwg-node__server/v4`. Lambda, Hono and whatwg are EXPERIMENTAL. Nuxt guide uses h3. No Next.js adapter.
- API: `grafserv({ preset, schema })`, `serv.addTo(app, server?)`, `createHandler()`, `release`, `onRelease`, `setSchema`, `setPreset`, `getSchema`, `getPreset`. h3: `handleGraphQLEvent`, `handleGraphiqlEvent`, `handleEventStreamEvent`, `makeWsHandler()`.
- Options: `port` (5678), `host`, `graphqlPath` (`/graphql`), `graphqlOverGET` (false, queries only, else 405), `graphiql` (true), `graphiqlOnGraphQLGET` (true), `graphiqlPath` (`/`), `graphiqlStaticPath` (`/ruru-static/`), `watch` (false), `eventStreamPath` (`/graphql/stream`), `maxRequestLength` (100000 bytes), `schemaWaitTime` (15000), `outputDataAsString`, `websockets`, `websocketKeepalive` (12000), `maskError` / `defaultMaskError`, `allowedRequestContentTypes`, `parseAndValidateCacheSize` (500), `dangerouslyAllowAllCORSRequests`.
- Content types: `application/json`, `application/graphql`. `application/x-www-form-urlencoded` is opt-in (CSRF risk). Responses: `application/graphql-response+json` or JSON. Incremental results as `multipart/mixed`. Follows GraphQL-over-HTTP.
- Watch mode: SSE stream at `eventStreamPath`, header `X-GraphQL-Event-Stream`. Only signals schema changes. No SSE transport for operations.
- Websockets: `graphql-ws` (graphql-transport-ws). On node, express, koa, fastify, h3, hono. I think lambda and whatwg have none.
- Error masking: safe errors are `SafeError` and `GraphQLError` without `originalError`. Others are replaced with a hash and id and logged.
- Middleware (`plugin.grafserv.middleware`): `setPreset`, `processRequest`, `processGraphQLRequestBody`, `ruruHTML`, `onSubscribe`. Old `hooks` (`init`, `ruruHTMLParts`) are deprecated.
- Envelop: `GrafservEnvelopPlugin` with `grafserv.getEnveloped` (no docs).
- `@grafserv/persisted`: `PersistedPlugin` with `hashFromPayload`, `persistedOperationsDirectory`, `persistedOperations`, `persistedOperationsGetter`, `allowUnpersistedOperation`. `persistedOperationsDirectoryScanInterval` (number or `"watch"`) is in code only. No website page.
- No CORS config beyond `dangerouslyAllowAllCORSRequests`. Docs say to use your own middleware for compression, rate limits and sessions.

## Ruru (GraphiQL)

- GraphiQL with the Explorer plugin. Hot-reloads the schema via `X-GraphQL-Event-Stream`. Shows Grafast plan diagrams and SQL explain. Sends `X-GraphQL-Explain: plan,sql`.
- Ways to run: hosted page (`grafast.org/myruru/#endpoint=...`), self-hosted `ruru.html`, React component, CLI `npx ruru -SPe <url>` (`-e`, `-p` default 1337, `-P` proxy, `-S`, `-s`). CLI needs Node 22+.
- Server: `ruruHTML(config)` (`ruru/server`), `serveStatic(staticPath)`, `getStaticFile({ staticPath, urlPath, acceptEncoding, disallowDevAssets })` (`ruru/static`).
- Preset `ruru.*`: `endpoint`, `subscriptionEndpoint`, `subscriptions`, `enableProxy`, `port`, `staticPath`, `htmlParts` (`metaTags`, `titleTag`, ..., `bodyInitScript`).
- `clientConfig` (no docs): `debugTools: ("explain"|"plan")[]`, themes, headers, `defaultQuery`, `initialQuery`, `initialVariables`, `maxHistoryLength`, `eventSourceInit` and more (`ruru/src/interfaces.ts`).
- No Ruru plugin system yet.

## PostGraphile generated schema

- Build phases: `inflection` (sync), `gather` (async introspection, builds the registry of codecs, resources and relations), behavior, `schema`.
- Root fields (amber): `allUsers` connection (inflector `allRowsConnection`), `allUsersList` (`allRowsList`, only if lists enabled), `userBy<Key>` per unique constraint (`rowByUnique`), a node fetcher per type, `node(id:)`, `query`, `Query.id`.
- Node ID field: amber uses `id` for the global ID. A column named `id` becomes `rowId` (`graphile-build/graphile-build/src/plugins/NodePlugin.ts:65`, `PgAttributesPlugin.ts:338`). `makeV4Preset` renames it back to `nodeId`.
- Global ID format: base64 JSON `["Post",1]` from the type name (V4 preset: table name). Opaque, not secret. `schema.defaultNodeIdCodec` (default `"base64JSON"`), `@nodeIdCodec` per table. `schema.nodeIdFieldName`. Disable with `disablePlugins: ["NodePlugin"]`. Decode with `specFromNodeId(build.getNodeIdHandler("Item"), $nodeId)`.
- Connections: `nodes`, `edges { cursor node }`, `pageInfo { hasNextPage hasPreviousPage startCursor endCursor }`, `totalCount` (runs `count(*)`).
- Pagination args: `first`, `last`, `before`, `after` (type `Cursor`), `offset`. Cursor pagination is keyset-based on the order. Function `SETOF` results use `LIMIT`/`OFFSET`.
- List vs connection: connections by default. `schema.defaultBehavior: "-connection +list"` for lists, `+connection +list` for both. List inflector `listField` appends `List`.
- Ordering: `orderBy: [UsersOrderBy!] = [PRIMARY_KEY_ASC]`, values like `CREATED_AT_DESC`. Per column, primary key and computed columns (`PgOrderAllAttributesPlugin`, `PgOrderByPrimaryKeyPlugin`, `PgOrderCustomFieldsPlugin`). `schema.pgOrderByNullsLast`.
- Custom ordering: `addPgTableOrderBy(match, ordersGen)` with `orderByAscDesc(baseName, spec, { unique, nulls, nullable })`. `nulls`: `first`, `last`, `first-iff-ascending`, `last-iff-ascending`. Nullable expressions need `nullable` or `nulls` or cursor pagination breaks.
- Filtering (built in): `condition:` argument only. Equality only. Only indexed columns by default (all columns under the V4 preset). `null` matches `IS NULL`. Force with `@behavior filterBy`, hide with `-filterBy`. Functions tagged as filterable add conditions (`PgConditionCustomFieldsPlugin`).
- Custom conditions: `addPgTableCondition({ serviceName?, schemaName, tableName }, name, build => ({ type, apply(condition, value) }))` with `condition.where(sql => ...)` and `sqlValueWithCodec`.
- Rich filtering (`filter:` with operators, and/or/not, relation filters) is only in the community plugin `postgraphile-plugin-connection-filter`. The docs discourage generic filtering and tell users to pair it with persisted operations.
- Aggregates: not built in. Community `@graphile/pg-aggregates` (connections only, ignores pagination args).
- Relations from foreign keys. Forward inflector `singleRelation` (`personByAuthorId`). Backward `singleRelationBackwards`, `manyRelationConnection`, `manyRelationList` (`usersByOrganizationId`). `PgIndexBehaviorsPlugin` hides backward relations with no index. Force with `+select` or `@isIndexed`.
- Many-to-many: community `@graphile-contrib/pg-many-to-many`, or a `setof` computed column.
- Refs: `@ref name to:Type from:Type via:<route> singular|plural` and `@refVia name via:<route>` (`PgRefsPlugin`). Route: `table`, `(cols)->table`, `(cols)->table(cols)`, joined by `;`. One way. Needs a real or fake foreign key.
- Computed columns: function `<table>_<name>(t table, ...)`, `STABLE` or `IMMUTABLE`, same schema, not `void`. Extra parameters become field args. `SETOF` gives a connection or list. Computed columns can be ordered and filtered with behaviors.
- Custom queries: `STABLE`/`IMMUTABLE` function whose first arg is not a table type. Unnamed args become `arg1`, `arg2`. Avoid `returns table(...)`.
- Custom mutations: `VOLATILE` function. Relay input shape `myFn(input: { a, b })`. `gather.pgStrictFunctions: true` makes args without defaults required. `@arg0variant nodeId` takes node IDs. `pgFunctionsPreferNodeId`.
- Function limits: no VARIADIC, no overloads, no bare `record` return. Procedures not supported.
- CRUD mutations: `createUser(input: { user })`, `updateUser` (by node ID), `updateUserById(input: { id, userPatch })`, `updateUserByUsername`, `deleteUser`, `deleteUserById`, `deleteUserByUsername` (returns `deletedUserId`). Update and delete need a unique key.
- Mutation payload: `clientMutationId`, the record, `query`, related records, `<record>Edge(orderBy)` (only with a primary key). `schema.pgMutationPayloadRelations` (no description).
- Turn off mutations: `defaultBehavior: "-insert -update -delete"`. No CRUD mutations on polymorphic types. No bulk or nested mutations built in (community `@haathie/postgraphile-fancy-mutations`).
- Enums: Postgres enums auto-mapped. Enum tables with `@enum` on table or unique constraint. Values from the primary key. Descriptions from a `description` column or `@enumDescription`. Rename with `@enumName`. `*_enum_domain` domains (`PgEnumDomainsPlugin`).
- Scalars: `bytea` is `Base64EncodedBinary`. `ltree` support. `schema.pgUseCustomNetworkScalars`, `schema.jsonScalarAsString`. Unknown types are omitted.
- Polymorphism: `@interface mode:single type:<col>` + `@type VALUE name:X attributes:a,b`. `@interface mode:relational type:<col>` + `@type VALUE references:<table>`. `@interface mode:union` on a composite type + `@implements <Interface>` on tables. `@unionMember <UnionName>` for unions. `only` arg on interface root fields (`PgPolymorphismOnlyArgumentPlugin`). Needs a primary key.
- Views and materialized views: read and write. Fake constraints `@primaryKey`, `@unique`, `@foreignKey`, `@notNull`. Fake constraints count as indexed. Unlogged tables are hidden unless given behaviors.
- Partitions: `schema.pgDefaultPartitionedTableExpose` or `@partitionExpose parent|child|both`. Default parent.
- Nullability: root fields, relations, payload fields, computed columns and `SETOF` rows are nullable. `schema.pgForbidSetofFunctionsToReturnNull` (off by default). `changeNullability({ Type: { field: "[!]!" } })`.
- Schemas: `makePgService({ schemas: [...] })` or `-s a,b`. Extension objects hidden (`PgRemoveExtensionResourcesPlugin`). `gather.pgIdentifiers: "unqualified"` uses `search_path` (multi-tenant).
- Multiple databases: several `pgServices`. Multiple GraphQL schemas: one `postgraphile()` instance each.
- Reserved names: tables `query`, `mutation`, `subscription`, `node`. Columns or args `order_by`, `primary_key`. Fix with `@name` or an inflector.
- `PgRBACPlugin` (default on, experimental): hides what the connecting role cannot use, from GRANTs. Union over all roles the user can become. `pgSettingsForIntrospection`. Do not use column-level SELECT grants.
- Inflection: about 100 inflectors (`inflection/reference.mdx`). Override with `inflection.replace.<name>(previous, resolvedPreset, ...args)`. Add with `inflection.add`. `inflection.ignoreReplaceIfNotExists`. `graphile inflection list`.

## Smart tags

- Sources: smart comments (`COMMENT ON ...`, blank line ends tags, repeat gives array), `postgraphile.tags.json5` (`TagsFilePlugin`, `{ version: 1, config: { class|attribute|constraint|procedure: { id: { tags, description, attribute, constraint } } } }`), `pgSmartTagsFromFile(path)`, `jsonPgSmartTags(obj)`, `pgSmartTags({ kind, match, tags, description })` (`kind` also `type`, `namespace`), `gather.hooks.pgIntrospection_introspection`.
- Tags on fake constraints: `|@fieldName x` after the constraint text.
- `@name`: rename table, view, type, column or function.
- `@fieldName`, `@foreignFieldName`, `@foreignSimpleFieldName`, `@foreignConnectionFieldName`: relation and finder field names.
- `@resultFieldName`: mutation payload result field. `@returnType`: GraphQL type a function returns.
- `@deprecated`: deprecate a column.
- `@behavior`: add behavior strings to any entity.
- `@arg0variant`, `@arg1variant`, ...: `patch`, `nodeId` or `base`.
- `@notNull`, `@primaryKey`, `@foreignKey`, `@unique`: fake constraints. `@isIndexed` (5.1.1+).
- `@hasDefault`: makes a column optional on insert. In code only (`PgAttributesPlugin.ts:764`).
- `@interface`, `@type`, `@implements`, `@unionMember`, `@ref`, `@refVia`, `@partitionExpose`, `@enum`, `@enumName`, `@enumDescription`, `@nodeIdCodec`.
- V4 preset only (deprecated): `@omit` (use `@behavior -*`), `@simpleCollections`, `@sortable`, `@filterable`, `@uniqueKey`.

## Behaviors

- Behavior string: space-separated fragments. Optional `+`/`-` prefix, then a scope of camelCase parts joined by `:`, or `*`. Examples: `+list -connection -list:filter`, `-insert -update -delete query:*:filter`.
- Matching from right to left. The last match wins. Narrower scopes add prefixes on the left (`constraint:resource:update`).
- Precedence low to high: plugin defaults, global default, inferred behaviors, secondary entity behaviors (for example the column's codec), smart tags.
- `schema.defaultBehavior`: user global default. `schema.globalBehavior` (string or callback) for preset authors. `schema.entityBehaviors.{pgCodec,pgResource,...}`, `schema.behaviorRegistry.add`. Check with `build.behavior.pgCodecMatches(codec, "x")`.
- Common strings: `insert`, `update`, `delete`, `select`, `list`, `connection`, `single`, `queryField`, `mutationField`, `typeField`, `filter`, `filterBy`, `order`, `orderBy`, `singularRelation:resource:*`, `manyRelation:resource:list`, `manyRelation:resource:connection`, `constraint:resource:update`, `nodeId:resource:update`, `nodeId:resource:delete`, `attribute:insert`, `attribute:update`, `attribute:base`, `type:node`, `interface:node`, `jwt`, `totalCount`, `resource:connection:backwards`. Plugins add more (`aggregates`, `groupedAggregates`, `having`, `filter:proc:filterBy`).
- Avoid `create` (use `insert`) and `root:` (use `query:`, `mutation:`, `subscription:`).
- Debug: `npx graphile behavior debug [entityType] [id] [filterString]`. Entity types: `pgResource`, `pgResourceUnique`, `pgCodec`, `pgCodecAttribute`, `pgCodecRelation`, `pgRefDefinition`, `pgCodecRef`.
- No registry of all behaviors in the docs ("need an automated registry").

## Config, presets, CLI and library use

- Config file: `graphile.config.{mjs,ts,mts,js,cjs,cts}`. One file for CLI, library and schema-only modes. No top-level `default` key.
- Preset keys: `extends`, `plugins`, `disablePlugins`, `inflection`, `gather`, `schema`, `grafast`, `grafserv`, `ruru`, `pgServices`.
- Presets: `PostGraphileAmberPreset` (`postgraphile/presets/amber`, required base). `makeV4Preset({...})` (`presets/v4`). `PostGraphileRelayPreset` (`presets/relay`, experimental, hides raw primary keys, prefers connections). `PgLazyJWTPreset` (`presets/lazy-jwt`). `PgMinifySchemaPreset` (`presets/minify`, experimental, destructive). `PgSimplifyInflectionPreset` (`@graphile/simplify-inflection`).
- `makePgService` (`postgraphile/adaptors/pg`): `connectionString`, `schemas`, `superuserConnectionString`, `pubsub` (default true), `name` (default "main"), `pgSettings(requestContext)`, `pgSettingsKey`, `pgSettingsForIntrospection`, `withPgClientKey`, `pgSubscriber`, `pgSubscriberKey`, `pool`, `poolConfig`, `superuserPool`, `superuserPoolConfig`.
- `gather.*`: `pgStrictFunctions`, `pgJwtTypes`, `installWatchFixtures` (default true), `pgIdentifiers`, `muteWarnings` (experimental). Deprecated `pgJwtType`, `pgFakeConstraintsAutofixForeignKeyUniqueness`.
- `schema.*`: `defaultBehavior`, `defaultNodeIdCodec`, `dontSwallowErrors` (recommended in production), `exportSchemaSDLPath`, `exportSchemaIntrospectionResultPath`, `sortExport`, `jsonScalarAsString`, `nodeIdFieldName`, `pgDefaultPartitionedTableExpose`, `pgForbidSetofFunctionsToReturnNull`, `pgFunctionsPreferNodeId`, `pgJwtSecret`, `pgJwtSignOptions`, `pgMutationPayloadRelations`, `pgOrderByNullsLast`, `pgUseCustomNetworkScalars`, `pgV4UseTableNameForNodeIdentifier`, `retryOnInitFail`.
- CLI `postgraphile` / `pgl`: `-P/--preset`, `-c/--connection`, `-S/--superuser-connection`, `-s/--schema`, `-w/--watch`, `-n/--host`, `-p/--port`, `-C/--config`, `-e/--allow-explain`, `--subscriptions` (not in the docs, `postgraphile/postgraphile/src/cli.ts:59`). `pgl` has no peerDependencies.
- `graphile` helper CLI: `graphile config options`, `graphile config print [section]`, `graphile inflection list`, `graphile behavior debug`.
- Library: `const pgl = postgraphile(preset)`, `pgl.createServ(grafserv)`, `serv.addTo(app, server)`, `pgl.getSchemaResult()` (`{ schema, resolvedPreset }`), `pgl.getSchema()`, `pgl.getResolvedPreset()`, `pgl.release()`.
- Schema only: `makeSchema(preset)` returns `{ schema, resolvedPreset }`. Then `grafast({ schema, resolvedPreset, requestContext, source, variableValues })`, or `hookArgs()` plus `execute()`. `buildSchema(resolvedPreset, input, shared)` is sync after `gather()`.
- Watch mode: `grafserv.watch` / `--watch`. Installs `postgraphile_watch` event triggers. Needs superuser. Rebuilds the schema on DDL change.
- Export: `exportSchema(schema, file, { mode: "graphql-js" | "typeDefs", modules })` (`graphile-export`). Writes the schema with plans as code, so no introspection at start. Every plugin must use `EXPORTABLE()`. Experimental. Replaces V4 `--read-cache` / `--write-cache`.
- `processSchema(fn)`: hook after the schema is built. `exportSchemaSDLPath` prints SDL.
- Package subpaths: `postgraphile/{grafast, grafserv, @dataplan/pg, @dataplan/json, graphile-build, graphile-build-pg, pg-sql2, tamedevil, utils, graphql, adaptors/pg, cli}` and adapter subpaths. No subpath for `graphile-config` or `graphile-export`.
- Requirements: Node 22+ (24 recommended). PostgreSQL 14 to 18 supported. 12 and 13 work but are not supported. `graphql@^16.9.0`.

## Plugin system (graphile-config, graphile-build)

- Preset resolution: depth-first through `extends`. Plugins deduped, then sorted by `before` / `after` / `provides`. Options merge like `Object.assign` (last wins). Docs warn against diamond `extends` and depth over 2.
- Plugin fields: `name` (required, unique), `version`, `description`, `experimental`, `provides`, `before`, `after`. Scopes: `inflection`, `gather`, `schema`, `grafast`, `grafserv`.
- Middleware: `plugin.<scope>.middleware.<action>(next, event)`, `next.callback()`, `runSync` vs `run`.
- Gather hooks: for example `pgCodecs_PgCodec`, `pgIntrospection_introspection`. Gather turns introspection into codecs, resources, relations, behaviors.
- Schema hooks (in order): `build`, `init`, `GraphQLSchema`, `GraphQLSchema_types`, `GraphQLObjectType` (`_interfaces`, `_fields`, `_fields_field`, `_fields_field_args`, `_fields_field_args_arg`), `GraphQLInputObjectType` (`_fields`, `_fields_field`), `GraphQLEnumType` (`_values`, `_values_value`), `GraphQLUnionType` (`_types`), `GraphQLInterfaceType` (`_interfaces`, `_fields`, ...), `GraphQLScalarType`, `finalize`.
- Build object: `extend`, `append`, `getTypeByName`, `inflection`, `graphql`, `grafast`, `wrapDescription`, `behavior`, `registerObjectType`, `registerInterfaceType`, `registerUnionType`, `registerScalarType`, `registerEnumType`, `registerInputObjectType`, `getNodeIdHandler`, `pgExecutor`, `pgResources`, `input.pgRegistry`. Frozen after `build`.
- Context object: `scope`, `Self`, `fieldWithHooks`. Scope types named after hooks (`ScopeObjectFieldsFieldArgsArg`).
- Types are registered at `init` and built lazily. Fixes V4 ordering bugs.
- `graphile-build-pg` plugins (one per feature, all disableable by name): `PgAllRowsPlugin`, `PgAttributesPlugin`, `PgAttributeDeprecationPlugin`, `PgCodecsPlugin`, `PgConditionArgumentPlugin`, `PgConditionCustomFieldsPlugin`, `PgConnectionArgOrderByPlugin`, `PgConnectionArgOrderByDefaultValuePlugin`, `PgConnectionTotalCountPlugin`, `PgCustomTypeFieldPlugin`, `PgEnumDomainsPlugin`, `PgEnumTablesPlugin`, `PgFakeConstraintsPlugin`, `PgFirstLastBeforeAfterArgsPlugin`, `PgIndexBehaviorsPlugin`, `PgInterfaceModeUnionAllRowsPlugin`, `PgIntrospectionPlugin`, `PgJWTPlugin`, `PgLtreePlugin`, `PgMutationCreatePlugin`, `PgMutationPayloadEdgePlugin`, `PgMutationUpdateDeletePlugin`, `PgNodeIdAttributesPlugin`, `PgOrderAllAttributesPlugin`, `PgOrderByPrimaryKeyPlugin`, `PgOrderCustomFieldsPlugin`, `PgPolymorphismPlugin`, `PgPolymorphismOnlyArgumentPlugin`, `PgProceduresPlugin`, `PgRBACPlugin`, `PgRefsPlugin`, `PgRegistryPlugin`, `PgRegistryReductionPlugin` (experimental), `PgRelationsPlugin`, `PgRemoveExtensionResourcesPlugin`, `PgRowByUniquePlugin`, `PgTableNodePlugin`, `PgTablesPlugin`, `PgTypesPlugin`.

## Extension APIs (`postgraphile/utils`)

- `extendSchema(definitionOrCallback, uniquePluginName?)` (alias `makeExtendSchemaPlugin`). Keys: `typeDefs`, `objects`, `inputObjects`, `enums`, `scalars`, `unions`, `interfaces`. Object entries: `assertStep`, `scope`, per-field `{ plan, scope }`. `plans` and `resolvers` keys are deprecated. Mixing `plans` with new keys throws.
- `gql` tag for `typeDefs` (not graphql-tag). Can embed strings and other gql docs.
- `wrapPlans(rules | generator, options?)` or `wrapPlans(filter, ruleGen, options?)` (alias `makeWrapPlansPlugin`). Wrapper: `(plan, $source, fieldArgs, info)`. Option `disableResolverEmulationWarnings`.
- `addPgTableCondition(...)`, `addPgTableOrderBy(...)`, `orderByAscDesc(...)`, `changeNullability(rules)`, `processSchema(cb)`, `pgSmartTags(rules)`, `jsonPgSmartTags(json)`, `pgSmartTagsFromFile(path?, name?)`. Old `make*Plugin` names are aliases.
- `EXPORTABLE(factory, deps, nameHint?)`.
- `makeAddInflectorsPlugin` is exported but always throws. `makePluginByCombiningPlugins` removed (use a preset).
- Plan steps the docs recommend in extensions: `pgResource.get/find/execute`, `pgSelect`, `pgSelectSingle`, `context`, `loadOne`, `loadMany`, `get`, `sideEffect`, `constant`, `each`, `lambda`, `object`, `connection`, `list`, `access`, `specFromNodeId`, `*WithPgClient` steps.

## Supporting libraries

- `pg-sql2`: tagged template `` sql`...` ``. Only fragments embed. Raw values throw. `sql.compile`, `sql.value`, `sql.literal`, `sql.identifier(...names)`, `sql.join`, `sql.parens`, `sql.indent`, `sql.indentIf`, `sql.comment`, `sql.placeholder`, `sql.withTransformer`, `sql.isSQL`, `sql.isEquivalent`, `sql.symbolAlias`, `sql.replaceSymbol`, `sql.raw` (dangerous), `sql.json`, `sql.true/false/null/blank`, `escapeSqlIdentifier`. `sql.fragment` and `sql.query` are deprecated aliases. Comments and indent only in dev mode.
- `pg-introspection`: `makeIntrospectionQuery()`, `parseIntrospectionResults()`. Typed catalog with lazy accessors (`getNamespace()`), `_id` instead of `oid`.
- `graphile-export`: `exportSchema`, `exportSchemaAsString`, `exportValueAsString`, `EXPORTABLE`, `$$export: { moduleName, exportName }`. `eslint-plugin-graphile-export` (experimental) autofixes deps.
- `tamedevil`: `te` template for safe `new Function` code generation. `te.ref`, `te.lit`, `te.identifier`, `te.join`, `te.substring`, `te.safeKeyOrThrow`, `te.get`, `te.set`, `te.tmp`, `te.tempVar`, `te.run`, `te.compile`.
- `@graphile/lru`: small LRU cache. I think Grafast and Grafserv use it for their caches.

## Auth and security

- Model: authorization in the database. RLS policies plus GRANTs. Identity reaches Postgres only through `pgSettings`, applied with `set_config(k, v, true)` per transaction.
- Custom setting keys must contain a period (`jwt.claims.x`). Keys without a period are Postgres settings (`role`, `statement_timeout`).
- Recommended: do authentication yourself (sessions, JWT, API keys, mTLS) and return `pgSettings` from `grafast.context`. Do not put `req`/`res` in context.
- Default role pattern: `authenticator` login role with `noinherit`, granted visitor roles. Switch with `pgSettings.role`. V4 `defaultRole` throws.
- JWT claims: `role` maps to `set local role`. Other claims map to `jwt.claims.<name>`.
- `PgLazyJWTPreset`: stopgap. `PgJWTPlugin` + `GrafservPgJWTPlugin` (`prepareArgs` middleware). Reads Bearer token from `requestContext.node.req`. Verifies with `jsonwebtoken`, secret `grafserv.pgJwtSecret` or `schema.pgJwtSecret`, HS256/HS384, audience `postgraphile`, `grafserv.pgJwtVerifyOptions`. No refresh, revocation or rotation.
- Issuing JWTs: `gather.pgJwtTypes: "schema.jwt_token"` (string or string[]) gives the type `@behavior -table +jwt`. Functions returning it return a signed token. `schema.pgJwtSecret`, `schema.pgJwtSignOptions`. Defaults aud and iss `postgraphile`, `expiresIn: "1 day"`.
- JWK / Auth0: done in the web framework (`express-jwt`, `jwks-rsa`). Not built in.
- `PgRBACPlugin` hides fields the role cannot access. `makeV4Preset` disables it unless `ignoreRBAC: false`.

## Realtime

- Websockets: `grafserv.websockets: true` (or `--subscriptions`). `graphql-ws` protocol on the same path.
- No generated subscription fields in amber. Add them with `extendSchema` on `Subscription`: `subscribePlan()` returns `listen(context().get("pgSubscriber"), $topic, jsonParse)`, `plan($event)` maps the event.
- `pgSubscriber` uses LISTEN/NOTIFY. On by default (`pubsub: true`). Topic max 63 chars. Generic trigger `tg__graphql_subscription`. Other backends (Redis, MQTT) via the `GrafastSubscriber` interface.
- V4 simple subscriptions: `simpleSubscriptions: true` in `makeV4Preset` or `PgV4SimpleSubscriptionsPlugin`.
- Live queries: not in V5. Planned, needs sponsorship.
- `multiple-schemas.md`: subscriptions not supported in the single-endpoint schema-switching setup.

## Production and limits

- No built-in depth limit, cost/complexity limit, pagination cap or `maxListSize`. No read-replica routing. The old V4 "Pro" text in `production.md` is commented out.
- Built-in limits: `grafserv.maxRequestLength`, `grafast.maxPlanningDepth` (default 100, `grafast/grafast/src/engine/OperationPlan.ts:161`), `grafast.timeouts.{planning,execution}`, `grafserv.parseAndValidateCacheSize`.
- Recommended: `statement_timeout` via `pgSettings` or pool `connect` hook. Trusted documents via `@grafserv/persisted` (recommended for most users). Rate limits, logging and compression via your own middleware. Library mode. Index foreign keys. `language sql` functions for inlining. Move expensive computed columns to `extendSchema`. `grafast.explain` in dev only. `grafserv.maskError` with `isSafeError`. `dontSwallowErrors: true`.
- Debug: `DEBUG=@dataplan/pg:PgExecutor`, `@dataplan/pg:PgExecutor:explain`, `graphile-build:warn`. SQL explain in Ruru needs `grafast.explain` / `-e`.
- No option to disable introspection. No federation.
- `performance.md` still shows V4 benchmark numbers.
- Testing: `testing-jest.md` (GraphQL helper is marked untested).

## Community plugins (V5 status from `community-plugins.md`)

- Ported: `postgraphile-plugin-connection-filter@^3` (`filter:` argument with operators, `PostGraphileConnectionFilterPreset`), `@graphile/pg-aggregates` (`PgAggregatesPreset`, aggregates and grouped aggregates on connections), `@graphile/simplify-inflection` (shorter names, drops `ByFooId`), `@graphile-contrib/pg-many-to-many` (`PgManyToManyPreset`), `@graphile-contrib/pg-omit-archived` (soft-delete hiding), `@haathie/postgraphile-fancy-mutations` (bulk and nested upserts, updates, deletes), `@haathie/postgraphile-targeted-conditions` (relational filters, ParadeDB), `@haathie/postgraphile-realtime` (conditional subscriptions), `@haathie/postgraphile-rate-limits` (rate limits via smart tags), `@haathie/postgraphile-reasonable-limits` (query limits), `@haathie/postgraphile-otel` (OpenTelemetry), `@grafserv/persisted` (persisted operations).
- Not yet ported: PostGIS (`@graphile/postgis`), `@graphile/operation-hooks`, nested mutations, upsert plugins, many create/update/delete, file upload field, `pg-order-by-related` (status conflicts, see below), multi-column-index ordering, fulltext filter, ZomboDB, polymorphic filter and relation plugins, multi-tenant connection, timestamp format, PassportLogin, pm2 status, hapi adapter.
- `plugin-gallery.md` is not ported. It links to V4.

## V4 to V5 changes

- Engine: V4 lookahead plus resolvers replaced by Grafast plans. `addArgDataGenerator`, QueryBuilder, `pgIntrospectionResultsByKind`, `@pgField`, `@pgQuery`, `@requires`, `embed`, `selectGraphQLResultFromTable`, `context.pgClient`, savepoints and `build.getTypeAndIdentifiersFromNodeId` are gone.
- Packages: `postgraphile-core` removed (`createPostGraphileSchema` becomes `makeSchema`). All parts importable via `postgraphile/*` subpaths.
- Config: one `graphile.config.*` file. No `.postgraphilerc`. A preset is required. `makeV4Preset(options)` maps V4 options. `pluginHook` removed. `appendPlugins` / `skipPlugins` need V5 plugins.
- Removed or throwing options: `legacyRelations`, `disableQueryLog`, `operationMessages`, `enableQueryBatching` (throws), `defaultRole` (throws), `readCache` / `writeCache`.
- Server: PostGraphile HTTP server replaced by Grafserv. PostGraphiQL replaced by Ruru. Most V4 server hooks are gone.
- Schema breaks even with the V4 preset: no legacy relations, bigint node IDs encode differently, edges nullable and cursors non-null, `fooEdge.orderBy` non-null, `fooEdge` only with a primary key, `deletedFooId` only with `NodePlugin`, `bytea` is `Base64EncodedBinary`, `hasPreviousPage` always false when paginating forward, `PgIndexBehaviorsPlugin` only removes backward relations.
- Amber vs V4 naming: `id` is the global ID, column `id` becomes `rowId`. Condition only on indexed columns.
- Smart tags: `@omit` and `@simpleCollections` replaced by `@behavior`. `@uniqueKey` becomes `@unique ...|@behavior -single -update -delete`. `@foreignKey` must reference a unique key.
- Hooks: V4 colon names (`GraphQLObjectType:fields`) became underscores (`GraphQLObjectType_fields`).
- New: behaviors, polymorphism, `@ref`/`@refVia`, multiple databases, plan diagrams, `@stream`/`@defer` (experimental), schema export (experimental), SQL caching (experimental), alternative authorization (experimental), no `RETURNING *` (write-only columns work), on-demand transactions, unknown types omitted, GraphQL 16, GraphQL-over-HTTP, `PgRBACPlugin`, relay preset.
- Subscriptions: `@graphile/pg-pubsub` built in. `subscribePlan` + `listen()`.
- `@graphile-contrib/pg-simplify-inflector` renamed to `@graphile/simplify-inflection`. Not default.
- `makeWrapResolversPlugin` replaced by `wrapPlans`. `makeExtendSchemaPlugin` renamed `extendSchema`.

## Not supported

- Rich filtering (operators, and/or/not, relation filters): not built in. Only equality `condition:`. Needs `postgraphile-plugin-connection-filter`.
- Aggregates and group by in the generated schema: not built in. Needs `@graphile/pg-aggregates`.
- Bulk, nested and upsert mutations: not built in.
- Many-to-many fields: not built in.
- PostgreSQL procedures, VARIADIC functions, overloaded functions, bare `record` returns. Procedure support is in open PR #3124.
- CRUD mutations on polymorphic types. Functions returning a `mode:union` type.
- Live queries. Generated subscription fields (amber).
- PostGIS (not yet ported).
- Depth limits, cost/complexity analysis, pagination caps, introspection disabling, rate limiting.
- Federation (Apollo or other). No sign in docs or source.
- Query batching (array request bodies return 400. `enableQueryBatching` throws).
- File uploads (`multipart/form-data`).
- SSE transport for operations (SSE is only for schema-change events).
- CORS config, other than `dangerouslyAllowAllCORSRequests`.
- Next.js adapter. Websockets on Lambda and whatwg adapters (I think).
- Spec-compliant `@defer`/`@stream`. The old draft exists behind `enableDeferStream` and the code says to avoid it.
- Persisted or shared plan cache across processes. In-memory only.
- Lazy polymorphic planning.
- `info.path` in emulated resolvers.
- Ruru plugin system. Operation hooks / `operationMessages`. `@graphile/logger`. Most V4 server hooks. `defaultRole`. `legacyRelations`. Introspection cache (replaced by graphile-export). Codemods.
- Grafast is JavaScript only. A cross-language spec is "working on".
- Experimental: `PostGraphileRelayPreset`, `PgMinifySchemaPreset`, `PgRBACPlugin`, `PgRegistryReductionPlugin`, `graphile-export`, `eslint-plugin-graphile-export`, `muteWarnings`, `getDepDeep`, `metaKey`, `optimizeMetaKey`, `applyScope`, enum value `apply`, `hookArgs`, `proxy()`, Lambda, Hono and whatwg adapters.

## Docs and code disagree

Grafast and Grafserv:
- `production-considerations.md` says the preset is the 2nd argument of `grafast()` / `execute()`. Code marks that `@deprecated`. Current form is `args.resolvedPreset`.
- `index.mdx` says the plan cache is keyed by schema, document and operation name, and only `@skip`/`@include` add constraints. Code keys on the operation AST node. Constraints also come from `eval*` on variables, context and rootValue, and from `onError` (`grafast/grafast/src/engine/establishOperationPlan.ts`).
- `plan-diagrams.mdx` leaves out the `polymorphicPartition` and `combined` layer plan reasons. `operation-plan.mdx` lists them.
- `standard-steps/index.mdx` links `./error` and `./setter`. Those pages do not exist. It also misses `sideEffect`, `get`, `coalesce`, `condition`, `applyTransforms`, which have pages.
- `servers/next.md` imports `grafserv/next/v13`. It does not exist. The same page says there is no adapter.
- `fastify.md` shows only v4. Code also ships `fastify/v5`.
- `step-classes.mdx` and `loadOne.md` say `setParams` once. The real method is `setParam`.
- `loadOne.md` passes `shared: $dbClient` as a step. The type says `Thunk`. Both work via `multistep()`.
- `listen.md` does not show `subscribePlan`. The website never mentions `subscribePlan`.
- I think Grafserv ignores the `X-GraphQL-Explain` header that Ruru sends. Only the envelop plugin reads it.

PostGraphile:
- `tables.md`, `crud-mutations.md`, `why-nullable.md` use V4 names (`nodeId`, `user(nodeId:)`, `userById(id:)`). Amber uses `id` for the global ID and `rowId` for the column.
- `tables.md` and `relations.md` name V4 inflectors (`rowByUniqueKeys`, `singleRelationByKeys`, `manyRelationByKeys`, `allRows`). V5 names are `rowByUnique`, `singleRelation`, `manyRelationConnection`, `allRowsConnection`.
- `smart-tags.md` says `@sortable` maps to `+sort +sortBy`. Code maps it to `orderBy order resource:connection:backwards` (`postgraphile/postgraphile/src/plugins/PgV4SmartTagsPlugin.ts:125`). `@filterable` also adds `filterProc` in code.
- `smart-comments.mdx`, `smart-tags-file.md`, `pg-smart-tags.md` use `@omit`. It only works with the V4 preset.
- `extend-schema.md` recommends `typeDefs` plus `plans`. Code deprecates `plans` and `resolvers`, prefers `objects` and friends, throws when mixed, and also accepts a plain object and a `uniquePluginName` (`graphile-build/graphile-utils/src/makeExtendSchemaPlugin.ts:120-133`, `:198-202`, `:375-383`).
- `all-hooks.mdx` says `init` registers types via `build.registerType`. No such method. Real: `build.registerObjectType` and siblings (`graphile-build/graphile-build/src/global.ts:447`).
- `build-object.md` gives `registerObjectType(type, spec, scope)`. Real signature is `(typeName, scope, specGenerator, origin)`.
- `security.md` calls `pgJwtTypes` a schema/type tuple. Code takes `string | string[]` like `"schema.type"` (`graphile-build/graphile-build-pg/src/plugins/PgJWTPlugin.ts:23-37`).
- Docs allow several JWT types. I think only the first matching codec becomes the JWT scalar, because the code uses `.find()` (`PgJWTPlugin.ts:135`).
- Lazy JWT docs say "alphanumeric claims" are copied. Code copies only truthy values with keys matching `/^[a-z_][a-z0-9_]*$/i`, max 52 chars. `false` and `0` claims are dropped (`postgraphile/postgraphile/src/presets/lazy-jwt.ts`).
- `postgresql-schema-design.mdx` says JWTs never expire unless set. Code defaults `expiresIn: "1 day"` (`PgJWTPlugin.ts:190-195`).
- `migrating-from-v4/index.mdx` lists `pg-order-by-related` and `postgraphile-plugin-fulltext-filter` as ported. `community-plugins.md` says not yet ported. I did not check npm.
- Inflector replace example uses `name === "Query"` but the parameter is `text` (`adding-and-replacing-inflectors.md:53`, `migrating-from-v4/make-add-inflectors-plugin.md:41`). It would throw.
- Docs say `makeAddInflectorsPlugin` no longer exists. It is exported but throws (`graphile-build/graphile-utils/src/makeAddInflectorsPlugin.ts:2`).
- `plugins.md` prose says `processGraphQLRequstBody` (typo).
- Table condition and order-by examples use deprecated `sql.fragment`.
- `production.md` `statement_timeout` example puts it at the top of the context, not in `pgSettings`. I think it has no effect.
- `crud-mutations.md` says update/delete need a primary key. `requirements.md` says a unique constraint is enough. It also says `userById` reads by global ID, which is wrong.
- `functions.md` uses `pageInfo.hasPrevPage`. Real field is `hasPreviousPage`.
- `subscriptions.mdx` NOTIFY example uses `sub`. The trigger sends `subject`.
- `config/overview.mdx` says default host `127.0.0.1`. `usage-cli.mdx` says `localhost`. `debugging.md` puts Ruru at `/graphiql`. `graphiqlPath` defaults to `/`.
- `multiple-schemas.md` example does not compile (`export` inside a loop, missing import, default import of `postgraphile`).
- `@hasDefault` tag and CLI `--subscriptions` flag exist in code but not in docs.
- `extending-raw.md` links `github.com/benjie/crystal`. Canonical repo is `graphile/crystal`.

## Sources

Repo: https://github.com/graphile/crystal (clone `/tmp/graphile-crystal`, `main` at `65f5704`, 2026-10-05). Paths used: `grafast/grafast/src/` (`index.ts`, `engine/OperationPlan.ts`, `engine/LayerPlan.ts`, `engine/establishOperationPlan.ts`, `constraints.ts`, `prepare.ts`, `execute.ts`, `grafastGraphql.ts`, `makeGrafastSchema.ts`), `grafast/dataplan-pg/src/steps/pgSelect.ts`, `grafast/grafserv/`, `grafast/ruru/src/interfaces.ts`, `grafast/website/`, `graphile-build/graphile-build/src/` (`global.ts`, `plugins/NodePlugin.ts`, `SchemaBuilderHooks.ts`), `graphile-build/graphile-build-pg/src/plugins/` (`PgAttributesPlugin.ts`, `PgJWTPlugin.ts` and others), `graphile-build/graphile-utils/src/`, `graphile-build/website/`, `postgraphile/postgraphile/src/` (`cli.ts`, `presets/`, `plugins/PgV4SmartTagsPlugin.ts`), `postgraphile/website/postgraphile/`, `utils/website/`, per-package `CHANGELOG.md`, `.changeset/` on `next`.

PostGraphile docs (source in `postgraphile/website/postgraphile/`, current at `/next/`, released at `/postgraphile/5/`):
- https://postgraphile.org/postgraphile/5/ and https://postgraphile.org/postgraphile/next/
- https://postgraphile.org/postgraphile/next/usage-cli, https://postgraphile.org/postgraphile/next/usage-library, https://postgraphile.org/postgraphile/next/usage-schema
- https://postgraphile.org/postgraphile/next/config/, https://postgraphile.org/postgraphile/next/config/reference, https://postgraphile.org/postgraphile/next/config/presets
- https://postgraphile.org/postgraphile/next/tables, https://postgraphile.org/postgraphile/next/relations, https://postgraphile.org/postgraphile/next/connections, https://postgraphile.org/postgraphile/next/filtering, https://postgraphile.org/postgraphile/next/aggregates
- https://postgraphile.org/postgraphile/next/add-pg-table-condition, https://postgraphile.org/postgraphile/next/add-pg-table-order-by
- https://postgraphile.org/postgraphile/next/crud-mutations, https://postgraphile.org/postgraphile/next/custom-mutations, https://postgraphile.org/postgraphile/next/custom-queries, https://postgraphile.org/postgraphile/next/computed-columns, https://postgraphile.org/postgraphile/next/function-restrictions, https://postgraphile.org/postgraphile/next/procedures
- https://postgraphile.org/postgraphile/next/views, https://postgraphile.org/postgraphile/next/enums, https://postgraphile.org/postgraphile/next/node-id, https://postgraphile.org/postgraphile/next/refs, https://postgraphile.org/postgraphile/next/polymorphism, https://postgraphile.org/postgraphile/next/multiple-schemas, https://postgraphile.org/postgraphile/next/why-nullable
- https://postgraphile.org/postgraphile/next/smart-tags, https://postgraphile.org/postgraphile/next/smart-tags-file, https://postgraphile.org/postgraphile/next/smart-comments, https://postgraphile.org/postgraphile/next/pg-smart-tags, https://postgraphile.org/postgraphile/next/behavior
- https://postgraphile.org/postgraphile/next/inflection/, https://postgraphile.org/postgraphile/next/inflection/reference
- https://postgraphile.org/postgraphile/next/extend-schema, https://postgraphile.org/postgraphile/next/wrap-plans, https://postgraphile.org/postgraphile/next/plugins, https://postgraphile.org/postgraphile/next/community-plugins, https://postgraphile.org/postgraphile/next/grafast-for-postgraphile-users
- https://postgraphile.org/postgraphile/next/security, https://postgraphile.org/postgraphile/next/jwt-guide, https://postgraphile.org/postgraphile/next/jwt-specification, https://postgraphile.org/postgraphile/next/jwk-verification, https://postgraphile.org/postgraphile/next/default-role
- https://postgraphile.org/postgraphile/next/subscriptions, https://postgraphile.org/postgraphile/next/realtime, https://postgraphile.org/postgraphile/next/live-queries
- https://postgraphile.org/postgraphile/next/exporting-schema, https://postgraphile.org/postgraphile/next/production, https://postgraphile.org/postgraphile/next/performance, https://postgraphile.org/postgraphile/next/debugging, https://postgraphile.org/postgraphile/next/requirements
- https://postgraphile.org/postgraphile/next/migrating-from-v4/, https://postgraphile.org/postgraphile/next/migrating-from-v4/v5-new-feature-summary

Grafast, Grafserv and Ruru docs (source in `grafast/website/`):
- https://grafast.org/grafast/, https://grafast.org/grafast/flow, https://grafast.org/grafast/operation-plan, https://grafast.org/grafast/plan-diagrams, https://grafast.org/grafast/step-classes, https://grafast.org/grafast/polymorphism, https://grafast.org/grafast/config, https://grafast.org/grafast/production-considerations, https://grafast.org/grafast/access-control, https://grafast.org/grafast/glossary
- https://grafast.org/grafast/getting-started, https://grafast.org/grafast/getting-started/existing-schema
- https://grafast.org/grafast/plan-resolvers, https://grafast.org/grafast/plan-resolvers/best-practices, https://grafast.org/grafast/plan-resolvers/complex-inputs
- https://grafast.org/grafast/standard-steps/ (for example https://grafast.org/grafast/standard-steps/lambda, https://grafast.org/grafast/standard-steps/loadOne, https://grafast.org/grafast/standard-steps/listen)
- https://grafast.org/grafast/step-library/dataplan-pg/ (pgSelect, pgUnionAll, pgCondition, registry, withPgClient, adaptors)
- https://grafast.org/grafserv/, https://grafast.org/grafserv/config, https://grafast.org/grafserv/plugins, https://grafast.org/grafserv/servers/
- https://grafast.org/ruru/, https://grafast.org/ruru/cli, https://grafast.org/ruru/config

Graphile Build and utils docs:
- https://build.graphile.org/graphile-build/next/ (hooks, all-hooks, build-object, context-object), https://build.graphile.org/graphile-build-pg/next/
- https://star.graphile.org/graphile-config/, https://star.graphile.org/graphile-export/, https://star.graphile.org/pg-introspection/, https://star.graphile.org/pg-sql2/, https://star.graphile.org/tamedevil/

Note: the doc URLs follow the Docusaurus path rule. The earlier research did not open each live page.
