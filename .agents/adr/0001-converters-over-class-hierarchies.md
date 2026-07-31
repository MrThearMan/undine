---
status: accepted
---

# Converters over class hierarchies for schema-declaration types

Full rationale: [`.agents/docs/why-converters.md`](../docs/why-converters.md)

## Context

Undine is Django-first: the Django model is the source of truth for **both
data and types**, and GraphQL is a *derivation* of the model. QueryType,
MutationType, and their siblings are **schema declarations**, not data
classes — user code never holds instances of them. Every hook
(`__permissions__`, resolvers, validators) receives a model instance or an
input dict, never a QueryType instance.

## Decision

Schema-declaration classes — `Field`, `Input`, `Entrypoint`, `Filter`,
`Order`, `FederationField` — do **not** form class hierarchies keyed on the
kind of thing they represent. Each holds a single `ref: Any` and delegates
every ref-dependent behavior (GraphQL type, resolver, nullability,
complexity, argument map, description, …) to single-dispatch generic
functions in `undine/converters`, built on a bespoke `FunctionDispatcher`
rather than `functools.singledispatch`.

Users extend or override behavior by registering new implementations for
their own ref types. Registration is **last-wins** by design.

## Why not the obvious alternatives

- **Per-ref subclasses (`IntegerField`, `CharField`, …).** Blocks
  cross-class strategy reuse (Field, Input, Filter would each need their own
  `DateTimeXxx`), forces per-declaration opt-in for overrides (the user
  says "we use `whenever` everywhere", not "in fields we remembered to
  swap"), and makes library-default overrides require subclassing or
  monkey-patching. A single `.register` call reaches every consumer.
- **Restating types on the GraphQL side (dataclass annotations or explicit
  field-per-column).** Reintroduces model/GraphQL drift, which is exactly
  the impedance mismatch the Django-first premise exists to avoid.
- **`functools.singledispatch`.** Cannot distinguish `Field(int)` from
  `Field(str)` (both are `type`), cannot distinguish `Field(lambda: T)`
  from a `def` resolver (both are `FunctionType` — the lambda form is how
  circular refs stay declarative and optimizer-visible), and cannot
  dispatch on specific string values (Undine dispatches on `Literal[...]`).

## Consequences and anti-patterns

Things a future contributor (human or AI) is likely to "fix" and should not:

- **`ref: Any` is intentional.** Type erasure at the descriptor is bounded
  because user code never reads Field instances at runtime. The one seam
  that would leak (resolver return type vs ref) is covered by the mypy
  plugin. Do not try to make `Field` generic in its ref, do not add
  `IntegerField`/`CharField` subclasses to "recover types".
- **Last-wins registration is the override mechanism**, not a missing
  duplicate-guard. Do not add "already registered" errors to
  `FunctionDispatcher`. Users override library defaults (and vendor
  library converters) through this seam.
- **Converters are organized by concern, not by ref kind.** One file per
  behavior; a given ref participates in many converters across many files.
  This is a deliberate maintainer-ergonomics trade against newcomer
  locality. Use `just ref-find <RefName>` instead of reorganizing.
- **Registration as an import side effect is load-bearing.** Undine's
  `AppConfig.ready()` imports every converter implementation so defaults
  are in place before user code runs. User-registered converters must be
  reachable via import — either co-located with the ref or imported from
  their app's `ready()`. Do not "clean this up" into lazy or explicit
  registration APIs without preserving both properties.
- **Subclassing schema-declaration types to vary ref-dependent behavior is
  the wrong seam.** Subclassing is tolerated for bundling configuration or
  adding structural constraints; varying schema derivation is what
  converters are for.

If a change seems to want a class hierarchy, or a shared base class between
Field/Input/Filter, or `functools.singledispatch`, or an "unregister" API,
re-read the full rationale first — the alternative was considered and
rejected for reasons that are not obvious from the code.
