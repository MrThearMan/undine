## What's Changed?

> This is a big release and changes some public behavior. See the warnings below.

### Features

#### Cross-process signal subscriptions

Signal subscriptions now publish their events to a **broker**, selected with the new
`SUBSCRIPTION_BROKER_CLASS` setting. `InMemorySubscriptionBroker` is the default and serves a
single process. The `channels` integration adds `ChannelLayerSubscriptionBroker`, which delivers
events between worker processes over a shared channel layer.

Each subscriber now buffers at most `max_backlog` events, which defaults to 100. A subscriber that
falls behind ends its subscription with a `SUBSCRIPTION_BACKLOG_FULL` error instead of growing its
buffer without a limit. Set `max_backlog=0` to keep the old unbounded behavior.

> [!WARNING]
> **Breaking.** A custom `SignalSubscription` needs a rewrite. It must implement the new abstract
> `serialize(params)` method, which runs in the process that dispatched the signal and reduces the
> signal arguments to primitives that a broker can carry. `process()` is removed, and `filter()`
> and `transform()` now receive that serialized event instead of the raw signal arguments.
> `ModelSaveSubscription.transform` returns the primary key of the saved instance instead of the
> instance, and `ModelDeleteSubscription.transform` rebuilds an instance from a column snapshot.
> A subscription no longer holds its subscribers in a `subscribers` dict, and its
> `__init__` takes the new `max_backlog` argument.

Docs: [Brokers](https://mrthearman.github.io/undine/subscriptions/#brokers)

#### Keyset cursor pagination

`Connection` pagination now uses keysets. A cursor encodes the ordering values of the row it points
to, so pages stay correct when items are added to or removed from the parts of a list that were
already read. `UnionType` and `InterfaceType` connections encode the shared ordering values, the
type name of the row, and the ordering values of the query type the row came from.

> [!WARNING]
> **Breaking.** Cursors issued by earlier versions are no longer valid, since the format changed
> from an offset to a keyset payload. Clients that stored cursors must refetch.
> `undine.relay.offset_to_cursor` and `undine.relay.cursor_to_offset` are removed. A cursor is
> opaque, so read it from the `endCursor` or `startCursor` of a response.
> A cursor is only valid for the ordering it was issued under. Replaying a cursor after changing
> the `OrderSet` arguments returns a `Bad Request` error.

> [!WARNING]
> **Breaking.** A custom pagination handler needs a rewrite. `PaginationHandler` is now an
> abstract base class with three abstract methods: `paginate_queryset`,
> `paginate_prefetch_queryset` and `optimize`. Its `__init__`, `validate`, `apply_pagination`,
> `apply_prefetch_pagination`, `calculate_pagination_arguments` and
> `calculate_prefetch_pagination_arguments` are removed, as are the `ValidatedPaginationArgs`,
> `OptimizationWithPagination` and `QuerySetMapWithPagination` dataclasses. Subclass
> `undine.relay.CursorPaginationHandler` or `undine.pagination.OffsetPaginationHandler`, which
> carry the cursor and offset behavior and hand out the new `PaginationCut` and `PaginationPage`
> results. `CursorPaginationHandler.__init__` does not accept `offset` or `limit`.

Docs: [Cursor pagination](https://mrthearman.github.io/undine/pagination/#cursor-pagination)

#### Custom GraphQL context object

`info.context` is now a `GQLContext` object instead of the Django request. The request is on
`info.context.request`. `info.context.user` and `await info.context.auser()` keep working, so
permission checks and resolvers that only read the user need no change. The object also carries
`info.context.extensions`, a dict you can put your own data in for the lifetime of the operation.

> [!WARNING]
> **Breaking.** Any other use of the request through `info.context` must go through
> `info.context.request`. This covers `headers`, `META`, `session`, `COOKIES`, `build_absolute_uri()`
> and every other request member.

#### Error masking

Unexpected errors are no longer sent to the client as they are. An error that comes from an
exception nobody raised for the client, such as a `RuntimeError` in a resolver, is replaced with
the `ERROR_MASKING_MESSAGE` text, and its `extensions` are removed. `GraphQLErrors` reach the
client unchanged. The original message and traceback are always logged to the `undine` logger.

> [!WARNING]
> **Breaking.** Masking is on by default. Clients that read messages or `error_code` values of
> unhandled server errors see the generic message instead. Set `ERROR_MASKING_PREDICATE` to
> `"undine.utils.graphql.utils.never_mask_error"` to turn masking off.

Docs: [`ERROR_MASKING_PREDICATE`](https://mrthearman.github.io/undine/settings/#error_masking_predicate)

#### Lifecycle hook registration

Built-in hooks are now added automatically when the schema needs them. Register your own hooks with
the new `ADDITIONAL_LIFECYCLE_HOOKS` setting. Hooks now have a `priority` class attribute that sets
the order they run in, and an `is_enabled` classmethod that decides when they are used. The built-in
priorities are available as `undine.hooks.HookPriority`.

> [!WARNING]
> **Breaking.** The `LIFECYCLE_HOOKS` setting is removed. Move your own hooks to
> `ADDITIONAL_LIFECYCLE_HOOKS` and drop the built-in hooks from the list.
> Automatic persisted queries are now enabled with the `AUTOMATIC_PERSISTED_QUERIES` setting
> instead of by registering `undine.hooks.AutomaticPersistedQueriesHook`. The
> `GraphQLRequestParamsParser.automatic_persisted_queries_enabled` classmethod is removed with it.

Docs: [Registering hooks](https://mrthearman.github.io/undine/lifecycle-hooks/#registering-hooks),
[Priority](https://mrthearman.github.io/undine/lifecycle-hooks/#priority)

#### OpenTelemetry integration

`pip install undine[opentelemetry]` adds `OpenTelemetryHook`, which records a span for each GraphQL
operation with child spans for the parse, validation and execution steps. `OpenTelemetryFullHook`
adds a span per resolved field. Documents and variables are redacted by default. Configure it with
`OPENTELEMETRY_VARIABLES_CALLBACK`, `OPENTELEMETRY_SPAN_CALLBACK` and
`OPENTELEMETRY_SKIP_FIELD_SPANS_PREDICATE`.

Docs: [OpenTelemetry](https://mrthearman.github.io/undine/integrations/#opentelemetry)

#### Datadog integration

`pip install undine[datadog]` adds `DatadogHook` and `DatadogFullHook`, which record native
`ddtrace` spans. The operation span resource is built from the operation name and the query hash,
which keeps traces for the same operation grouped. Configure it with `DATADOG_SERVICE_NAME`,
`DATADOG_VARIABLES_CALLBACK`, `DATADOG_SPAN_CALLBACK` and `DATADOG_SKIP_FIELD_SPANS_PREDICATE`.

Docs: [Datadog](https://mrthearman.github.io/undine/integrations/#datadog)

#### Sentry integration

`pip install undine[sentry]` adds `SentryHook` and `SentryFullHook`. The hook starts a transaction
for WebSocket and SSE connections, names the transaction after the GraphQL operation, records spans,
and reports failing operations as issues with the unmasked error. Configure it with
`SENTRY_REPORT_ERROR_PREDICATE`, `SENTRY_VARIABLES_CALLBACK`, `SENTRY_SPAN_CALLBACK` and
`SENTRY_SKIP_FIELD_SPANS_PREDICATE`.

Docs: [Sentry](https://mrthearman.github.io/undine/integrations/#sentry)

#### Document caching

Two new hooks reuse parse and validation results between requests, in the memory of the process.
Enable them by setting `PARSE_CACHE_MAX_SIZE` and `VALIDATION_CACHE_MAX_SIZE` above zero. The
validation cache is skipped for schemas that use visibility. All caching is now described on one
docs page.

Docs: [Document caching](https://mrthearman.github.io/undine/caching/#document-caching),
[Caching](https://mrthearman.github.io/undine/caching/)

#### Per-request mutation instance limit

`MUTATION_INSTANCE_LIMIT` now caps the number of Model instances a whole request may mutate. Nested
related objects, through Model rows, and objects deleted or disconnected by a related mutation
action all count towards it. The count carries over between the mutations of one operation.

> [!WARNING]
> **Breaking.** Operations that passed before can now fail with a `MUTATION_TOO_MANY_OBJECTS`
> error, because the limit counts more objects and is shared by the request.

A call to `undine.utils.mutation_tree.mutate` counts against the request only when you pass the
running counter, which is on `info.context.undine_internal.mutation_counter`. Without it, the
limit applies to that call alone.

Docs: [Mutation instance limit](https://mrthearman.github.io/undine/mutations/#mutation-instance-limit)

#### Max list nesting depth rule

The new `MaxListNestingDepthRule` caps how many to-many relations an operation may nest inside one
another. The `MAX_LIST_NESTING_DEPTH` setting sets the cap, and defaults to `5`. Only fields that
return a list count, since a to-one relation joins into the same query and does not multiply the
rows. The depth is counted per selection path, so to-many relations selected side by side do not
add up. This complements `MaxComplexityRule`, which bounds the number of queries rather than the
number of rows.

> [!WARNING]
> **Breaking.** The rule is on by default. An operation that nests more than five to-many
> relations now fails validation. Raise `MAX_LIST_NESTING_DEPTH` if your schema needs deeper
> nesting.

Docs: [`MaxListNestingDepthRule`](https://mrthearman.github.io/undine/validation-rules/#maxlistnestingdepthrule)

#### Entrypoint complexity

An `Entrypoint` now works out its own complexity. One that runs a database query, like one based on
a `QueryType`, counts as 1. A `MutationType` counts as 1, but if its return type is a `QueryType`,
that `QueryType's` complexity is counted as well. One that runs none, like one based on a function,
counts as 0.

An `Entrypoint` based on a `UnionType` or an `InterfaceType` counts 1, plus 1 for each
member the operation selects fields from, since it runs one query per fetched member. Selecting a
field on the interface itself fetches every implementation, so it counts them all. The complexity
you pass to `Entrypoint` still adds on top of this. Note that `ComplexityDirective` in the schema
definition only counts the initial complexity.

> [!WARNING]
> **Breaking.** Every `Entrypoint` that reads the database now adds 1 to the complexity of an
> operation. An operation that passed before can now exceed `MAX_QUERY_COMPLEXITY`. Raise the
> setting to keep the budget you had.

The new `convert_to_entrypoint_complexity` converter decides these values for a reference.

Docs: [Complexity](https://mrthearman.github.io/undine/schema/#complexity)

#### Incremental delivery over HTTP

An operation that uses `@defer` or `@stream` now fails with a `400` and an
`INCREMENTAL_DELIVERY_NOT_REQUESTED` error when the client does not ask for incremental delivery.
The client asks for it by setting the `Accept` header to `multipart/mixed`. Before, such an
operation produced a response the client could not read.

`INCREMENTAL_DELIVERY_HEARTBEAT_INTERVAL` now defaults to `0`, which turns heartbeats off.
Heartbeats are not part of the incremental delivery over HTTP specification, so a client may
mishandle them. Set an interval to turn them back on.

Streaming responses no longer send the `Connection` header on HTTP/2 and later, where the
specification prohibits it.

Docs: [Incremental Delivery](https://mrthearman.github.io/undine/incremental/)

#### Schema export for federation and schema drift

`python manage.py print_schema` now prints the subgraph SDL for a schema built with
`create_federation_schema`, which matches what `Query._service` serves. The new `--check` option
compares the current schema against a committed SDL file, defaulting to `schema.graphql`, and exits
with a non-zero status if they differ.

Docs: [Federated subgraphs](https://mrthearman.github.io/undine/schema/#federated-subgraphs),
[Checking for schema drift](https://mrthearman.github.io/undine/schema/#checking-for-schema-drift)

### Minor features

- `QueryType.__optimizations__` is renamed to `QueryType.__optimize__`. The old name still works and
  raises a deprecation warning.
- `LifecycleHookContext` has a new `validation_errors` attribute. Adding errors to it in a hook
  exits the operation early with those errors.
- `ENTRYPOINT_DEFAULT_CACHE_TIME` now applies to every Query `Entrypoint` that does not set its own
  `cache_time`.
- `print_schema` builds the schema before printing it, so it can be used as a schema build smoke
  test in CI.
- `NamedTupleFieldResolver` and `TypedDictFieldResolver` are now exported from `undine.resolvers`.
- New settings for cursor pagination internals: `PAGINATION_ORDERING_KEY` and
  `PAGINATION_MEMBER_RANK_KEY`.
- New `VISIBILITY_MEMO_ATTRIBUTE` and `REQUEST_CACHE_ACTIVE_EXTENSIONS_KEY` settings.
- Added `graphql-core` 3.2 fallbacks for members that only exist on 3.3 `GQLInfo` objects.

### Fixes

- Operation lifecycle hooks for a subscription now stay open until the event stream ends.
- Visibility checks are memoized correctly. A re-entrant check no longer reads an unfinished result.
- Signal subscriber event delivery is now thread-safe.
- Interface implementations that are not reachable from a root type no longer crash the schema build.
- `BulkDeleteResolver.run_async` now checks `MUTATION_INSTANCE_LIMIT`.
- `GenericForeignKey` fields are no longer always nullable in the schema. This can change the
  nullability of existing fields.
- A `NamedTuple` annotation is no longer treated as a list. This can change the type of existing
  fields.
- `Entrypoint.limit` is no longer applied to a paginated `Entrypoint`, which returns the page its
  own arguments ask for.
- Connection `hasNextPage` no longer forces a total count query.
- Bulk mutations no longer return instances in database order.
- `django-debug-toolbar` 7.0.0 and later works with the GraphiQL integration again.
- `MaxComplexityRule` counts a fragment once per selection path instead of once per operation, so a
  fragment used in several places now adds up. An operation that passed before can now exceed
  `MAX_COMPLEXITY`.
- A `UnionType` or `InterfaceType` connection no longer fetches a member the operation selects no
  fields from. Such a member is left out of `totalCount` and gets no edges, which matches how the
  list `Entrypoints` have always behaved.
- A named fragment on a union member or an interface implementation now selects from that member
  only. Its fields used to be read from every member, which crashed for an interface and returned
  nothing for a union. An inline fragment on the abstract type itself now selects from every member,
  the same way a named fragment on it does.
- A `UnionType` or `InterfaceType` with three or more members no longer crashes. The members are now
  combined in a single union query instead of one nested union per member.
- ComplexityDirectives applied to Fields that have a default positive complexity no longer crashes.

### Maintenance

- `undine.relay` and `undine.resolvers.query` are now packages. Their public names are unchanged,
  except for the removed cursor helpers listed above.
- `InterfaceTypeResolver` takes its interface as the `interface_type` argument instead of
  `interface`.
- The `QuerySetMap` type alias is removed from `undine.typing`.
- Resolvers are now tested end-to-end.
- Minimum Django version restored to 5.0. 5.2.17 was set mistakenly by a previous release.
- Minimum versions raised: `graphql-core` 3.2.12 and `sqlparse` 0.6.0. For the
  extras, `django-debug-toolbar` 7.1.1 and `protobuf` 7.36.0.

---

**Full Changelog**: https://github.com/MrThearMan/undine/compare/v0.3.9...v0.4.0
