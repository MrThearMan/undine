# AWS AppSync findings

Versions checked: managed service, no source repo. Docs read on 2026-10-11 from the markdown variants of the AWS docs pages (`<page>.md` next to each `<page>.html`, served as `text/markdown`). AppSync GraphQL Developer Guide: 189 pages listed in https://docs.aws.amazon.com/appsync/latest/devguide/llms.txt. AppSync Events Developer Guide: 65 pages listed in https://docs.aws.amazon.com/appsync/latest/eventapi/llms.txt. Service quotas from https://docs.aws.amazon.com/general/latest/gr/appsync.html.
AppSync is a managed GraphQL service. The user uploads an SDL schema. Each field can get a resolver. A resolver is a small piece of code (JavaScript on the `APPSYNC_JS` runtime, or Apache VTL) that turns a GraphQL field into a request to a data source (DynamoDB, Lambda, HTTP, RDS Data API, OpenSearch, EventBridge, Bedrock, or `NONE`) and maps the response back. AppSync also has a separate pub/sub product, AppSync Events (no GraphQL). This file covers both, with the focus on GraphQL APIs.

## Sources and maintenance status

- No public source repo. The old docs repo `awsdocs/aws-appsync-developer-guide` returns 404 on the GitHub API (deleted or private). AWS removed most `awsdocs/*` repos in 2023, I think.
- `llms.txt` exists per guide (devguide and eventapi). The root https://docs.aws.amazon.com/llms.txt also exists. Every page has a `.md` variant. The devguide also has a `full.md` with the whole guide in one file (about 235k words).
- The devguide has no document history page anymore. `doc-history.html` redirects to the guide root. One IAM page still links to "the AWS AppSync Document history page" and its RSS feed. That page is gone.
- The Events guide has a document history (`event-api-document-history.md`): Events released 2024-10-30, publish over WebSocket 2025-03-13, data source integrations 2025-04-24 (marked "Latest documentation update").
- The devguide intro says: "As of Mar 13, 2025, you can build a real-time PubSub API powered by WebSockets using AWS AppSync Events."
- VTL is in maintenance mode in the docs. Many VTL pages carry the note "We now primarily support the APPSYNC_JS runtime and its documentation."
- Service is active. Region list has 32 commercial Regions plus 2 China Regions.

## Architecture and API types

- API types: GraphQL API (`GraphqlApi`), Merged API (a GraphQL API that combines source APIs), Event API (AppSync Events, pub/sub over HTTP and WebSocket, no GraphQL).
- GraphQL API endpoints: `https://<id>.appsync-api.<region>.amazonaws.com/graphql` (HTTP POST) and `wss://<id>.appsync-realtime-api.<region>.amazonaws.com/graphql` (subscriptions).
- Schema is SDL only. Upload through console, CLI (`start-schema-creation`), CloudFormation, CDK, or Amplify, I think for the last three. Max schema size 1 MB.
- Resolver attaches to `Type.field`. Fields with no resolver return the matching key from the parent result, I think (standard GraphQL default resolver). A root field with no resolver returns `null`.
- Config changes propagate asynchronously. The old config serves until propagation ends. Docs say there is no way to tell which config served a request during propagation.
- `CreateGraphqlApi` request fields: `name`, `authenticationType`, `additionalAuthenticationProviders`, `userPoolConfig`, `openIDConnectConfig`, `lambdaAuthorizerConfig`, `logConfig`, `enhancedMetricsConfig`, `xrayEnabled`, `apiType` (`GRAPHQL` or `MERGED`), `mergedApiExecutionRoleArn`, `visibility` (`GLOBAL` or `PRIVATE`), `ownerContact`, `introspectionConfig` (`ENABLED` or `DISABLED`), `queryDepthLimit`, `resolverCountLimit`, `tags`.

## Authorization modes

- Five modes (`authenticationType`): `API_KEY`, `AWS_LAMBDA`, `AWS_IAM`, `OPENID_CONNECT`, `AMAZON_COGNITO_USER_POOLS`.
- One default mode on the API plus a list of `additionalAuthenticationProviders`. Max 50 auth providers per API.
- `API_KEY`, `AWS_LAMBDA` and `AWS_IAM` can appear only once in total (default plus additional). Several Cognito user pools and several OIDC providers are allowed, but no duplicate pool or issuer.
- Only one Lambda authorizer per API.
- Fields and types without an auth directive use the default mode. With additional modes, a field must carry the directive of each extra mode that may access it.
- `API_KEY`: header `x-api-key`. Keys expire after 1 to 365 days. Expiry can be extended by up to 365 days from the extension date. Max 50 keys per API. Docs say keys are for development or public APIs and for throttling unauthenticated access.
- `AWS_IAM`: SigV4-signed requests. IAM action `appsync:GraphQL`. Resource ARN can target a whole API (`apis/<id>/*`) or a root field (`apis/<id>/types/Query/fields/<name>`). Only root fields of `Query`, `Mutation`, `Subscription` are addressable in IAM policies. Typical use: Cognito identity pool roles (authenticated and unauthenticated).
- `OPENID_CONNECT`: only `issuer` is required. Discovery at `<issuer>/.well-known/openid-configuration`. Signing algorithms RS256/384/512, PS256/384/512, HS256/384/512, ES256/384/512. Optional `iatTTL`, `authTTL` (token age limits) and `clientId` (a regex, use `|` for several client IDs).
- OIDC issuer check: with several auth types AppSync validates the `iss` claim against the configured issuer. With `OPENID_CONNECT` as the only type, AppSync skips the issuer check (documented behavior).
- `AMAZON_COGNITO_USER_POOLS`: Cognito JWT in the `Authorization` header. Pools from other AWS accounts allowed. `userPoolConfig.defaultAction` is `ALLOW` or `DENY` (the security guide CLI example says `defaultEffect`, see the contradictions section). It decides access for fields without `@aws_auth` when Cognito is the only mode. `appIdClientRegex` restricts client IDs.
- `AWS_LAMBDA`: the client sends any token in `Authorization`. AppSync calls the Lambda with `{authorizationToken, requestContext: {apiId, accountId, requestId, queryString, operationName, variables}, requestHeaders}`. For the WebSocket connect, `operationName` is `"DeepDish:Connect"`.
- Lambda authorizer response keys: `isAuthorized` (required), `resolverContext` (flat key-value map, max 5 MB, exposed as `ctx.identity.resolverContext`), `deniedFields` (list of `Type.field` or full field ARNs that are forced to `null`), `ttlOverride` (seconds, `0` disables cache).
- Lambda authorizer config: `authorizerUri`, `authorizerResultTtlInSeconds`, `identityValidationExpression` (regex that rejects tokens before the Lambda call). Responses under 1,048,576 bytes are cached per API ID and token. Timeout 10 s. Cross-account authorizer Lambdas are not allowed. One Lambda may serve several APIs.
- Token clash rules: with `AWS_IAM` plus `AWS_LAMBDA`, a SigV4 signature cannot be the Lambda token. With OIDC or Cognito plus `AWS_LAMBDA`, an OIDC token cannot be the Lambda token. The docs workaround is to add random prefixes or suffixes to the token and strip them in the Lambda.
- Requests that fail authorization are not billed. Requests with a missing or invalid API key are not billed.
- Field-level `deniedFields` from the Lambda authorizer is the only built-in per-request field hiding. Other row-level or owner checks are done in resolver code with `ctx.identity` (docs page "Access control use cases": owner can read, group can read, multiple owners, public and private records, subscription checks).
- `ctx.identity` fields by mode. Cognito: `sub`, `username`, `claims`, `issuer`, `sourceIp`, `defaultAuthStrategy`. IAM: `accountId`, `cognitoIdentityPoolId`, `cognitoIdentityId`, `sourceIp`, `username`, `userArn`, `cognitoIdentityAuthType`, `cognitoIdentityAuthProvider`. OIDC: `sub`, `issuer`, `claims`. Lambda: `resolverContext`. API key: `null`.
- `util.authType()` returns the auth type used for the current request. `util.unauthorized()` throws an `Unauthorized` error for the current field.
- Data source access uses IAM service roles that AppSync assumes (`appsync.amazonaws.com` trust policy). This is separate from client auth.
- AWS WAF can be attached to a GraphQL API (rate limits, IP sets, managed rule groups, header rules). See the WAF section.

## Auth directives

- `@aws_api_key`, `@aws_iam`, `@aws_oidc`, `@aws_cognito_user_pools`, `@aws_lambda`: on object types and fields. Each marks which modes may access it. Several can be combined on one type or field (for example `type Post @aws_api_key @aws_iam`).
- A directive on a field replaces the type-level directive for that field, I think (the docs example adds `@aws_iam` on `restrictedContent` inside a `@aws_api_key @aws_iam` type, and says `API_KEY` requests then cannot read it). Directives do not inherit through the return type. The docs say the returned type must also be marked (for example `Post` must have `@aws_api_key` if `getAllPosts` does).
- `@aws_cognito_user_pools(cognito_groups: [String])`: restricts to Cognito groups. Enforced only when the API has additional modes.
- `@aws_auth(cognito_groups: [String])`: the older form. Only on fields of root types, I think (docs say `@aws_cognito_user_pools` can be used on "any field or object type definition", "unlike `@aws_auth`"). Enforced only when Cognito is the only mode. Cannot be combined with additional modes.
- `@aws_subscribe(mutations: [String])`: see Subscriptions.
- Merged API directives `@canonical`, `@hidden`, `@renamed(to:)`: see Merged APIs.
- No auth directive takes custom rules or arguments other than `cognito_groups`. No OIDC claim or IAM condition matching in directives.
- No `@aws_*` directive for rate limits, cost, or caching.

## Resolvers

- Resolver `kind`: `UNIT` (one data source, request and response handler) or `PIPELINE` (before handler, up to 10 AppSync functions, after handler). Max 10 functions per pipeline.
- AppSync function: reusable unit with its own data source, request and response handler. Functions are shared across resolvers. Pipeline data flows with `ctx.prev.result` and `ctx.stash` (stash lives for one resolver run).
- Runtimes: `APPSYNC_JS` (`runtime: {name: "APPSYNC_JS", runtimeVersion: "1.0.0"}`, field `code`) or VTL (`requestMappingTemplate`, `responseMappingTemplate`). JS is the recommended runtime. VTL docs carry a "primarily support the APPSYNC_JS runtime" note.
- JS handlers: `export function request(ctx)` returns the data source request object. `export function response(ctx)` maps `ctx.result` to the field value.
- `ctx` fields: `arguments` (`args`), `identity`, `source`, `stash`, `result`, `prev.result`, `error`, `request.headers` (multi-value headers become arrays, no `cookie` header), `request.domainName` (custom domain or `null`), `info` (`fieldName`, `parentTypeName`, `variables`, `selectionSetList`, `selectionSetGraphQL`), `env`.
- `ctx.info.selectionSetList` only lists fields of the current type. For interface or union fields it only lists interface fields. `JSON.stringify(ctx.info)` drops the selection set properties.
- `APPSYNC_JS` is a restricted ES subset. Supported: `const`/`let`/`var`, `if`, `switch`, `for-in`, `for-of`, arrow functions, rest and spread, template literals, optional chaining, `??`. Not supported: `try`/`catch`/`throw`, `while`, `do-while`, classic `for(;;)`, `continue`, labels, classes, `this`, generators, `async`/`await`, promises, `in`, `instanceof`, `++`/`--`/`~`, recursion, passing functions as arguments, function constructors, `apply`/`bind`/`call`, JS regex literals (Java regex strings in `replace`/`split`/`util.matches`). Network and file access not possible. Code is strict mode.
- `Array.prototype.sort()` takes no comparator. `JSON.parse` returns `""` for invalid JSON. `console.log`/`console.error` go to CloudWatch Logs.
- Max code size 32 KB per handler, resolver or function. Max 1,000 loop iterations. Max 5 MB evaluated response. VTL templates max 64 KB each. Max request execution time 30 s.
- Libraries: code must be one ESM file. Bundle with esbuild, keep `@aws-appsync/*` external. Inline source maps allowed (no source content). TypeScript must be transpiled first. `@aws-appsync/utils` gives types. `@aws-appsync/eslint-plugin` has rule sets `plugin:@aws-appsync/base` and `plugin:@aws-appsync/recommended` (`no-recursion`, `no-function-passing`, ...).
- Type generation: `npx @aws-amplify/cli codegen add` generates TS types for the schema.
- Testing: `EvaluateCode` API (`aws appsync evaluate-code`) runs a handler remotely with a mocked context and returns `evaluationResult` and `logs`. `EvaluateMappingTemplate` does the same for VTL. Needs IAM `appsync:EvaluateCode`. Console has a test tab with mock context.
- Errors: `util.error(message, errorType?, data?, errorInfo?)` stops the field. `util.appendError(...)` adds an error and keeps the value. `util.unauthorized()`. No `throw`.
- Early exit: `runtime.earlyReturn(obj)` in a request handler skips the data source call. In a pipeline function it moves on to the next function. VTL uses `#return` and `#return(obj)`.
- `util` (JS): `autoId`, `autoUlid`, `autoKsuid`, `matches`, `urlEncode`, `urlDecode`, `escapeJavaScript`, `authType`, `error`, `appendError`, `unauthorized`. Sub-namespaces: `util.time` (now, parse, format, epoch conversions), `util.dynamodb` (`toDynamoDB`, `toMapValues`, `toS3Object`, ...), `util.str`, `util.math`, `util.transform` (`toDynamoDBFilterExpression`, `toElasticsearchQueryDSL`, `toSubscriptionFilter`, `toDynamoDBConditionExpression`), `util.http` (`copyHeaders`, `addResponseHeader`, `addResponseHeaders`), `util.xml` (`toMap`, `toJsonString`), `util.rds` (`toJsonObject`).
- Modules: `@aws-appsync/utils/dynamodb` (`get`, `put`, `remove`, `query`, `scan`, `sync`, `update`, plus `operations` `add`, `append`, `prepend`, `replace`, `increment`, `decrement`, `updateListItem`). `@aws-appsync/utils/rds` (`select`, `insert`, `update`, `remove`, `sql` tagged template, `createPgStatement`, `createMySQLStatement`, `toJsonObject`, `typeHint`). `@aws-appsync/utils/ai` (`invokeModel`, `converse`).
- `extensions` (JS) / `$extensions` (VTL): `evictFromApiCache`, `setSubscriptionFilter`, `setSubscriptionInvalidationFilter`, `invalidateSubscriptions`.
- Environment variables: up to 50 string key-value pairs per API. Keys start with a letter, at least 2 chars, `[A-Za-z0-9_]`. Values up to 512 chars. Read with `ctx.env.NAME` (JS) or `$ctx.env` (VTL). Set with `PutGraphqlApiEnvironmentVariables`, which replaces the whole map. Docs recommend Secrets Manager for secrets.
- VTL versions: `2017-02-28` and `2018-05-29`. They change request shapes and null or error handling in templates. VTL extras: `$util.qr()`, `$util.quiet()`, `#foreach`, `$util.toJson`, `$util.defaultIfNull`, ...
- Direct Lambda resolvers: a Lambda data source with no request or response template. AppSync sends the full context to the Lambda and maps the return value directly.
- Resolver `maxBatchSize` (0 to 2000): batches Lambda calls for one field across list items (`BatchInvoke`). Lambda gets a list of payloads and returns a list in the same order. Each item can be `{data, errorMessage, errorType}`. This is the built-in N+1 answer. It only exists for Lambda data sources.
- Lambda `invocationType: "Event"` makes an async fire-and-forget call. Works with `BatchInvoke` too.
- `errorType: "UnauthorizedException"` from Lambda gives the default "You are not authorized to make this call." message.
- Custom HTTP response headers: `util.http.addResponseHeader(name, value)` / `addResponseHeaders(map)` from any resolver. Max 4 KB total. No `x-amz-`/`x-amzn-` prefixes or hop-by-hop headers. Bad headers add a `ResponseHeaderError` to `errors`. Last write wins.
- Resolver `cachingConfig` (`ttl`, `cachingKeys`) and `syncConfig` and `metricsConfig` (`ENABLED`/`DISABLED`).

## Data sources

- Types (`CreateDataSource.type`): `AMAZON_DYNAMODB`, `AWS_LAMBDA`, `HTTP`, `RELATIONAL_DATABASE`, `AMAZON_OPENSEARCH_SERVICE`, `AMAZON_ELASTICSEARCH` (old name), `AMAZON_EVENTBRIDGE`, `AMAZON_BEDROCK_RUNTIME`, `NONE`.
- Access is through an IAM `serviceRoleArn` that AppSync assumes. DynamoDB also has `useCallerCredentials` (use the caller's IAM credentials).
- DynamoDB: `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Query`, `Scan`, `Sync`, `BatchGetItem`, `BatchPutItem`, `BatchDeleteItem`, `TransactGetItems`, `TransactWriteItems`. Condition expressions, filter expressions, projections, typed values. Batch and transaction ops can span several tables.
- DynamoDB versioned data sources and conflict detection: `versioned: true` plus `deltaSyncConfig` (`baseTableTTL`, `deltaSyncTableName`, `deltaSyncTableTTL`). Adds `_version`, `_deleted`, `_lastChangedAt` fields. `syncConfig.conflictDetection` `VERSION` or `NONE`. `conflictHandler` `OPTIMISTIC_CONCURRENCY`, `AUTOMERGE`, `LAMBDA`, `NONE`. Unresolved conflicts return `ConflictUnhandled`. `Sync` operation with `lastSync` for delta sync. Built for Amplify DataStore offline sync.
- Lambda: `Invoke` and `BatchInvoke`. Any business logic or any backend.
- HTTP: any public HTTP endpoint. `authorizationConfig.authorizationType: AWS_IAM` with `awsIamConfig` (`signingRegion`, `signingServiceName`) signs requests with SigV4, so AppSync can call any AWS service API directly (SNS, SQS, Step Functions, ...). HTTPS endpoints need a certificate from a listed public CA (page "Certificate authorities recognized by AppSync").
- RDS: `relationalDatabaseSourceType: RDS_HTTP_ENDPOINT` only (Aurora Data API, MySQL and PostgreSQL). Credentials from Secrets Manager. `StartDataSourceIntrospection` / `GetDataSourceIntrospection` read the DB schema and propose GraphQL types and SDL. The console "Create API" wizard generates a full CRUD API with JS resolvers from an Aurora database.
- OpenSearch: `GET`, `POST`, `PUT`, `DELETE` with a path and body. Domains inside a VPC are not supported (documented).
- EventBridge: `PutEvents` to an event bus.
- Bedrock runtime: `InvokeModel` and `Converse`. Sync only, 10 s max. No streaming APIs. Guardrails supported in requests.
- `NONE`: local resolver. The request payload passes through to the response handler. Used for pub/sub mutations that only trigger subscriptions, and for data shaping.
- Data source `metricsConfig` for per-data-source enhanced metrics.
- No direct connectors for S3 reads, SQL over TCP (non-Aurora), MongoDB, Redis, or VPC-private HTTP endpoints, I think. Docs route such cases through Lambda.

## Subscriptions (GraphQL)

- Subscriptions are triggered only by AppSync mutations. `@aws_subscribe(mutations: ["addPost", "updatePost"])` on a `Subscription` field links it to one or more mutation fields. The subscription return type must match the mutation return type.
- Changes made directly in the data source do not trigger subscriptions. The usual pattern is a mutation on a `NONE` data source called from a backend (for example a Lambda with IAM auth) that only publishes. I think this is the main design limit of AppSync subscriptions.
- The client selection set must be a subset of the mutation selection set. Fields not selected in the triggering mutation arrive as `null` (or as an error if non-null). Each client gets its own selection set.
- Basic filtering: subscription arguments. Each argument is an equality check against the same-named field of the mutation result. Arguments combine with AND. All arguments are optional unless the schema marks them required.
- A `null` argument value differs from an omitted argument. `owner: null` matches only results with no owner.
- Subscription resolvers: a resolver on a `Subscription` field runs when the subscription is established (docs: filters use `context.identity` "when the subscription is established"). Used for auth checks (return an error to reject) and to set filters. I think it does not run per event.
- Enhanced filtering: in the subscription response handler, `extensions.setSubscriptionFilter(util.transform.toSubscriptionFilter(filterObj, ignoredFields?, rules?))`. Filters are evaluated on the server per event.
- Enhanced filter grammar: `filterGroup` is a list of filters (OR, max 10). Each filter has up to 5 rules (AND), each `{fieldName, operator, value}`. In the JS helper the object form is `{ field: { op: value } }` with `or`/`and` keys.
- Filter operators: `eq`, `ne`, `le`, `lt`, `ge`, `gt`, `contains`, `notContains`, `beginsWith`, `in`, `notIn`, `between`, `containsAny`.
- Filter limits: max 5 values for `in`/`notIn`, max 20 for `containsAny`, strings max 256 chars, string compare is case sensitive, nested fields with `.` (`location.address.country`) up to 5 levels, no filtering on top-level object lists (such events are ignored for enhanced subscriptions).
- Enhanced filters replace basic argument filtering for that subscription. Required arguments only filter if the resolver adds them as rules. Basic and enhanced filtering cannot be mixed on one subscription.
- Client-defined enhanced filters: add a `filter: String` (JSON) argument and pass it to `util.transform.toSubscriptionFilter(JSON.parse(ctx.args.filter))`. Lets clients send OR/AND filter trees.
- Filters can use `ctx.identity` (Cognito, OIDC, Lambda claims) at subscribe time. Used for per-user delivery.
- Subscription invalidation: mutation response handler calls `extensions.invalidateSubscriptions({subscriptionField, payload})`. The subscription response handler sets `extensions.setSubscriptionInvalidationFilter(filter)`. Matching subscriptions are closed and the WebSocket connection closes. Client gets an unsubscribe message. Max 5 unique `invalidateSubscriptions` calls per request. Quota 100 invalidation requests per second per account and Region.
- Transport: WebSocket only. Subprotocol `graphql-ws`, but with AppSync's own message set: `connection_init`, `connection_ack` (with `connectionTimeoutMs`), `ka`, `start`, `start_ack`, `data`, `error`, `stop`, `complete`. This is close to the old Apollo `subscriptions-transport-ws` protocol, not the newer `graphql-transport-ws` protocol, I think.
- Auth on the WebSocket: base64 JSON auth headers in the `header` query param plus `payload=e30=`, or in a second subprotocol `header-<base64url>`. Each `start` message also carries an `authorization` object in `extensions`. So each subscription can use a different auth mode on one connection.
- Real-time endpoint is `appsync-realtime-api` (separate host). With a custom domain the real-time endpoint is `wss://<domain>/graphql/realtime`.
- Connections are closed by AppSync after 24 hours. Max 200 subscriptions per connection (adjustable). Max payload 240 KB per message.
- MQTT over WebSockets was removed on 2022-01-01. Only pure WebSockets remain.
- No SSE transport. No HTTP multipart subscriptions. No subscriptions on queries (no live queries).
- Generic pub/sub API: console wizard that generates a schema with `publish(name, data: AWSJSON)` and `subscribe(name)` on a `NONE` data source. Superseded by AppSync Events in the docs.

## Server-side caching and compression

- Cache is a managed ElastiCache (Redis OSS) instance per API. Sizes `SMALL`, `MEDIUM`, `LARGE`, `XLARGE`, `LARGE_2X`, `LARGE_4X`, `LARGE_8X`, `LARGE_12X`. Legacy `T2_*`/`R4_*` types are deprecated. Billed per hour.
- `apiCachingBehavior`: `FULL_REQUEST_CACHING`, `PER_RESOLVER_CACHING`, `OPERATION_LEVEL_CACHING`.
- Full request caching: every resolver result is cached separately. Default key is `ctx.arguments`, `ctx.source` and `ctx.identity`.
- Per-resolver caching: opt in per resolver with `cachingConfig.ttl` (required) and `cachingConfig.cachingKeys` (optional). Keys may be `$context.arguments`, `$context.source`, `$context.identity`, or string fields in them (for example `$context.identity.sub`, `$context.arguments.id`). Max 25 caching keys.
- Operation-level caching: caches the whole query response. Max 15 MB response. Key is `query` + `operationName` + `variables` + `ctx.identity` (minus `sourceIp` for IAM and Cognito) + all request headers except a reserved list (`authorization`, CloudFront headers, `host`, `x-amz-date`, ...). For IAM the key adds the allowed and denied resources. For Lambda auth it adds `deniedFields`.
- TTL 1 to 3,600 seconds.
- Eviction: `extensions.evictFromApiCache(typeName, fieldName, {cacheKeyName: value})` from a mutation only. Keys must be in the same order as `cachingKeys`. Response gets `extensions.apiCacheEntriesDeleted: N`. Full flush with `FlushApiCache` (console or CLI).
- Encryption at rest and in transit is always on for new caches. Older caches must be deleted and recreated to get encryption.
- Cache health metrics (`healthMetricsConfig`) and per-resolver `CacheHit`/`CacheMiss` enhanced metrics.
- No HTTP cache headers (`Cache-Control`), no CDN caching of GraphQL responses, no `@cacheControl` directive. Cache config is outside the schema.
- Response compression: client sends `Accept-Encoding: gzip`. Responses of 1,000 to 10,000,000 bytes are gzip-compressed on a best-effort basis. Only on APIs created after 2020-06-01. Only gzip is documented.

## Merged APIs

- A Merged API (`apiType: MERGED`) combines up to 10 source AppSync GraphQL APIs (adjustable) into one endpoint. Composition is at build time ("merge"), not at request time. Resolvers, data sources and functions of the sources run inside the Merged API. No router hop.
- Merge modes per association: manual (default, `StartSchemaMerge`) or auto-merge on every source change (`sourceApiAssociationConfig.mergeType`: `MANUAL_MERGE` default, or `AUTO_MERGE`).
- Schema of a Merged API is read-only. Changes go through source APIs.
- Conflicts: same-named types are merged as a union of their fields. Same field with resolvers in two sources is a merge error ("field resolver pattern" is the docs fix). Two `@canonical` on one field fail with `Multiple subschemas cannot declare the same field as canonical`.
- Directives: `@canonical` (this source wins for the type or field), `@hidden` (do not merge this type or field), `@renamed(to: "NewName")` (rename type or field in the merged schema).
- Auth: Merged API owner sets auth modes. Each source's primary mode must exist on the Merged API, or merge fails. Source primary mode is added as a directive to the fields that source contributes. When two sources declare the same field, their auth directives are combined (OR), so a field can become reachable with a weaker mode. The fix is `@canonical` plus an explicit directive.
- Execution role `mergedApiExecutionRoleArn` needs IAM `appsync:SourceGraphQL` on source APIs. Can be scoped to top-level fields. Non-top-level fields can only be scoped at the source API level.
- Cross-account sources through AWS RAM resource shares, with AWS-managed or customer-managed RAM permissions.
- Rules: a Merged API cannot be a source of another Merged API. A source API can be in only one Merged API. Merged schema max 10 MB.
- Subscriptions from sources work in the Merged API without change. Caching, WAF, private APIs, custom domains, X-Ray, CloudWatch and CloudTrail all work on Merged APIs.
- Not Apollo Federation. Sources must be AppSync APIs. No entity keys, `@key`, `_entities`, or reference resolvers. Docs suggest putting AppSync behind an Apollo router for non-AppSync subgraphs (blog reference). AppSync cannot act as an Apollo Federation subgraph out of the box, I think (the docs mention a blog post that adds AppSync APIs as subgraphs, I did not read it).

## Private APIs, sharing, custom domains, WAF

- Private API: `visibility: PRIVATE`. Only reachable through an interface VPC endpoint (`com.amazonaws.<region>.appsync-api`, AWS PrivateLink). Set at creation only. Cannot be changed later. The VPC must be in the same account and Region.
- With private DNS on the VPC endpoint, resources in that VPC can no longer call public AppSync APIs by their generated URL. Docs recommend custom domain names on the public APIs for this case.
- A VPC endpoint can reach every private API in the same account and Region. Narrow it with VPC endpoint policies and IAM condition keys.
- Control plane endpoint `com.amazonaws.<region>.appsync` for management calls from a VPC.
- `ctx.request.headers` for VPC endpoint requests carries `x-amzn-appsync-is-vpce-request` (listed as a reserved header in the caching docs).
- Sharing: AWS RAM can share GraphQL APIs (invoke rights for query, mutation, subscription, WebSocket connect) with other accounts, OUs or the whole organization. RAM permission `AWSRAMPermissionAppSyncGraphQLApiInvokeAccess`. Requires `AWS_IAM` as one of the auth modes. Only whole APIs, not per type or field. Event APIs cannot be shared.
- Custom domains: one domain for both endpoints, `https://<domain>/graphql` and `wss://<domain>/graphql/realtime`. Backed by a CloudFront distribution. ACM certificate must be in `us-east-1`. Wildcard domains allowed (`*.example.com`). TLS 1.2 and 1.3 only. Max 50 custom domains per Region (adjustable). Resolver sees the domain in `ctx.request.domainName`. API association with `AssociateApi`.
- WAF: associate an AWS WAF web ACL with the API. Rules run before auth. Rate-based rules, IP sets, geo match, header and body matching (first 8 KB of body), managed rule groups. On the real-time endpoint WAF only sees the subscription registration (`start`) message. Blocked registrations get an error instead of `start_ack`.

## Observability

- CloudWatch metrics (API level): `4XXError`, `5XXError`, `Latency`, `Requests`, `TokensConsumed`, `NetworkBandwidthOutAllowanceExceeded`, and cache `EngineCPUUtilization`.
- Real-time metrics: `ConnectRequests`, `ConnectSuccess`, `ConnectClientError`, `ConnectServerError`, `DisconnectSuccess`, `DisconnectClientError`, `DisconnectServerError`, `SubscribeSuccess`, `SubscribeClientError`, `SubscribeServerError`, `UnsubscribeSuccess`, `UnsubscribeClientError`, `UnsubscribeServerError`, `PublishDataMessageSuccess`, `PublishDataMessageClientError`, `PublishDataMessageServerError`, `PublishDataMessageSize`, `ActiveConnections`, `ActiveSubscriptions`, `ConnectionDuration`, `InboundMessageSuccess`, `InboundMessageError`, `InboundMessageFailure`, `InboundMessageDelayed`, `InboundMessageDropped`, `OutboundMessages`, `InvalidationSuccess`, `InvalidationRequestSuccess`, `InvalidationRequestError`, `InvalidationRequestFailure`, `InvalidationRequestDropped`.
- Enhanced metrics (`enhancedMetricsConfig`, extra cost): `resolverLevelMetricsBehavior` (`FULL_REQUEST_RESOLVER_METRICS` or `PER_RESOLVER_METRICS`): errors, invocations, latency, cache hit and miss per resolver. `dataSourceLevelMetricsBehavior` (`FULL_REQUEST_DATA_SOURCE_METRICS` or `PER_DATA_SOURCE_METRICS`): invocations, latency, errors per data source. `operationLevelMetricsConfig` (`ENABLED` or `DISABLED`): request count and errors per named GraphQL operation (dimension `Operation`).
- Request tokens: one token per 1,500 KB-seconds of memory and vCPU time. Response header `x-amzn-appsync-TokensConsumed` shows tokens used. Throttling is per account and Region in tokens per second (5,000 or 10,000 by Region, adjustable).
- CloudWatch Logs: `logConfig.fieldLogLevel` `NONE`, `ERROR`, `INFO`, `DEBUG`, `ALL`. `excludeVerboseContent` controls request-level logs (headers, query, tokens, subscription registrations). Field-level logs include evaluated request and response per field and tracing info. Log group `/aws/appsync/apis/<api_id>`. Max 1 MB of logs per request, then truncated. `console.log` in resolver code goes to these logs.
- Log types: `RequestSummary`, `ExecutionSummary`, `Tracing` (per-field timing, like Apollo tracing), plus mapping template and auth logs. Logs are JSON. A sample script (`aws-samples/aws-appsync-cwl-migrator`) converts older unstructured log lines.
- Every response has `x-amzn-RequestId`. Every log event has it too.
- AWS X-Ray tracing (`xrayEnabled`): segments per resolver and data source call. Sampling rules from X-Ray.
- CloudTrail logs control plane calls as management events. GraphQL requests can be logged as CloudTrail data events (resource type `AWS::AppSync::GraphQLApi`, extra cost, off by default). Advanced selectors filter on `eventName`, `readOnly`, `resources.ARN`.
- No OpenTelemetry export. No Apollo-style usage reporting or schema registry. No `extensions.tracing` in the GraphQL response.

## AppSync Events (pub/sub, no GraphQL)

- Released 2024-10-30. Publish over WebSocket added 2025-03-13. Data source integrations added 2025-04-24.
- Event API: HTTP publish endpoint `https://<id>.appsync-api.<region>.amazonaws.com/event` and WebSocket endpoint `wss://<id>.appsync-realtime-api.<region>.amazonaws.com/event/realtime`. WebSocket subprotocol `aws-appsync-event-ws` plus `header-<base64url auth>`.
- Event: any JSON value. Max 240 KB per event. Publish batches max 5 events and 1.2 MB.
- Channel: path like `/namespace/a/b`. Max 5 segments, 50 chars each. Channels are ephemeral and need no setup. The first segment must be a configured channel namespace.
- Wildcard subscriptions: `/namespace/a/*`.
- Channel namespace: per-namespace auth overrides, handlers, and data source integrations. Max 50 namespaces per API (adjustable).
- Auth modes same as GraphQL (API key, IAM, Cognito, OIDC, Lambda). Separately configured for connect, default publish and default subscribe. Namespaces can override publish and subscribe modes.
- Handlers (`APPSYNC_JS`): `onPublish(ctx)` returns the events to broadcast (filter, transform, or drop). Returned events must keep incoming IDs. Events with an `error` property are not broadcast. `onSubscribe(ctx)` can reject with `util.unauthorized()` or `util.error()`. Context has `events`, `identity`, `result`, `request`, `stash`, and `info` (`info.channel.path`, `info.channel.segments`, `info.channelNamespace.name`, `info.operation`, I think for the last).
- Handlers can call data sources with request and response functions: DynamoDB, RDS Data API, Lambda, Bedrock, OpenSearch, EventBridge, HTTP. Same `@aws-appsync/utils` modules as GraphQL.
- Direct Lambda integration on a namespace (`handlerConfigs`): no handler code. Invocation type `REQUEST_RESPONSE` or `EVENT` (async).
- WebSocket messages: `connection_init`, `connection_ack`, `ka`, `subscribe`/`subscribe_success`/`subscribe_error`, `unsubscribe`/`unsubscribe_success`/`unsubscribe_error`, `publish`/`publish_success`/`publish_error`, `data`, `broadcast_error`.
- HTTP publish errors return HTTP 403. WebSocket publish errors return `publish_error`.
- Lambda authorizer caching for wildcard subscribe uses the literal channel string in the cache key.
- Quotas: 2,000 connects per second, 10,000 inbound events per second, 1,000,000 outbound messages per second (5 KB units), 25 publishes per second per connection. All adjustable except per-connection.
- Client: Amplify `events.connect(channel)` and `events.post(channel, data)` from `aws-amplify/data`.
- Custom domains, CloudWatch metrics and logs, and WAF work for Event APIs. Event APIs cannot be shared with AWS RAM.
- No event persistence or replay, no message history, no delivery or ordering guarantees in the docs. Persistence is done by a handler writing to DynamoDB (tutorial).

## AWS-specific scalars and schema rules

- Built-in scalars: `ID`, `String`, `Int`, `Float`, `Boolean`.
- AWS scalars: `AWSDate` (`YYYY-MM-DD`), `AWSTime` (`hh:mm:ss.sss`), `AWSDateTime` (`YYYY-MM-DDThh:mm:ss.sssZ`), `AWSTimestamp` (integer seconds since epoch), `AWSEmail` (RFC 822), `AWSJSON` (JSON string, parsed into maps and lists in resolver code), `AWSPhone` (spaces or hyphens allowed, no country code means NANP), `AWSURL` (RFC 1738, needs a scheme, no `//` in path), `AWSIPAddress` (IPv4 or IPv6, optional CIDR suffix).
- Date and time scalars accept an optional offset (`Z`, `+05:30`, `-07:00`, optional seconds).
- User-defined custom scalars are not supported (`scalar Foo` is rejected). The docs say it twice.
- Type names cannot start with `AWS`.
- Interfaces and unions need `__typename` in each result object. AppSync uses it to resolve the concrete type. There is no `resolveType` hook in code.
- Custom schema directives cannot be defined. Only the AWS directives exist, I think (the docs list no `directive @...` definitions and no way to add behavior to a directive).
- Removing a field also deletes its resolver. Restoring the field does not restore the resolver. CloudFormation and CDK do not see this deletion (stack drift, `UPDATE_ROLLBACK_FAILED`).
- Schema max 1 MB (10 MB for a Merged API).
- `StartDataSourceIntrospection` can generate SDL from an Aurora schema. No code-first schema in AppSync itself. Code-first exists only through CDK, Amplify Gen 2 (`a.schema`) or third-party tools.

## GraphQL request handling and spec features

- HTTP POST with JSON body `{query, operationName, variables}` at `/graphql`. Docs curl examples use `Content-Type: application/graphql` with a JSON body. HTTP GET is not documented.
- Error objects carry non-spec top-level keys `errorType`, `errorInfo` and `data` (set by `util.error(message, errorType, data, errorInfo)`), next to `message`, `path`, `locations`. They are not inside `extensions`.
- Response `extensions` is used for AppSync data (for example `apiCacheEntriesDeleted`).
- Invalid input reaching a resolver gives `null` field data plus errors.
- Introspection can be turned off (`introspectionConfig: DISABLED`). Then `__schema` queries fail validation.
- Query depth limit `queryDepthLimit` 1 to 75 (default off). Error `QueryDepthLimitReached` bubbles to the nearest nullable parent.
- Resolver count limit `resolverCountLimit` 1 to 10,000 (default 10,000). Error `ResolverExecutionLimitReached` on resolvers past the limit.
- Max query length 15,000 tokens (error "Maximum char length exceeded").
- No query cost or complexity analysis. Throttling uses request tokens based on measured CPU and memory after execution.
- Not documented, so I think not supported: `@defer`, `@stream`, `@oneOf`, `@specifiedBy`, persisted queries (APQ or trusted documents), batched operations (JSON array of requests), file uploads (multipart), GET requests, `graphql-transport-ws` protocol, SSE.
- `@deprecated` is not mentioned anywhere in the AppSync devguide. I think it is accepted as a standard directive, but I did not verify.
- No field-level resolvers in code outside the data source model (no general-purpose server code, except through Lambda).
- No built-in dataloader. Batching exists only for Lambda (`BatchInvoke`, `maxBatchSize`) and DynamoDB batch operations in a resolver.
- No query planning or SQL generation from the selection set. `ctx.info.selectionSetList` is available for hand-written projection.
- Mutations run in serial, queries in parallel, I think (standard GraphQL execution, not stated in the docs).
- No Relay `Node` interface, connections, or global IDs built in. Pagination is by `nextToken` from DynamoDB (Amplify generates `limit`/`nextToken` arguments).
- No input validation directives in AppSync itself. Validation is in resolver code (Amplify Gen 2 adds `.validate()`).

## Service quotas (defaults)

- GraphQL APIs per Region 50 (adj.). API keys per API 50. Auth providers per API 50.
- Request execution time 30 s. Resolvers per request 10,000. Functions per pipeline 10.
- JS code size 32 KB. VTL template 64 KB each. Evaluated response 5 MB. Loop iterations 1,000.
- Schema document 1 MB. Query length 15,000 tokens. Caching keys 25. Lambda batch size 2,000.
- Subscription payload 240 KB. Subscriptions per connection 200 (adj.). Connection max 24 h.
- Rate of request tokens: 10,000/s in large Regions, 5,000/s in others (adj.). Connections 2,000/s (adj.). Inbound messages 10,000/s (adj.). Outbound messages 1,000,000/s in 5 KB units (adj.).
- Invalidation requests 100/s per account and Region.
- Source APIs per Merged API 10 (adj.). Custom domains per Region 50 (adj.).
- Lambda authorizer timeout 10 s, response cached if under 1 MB, `resolverContext` max 5 MB.
- Environment variables 50 per API, value max 512 chars.
- Event APIs: see the Events section.

## Amplify GraphQL transformer (Gen 1 directives, Gen 2 `a.schema`)

Amplify is a separate tool. It turns an annotated SDL (Gen 1) or a TypeScript schema builder (Gen 2) into an AppSync API with DynamoDB tables, resolvers and generated CRUD. Many users meet AppSync this way. Brief list, from `aws-amplify/docs` (`src/pages/gen1/[platform]/build-a-backend/graphqlapi/` and `src/pages/[platform]/build-a-backend/data/`, commit `714b208`, 2026-10-06).

- `@model(queries:, mutations:, subscriptions: {level: off|public|on}, timestamps: {createdAt:, updatedAt:})`: DynamoDB table plus `get`, `list`, `create`, `update`, `delete`, `onCreate`/`onUpdate`/`onDelete` subscriptions, `createdAt`/`updatedAt`. Any operation can be renamed or turned off with `null`.
- `@primaryKey(sortKeyFields:)` and `@index(name:, sortKeyFields:, queryField:)`: DynamoDB keys and GSIs with generated query fields.
- Relations: `@hasOne`, `@hasMany`, `@belongsTo` (Gen 1 uses `fields: [...]` for the foreign key fields), `@manyToMany(relationName:)` (join table). Each relation is a separate resolver call (no joins).
- `@default(value:)`, `@mapsTo(name:)` (rename a model without losing the table), `@refersTo(name:)` (map to a SQL table or column name), `@sql(statement:, reference:)` (custom SQL query on SQL data sources).
- `@auth(rules: [...])`: `allow: public` (API key or `provider: iam` for guests), `allow: private` (any signed-in user, `provider: userPools|oidc|iam`), `allow: owner` (`ownerField`, `identityClaim`, list of owners), `allow: groups` (static `groups:` or dynamic `groupsField:`, `groupClaim`), `allow: custom` (Lambda authorizer). `operations: [create, read, update, delete]` or finer `get`, `list`, `listen`, `sync`, `search`. Rules OR together. Field-level `@auth` replaces model-level rules for that field (no inheritance). Global `input AMPLIFY { globalAuthRule: AuthRule = { allow: public } }` for prototypes.
- Owner auth is enforced in generated resolvers and on generated subscriptions (owner argument is added and checked).
- `@searchable`: streams the table to OpenSearch. Adds `search<Model>s` with `SearchableXFilterInput` (`eq`, `ne`, `gt`, `match`, `matchPhrase`, `matchPhrasePrefix`, `multiMatch`, `exists`, `wildcard`, `regexp`, `range`), sort, and `aggregates` (`terms`, `avg`, `min`, `max`, `sum`).
- `@function(name:, region:)`: Lambda resolver, can be chained into a pipeline. `@http(url:, method:, headers:)`: HTTP resolver with `${env}` and `${ctx...}` interpolation. `@predictions(actions: [identifyText, identifyLabels, convertTextToSpeech, translateText])`: AI service calls.
- Generated filters on `list` queries: `Model<Type>Input` with `eq`, `ne`, `le`, `lt`, `ge`, `gt`, `contains`, `notContains`, `between`, `beginsWith`, `attributeExists`, `attributeType`, plus `and`/`or`/`not`. Pagination by `limit` and `nextToken`. `sortDirection` on index queries. Filters are DynamoDB filter expressions after the read, so `limit` applies before the filter.
- Conflict resolution and DataStore sync: `_version`, `_deleted`, `_lastChangedAt`, `sync<Model>s` queries (Amplify DataStore, now in maintenance, I think).
- Gen 2 (`@aws-amplify/backend`): `a.schema({...})`, `a.model`, `a.customType`, `a.enum`, `a.ref`, `a.hasMany`/`a.hasOne`/`a.belongsTo`, `a.query`/`a.mutation`/`a.subscription` with `a.handler.function`, `a.handler.custom` (JS resolver file), `a.handler.inlineSql`, `a.handler.sqlReference`. Auth with `allow.publicApiKey()`, `allow.guest()`, `allow.authenticated()`, `allow.owner()`, `allow.ownerDefinedIn()`, `allow.ownersDefinedIn()`, `allow.group()`, `allow.groups()`, `allow.groupDefinedIn()`, `allow.groupsDefinedIn()`, `allow.custom()`, `allow.resource(fn)`. `a.combine([...])` merges schemas. AI kit: `a.conversation()` and `a.generation()` (Bedrock). Docs pages exist under `src/pages/[platform]/ai/`. I did not read them.
- Gen 2 field-level validation: `.validate(v => v.minLength(n, msg))` with `minLength`, `maxLength`, `startsWith`, `endsWith`, `matches` (Java regex), `gt`, `gte`, `lt`, `lte`, `positive`, `negative`. Runs in generated resolvers.
- Gen 2 can connect to Event APIs (`connect-event-api` page) and to existing Postgres/MySQL (`npx ampx generate schema-from-database`).
- AWS AppSync Apollo Extensions: `apollo-appsync` (Android) and Swift packages that add AppSync authorizers (API key, Cognito, IAM SigV4) and the AppSync WebSocket protocol to Apollo clients.

## Recent and upcoming features

- No public roadmap and no devguide changelog. Dates below come from AWS What's New posts and the Events doc history.
- 2024-10-30: AppSync Events released.
- 2024-11: Amazon Bedrock runtime data source for GraphQL ("AI gateway") ([What's New](https://aws.amazon.com/about-aws/whats-new/2024/11/aws-appsync-ai-gateway-bedrock-integration-appsync-graphql/)).
- 2025-02: operation-level caching (`OPERATION_LEVEL_CACHING`) ([What's New](https://aws.amazon.com/about-aws/whats-new/2025/02/aws-appsync-graphql-operation-level-caching-api-responses/)).
- 2025-03-13: Events publish over WebSocket.
- 2025-04-24: Events data source integrations for namespace handlers ([What's New](https://aws.amazon.com/about-aws/whats-new/2025/04/aws-appsync-events-data-source-integrations-channel-namespaces/)).
- 2025-06-23: Regions Malaysia, Thailand, Calgary ([What's New](https://aws.amazon.com/about-aws/whats-new/2025/06/aws-appsync-additional-regions)).
- I found no 2026 What's New posts for AppSync in a web search. The docs show recent edits (Merged API auth-combination warnings, the troubleshooting page about resolvers removed with schema fields, PrivateLink control plane endpoint), but they have no dates.
- Direction: GraphQL subscription pages now point to AppSync Events for pub/sub. VTL is in maintenance in the docs. New features (Bedrock, Events handlers) are JS-only.

## Not supported

- Custom scalars. Custom directives with behavior.
- Any server code except the restricted `APPSYNC_JS` runtime and Lambda. No async code, no network calls from resolver code, no npm packages with I/O.
- Apollo Federation (as gateway or subgraph). Composition is only Merged APIs of AppSync sources.
- `@defer`, `@stream`, persisted queries, request batching, file uploads, GET, SSE, `graphql-transport-ws` (none documented).
- Query cost or complexity analysis. Only depth limit, resolver count limit, and token-based throttling.
- Subscriptions triggered by data source changes. Only mutations trigger them.
- Live queries.
- Per-viewer schema visibility. Introspection is all or nothing. `deniedFields` nulls values but does not hide schema.
- Dataloader-style batching for non-Lambda data sources.
- OpenSearch domains in a VPC. HTTP data sources with self-signed certificates. HTTP data sources inside a VPC (except through Lambda), I think.
- Cross-account Lambda authorizers.
- Changing a public API to private or back.
- HTTP cache headers or CDN caching of responses.
- OpenTelemetry export.
- RDS data sources other than Aurora Data API.
- Merged API of Merged APIs. One source API in several Merged APIs.
- Event persistence or replay in AppSync Events.

## Docs pages contradict each other

- Cognito default action: the security page CLI example uses `--user-pool-config '{"defaultEffect":"ALLOW", ...}'`. The API reference `UserPoolConfig` field is `defaultAction` (`ALLOW` or `DENY`).
- Schema size: the service quota says schema document max 1 MB. The Merged API page says the default Merged API schema size limit is 10 MB. I think the quota page only covers normal GraphQL APIs.
- Owner check example (security page): `addPost` stores the creator as `Author`, but `editPost` checks `condition: { author: { contains: ctx.identity.username } }` (lowercase). The example would not match.
- Same page: `get({ key: { ctx.args.id } })` is not valid JavaScript.
- Enhanced filtering page: the text says tickets match if "`classification` ticket set to `Security`". The filter in the code is `category: { eq: 'security' }`.
- The JS `extensions` page has no operator table and no filter limits. The VTL `extensions` page has both. JS users must read the VTL page.
- The Merged API comparison table says router-based federation has no subscription support. Apollo Router and Cosmo support subscriptions today. I think this table is outdated.
- An IAM page links to "the AWS AppSync Document history page" and its RSS feed. That page now redirects to the guide root.
- `@aws_cognito_user_pools` is enforced only with additional modes, and `@aws_auth` only without them. The two pages present this as a note, but the directives page itself (`aws-appsync-directives.md`) only covers VTL `#return`, not schema directives. There is no single reference page for schema directives.

## Sources

- AppSync devguide llms.txt: https://docs.aws.amazon.com/appsync/latest/devguide/llms.txt (all 189 `.md` pages downloaded to `/tmp/appsync-docs/dev/`).
- AppSync Events guide llms.txt: https://docs.aws.amazon.com/appsync/latest/eventapi/llms.txt (65 pages in `/tmp/appsync-docs/ev/`).
- Key pages: https://docs.aws.amazon.com/appsync/latest/devguide/security-authz.html, https://docs.aws.amazon.com/appsync/latest/devguide/scalars.html, https://docs.aws.amazon.com/appsync/latest/devguide/aws-appsync-real-time-data.html, https://docs.aws.amazon.com/appsync/latest/devguide/aws-appsync-real-time-enhanced-filtering.html, https://docs.aws.amazon.com/appsync/latest/devguide/aws-appsync-real-time-invalidation.html, https://docs.aws.amazon.com/appsync/latest/devguide/real-time-websocket-client.html, https://docs.aws.amazon.com/appsync/latest/devguide/extensions.html, https://docs.aws.amazon.com/appsync/latest/devguide/enabling-caching.html, https://docs.aws.amazon.com/appsync/latest/devguide/merged-api.html, https://docs.aws.amazon.com/appsync/latest/devguide/using-private-apis.html, https://docs.aws.amazon.com/appsync/latest/devguide/custom-domain-name.html, https://docs.aws.amazon.com/appsync/latest/devguide/WAF-Integration.html, https://docs.aws.amazon.com/appsync/latest/devguide/monitoring.html, https://docs.aws.amazon.com/appsync/latest/devguide/configuration-limits.html, https://docs.aws.amazon.com/appsync/latest/devguide/supported-features.html, https://docs.aws.amazon.com/appsync/latest/devguide/resolver-reference-overview-js.html, https://docs.aws.amazon.com/appsync/latest/devguide/environment-variables.html, https://docs.aws.amazon.com/appsync/latest/devguide/rds-introspection.html, https://docs.aws.amazon.com/appsync/latest/devguide/troubleshooting-and-common-mistakes.html.
- Events: https://docs.aws.amazon.com/appsync/latest/eventapi/event-api-concepts.html, https://docs.aws.amazon.com/appsync/latest/eventapi/channel-namespace-handlers.html, https://docs.aws.amazon.com/appsync/latest/eventapi/event-api-document-history.html.
- API reference (`.md` pages in `/tmp/appsync-docs/apiref/`): https://docs.aws.amazon.com/appsync/latest/APIReference/API_CreateGraphqlApi.html, `API_UserPoolConfig`, `API_LambdaAuthorizerConfig`, `API_CreateDataSource`, `API_CreateResolver`, `API_CachingConfig`, `API_SyncConfig`, `API_ApiCache`, `API_CreateApiCache`, `API_EnhancedMetricsConfig`, `API_LogConfig`, `API_SourceApiAssociationConfig`.
- Service quotas: https://docs.aws.amazon.com/general/latest/gr/appsync.html.
- Amplify docs: https://github.com/aws-amplify/docs (sparse shallow clone in `/tmp/amplify-docs`, commit `714b208`, 2026-10-06).
- Old docs repo `awsdocs/aws-appsync-developer-guide`: 404 on GitHub.
