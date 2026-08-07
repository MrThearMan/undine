# OpenTelemetry instrumentation hook

## Context

Undine has no observability integration. This is the clearest feature gap against
strawberry-graphql, which ships `OpenTelemetryExtension` / `OpenTelemetryExtensionSync` plus
Sentry, Datadog, Apollo-tracing and pyinstrument extensions. Ariadne ships an OTel extension too.

**The user has decided** to close this by shipping instrumentation built on Undine's existing
lifecycle hooks, mirroring what Strawberry's extensions do. This is packaging work, not
architecture work — every seam needed already exists.

### The architecture is already proven in-tree

`undine/federation/tracing.py` (`FederatedTracingHook`) is a working per-field tracer built on
`LifecycleHook`. Read it before writing anything; an OTel hook is the same shape with spans
instead of protobuf nodes. In particular `resolve` (`undine/federation/tracing.py:93-115`)
already solves the two non-obvious problems:

- It times sync and async resolvers uniformly by checking `isawaitable(result)` and, when
  awaitable, returning a wrapper coroutine that records in a `finally`. There is no
  `resolve_async` on `LifecycleHook`, so this pattern *is* the async story.
- It builds a node tree from `info.path.as_list()`, and reads `info.parent_type` /
  `info.return_type` for span attributes.

`FederatedTracingHook` also demonstrates the optional-dependency pattern (`_require_protobuf`,
raising a clear error when the extra is missing) and the `pyproject.toml` extras convention
(`federation-tracing = ["protobuf"]`, `undine/federation/tracing.py:42`).

### Cost when not installed is already zero

The hook managers skip hooks that don't override a given method — e.g.
`OperationLifecycleHookManager.enter_sync` compares `hook.__class__.on_operation` against
`LifecycleHook.on_operation` (`undine/hooks.py:527`), and `_get_middleware_manager`
(`undine/execution.py:660-662`) returns `None` unless some hook overrides `resolve`. So an
uninstalled hook adds no per-field overhead, and a hook that only implements operation-level
spans adds no per-field overhead either. This matters for the design decision below.

## The work

### 1. Operation-level spans

One span per GraphQL operation via `on_operation`, with child spans for `on_parse`,
`on_validation` and `on_execution`. All four hooking points already exist in both sync and async
form, and `LifecycleHookContext` (`undine/hooks.py:52-77`) carries everything needed for
attributes: `source`, `document`, `variables`, `operation_name`, `extensions`, `request`, `result`.

Use the OpenTelemetry semantic conventions for GraphQL rather than inventing attribute names:
`graphql.operation.name`, `graphql.operation.type` (values `query` / `mutation` / `subscription`),
and `graphql.document`.
See https://opentelemetry.io/docs/specs/semconv/registry/attributes/graphql/

The operation *type* is on the parsed operation definition, not the context — there is an existing
`get_operation_definition` helper used by `AtomicMutationHook` (`undine/hooks.py:181`). Note the
document is only parsed after `on_parse`, so operation type is unavailable at the very start of
`on_operation`; set it once known rather than restructuring the hooks.

Record errors on the span and set the span status when the operation fails. `context.result`
holds the execution result.

### 2. Per-field spans, off by default

A span per resolver is genuinely expensive on large responses — a 100-item list with 10 fields is
1,000 spans.

**Decided by the user:** ship two hook classes and let a setting select between them, rather than
one class with a runtime flag. This is not just a style preference — `_get_middleware_manager`
(`undine/execution.py:660-662`) filters on `hook.__class__.resolve != LifecycleHook.resolve`,
i.e. on the *class*, so a per-instance flag would still drag every field through the middleware
chain and defeat the zero-overhead path. Only the operation-level class overrides `resolve`.

### 3. Redaction

The OTel semconv note on `graphql.document` says instrumentation SHOULD redact sensitive
information where it can reliably identify it. The concern is PII — emails, phone numbers,
addresses — not just credentials.

There are **two** distinct channels, and covering only the first is a trap:

1. **Variables** — `context.variables`. Do not attach by default.
2. **Inline literals in the document** — `context.source` is the raw client-sent string
   (`LifecycleHookContext.source` ← `GraphQLHttpParams.document`, `undine/hooks.py:85`), so
   attaching it verbatim leaks any argument the client hardcoded rather than parameterised.

**Verified by experiment on this machine** that this is a real distinction and that the fix is
cheap. Given:

```graphql
query Login($pw: String!) {
  a: user(email: "alice@example.com", ssn: "123-45-6789") { id }
  b: user(token: $pw) { id }
}
```

`context.source` contains the email and SSN verbatim. Rewriting the parsed AST with a
`graphql.Visitor` that replaces `StringValueNode` / `IntValueNode` / `FloatValueNode`, then
`print_ast`, yields:

```graphql
query Login($pw: String!) {
  a: user(email: "***", ssn: "***") { id }
  b: user(token: $pw) { id }
}
```

Note this is exactly the shape the semconv example shows (`bookById(id: ?)`) — the document
retains its structure, which is what makes it useful for grouping traces by operation shape,
while the values are gone. It also means the attribute has bounded cardinality, which matters to
tracing backends.

Prefer redacting the printed AST over attaching `context.source`. The document is only parsed
after `on_parse`, so the redacted form is unavailable at the very start of the operation span —
same sequencing caveat as operation type.

For variables, follow Undine's existing callback-setting convention (see
`PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`, `REQUEST_CACHE_READ_PREDICATE`). Default to attaching
no variables.

### 4. Packaging

Add an `opentelemetry` extra in `pyproject.toml` alongside the existing `image`, `debug`,
`channels`, `federation-tracing` extras, and fail with a clear actionable error when the hook is
configured without the dependency installed — copy `_require_protobuf`'s approach.

**Depend on `opentelemetry-api`, not `opentelemetry-sdk`.** This is the standard split — libraries
instrument against the API, applications configure the SDK — and here it has a concrete payoff
documented in section 6: it is what allows Datadog users to get full Datadog features from the
same code.

Place the module where it will be found by analogy with existing integrations; `undine/integrations/`
holds the third-party integrations (`channels.py`, `debug_toolbar.py`, `modeltranslation.py`),
which looks like the right home, but check whether `LIFECYCLE_HOOKS` consumers expect hooks
elsewhere before deciding.

### 5. Documentation

`docs/lifecycle-hooks.md` documents the hook system; the new hook belongs there or in
`docs/integrations.md` alongside the other third-party integrations. Include the `LIFECYCLE_HOOKS`
setting snippet needed to enable it, and state plainly that per-field spans are opt-in and why.

Document the vendor situation from section 6 — specifically the Datadog `DD_TRACE_OTEL_ENABLED`
path, since users will not discover it on their own.

### 6. Relationship to the Sentry and Datadog integrations

An earlier draft of this plan recommended shipping OTel only, on the grounds that both vendors
ingest it. Research against primary vendor docs showed the caveats are real, and **the user
decided** to ship bespoke integrations for both. See `.agents/plans/sentry-integration.md` and
`.agents/plans/datadog-integration.md`, which record the evidence.

The short version of why OTel alone was not enough:

- **Sentry's** OTLP endpoint is in open beta and drops span events. Strawberry's
  `SentryTracingExtension` was removed only because Sentry ships a first-party
  `StrawberryIntegration` — and Sentry maintains integrations for established frameworks, so
  Undine cannot expect the same treatment.
- **Datadog** users on the OTel SDK lose Continuous Profiler, App & API Protection, Data Streams
  Monitoring, RUM correlation and Source Code Integration
  (https://docs.datadoghq.com/opentelemetry/compatibility.md).

This hook remains the right default for everyone not on those two vendors, and the
`opentelemetry-api` requirement in step 4 still matters: it is what makes
`DD_TRACE_OTEL_ENABLED=true` work for Datadog users who prefer the OTel path.

**Shared work:** all three integrations need the same AST redaction helper (step 3), the same
operation-type-from-AST logic, and the same operation-level/field-level class split. Whichever is
implemented first should factor those so the other two reuse them rather than reimplementing.

## Done when

- A test asserts spans are emitted for a GraphQL operation with the semconv attributes set,
  using the OTel in-memory span exporter (`InMemorySpanExporter`) rather than a live collector.
- Operation type is correct for queries, mutations and subscriptions.
- A failing operation marks the span with error status and records the exception.
- Async execution produces the same spans as sync — the async path is a genuinely separate code
  path through the hook managers, so it needs its own test.
- With the hook not configured, `_get_middleware_manager` still returns `None` for a normal
  operation. This is the regression guard for the zero-overhead claim; assert it directly.
- Per-field spans appear only when explicitly enabled.
- Variables are absent from span attributes unless a redaction callback opts them in.
- Inline literal values in the document do not appear in span attributes. Test with a query that
  hardcodes a string argument rather than passing it as a variable — the value must be absent
  while the operation's structure is retained.
- The library imports and the suite passes with the `opentelemetry` extra *not* installed —
  the dependency must stay genuinely optional.
- The hook works with only `opentelemetry-api` installed (no SDK). This is what makes the
  Datadog `DD_TRACE_OTEL_ENABLED` path work, so it is worth asserting rather than assuming.
