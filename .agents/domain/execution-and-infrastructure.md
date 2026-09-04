# Execution and infrastructure

**Operation**:
A single GraphQL request — parsed, validated, then executed through parsing, validation, and execution phases.
_Avoid_: Request (HTTP term alone), query (when mutations/subscriptions are included)

**Root value**:
The object passed as the first argument to a field resolver — always null at entrypoints, the model instance at query type fields.
_Avoid_: Root, self (Python convention), parent

**GQL info**:
Typed resolve info carrying the GraphQL execution context and Django request.
_Avoid_: Info, context (ambiguous with Django request context)

**Query optimizer**:
The component that inspects an incoming query's selection set and applies select_related, prefetch_related, and annotations to avoid N+1 queries and over-fetching.
_Avoid_: Optimizer (unqualified), ORM optimizer

**Optimization data**:
Per-queryset state accumulated by the query optimizer — selects, prefetches, annotations, filters, orders, and pagination.
_Avoid_: Optimization results (when meaning the in-flight accumulator)

**Data loader**:
A request-scoped batch loader for resolving related objects asynchronously without N+1 queries.
_Avoid_: DataLoader (in prose), batch loader

**Lifecycle hook**:
A callback invoked during parsing, validation, execution, or individual field resolution of an operation.
_Avoid_: Hook (unqualified), middleware (Django term)

**Directive**:
Metadata attached to schema types or operations — for example @atomic, cache rules, or complexity limits.
_Avoid_: Decorator (Python term), annotation

**Persisted document**:
A GraphQL operation stored server-side and referenced by document ID instead of sending the full query string.
_Avoid_: Stored query, allow-listed query

**Cache time**:
The number of seconds to cache a query response, settable on entrypoints, fields, query types, interface types, interface fields, and union types.
_Avoid_: TTL (unqualified), cache duration

**Per-user cache**:
Caching keyed to the authenticated user, enabled via `cache_per_user` alongside cache time.
_Avoid_: User cache, authenticated cache

**Restrictive cache rule**:
When nested objects define their own cache time, the shortest cache time among entrypoint and nested objects wins.
_Avoid_: Cache inheritance, cache override

**Query complexity**:
A cost score assigned to fields and entrypoints, summed for an operation and capped by the maximum query complexity validation rule.
_Avoid_: Complexity (unqualified), cost limit

**Subscription**:
A long-lived operation that pushes events to the client over WebSocket, SSE, or multipart HTTP.
_Avoid_: Live query, push notification

**Signal subscription**:
A subscription backed by a Django signal, typically for model create, update, or delete events.
_Avoid_: Model subscription, event subscription

**Subscription broker**:
The component that carries signal subscription events from the process that publishes an event to the processes holding subscribers for it.
_Avoid_: Message queue, event bus, pub/sub (unqualified)

**Subscription topic**:
The name of the event stream a signal subscription publishes to and its subscribers read from, computed identically in every process.
_Avoid_: Channel, group (both channel layer terms), queue
