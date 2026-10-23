# Neo4j GraphQL Library findings

Versions checked: repo `neo4j/graphql` default branch `dev` at `ff0637b` (2026-09-25). Package `@neo4j/graphql` 7.6.3 in `packages/graphql/package.json`. Docs repo `neo4j/docs-graphql` branch `7.x` at `584845a` (2026-09-29). Docs are Antora AsciiDoc in `modules/ROOT/pages/` (72 files, about 41k words).
The library is a TypeScript package. The user writes GraphQL SDL type definitions with directives. `new Neo4jGraphQL({ typeDefs, driver })` builds an executable `GraphQLSchema` with generated queries, mutations, subscriptions, filters, sorts, aggregates and nested mutation inputs. It runs on any JS GraphQL server (Apollo Server, Yoga and so on). Each root field is translated to one Cypher statement and runs in Neo4j. Apache-2.0.

## Maintenance status

- GitHub: 550 stars, 68 open issues plus PRs, last push 2026-10-09, not archived. Last commit on `dev` 2026-09-25.
- Latest release: `@neo4j/graphql@7.6.3` (2026-09-02). Release cadence about 1 to 4 weeks. 7.6.0 (2026-08-18), 7.5.0 (2026-03-26), 7.4.0 (2025-12-17).
- Major release dates (npm): 4.0.0 (2023-09-01), 5.0.0 (2024-02-23), 6.0.0 (2024-10-31), 7.0.0 (2025-04-08).
- LTS: version 5 is LTS (npm dist-tag `lts` = 5.12.15, 2026-08-18). It gets fixes but no features (`versioning.adoc`). Branch `lts`. Version 7 is the current version. 6.x is dist-tag `previous` (6.6.4).
- Packages in the monorepo `packages/`: `graphql`, `introspector`, `apollo-federation-subgraph-compatibility`, `package-tests`. The OGM package is not in `dev` any more (see "OGM" below).
- Unreleased in `.changeset/`: one patch, "Fix type-level `@authentication` not enforced on entities returned by `@cypher` fields".
- Unmerged branches with features: `group-by-nested` (nested `groupBy` on relationship connections, last commit 2026-03-11, 297 commits behind `dev`), `poc-hooks`, `update-populated-by-new-translation-layer`, `6805-authorization-after-rules-triggered-in-the-middle-of-mutation-in-connect-operations`, `benchmark-tools`.
- Minimum versions: Neo4j 5.23 (7.4.2), Node.js 20 (6.0.0). `neo4j-driver` peer dependency covers driver 5 and 6 (7.3.2).
- `https://neo4j.com/docs/graphql/current/llms.txt` is 404. `https://neo4j.com/llms.txt` exists and lists the GraphQL docs, but has no GraphQL-specific text. I used the AsciiDoc source instead.
- Security fixes in 2026: subscription JWT in WebSocket `connectionParams` was trusted without verification (fixed 7.5.6). Field-level `@authentication` on root custom-resolver fields ignored when a type-level rule exists (fixed 7.6.0). Several authorization fixes for `CREATE_RELATIONSHIP` and `DELETE_RELATIONSHIP` (7.5.3, 7.6.2, 7.6.3).

## Big changes between majors

- 3.22 to 4.0.0 (2023): `@authentication`, `@authorization`, `@subscriptionsAuthorization` were added in 3.x and replaced `@auth`, which was removed in 4.0.0. 4.0.0 also removed `@computed` (use `@customResolver`), `@callback` (use `@populatedBy`), `@queryOptions` (use `@limit`), `@node(label, additionalLabels, plural)` (use `labels` and `@plural`), and `enableRegex` (use `features.filters.*.MATCHES`). `@cypher` now requires `columnName`. All labels, types and properties are escaped. `@cypher` on `Query` runs in READ mode, on `Mutation` in WRITE mode.
- 5.0.0 (2024-02-23): `@relationshipProperties` moved from interfaces to object types. Connection edges got a `properties` field for edge properties. `@subscription(operations:)` renamed to `events` (past tense). Aggregation types made nullable. Aggregations on single (non-list) relationships removed. 5 is the LTS line and still has the OGM (`@neo4j/graphql-ogm` 5.12.x).
- 6.0.0 (2024-10-31): requires Neo4j 5.x and Node 20. Removes non-CDC subscriptions. Only `Neo4jGraphQLSubscriptionsCDCEngine` is left. Removes relationship subscriptions (`relationshipCreated` and so on). Removes `_NOT` filters (use `NOT`). Removes the `options` argument of `assertIndexesAndConstraints` (no more index creation, only checks). Removes `bookmark` field. Adds `@vector`, filtering on scalar `@cypher` fields, `@populatedBy` on lists and temporals, top-level connection queries on interfaces.
- 7.0.0 (2025-04-08): `@node` is now required on every type that maps to a node. Types without `@node` are plain types (for `@cypher` results and similar). Subscriptions are opt-in with `@subscription`. Removed: `connectOrCreate`, `@unique`, `@private`, `options` argument (use `limit`, `offset`, `sort` directly), `overwrite` in connect, implicit filters (`title: "x"`, use `title: { eq: "x" }`), implicit set (`title: "x"`, use `title: { set: "x" }`), top-level `*Aggregate` queries (use `aggregate` in connections), single element relationships, `directed` argument. `typename_IN` renamed to `typename`. `connect` always creates new relationships. Lists of nullable elements are now rejected. `DateTime` and `Time` conversion moved into Cypher. `addVersionPrefix` defaults to true (queries start with `CYPHER 5`).
- 7.x minors: new "generic" filter and mutation inputs (`title: { eq }`, `title: { set }`, `actors: { some: {...} }`). The old suffix style (`title_EQ`, `actors_SOME`, `title_SET`) is still generated but `@deprecated`. It can be removed with `features.excludeDeprecatedFields`. 7.5.0 adds single element relationships back (`director: Director!`), and adds `@groupBy`.
- OGM: `@neo4j/graphql-ogm` is not supported in 7.x. The 7.0.0 changelog says `@private` was removed because the OGM "is no longer supported". OGM 5.12.15 is still released for the v5 LTS line.

## Architecture

- Input: SDL `typeDefs` (string, DocumentNode, or arrays), optional `resolvers`, `features`, `driver`, `debug`, `validate` (`Neo4jGraphQLConstructor` in `src/classes/Neo4jGraphQL.ts`).
- Methods on `Neo4jGraphQL`: `getSchema()` (same as `getExecutableSchema()`), `getSubgraphSchema()` (Apollo Federation), `checkNeo4jCompat({ driver, sessionConfig })` (checks Neo4j version and APOC), `assertIndexesAndConstraints({ driver, sessionConfig })` (checks that indexes and constraints for `@fulltext`, `@vector`, `@relayId` exist. It does not create them since 6.0).
- Schema build: SDL is validated against directive definitions (`validate: false` turns this off). Then a "schema model" (`src/schema-model/`) is built with entities, attributes, relationships and annotations (one annotation class per directive). Then the generated schema is built with `graphql-compose` (`src/schema/make-augmented-schema.ts`).
- Query translation: each root field resolver parses `resolveInfo` into a "QueryAST" (`src/translate/queryAST/`) with Operations, Filters, Fields, Sorts, Pagination and auth nodes. The QueryAST is transpiled to Cypher with `@neo4j/cypher-builder` (a separate Neo4j package). Result: one Cypher statement plus params per root field. Nested selections become `CALL { ... }` subqueries and map projections. No N+1. No dataloader.
- The generated Cypher uses `CYPHER 5` prefix by default (`cypherQueryOptions.addVersionPrefix`).
- All values are passed as Cypher parameters. Labels and relationship types are escaped. `features.unsafeEscapeOptions.disableNodeLabelEscaping` and `disableRelationshipTypeEscaping` turn escaping off (documented as unsafe).
- Execution: the library runs the Cypher with the driver from the constructor or from `context.executionContext` (a driver, session or transaction). Read queries run in `session.executeRead`, mutations in `session.executeWrite` (`src/classes/Executor.ts`). Each root field is its own transaction.
- Context (`Neo4jGraphQLContext` in `src/types/neo4j-graphql-context.ts`): `cypherParams`, `cypherQueryOptions`, `executionContext`, `sessionConfig` (database, impersonatedUser, auth), `transactionMetadata`, `transaction` (timeout and metadata, added 7.3.0). The JWT is read from `context.token` or `context.jwt` (see auth).
- `debug: true` turns on `debug` package logging of generated Cypher and params. The namespace prefix is `@neo4j/graphql` (`src/constants.ts`).
- Neo4j Aura has a hosted product "GraphQL for Aura" (`aura-graphql/` docs pages). It deploys the same library as a managed API, configured with the Aura CLI. Auth there is by API key or JWKS.

## Type definition directives (full list from `src/graphql/directives/`)

Database mapping:
- `@node(labels: [String!])` on OBJECT. Required for a type to be a node (since 7.0). `labels` replaces the type name as label. Labels may use `$jwt.<claim>` and `$context.<key>` for dynamic labels per request. Only the first label is used for indexes.
- `@relationship(type: String!, direction: RelationshipDirection!, queryDirection: RelationshipQueryDirection = DIRECTED, properties: String, nestedOperations: [RelationshipNestedOperations!]! = [CREATE, UPDATE, DELETE, CONNECT, DISCONNECT], aggregate: Boolean = true)` on FIELD_DEFINITION. `direction`: `IN` or `OUT`. `queryDirection`: `DIRECTED` or `UNDIRECTED` (undirected matches both ways in reads). `properties` names a `@relationshipProperties` type. `nestedOperations` limits generated nested mutation inputs. `aggregate: false` removes the `aggregate` field and aggregate filters.
- `@relationshipProperties` on OBJECT. Marks a type as edge properties.
- `@declareRelationship(nestedOperations, aggregate)` on interface fields. Every implementing type must put `@relationship` on that field. Gives relationship fields on interfaces.
- `@alias(property: String!)` on FIELD_DEFINITION. Maps a field to another database property name. Works on node and relationship properties. Not on `@cypher` or `@relationship` fields.

Autogeneration and defaults:
- `@id` on FIELD_DEFINITION. Generates a UUID with Cypher `randomUUID()` on create. Removes the field from create input. In 7.x `@id` has no arguments (the old `autogenerate` and `unique` args are gone).
- `@timestamp(operations: [TimestampOperation!]! = [CREATE, UPDATE])` on FIELD_DEFINITION. Sets `datetime()` (or the matching temporal) on create or update. Removed from inputs.
- `@default(value: ScalarOrEnum!)` on FIELD_DEFINITION. Default value in the create input.
- `@populatedBy(callback: String!, operations: [PopulatedByOperation!]! = [CREATE, UPDATE])` on FIELD_DEFINITION. Calls a JS callback from `features.populatedBy.callbacks` to fill the field on create or update. The callback gets `(parent, args, context)`. Since 7.4.0 `context.populatedByOperation` says `CREATE` or `UPDATE`. Works on node and relationship properties, lists, temporals, enums (7.5.1).
- `@coalesce(value: ScalarOrEnum!)` on FIELD_DEFINITION. Wraps the property in Cypher `coalesce()` in filters and (since 7.0) in returned values. A read-side default for missing properties.

Schema configuration:
- `@query(read: Boolean! = true, connection: Boolean, aggregate: Boolean! = false)` on OBJECT, SCHEMA, INTERFACE, UNION. Removes the list query, the connection query, or the connection `aggregate` field. `connection` defaults to `read` (added 7.4.3). Without the directive aggregate is generated.
- `@mutation(operations: [MutationFields]! = [CREATE, UPDATE, DELETE])` on OBJECT, SCHEMA. Removes `create*`, `update*`, `delete*` root fields.
- `@subscription(events: [SubscriptionEvent]! = [CREATED, UPDATED, DELETED])` on OBJECT, SCHEMA. Turns on subscriptions. Opt-in since 7.0. `extend schema @subscription` turns them on for all types. `@subscription(events: [])` on a type turns them off for that type.
- `@query`, `@mutation`, `@subscription` cannot be on both the schema and a type. Error: `"@query directive already defined at the schema location"`.
- `@plural(value: String!)` on OBJECT, INTERFACE, UNION. Sets the plural used in root field names (`techs`, `createTechs`). Schema build fails on clashing plurals (7.0).
- `@selectable(onRead: Boolean! = true, onAggregate: Boolean! = false)` on FIELD_DEFINITION. Hides a field from output types (read and subscription) and from aggregation selections.
- `@settable(onCreate: Boolean! = true, onUpdate: Boolean! = true)` on FIELD_DEFINITION. Hides a field from create or update inputs. On relationship fields it removes the nested input.
- `@filterable(byValue: Boolean! = true, byAggregate: Boolean! = false)` on FIELD_DEFINITION. Removes value filters or aggregate filters for a field. Also works on relationship fields.
- `@sortable(byValue: Boolean! = true)` on FIELD_DEFINITION. Removes the field from `<Type>Sort`. If no field is sortable, `<Type>Sort` and `sort` are not generated.
- `@groupBy` on FIELD_DEFINITION. Adds the field to `<Type>GroupByInput`. Added 7.5.0.
- `@limit(default: Int, max: Int)` on OBJECT, INTERFACE. Default page size and maximum page size for list and connection queries of that type. A larger `limit`/`first` is silently cut down to `max` (`Math.min` in `OperationFactory.ts`). Docs say "If a higher value is passed, it is used instead", which reads the other way.

Indexes and search:
- `@fulltext(indexes: [{ indexName: String!, queryName: String!, fields: [String]! }]!)` on OBJECT. Generates a root query `<queryName>(phrase: String!, where, sort, first, after)` that calls `db.index.fulltext.queryNodes` and returns a connection with `score`. The index must exist in the DB. The `fulltext` docs page still shows the old 6.x shape (`productsFulltextProductName(phrase, where, sort, limit, offset): [ProductFulltextResult!]!`). Code generates the connection shape (`tests/schema/fulltext.test.ts`).
- `@vector(indexes: [{ indexName: String!, embeddingProperty: String!, queryName: String!, provider: VectorProvider, maxPhraseLength: Int }]!)` on OBJECT. Generates `<queryName>(vector: [Float!], where, sort, first, after)` returning a connection with `score`. With `provider` (`VERTEX_AI`, `OPEN_AI`, `AZURE_OPEN_AI`, `BEDROCK`) it takes `phrase: String` and calls the provider through Neo4j GenAI (`genai.vector.encode`) to make the embedding. Provider tokens go in `features.vector`. `maxPhraseLength` caps phrase length (7.6.0). Requires `@node`.

Custom logic:
- `@cypher(statement: String!, columnName: String!)` on FIELD_DEFINITION. Field value comes from a Cypher statement. `this` is the parent node. Field arguments are Cypher params `$argName`. `$jwt` and `$context`/`cypherParams` are available. Can be on node fields, relationship properties (7.4.1), and on `Query`/`Mutation` fields (root custom queries and mutations). Target can be a scalar, a `@node` type (then it gets generated `where`, `sort` and nested fields), an interface, a union, or a non-node type (7.1.0).
- Filtering and sorting on `@cypher` fields: scalar `@cypher` fields get filters (6.x) and sorting. Lists of scalars get filters. Relationship-like `@cypher` fields to node types get `some`/`all`/`none`/`single` style filters (I think, from the 6.x changelog "Add cypher filtering on lists of scalars").
- `@customResolver(requires: SelectionSet)` on FIELD_DEFINITION. The field is resolved by a user JS resolver from `resolvers`. `requires` lists fields (any depth, including relationships, as a selection set string) that the library must fetch so the resolver can use them. The field is not filterable or sortable.
- `@relayId` on FIELD_DEFINITION. Marks the global ID field. Adds `Node` interface, `node(id: ID!)` root query, and a unique constraint requirement. The `id` is base64 of `<Type>:<value>`.

Security:
- `@authentication(operations: [AuthenticationOperation!] = all, jwt: JWTPayloadWhere)` on OBJECT, FIELD_DEFINITION, SCHEMA. Operations: `CREATE`, `READ`, `AGGREGATE`, `UPDATE`, `DELETE`, `CREATE_RELATIONSHIP`, `DELETE_RELATIONSHIP`, `SUBSCRIBE`.
- `@authorization(filter: [<T>AuthorizationFilterRule!], validate: [<T>AuthorizationValidateRule!])` on OBJECT, FIELD_DEFINITION. Generated per type. See auth section.
- `@subscriptionsAuthorization(filter: [<T>SubscriptionsAuthorizationFilterRule!])` on OBJECT, FIELD_DEFINITION.
- `@jwt` on OBJECT. Marks a type as the shape of the JWT payload. Its fields become filterable in `jwt: {...}` rules. Only one per schema.
- `@jwtClaim(path: String!)` on fields of the `@jwt` type. Maps a field to a nested or odd claim path like `"myApplication.roles"` or `"https://example\\.com/roles"`.

Other directives:
- `@deprecated` on generated fields is propagated. User directives on fields are copied to generated types (`tests/schema/directives/custom-directive-propagation.test.ts`). A warning is logged for unknown directives (`@customDirective` warning, fixed in 7.5.0).
- Apollo Federation directives (`@key`, `@shareable` and so on) are accepted with `extend schema @link(...)` and `getSubgraphSchema()`.
- Removed directives: `@auth` (4.0), `@computed` (4.0, use `@customResolver`), `@callback` (4.0, use `@populatedBy`), `@queryOptions` (4.0, use `@limit`), `@unique` (7.0), `@private` (7.0). `@exclude`, `@readonly` and `@writeonly` are also gone (replaced by `@query`/`@mutation`/`@subscription` and `@selectable`/`@settable`). I did not find the exact version for these three.
- Docs disagree with code:
  - `@relationship` page in `database-mapping.adoc` shows `queryDirection = DEFAULT_DIRECTED` and `CONNECT_OR_CREATE` in the default `nestedOperations`. Code: `DIRECTED` and no `CONNECT_OR_CREATE`. `field-configuration.adoc` also shows `DEFAULT_DIRECTED`.
  - `@relationshipProperties` docs say "can only be used on interfaces". Code: `OBJECT` only.
  - `@selectable` docs show `onAggregate: Boolean! = true`. Code default is `false`.
  - `@filterable` docs show `byAggregate: Boolean! = true`. Code default is `false`.
  - `@subscription` docs show enum `SubscriptionFields` with `DELETE`. Code: enum `SubscriptionEvent` with `DELETED`.
  - Docs examples still show `directed: Boolean = true` on relationship fields. 7.0 removed `directed`. Code does not generate it.
  - `@node` docs example uses `@node(label: [...])`. The argument is `labels`.

## Generated queries

- For `type Movie @node`: `movies(where: MovieWhere, sort: [MovieSort!], limit: Int, offset: Int): [Movie!]!` (the "entity API") and `moviesConnection(where, sort, first: Int, after: String): MoviesConnection!` (the "connection API", Relay style).
- `MoviesConnection { edges: [MovieEdge!]!, totalCount: Int!, pageInfo: PageInfo!, aggregate: MovieAggregate!, groupBy(fields: MovieGroupByInput!): [MovieGroupBy!]! }`. `groupBy` only when a field has `@groupBy`. `MovieEdge { cursor, node }`.
- Root field names use the camel-case plural of the type name (`pluralize` library). `@plural` overrides it.
- Relationship fields on the type: `actors(where, sort, limit, offset): [Actor!]!` and `actorsConnection(where: MovieActorsConnectionWhere, sort: [MovieActorsConnectionSort!], first, after): MovieActorsConnection!`. Relationship edges are `MovieActorsRelationship { cursor, node, properties: ActedIn! }`. Edge properties are only readable in the connection field.
- Interfaces with `@node` implementers get root `productions` and `productionsConnection` (with `sort`) (6.x). Interfaces without any `@node` implementation get no queries (7.0).
- Unions get a root list query only: `searches(where: SearchWhere, limit, offset): [Search!]!`. No connection and no sort for unions.
- `@fulltext` and `@vector` add search root queries (see directives). Both return `<Plural>IndexConnection { edges: [<T>IndexEdge { cursor, node, score: Float! }], pageInfo, totalCount }`. Arguments: `phrase: String!` or `vector: [Float!]`, plus `where: <T>IndexWhere { node, score: FloatWhere { min, max } }`, `sort: [<T>IndexSort { node, score }]`, `first`, `after`.
- `@relayId` adds the `Node` interface and `node(id: ID!): Node` root query.
- `@cypher` on `Query` fields adds custom root queries. Arguments become Cypher parameters.
- `@query` can turn off list, connection, or aggregate per type or for the schema.
- Single (non-list) relationship fields (`director: Person` or `director: Person!`): return one node or null. If several relationships exist, one is returned (not deterministic). Connection keeps list shape. Docs say the field must be nullable. Code allows `Person!` since 7.5.0. Docs disagree with code here.
- `queryDirection: UNDIRECTED` makes reads match the relationship in both directions.
- `features.limitRequired: true` makes `limit` (and `first`) required on all list reads (`tests/schema/limit-required.test.ts`).
- No root "get by ID" field for node types. You filter the list with `where: { id: { eq: ... } }`. Only `node(id:)` with `@relayId`.

## Filtering grammar (`<Type>Where`)

- Shape: `{ AND: [W!], OR: [W!], NOT: W, <field>: <ScalarFilters>, <rel>: <T>RelationshipFilters, <rel>Connection: <T><Rel>ConnectionFilters }`. `NOT` is a single object, not a list.
- Same `where` input is used for queries, connections, `update*`, `delete*`, nested operations, subscriptions and authorization rules.
- `StringScalarFilters`: `eq`, `in`, `contains`, `startsWith`, `endsWith`. Opt-in by `features.filters.String`: `lt`, `lte`, `gt`, `gte` (`LT`, `LTE`, `GT`, `GTE`), `matches` (regex, `MATCHES`), `caseInsensitive: CaseInsensitiveStringScalarFilters` (`CASE_INSENSITIVE`, 7.2.0, translates to `toLower(x) = toLower($p)`).
- `IDScalarFilters`: `eq`, `in`, `contains`, `startsWith`, `endsWith`. `matches` opt-in with `features.filters.ID.MATCHES`.
- `IntScalarFilters`, `FloatScalarFilters`, `BigIntScalarFilters`: `eq`, `in`, `lt`, `lte`, `gt`, `gte`. Temporal filters (`DateScalarFilters`, `DateTimeScalarFilters`, `DurationScalarFilters` and so on): same set.
- `BooleanScalarFilters`: `eq` only.
- Enum filters `<Enum>EnumScalarFilters`: `eq`, `in`. Custom scalar filters `<Scalar>ScalarFilters`: `eq`, `in`.
- List property filters (`StringListFilters`, `IntListFilters` and so on): `eq: [T!]` (whole list) and `includes: T`.
- Spatial: `PointFilters { eq, in, distance: PointDistanceFilters { from: PointInput!, eq, lt, lte, gt, gte } }`. Same for `CartesianPointFilters`. Distance is in metres for `Point`.
- Null: `{ field: { eq: null } }` is `IS NULL`. Not-null is `NOT: { field: { eq: null } }`. There is no `ne` or `isNull` operator. Non-equality is only by `NOT`.
- Relationship filters `<Target>RelationshipFilters { all, none, single, some }` each taking `<Target>Where`. Map to Cypher `all()`, `none()`, `single()`, `any()` list predicates (implemented as `EXISTS`/`COUNT` subqueries).
- Single relationship filter: `director: PersonWhere` directly. `NOT: { director: null }` checks existence (7.5.1 fix).
- Connection filters `<T><Rel>ConnectionFilters { all, none, single, some, aggregate }`. Each `all`/`some`/... takes `<T><Rel>ConnectionWhere { AND, OR, NOT, node: <Target>Where, edge: <RelProps>Where }`. So filters can use edge (relationship) properties.
- Aggregate filters in `<rel>Connection: { aggregate: { count: { nodes: IntScalarFilters, edges: IntScalarFilters }, node: <...>NodeAggregationWhereInput, edge: <Props>AggregationWhereInput, AND, OR, NOT } }`.
  - Int/Float/BigInt aggregation filters: `average`, `min`, `max`, `sum`, each with scalar filters (`{ average: { gt: 18 } }`).
  - String aggregation filters: `averageLength`, `shortestLength`, `longestLength`.
  - DateTime and other temporal: `min`, `max`. Duration: `average`, `min`, `max`.
  - ID: no aggregation filters (7.0).
  - Without `@filterable`, aggregate filters are generated (`filterable?.byAggregate !== false` in `AttributeAdapter.ts`). With an explicit `@filterable(...)`, `byAggregate` defaults to `false` in code, so writing `@filterable(byValue: true)` turns aggregate filters off. Docs say the default is `true`.
- Interface relationship filter: `typename: [Movie]` (was `typename_IN` before 7.0).
- Union relationship filter: `{ <MemberType>: <MemberType>Where }` per member, for example `content(where: { Blog: { title: { eq: "x" } } })`.
- `@cypher` fields: scalar results are filterable with the normal scalar filters. Node-typed `@cypher` fields are filterable with `all`/`none`/`single`/`some` (I think, based on 6.x changelog "Add filtering on scalar custom cypher fields" and "Add cypher filtering on lists of scalars").
- Fulltext score filter: `score: FloatWhere { min, max }`.
- Deprecated old style still generated: `title_EQ`, `title_CONTAINS`, `actors_SOME`, `actors_ALL`, `actorsConnection_SOME`, `actorsAggregate` filters and similar. All `@deprecated`. `features.excludeDeprecatedFields: { attributeFilters, relationshipFilters, aggregationFilters, aggregationFiltersOutsideConnection, mutationOperations }` removes them.
- Removed: implicit equality `title: "x"` (7.0), `_NOT` suffix filters (6.0), `_NOT_IN`, `_NOT_CONTAINS` and so on.

## Sorting and pagination

- `sort: [<Type>Sort!]`. `<Type>Sort { <field>: SortDirection }`. `SortDirection` is `ASC` or `DESC`. Order of the list is the sort priority. Fields inside one sort object have no guaranteed order (generated description says so).
- Sortable fields: scalars, enums, temporals, scalar `@cypher` fields. Not lists, not relationships. `@sortable(byValue: false)` removes a field.
- Connection sort: `<T><Rel>ConnectionSort { node: <Target>Sort, edge: <Props>Sort }`. Sorting by relationship properties only works in connections.
- No sort by aggregate (for example by count of related nodes). No sort by nested relationship field. No `NULLS FIRST`/`NULLS LAST` option.
- Offset pagination: `limit` and `offset` on list fields (top level and nested).
- Cursor pagination: `first` and `after` on connections. `PageInfo { hasNextPage, hasPreviousPage, startCursor, endCursor }`. No `last` and `before` (no backward pagination).
- Cursors are offset based (`offsetToCursor`/`cursorToOffset` from `graphql-relay`, `src/schema/pagination.ts`). They are not keyset cursors.
- `totalCount` on connections. Since 7.2.7 it is only computed when selected.
- `@limit(default, max)` per type. `features.limitRequired` forces a limit.
- Docs `pagination.adoc` say cursor pagination is "on relationship fields". Code also has root connections.

## Aggregations

- In 7.x aggregations are only inside connections: `moviesConnection { aggregate { count { nodes } node { title { longest shortest } } } }`. Top-level `moviesAggregate` and nested `actorsAggregate` fields were removed in 7.0.
- Root: `MovieAggregate { count: Count { nodes }, node: MovieAggregateNode }`.
- Nested: `MovieActorsConnection.aggregate: MovieActorActorsAggregateSelection { count: CountConnection { nodes, edges }, node: {...}, edge: {...} }`. `edge` aggregates relationship properties.
- Selections per type: `IntAggregateSelection { min, max, average, sum }`, `FloatAggregateSelection` (same), `BigIntAggregateSelection` (same), `StringAggregateSelection { shortest, longest }`, `DateTimeAggregateSelection { min, max }` (also `LocalDateTime`, `Time`, `LocalTime`, `Date`), `DurationAggregateSelection { min, max }`. No aggregates for `ID` (7.0), Boolean, lists, points.
- Aggregates honour `where` but ignore `first`/`after` (docs say so).
- `@query(aggregate: false)`, `@relationship(aggregate: false)`, `@selectable(onAggregate:)` control them.
- No `count distinct`, no `stddev`, no custom aggregate function. No `having`.

## Group by (`@groupBy`, 7.5.0)

- Field `groupBy(fields: <T>GroupByInput!): [<T>GroupBy!]!` on root connections only. `<T>GroupByInput { <field>: Boolean }` for each `@groupBy` field.
- `<T>GroupBy { edges: [<T>GroupByEdge { node }] }`. Each group holds the nodes that share the same values. There is no group key field and no per-group aggregate in the generated type.
- Nested `groupBy` on relationship connections is in branch `group-by-nested` (not merged).

## Types and scalars

- Built-in GraphQL scalars: `Int` (Neo4j integer, 32-bit range in GraphQL), `Float`, `String`, `Boolean`, `ID`.
- Extra scalars added by the library (`src/graphql/scalars/`): `BigInt` (64-bit, serialized as string), `Date`, `DateTime`, `LocalDateTime`, `Time`, `LocalTime`, `Duration` (ISO 8601). Mapped to Neo4j temporal types.
- Spatial object types: `Point { longitude, latitude, height, crs, srid }` and `CartesianPoint { x, y, z, crs, srid }`. Inputs `PointInput`, `CartesianPointInput`. Distance filters.
- Enums are stored as strings. Custom scalars are allowed (filters `eq` and `in`, no other operators).
- Lists of scalars are allowed. Lists of nullable elements (`[String]`) are rejected (7.0) because Neo4j lists cannot hold nulls.
- Interfaces and unions of `@node` types are supported for root queries and relationship targets. All implementers or members must have `@node`, or none (7.0 validation).
- Types without `@node` are plain GraphQL types. They are only usable as `@cypher` results or custom resolver results.
- Relationship properties can only be scalars, enums, temporals, spatial, and lists of these. No nested objects on edges.
- `_emptyInput: Boolean` placeholder appears in create and update inputs when a type has only generated or relationship fields (troubleshooting page).
- No JSON scalar. No Decimal. No file upload.

## Generated mutations

- Root fields: `createMovies(input: [MovieCreateInput!]!): CreateMoviesMutationResponse!`, `updateMovies(where: MovieWhere, update: MovieUpdateInput): UpdateMoviesMutationResponse!`, `deleteMovies(where: MovieWhere, delete: MovieDeleteInput): DeleteInfo!`.
- Responses: `CreateMoviesMutationResponse { info: CreateInfo { nodesCreated, relationshipsCreated }, movies: [Movie!]! }`. `UpdateMoviesMutationResponse { info: UpdateInfo { nodesCreated, nodesDeleted, relationshipsCreated, relationshipsDeleted }, movies }`. `DeleteInfo { nodesDeleted, relationshipsDeleted }`. The returned nodes support the full nested selection.
- All mutations are bulk. There is no single-object `createMovie` or `updateMovie(id:)`. `update` and `delete` act on everything that matches `where`. A missing `where` means all nodes.
- Each root mutation field is one Cypher statement in one write transaction. Several root fields in one request run in separate transactions (I think, based on one resolver per field).
- Create batching: top-level creates are compiled with `UNWIND` (`UnwindCreateOperation`, `src/translate/unwind-create.ts`). The docs say this optimization is off when `@populatedBy`, `connect`, or interfaces/unions are used.
- No upsert. `connectOrCreate` was removed in 7.0. `MERGE` is only possible with custom `@cypher` mutations.
- `connect` always creates a new relationship, even if one exists (7.0). So duplicate relationships are possible.
- Scalar update operators (`<Type>ScalarMutations`): `set` for all. `Int` and `BigInt`: `add`, `subtract`. `Float`: `add`, `subtract`, `multiply`, `divide`. Math operators run in Cypher and validate overflow and null with `apoc.util.validate`.
- List update operators (`List<Type>Mutations`): `set`, `push` (one item or a list), `pop: Int` (remove N items from the end). No remove-by-value and no insert-at-index.
- Updating the same field twice in one update throws (6.0).
- Deprecated old style update fields still generated: `title_SET`, `count_INCREMENT`, `count_DECREMENT`, `rating_ADD`, `tags_PUSH`, `tags_POP` and so on. Removed by `excludeDeprecatedFields.mutationOperations`.
- `@id`, `@timestamp` and `@populatedBy` fields are filled by the library. `@default` fills the create input default. `@settable` hides fields from inputs.

## Nested mutations

- Create input for a relationship field `actors: MovieActorsFieldInput { create: [{ node: ActorCreateInput!, edge: ActedInCreateInput }], connect: [{ where: { node: ActorWhere! }, edge: ActedInCreateInput, connect: [ActorConnectInput!] }] }`. `edge` is required when the relationship properties type has required fields.
- Update input for a relationship field `actors: [MovieActorsUpdateFieldInput!]` with `create`, `connect`, `disconnect: [{ where: MovieActorsConnectionWhere, disconnect: ActorDisconnectInput }]`, `delete: [{ where: MovieActorsConnectionWhere, delete: ActorDeleteInput }]`, `update: { where: MovieActorsConnectionWhere, node: ActorUpdateInput, edge: ActedInUpdateInput }`. `where` was moved inside `update` in 7.0.
- Delete input `delete: { actors: [{ where, delete }] }` cascades deletes along relationships to any depth. Delete of a node uses `DETACH DELETE` (`DeleteOperation.ts`).
- Nesting is recursive: `connect` inside `connect`, `create` inside `create`, `delete` inside `delete`, `disconnect` inside `disconnect`.
- Connect and disconnect select targets by `where` filter (can match many nodes). There is no connect by ID only shortcut.
- Interface relationship targets: nested inputs are split per implementing type (`{ Movie: {...}, Series: {...} }`) in create. For connect, update, delete and disconnect the `where` is on the interface with `typename` filter.
- Union relationship targets: nested inputs are split per member type (`content: { Blog: { create: [...] } }`).
- `@relationship(nestedOperations: [...])` limits which of `CREATE`, `UPDATE`, `DELETE`, `CONNECT`, `DISCONNECT` are generated. Empty list removes nested inputs.
- Single relationship fields: create and delete only. Nested `connect` and `disconnect` are not available on the single side (docs). 7.5.0 changelog says delete is only generated for nullable single fields.
- Relationship cardinality is not enforced. I think the 5.x checks ("Relationship field X.y cannot have more than one node linked") are gone in 7.x. I did not find that message in `src`.
- `nestedOperations` follow `queryDirection` (7.0). Undirected relationships match both directions in nested `update`/`delete`/`disconnect` `where`.
- Docs (`mutations/index.adoc`) warn that complex nested mutations can produce big Cypher and out-of-memory errors.

## Subscriptions

- Opt-in: `features.subscriptions: true` (or a `Neo4jGraphQLSubscriptionsCDCEngine` instance) plus `@subscription` on types or `extend schema @subscription`.
- Only Neo4j CDC (Change Data Capture, Enterprise or Aura, `FULL` mode) is supported since 6.0. The engine polls `db.cdc.query` every `pollTime` ms (default 1000).
- `Neo4jGraphQLSubscriptionsCDCEngine({ driver, pollTime, queryConfig: { database }, onlyGraphQLEvents })`. `onlyGraphQLEvents: true` ignores changes not made by the library (it tags transactions with metadata).
- Because it uses CDC, changes made outside GraphQL (Cypher, other apps) also trigger events by default.
- Generated root fields per type: `movieCreated(where: MovieSubscriptionWhere): MovieCreatedEvent!`, `movieUpdated(where)`, `movieDeleted(where)`.
- Event types: `MovieCreatedEvent { event: EventType!, createdMovie: MovieEventPayload!, timestamp: Float! }`, `MovieUpdatedEvent { event, updatedMovie, previousState, timestamp }`, `MovieDeletedEvent { event, deletedMovie, timestamp }`. `EventType` is `CREATE`, `UPDATE`, `DELETE`.
- `MovieEventPayload` only has scalar properties of the node. No relationships, no `@cypher` fields, no nested selection.
- `MovieSubscriptionWhere`: `AND`, `OR`, `NOT` and scalar filters on node properties only. No relationship filters. Docs say temporal and spatial filters are not supported.
- Relationship subscriptions (`movieRelationshipCreated`, `movieRelationshipDeleted`) were removed in 6.0. Docs `filtering.adoc` still talks about relationship events. Docs disagree with code.
- No aggregations in subscriptions. No live queries. No connection-level subscriptions.
- Transport is up to the server. Docs use `graphql-ws` with `ws`.
- CDC cursor errors (52N27 to 52N30) reset the cursor (7.1 to 7.2). I think events can be lost in that case.
- 7.5.6 fixed a bug where the JWT from WebSocket `connectionParams` was trusted without verification.

## Authentication and authorization

- JWT based. The library does not issue tokens. Context fields: `token` (encoded, the library decodes and verifies with `features.authorization.key`) or `jwt` (already decoded payload, trusted).
- `features.authorization: { key: string | { url, options } | (context) => key, verify?: boolean, verifyOptions?: JWTVerifyOptions }`. `key` string is a symmetric secret. `{ url }` is a remote JWKS endpoint (uses `jose`). A function returns a key per request. `verify: false` decodes without verifying.
- `@jwt` type describes extra claims for rules. `@jwtClaim(path:)` maps nested claims (uses `dot-prop`). Without `@jwt`, only standard claims (`iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`) can be used in rules. `@jwtClaim` mapping only applies when the library decodes the token.
- `@authentication(operations, jwt)`: checks that a valid JWT exists (and optionally matches `jwt: JWTPayloadWhere`) before Cypher runs. On schema, type, or field. Field level applies only when the field is selected or set. Unauthenticated requests never reach the database.
- `@authorization(filter: [...], validate: [...])` on type or field.
  - Filter rule: `{ operations: [AuthorizationFilterOperation!] = all, requireAuthentication: Boolean = true, where: <T>AuthorizationWhere }`. Operations: `READ`, `AGGREGATE`, `UPDATE`, `DELETE`, `CREATE_RELATIONSHIP`, `DELETE_RELATIONSHIP`. Adds a `WHERE` predicate. Unauthorized rows are silently dropped.
  - Validate rule: `{ operations: [AuthorizationValidateOperation!] = all, when: [BEFORE, AFTER] = both, requireAuthentication = true, where }`. Operations add `CREATE`. Fails the whole query via `apoc.util.validate`/`apoc.util.validatePredicate` in Cypher. The message is `@neo4j/graphql/FORBIDDEN` and it is mapped to `Neo4jGraphQLForbiddenError`. Missing auth gives `@neo4j/graphql/UNAUTHENTICATED` (`Neo4jGraphQLAuthenticationError`). `CREATE` is `AFTER` only. `READ`, `AGGREGATE`, `DELETE` are `BEFORE` only.
  - `<T>AuthorizationWhere { AND, OR, NOT, node: <T>Where, jwt: JWTPayloadWhere }`. `node` uses the full filter grammar including relationship filters. Values `"$jwt.<claim>"` and `"$context.<key>"` are substituted.
  - Rules in one list are OR-ed. `filter` and `validate` lists are AND-ed.
- `@subscriptionsAuthorization(filter: [{ events: [CREATED, UPDATED, DELETED], requireAuthentication, where: { node, jwt } }])`. Filters events before they are sent. `@authorization` does not apply to subscriptions.
- `@authentication(operations: [SUBSCRIBE])` covers subscriptions.
- Known gaps (docs warnings):
  - Field-level `@authentication` and `@authorization` do not protect a field in `where` or `sort`. Docs suggest adding `@filterable(byValue: false, byAggregate: false)` and `@sortable(byValue: false)`.
  - No `UPDATE_RELATIONSHIP` operation. Relationship property updates are not protected by `@authorization` (warning added 2026-09). Use `@settable(onUpdate: false)`.
  - If a query matches no rows, authorization is not triggered. The result is empty, not an error.
- Dynamic labels: `@node(labels: ["$jwt.tenant"])` gives label-based multi-tenancy.
- Database-level security: `context.sessionConfig.impersonatedUser` runs queries as another Neo4j user (impersonation). `sessionConfig.auth` switches user per session (user switching). This uses Neo4j RBAC.
- `@selectable`/`@settable` are recommended to hide fields entirely.
- No role or permission model beyond JWT predicates. No field masking with null (filter drops rows, validate errors).

## Query protection and performance

- `@limit(default, max)` per type. `features.limitRequired: true` makes `limit` required everywhere.
- `features.complexityEstimators: true` adds per-field complexity estimators for the `graphql-query-complexity` package. Export `DefaultComplexityEstimators`. The algorithm changed in 7.5.0. The library itself does not reject queries. The server must call `getComplexity`.
- No built-in depth limit, rate limit, or persisted queries. Docs (`securing-a-graphql-api.adoc`) point to external tools (`graphql-depth-limit`, Apollo features).
- `context.cypherQueryOptions` sets Cypher query options (`runtime`, `planner`, `addVersionPrefix` and so on).
- `context.transaction: { timeout, metadata }` (7.3.0) and `transactionMetadata` set driver transaction config.
- `totalCount` and `pageInfo` are not computed when not selected (7.2.7).
- `features.excludeDeprecatedFields` shrinks the schema (`optimization.adoc`).

## Custom logic and schema extension

- `resolvers` option: user resolvers are merged into the generated schema (`@graphql-tools/schema`). Custom `Query`, `Mutation` and `Subscription` fields without `@cypher` need a resolver.
- `@cypher` root queries and mutations: the library runs the statement. Mutation `@cypher` runs in a write transaction. Return types can be nodes with nested generated fields.
- `@customResolver(requires:)` for computed fields with declared dependencies (also through relationships and inline fragments). Cannot require generated fields like connections or aggregates.
- `@populatedBy` callbacks for write-time computed values.
- `@authentication` works on custom resolver root fields (6.x). Field-level and type-level rules are both enforced since 7.6.0.
- `extend type` and `extend schema` are supported for adding directives (for example `extend type Movie @authorization(...)`).
- User directives on fields are copied to the generated output types.
- Custom input validation: none built in. No validator directives (like `@constraint`). Validation is up to custom resolvers or Neo4j constraints.
- Unreleased POC: branch `poc-hooks` (2025-06-11, 915 commits behind `dev`) adds a `@hook(callback: String!)` directive on OBJECT and FIELD_DEFINITION for JS callbacks around reads. Not merged.

## Errors

- Error classes (`src/classes/Error.ts`): `Neo4jGraphQLError` (extends `GraphQLError`), `Neo4jGraphQLForbiddenError`, `Neo4jGraphQLAuthenticationError`, `Neo4jGraphQLConstraintValidationError` (database constraint violation), `Neo4jGraphQLRelationshipValidationError`, `Neo4jGraphQLSchemaValidationError`.
- Schema build errors use `DocumentValidationError` with paths in the type definitions.
- Errors are top-level GraphQL errors. There are no typed error payloads in mutation results.

## Apollo Federation

- Federation v2 only. Type definitions must contain `extend schema @link(url: "https://specs.apollo.dev/federation/v2.x", import: [...])`. Otherwise `getSubgraphSchema()` throws.
- `getSubgraphSchema()` uses `@apollo/subgraph` `buildSubgraphSchema`. Supported directives (`src/classes/Subgraph.ts`): `@key`, `@extends`, `@shareable`, `@inaccessible`, `@override`, `@external`, `@provides`, `@requires`, `@tag`, `@composeDirective`, `@interfaceObject`.
- `__resolveReference` is generated for each `@key` type. It is translated to Cypher (`src/translate/translate-resolve-reference.ts`). `@key(resolvable: false)` skips it.
- The repo has `packages/apollo-federation-subgraph-compatibility` for the Apollo subgraph compatibility test suite.

## Relay

- Connections and `PageInfo` follow the Relay connection spec (forward pagination only).
- `@relayId` on one field per type makes the type implement `Node { id: ID! }`. The generated `id` is a global ID (base64 of type name and value). `node(id: ID!): Node` root query refetches any such type. The field value must be unique. Docs warn the directive "does not guarantee uniqueness". `assertIndexesAndConstraints` checks for a unique constraint.
- No Relay-style mutation input (`clientMutationId`).

## Introspector (`@neo4j/introspector`)

- Separate package in `packages/introspector`. Version 5.0.1 (2025-10-31). Still in the monorepo.
- API: `toGraphQLTypeDefs(sessionFactory, readonly = false): Promise<string>` and `toGenericStruct(sessionFactory)`. Reads labels, properties and relationship types from a live DB (APOC `apoc.meta` and `db.schema.*` procedures, I think) and writes SDL with `@node`, `@relationship` (with properties types) and, for `readonly: true`, `@mutation(operations: [])`.
- Properties with mixed types across nodes are skipped (logged with debug).
- Docs mention `@node` arguments `label` and `additionalLabels`. Those are old (pre 4.x) names. Current code uses `labels`. Docs disagree with code.
- Intended as a one-time starting point. No schema migration or sync.

## OGM (`@neo4j/graphql-ogm`)

- Object Graph Mapper for server-side code. It used the same type definitions to give model classes with methods like `find`, `create`, `update`, `delete`, `aggregate`, plus a `generate` function for TypeScript types (I think, from 5.x knowledge, not verified in this run).
- Not in the `dev` branch any more. Not supported in 7.x. 7.0.0 removed `@private` "intended to be used with the library `@neo4j/graphql-ogm` which is no longer supported".
- Still released for v5 LTS: `@neo4j/graphql-ogm@5.12.15` (2026-08-18).

## Tooling and hosting

- Neo4j GraphQL Toolbox (`https://graphql-toolbox.neo4j.io`): web IDE. Connect to a DB, write or introspect type definitions, build the schema, run queries. I think its source moved out of this monorepo (no `packages/graphql-toolbox` in `dev`).
- GraphQL for Neo4j AuraDB ("Data APIs" in Aura Console): hosted version of the library. Created with Aura Console or `aura-cli`. Auth by API key or JWKS. Docs list what it does not support: `@customResolver`, `@populatedBy`, `@vector`, `@subscriptionsAuthorization`.
- Deprecated products: GRANDstack starter, Neo4j GraphQL Architect.
- Debug logging: `DEBUG=@neo4j/graphql:*` or constructor `debug: true`. Logs generated Cypher and params.

## Docs and code disagreements (summary)

- `@relationship` defaults: docs show `DEFAULT_DIRECTED` and `CONNECT_OR_CREATE`. Code has `DIRECTED` and no `CONNECT_OR_CREATE`.
- `@relationshipProperties`: docs say interfaces only. Code: objects only.
- `@selectable(onAggregate)` and `@filterable(byAggregate)` defaults: docs `true`, code `false` when the directive is present.
- `@subscription` enum: docs `SubscriptionFields` with `DELETE`. Code `SubscriptionEvent` with `DELETED`.
- `directed` argument still shown in docs examples. Removed in 7.0.
- `@fulltext` docs show the 6.x list-result query. Code generates a connection with `edges { score node }`.
- `@vector` docs show `queryName: String` (optional) and `provider: String`. Code: `queryName: String!` and `provider: VectorProvider` enum.
- `@limit(max)` docs wording says a higher value "is used instead". Code caps to `max`.
- Single relationships: docs say they must be nullable. Code allows non-null since 7.5.0.
- Subscription filtering docs describe relationship events. Code removed them in 6.0.
- Introspector docs mention `label` and `additionalLabels`. Code uses `labels`.
- Pagination docs say cursor pagination is for relationship fields. Root connections exist too.

## Not supported

- No root get-by-id field (only `node(id:)` with `@relayId`).
- No upsert (`connectOrCreate` removed in 7.0). No `MERGE` except custom `@cypher`.
- No backward pagination (`last`, `before`). Cursors are offset based.
- No sort by aggregate or by nested related field. No nulls-first or nulls-last control.
- No `ne`, `isNull` or `notIn` operators (use `NOT` and `eq: null`). Regex, string `lt`/`gt`, and case-insensitive filters are opt-in.
- No `distinct`, no `count distinct`, no `having`. Group by has no group key output and no per-group aggregates. Nested group by is not merged.
- No relationship subscriptions (removed 6.0). No subscription without Neo4j CDC (Enterprise or Aura). No nested data in subscription payloads.
- No relationship cardinality enforcement. Duplicate relationships possible on `connect`.
- No `UPDATE_RELATIONSHIP` authorization operation.
- No built-in depth limit, rate limit, persisted queries, caching, or dataloader.
- No input validation directives. No file upload. No JSON or Decimal scalar.
- No schema migrations, no index or constraint creation (only `assertIndexesAndConstraints` checks, since 6.0).
- No OGM in 7.x.
- Aura hosted version lacks `@customResolver`, `@populatedBy`, `@vector`, `@subscriptionsAuthorization`.
- Requires APOC core in the database (validation uses `apoc.util.validate`). Requires Neo4j 5.23 or later.

## Sources

- Code: https://github.com/neo4j/graphql (branch `dev`, `packages/graphql/src/graphql/directives/`, `src/classes/`, `src/types/index.ts`, `src/translate/`, `tests/schema/` snapshots, `tests/tck/`).
- Changelog: https://github.com/neo4j/graphql/blob/dev/packages/graphql/CHANGELOG.md
- Releases: https://github.com/neo4j/graphql/releases and npm `@neo4j/graphql`, `@neo4j/graphql-ogm`, `@neo4j/introspector`.
- Docs source: https://github.com/neo4j/docs-graphql (branch `7.x`, `modules/ROOT/pages/`).
- Docs site pages (same content): https://neo4j.com/docs/graphql/current/
  - https://neo4j.com/docs/graphql/current/directives/
  - https://neo4j.com/docs/graphql/current/filtering/
  - https://neo4j.com/docs/graphql/current/queries-aggregations/
  - https://neo4j.com/docs/graphql/current/mutations/
  - https://neo4j.com/docs/graphql/current/relationships/
  - https://neo4j.com/docs/graphql/current/subscriptions/
  - https://neo4j.com/docs/graphql/current/security/
  - https://neo4j.com/docs/graphql/current/integrations/apollo-federation/
  - https://neo4j.com/docs/graphql/current/integrations/relay-compatibility/
  - https://neo4j.com/docs/graphql/current/introspector/
  - https://neo4j.com/docs/graphql/current/versioning/
