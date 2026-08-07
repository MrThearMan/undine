# Datadog integration

## Context

**The user decided** to ship a bespoke Datadog integration rather than relying on Datadog's OTLP
ingestion. Read `.agents/plans/opentelemetry-hook.md` first — this plan is a sibling of it.

The evidence behind the decision, verified from Datadog's own documentation:

- Datadog's compatibility matrix (https://docs.datadoghq.com/opentelemetry/compatibility.md)
  states that using the **OTel SDK** loses Continuous Profiler, App & API Protection, Data Streams
  Monitoring, RUM correlation and Source Code Integration. Direct OTLP ingest additionally does not
  populate the Infrastructure Host List and yields sampled-only trace metrics.
- Strawberry's `DatadogTracingExtension` is **not** a legacy holdover, contrary to an assumption in
  an earlier draft of the OTel plan: it carries no deprecation notice and was recently updated to
  handle the ddtrace ≥3.0 import move. Datadog has signalled no intent to retire native
  instrumentation.

There is a partial escape hatch — `DD_TRACE_OTEL_ENABLED=true` makes ddtrace back the OTel API
(https://docs.datadoghq.com/opentelemetry/instrument/dd_sdks/api_support.md) — and the OTel plan
still requires depending on `opentelemetry-api` so that path works. But it depends on users
setting an environment variable they are unlikely to discover, and native ddtrace spans give
better Datadog-side ergonomics (resource names, service naming, span types). Hence a dedicated
integration.

### Reference implementation

`strawberry/extensions/tracing/datadog.py` in https://github.com/strawberry-graphql/strawberry.
Read it first. It is short, and it is a good model in most respects:

- **Version-gated import**, which is the sharp edge:
  ```python
  if version.parse(ddtrace.__version__) >= version.parse("3.0.0"):
      from ddtrace.trace import Span, tracer
  else:
      from ddtrace import Span, tracer
  ```
- **Operation span** via `tracer.trace(name, span_type="graphql", resource=..., service=...)`.
- **Resource name** of `f"{operation_name}:{md5(query)}"`, falling back to the bare hash when the
  operation is anonymous. This matters more than it looks: `resource` is Datadog's primary grouping
  dimension, so getting it wrong makes every trace land in one bucket.
- **Tags**: `graphql.operation_name`, `graphql.operation_type` on the operation span;
  `graphql.field_name`, `graphql.parent_type`, `graphql.field_path`, `graphql.path` on resolve
  spans.
- **Separate sync and async classes** (`DatadogTracingExtension` /
  `DatadogTracingExtensionSync`) — the same split this codebase needs for a different reason
  (see step 3).
- **An overridable `create_span` hook** so users can add their own tags without forking the
  extension. Worth copying; it is the difference between an integration people can adapt and one
  they have to replace.

One thing **not** to copy: operation type is detected with
`query.strip().startswith("mutation")`. See step 2.

## The work

### 1. Operation, parse and validation spans

Implement as a `LifecycleHook` (`undine/hooks.py`; `undine/federation/tracing.py` is a working
per-field tracer in this codebase to model on). Map `on_operation` / `on_parse` / `on_validation`
/ `on_execution` onto `tracer.trace(...)` spans with `span_type="graphql"`.

Default the service name to `"undine"` and make it configurable — the reference hardcodes
`service="strawberry"`, and users running several services will need to override it.

Reproduce the resource-name scheme (`operation_name:query_hash`), since Datadog grouping depends
on it. Note the hash is over the document text, so the same operation with different variable
values groups together, which is the desired behaviour.

### 2. Derive operation type from the AST, not the string

The reference does `query.strip().startswith("mutation")`. That is wrong for documents with a
leading comment, and for multi-operation documents where the executed operation is not the first.
Undine already parses the document and has `get_operation_definition` (used by
`AtomicMutationHook`, `undine/hooks.py:181`). Use it.

Sequencing caveat carried over from the OTel plan: the document is not parsed at the start of
`on_operation`, so operation name and type are set once known.

### 3. Per-field spans as a separate class

Same reasoning as the OTel and Sentry plans: `_get_middleware_manager`
(`undine/execution.py:660-662`) filters on `hook.__class__.resolve != LifecycleHook.resolve`, so
only a class that does not override `resolve` avoids the per-field middleware entirely. A runtime
flag would not.

Note the reference splits sync/async for a *different* reason — Strawberry's `resolve` is `async`
in the base class and overridden sync in the subclass. Undine's `LifecycleHook.resolve` is sync
and handles awaitables by wrapping, as `FederatedTracingHook.resolve` demonstrates
(`undine/federation/tracing.py:104-112`). Follow Undine's existing pattern rather than
Strawberry's class split.

### 4. Sensitive data

The reference attaches no query text by default — its docstring shows adding
`span.set_tag("graphql.query", ...)` as an *opt-in* customisation. Keep that default.

If the document is attached at all, the inline-literal problem from
`.agents/plans/opentelemetry-hook.md` §3 applies: `context.source` is the raw client document, so
hardcoded argument values leak. Share the AST-redaction helper across the OTel, Sentry and Datadog
integrations rather than writing it three times.

### 5. Packaging and docs

Add a `datadog` extra in `pyproject.toml` beside `image` / `debug` / `channels` /
`federation-tracing`. Fail with a clear actionable error when configured without `ddtrace` — copy
`_require_protobuf` (`undine/federation/tracing.py:42`). Place beside the other integrations in
`undine/integrations/`.

Pin a minimum ddtrace version if that lets you drop the <3.0 import branch; supporting both is a
maintenance cost worth declining unless there is a reason to carry it. Decide deliberately and
record the choice.

Document in `docs/integrations.md` with the `LIFECYCLE_HOOKS` snippet, the service-name setting,
and a note on when to prefer this over the OTel hook.

## Done when

- A GraphQL operation produces a Datadog trace with `span_type="graphql"`, a resource name of
  `operation_name:query_hash`, and the configured service name.
- Operation type is correct for query / mutation / subscription, including a document with a
  leading comment and a multi-operation document where the executed operation is not first —
  the cases the reference implementation gets wrong.
- Anonymous operations produce a stable resource name rather than an error.
- Async execution produces the same spans as sync; this is a separate path through the hook
  managers and needs its own test.
- Per-field spans appear only with the field-level hook class configured, and
  `_get_middleware_manager` returns `None` when only the operation-level class is enabled.
- No document text or variable values appear in span tags by default.
- The overridable span-creation hook lets a subclass add a tag without reimplementing the
  integration — cover it with a test, since it is the documented extension point.
- The library imports and the suite passes without the `datadog` extra installed.
