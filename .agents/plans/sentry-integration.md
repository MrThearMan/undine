# Sentry integration

## Context

**The user decided** to ship a bespoke Sentry integration rather than relying on Sentry's OTLP
ingestion. Read `.agents/plans/opentelemetry-hook.md` first — this plan is a sibling of it, not a
replacement.

The reasoning, which is worth recording because an earlier draft of the OTel plan got it wrong:

- Strawberry's `SentryTracingExtension` was removed in v0.249.0, but **not** because OTel made it
  obsolete. It was removed because Sentry built a first-party `StrawberryIntegration` inside the
  Sentry SDK (https://docs.sentry.io/platforms/python/integrations/strawberry/).
- The obvious conclusion — "so Sentry will do the same for Undine" — does not hold. Sentry
  maintains integrations for *established* frameworks. Undine is production-ready but not
  established, so waiting for a first-party `UndineIntegration` is waiting for something that has
  no reason to arrive.
- Sentry's direct OTLP endpoint is in **open beta** and **drops span events entirely**
  (https://docs.sentry.io/concepts/otlp/direct/traces/), so pointing OTel at Sentry is a
  degraded path, not an equivalent one.

So Undine ships this itself.

### Reference implementation

`sentry_sdk/integrations/strawberry.py` in https://github.com/getsentry/sentry-python is the
model. Read it before writing code. It does considerably more than emit spans, and the extra
parts are the whole reason a bespoke integration beats OTLP:

- **Transaction naming** — sets `transaction.name` to the GraphQL operation name with
  `TransactionSource.COMPONENT` and `op` set to `OP.GRAPHQL_QUERY` / `MUTATION` / `SUBSCRIPTION`.
  Without this every GraphQL request collapses into one `/graphql` transaction, which is the
  single biggest usability win here.
- **Error capture** — patches the view's `_handle_errors` and calls `event_from_exception` +
  `capture_event` per GraphQL error, with `mechanism={"type": ..., "handled": False}`.
- **Breadcrumbs** — `add_breadcrumb(category="graphql.operation", ...)`.
- **Event processors** — attach `request.data` with query / variables / operationName and set
  `request.api_target = "graphql"`, plus a response processor attaching response data.
- **Spans** for operation, parse, validation and per-field resolve.

Note that the reference achieves all this by monkeypatching `Schema.__init__` and the view
classes, because it is an outside observer of Strawberry. **Undine does not need to monkeypatch
anything** — it owns its execution path and already has `LIFECYCLE_HOOKS`. Ship a `LifecycleHook`
that users add to that setting. That is a strictly simpler design than the reference, and the
simplification is the point; do not port the patching machinery.

## The work

### 1. Spans and transaction naming

Implement as a `LifecycleHook` (see `undine/hooks.py`, and `undine/federation/tracing.py` for a
working per-field tracer in this codebase). Map `on_operation` / `on_parse` / `on_validation` /
`on_execution` onto Sentry spans using the `OP.GRAPHQL_*` constants from `sentry_sdk.consts`.

Set the transaction name from the operation name. Determine operation type from the parsed
document via the existing `get_operation_definition` helper (used by `AtomicMutationHook`,
`undine/hooks.py:181`) — **not** by string-prefix matching on the raw query, which is what both
the Sentry and Datadog reference implementations do
(`self.execution_context.query.strip().startswith("mutation")`). That heuristic misbehaves on
leading comments and on documents whose first operation is not the one being executed. Undine has
the AST; use it.

Remember the sequencing constraint from the OTel plan: the document is not parsed at the start of
`on_operation`, so operation name and type must be applied once known.

### 2. Error capture

Sentry's value over a pure tracer is that GraphQL errors become Sentry Issues with context. After
the yield in `on_operation`, `context.result` holds the `ExecutionResult`
(`GraphQLResult` is an alias for graphql-core's `ExecutionResult`, `undine/typing.py:336`), whose
`.errors` is the list to report. Use `event_from_exception` + `capture_event` per error, following
the reference's `mechanism` shape.

Consider whether every GraphQL error should become an Issue — validation errors and permission
denials are usually client errors, not incidents, and reporting them all is how observability
integrations become noise. A predicate setting (following `REQUEST_CACHE_READ_PREDICATE`'s
convention) lets users decide. Raise this with the user if the default is not obvious.

Undine logs through a logger named `"undine"` (`undine/utils/logging.py:17`). The reference calls
`ignore_logger("strawberry.execution")` to stop Sentry's logging integration double-reporting the
same failure. Check whether Undine's logger creates the same duplication and apply the same fix if
so.

### 3. PII — the part most likely to be got wrong

Do **not** attach the document or variables unconditionally. The reference gates them behind
`should_send_default_pii()` and, in newer SDKs, `has_data_collection_enabled(client_options)` with
separate `data_collection.graphql.document` and `data_collection.graphql.variables` flags. Follow
the SDK's own gating rather than inventing a parallel setting, so users get one consistent control.

The inline-literal problem from the OTel plan applies identically here: `context.source` is the
raw client document, so hardcoded argument values leak even when variables are withheld. The AST
redaction approach described in `.agents/plans/opentelemetry-hook.md` §3 is reusable — factor it
somewhere both integrations can share rather than implementing it twice.

### 4. Per-field spans

Same decision as the OTel plan: a separate hook class rather than a runtime flag, because
`_get_middleware_manager` (`undine/execution.py:660-662`) filters on
`hook.__class__.resolve != LifecycleHook.resolve`, so only a class that doesn't override `resolve`
avoids the middleware entirely. Field tags to mirror the reference: `graphql.field_name`,
`graphql.parent_type`, `graphql.field_path`, `graphql.path`.

### 5. Packaging and docs

Add a `sentry` extra in `pyproject.toml` beside `image` / `debug` / `channels` /
`federation-tracing`. Fail with a clear actionable error when configured without the dependency —
copy `_require_protobuf` (`undine/federation/tracing.py:42`). Place beside the other integrations
in `undine/integrations/`.

Document in `docs/integrations.md`, including the `LIFECYCLE_HOOKS` snippet, the PII defaults, and
a plain statement that this is the recommended path for Sentry users rather than OTLP.

## Done when

- A GraphQL operation produces one Sentry transaction named after the GraphQL operation, not the
  HTTP route, with the correct `op` for query / mutation / subscription.
- Operation type is derived from the AST — a query with a leading comment, and a document
  containing several operations where the executed one is not first, both report correctly. These
  are the cases the reference implementations get wrong, so test them explicitly.
- A resolver raising an exception produces a Sentry event with GraphQL context attached.
- The same failure is not reported twice via the logging integration.
- With default settings, neither variables nor inline literal argument values appear in any
  captured event or span. Test with a hardcoded string argument, not just a variable.
- Enabling Sentry's PII option attaches the document as expected.
- Async execution behaves identically to sync — separate code path through the hook managers,
  so it needs its own test.
- Per-field spans appear only with the field-level hook class configured.
- The library imports and the suite passes without the `sentry` extra installed.
