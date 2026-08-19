# Why Undine does not use class hierarchies

Undine's schema-declaration classes — `Field`, `Input`, `Entrypoint`, `Filter`,
`Order`, `FederationField` — do not form class hierarchies keyed on the kind of
thing they represent. Each holds a single `ref: Any` and delegates every
ref-dependent behavior (GraphQL type, resolver, nullability, complexity,
argument map, description, etc.) to a family of dispatch-based **converters**
in `undine/converters`. The dispatcher backing them (`FunctionDispatcher`) is
custom rather than `functools.singledispatch`. This document records why.

## Context — Django-first, not GraphQL-first

Undine assumes a service that owns its database, where Django Models are the
source of truth for *both data and types*. GraphQL is a *derivation* of the
model, not a parallel type system.

This premise inverts what Strawberry and Graphene do. Those libraries are
generic GraphQL-first frameworks with a Django adapter layered on top: you
declare GraphQL types as Python classes, and a Django wrapper
tries to line them up with your models. That path buys ecosystem generality
and dataclass-typed instances, and pays for it with a persistent
GraphQL-vs-model impedance mismatch that shows up as DataLoaders, N+1
workarounds, and typed shells that don't quite fit the underlying model.

Undine picks the opposite trade. The model is the type. QueryType and
MutationType are *schema declarations*, not data classes — user code never
holds instances of them. Every user hook (`__permissions__`, `@Field.resolve`,
`@MutationType.validate`) receives a Model instance or an input dict, not a
QueryType instance. That decision is what makes converters not just viable
but necessary, and this ADR is really about the shape that decision forces.

## Decision

Every schema-declaration class holds `ref: Any` and consults converters at
class-body evaluation time to derive its schema behavior. Converters are
single-dispatch generic functions built on a bespoke `FunctionDispatcher`.
The library ships default implementations under `../../undine/converters/impl`;
users extend or override behavior by registering new implementations for their
own ref types.

## Rationale

### 1. Inference from the model is not enough

The alternative that first suggests itself is a fixed lookup table.
That works for the built-in Django fields, and for a library that stops there,
it is the right answer. Undine cannot stop there.

Two things break the table.

First, the model is authoritative but *incomplete*. Users have custom Django
field subclasses, project-specific types, JSON payloads, and computed values
that don't correspond to any model field at all. If the mapping is a hardcoded table,
the user has no way to teach the library about any of these except by forking
or monkey-patching a library-internal dict. That is exactly the brittleness the
"Model as source of truth" premise was supposed to fix.

Second, users legitimately want to *override* the library's defaults for a type Django
already handles. A project standardizing on [`whenever`][whenever]{:target="_blank"}
will want it applied everywhere. A hardcoded table means editing the library or shipping
a wrapper that reaches into library internals.

[whenever]: https://github.com/ariebovenberg/whenever

Converter dispatch resolves both. The library ships defaults for the common
cases. Users register their own implementations for custom types. Overrides
propagate to every consumer without touching Field, Input, or any other
declaration class. The single-declaration property is preserved: the model
remains the one place types are declared, and the converter tree is how the
schema derives from it.

The alternative that seems to answer both is to restate types explicitly on
the GraphQL side — whether as dataclass-style attribute annotations (`id:
int`, `name: str`, `created_at: datetime` alongside the model) or as
per-type Field subclasses (`IntegerField()`, `CharField()`, `DateTimeField()`).
Either shape reintroduces the drift problem: every model change becomes
two edits, the second is easy to forget, and CI might not catch a GraphQL
field that silently kept its old shape while the underlying model column
changed. Undine's premise is that this drift is not worth paying for. The
subclass-hierarchy variant has additional problems beyond drift, addressed
in rationale 3.

A skeptical reader might note that both Strawberry-Django and Graphene-Django
ship inference layers of their own (`@strawberry_django.type` with `strawberry.auto`
and `DjangoObjectType` with `Meta.model` & `Meta.fields` respectively)
so the "restate types explicitly" alternative is not really what those libraries
offer to their Django users today. That is precisely the point. Peer libraries
recognized that Django users need inference and added it. Where they differ
from Undine is that inference is a Django-specific adapter over a GraphQL-first core:
the underlying library still expects declarative GraphQL types and the Django
integration is a second layer that translates between them. Undine collapses
the two layers by starting from the Django premise. The convergence on
inference is evidence that the premise is right, the disagreement is about
whether inference is the *core* or an *adapter*.

### 2. One-line global override

Once the extension seam exists at all, the shape of the seam matters.
A user who wants datetimes handled by a `whenever` writes:

```python
@datetime_scalar.parse.register
def _(value: str) -> ZonedDateTime:
    return ZonedDateTime.parse_common_iso(value)


@datetime_scalar.serialize.register
def _(value: Instant | ZonedDateTime | PlainDateTime) -> str:
    return value.format_common_iso()
```

Those registrations reach every place datetimes are used as a ref.
There is no other subclass to write, no other consumer to notify,
no monkey-patch of a Field method that some other consumer bypasses.

The alternative is a subclassing model: `class MyDateTimeField(DateTimeField):
...`, and every place the user's code declares a datetime field they must
remember to reach for `MyDateTimeField` rather than the library default. The
override is opt-in per-declaration, which is exactly the opposite of what the
user asked for. They said "we use `whenever` in this codebase"; they did not
say "we use `whenever` in the fields we remembered to convert."

Cross-class strategy reuse falls out of the same property. `Field` and
`Input` and `Filter` all agree on `convert_to_graphql_type` without sharing
a base class or a mixin. Adding a new consumer that also needs the same
type-conversion behavior costs zero — it just calls the same converter.

### 3. The class-hierarchy alternative

This is the rationale where the alternative is strongest and most familiar.
Django does `IntegerField()`. DRF does `serializers.IntegerField()`. Graphene
does `graphene.Int()`. Strawberry does typed dataclass attributes. Every peer
library takes this path, and it is not because they are confused. It is a
legitimate design choice. So this is the place to be most careful.

What Undine gets from *not* taking that path is not "correct ontology." It
is three specific properties that a class hierarchy cannot deliver together.

#### Cross-class reuse of a strategy

Field and Input need to agree on how a `datetime` becomes a GraphQL type.
Under a class hierarchy, that agreement can live in one of two places.
The first option is a shared base class or mixin that both parallel
hierarchies inherit from. This forces `DateTimeField` and `DateTimeInput`
to share more than their type-conversion behavior. The second option is a
helper function both hierarchies call. At that point the helper is a
proto-converter and the hierarchy has stopped carrying its weight.
Under converters, the shared strategy is a single `.register` and
the two hierarchies are just callers.

#### Overriding library defaults from user code without vendoring

Under a class hierarchy, overriding how the library's own `Field(datetime)`
resolves means either subclassing the library's Field type (which every
downstream user must then be taught to use) or monkey-patching a method on
the library's class. Under converters, a `.register` in user code shadows the
library default for every consumer at once. Consequence 4 documents the
cost of this.

#### A stable extension seam, whose shape depends on the converter's role

Undine's converters split into two kinds in practice.

First are the cross-cutting type-conversion converters whose implementations
are pure `ref -> value` transformations and do not read from the calling descriptor.
A user registering a new type here couples only to the converter interface.
The caller can be renamed, restructured, or split without affecting
these registrations. This is the "narrow contract survives refactors"
case in its strongest form.

Second are the per-descriptor converters whose implementations do reach
into the calling descriptor. These converters are less "shared strategy" and more
"the descriptor's own per-ref-kind logic factored out of a hypothetical subclass".
The user-facing win here is different: a user can teach Undine how a specific
descriptor handles a new ref kind without patching that descriptor's source.
Coupling to the caller is intrinsic to what these converters are for, and
a rename of the caller internals would need matching updates in these converters.
That is a real cost but the alternative under a class hierarchy would be
either editing the library's source or subclassing it, and subclass
extensions couple to the same internals plus the MRO.

### 4. A bespoke dispatcher

Once converters are the plan, the natural next step is `functools.singledispatch`.
It is stdlib, familiar, and covers the simple cases. Undine started this way
but outgrew it. `FunctionDispatcher` exists to fill the gaps `singledispatch`
does not cover.

#### Classes vs instances

`singledispatch` dispatches on `type(value)`. Undine's refs are frequently
*not* instances: `Field(int)`, `Field(str)`, `Field(UUID)`, and
`Field(QueryType)` each pass a class value that must resolve to a
different GraphQL type or scalar.

Under `singledispatch`, `type(str)`, `type(int)`, and `type(UUID)` are all `type`.
Every "the ref is a class" registration collapses into a single `type` handler
with no way to fan out to per-class behavior. The only workaround is an
`isinstance` chain inside that one handler, which is precisely what a
dispatch table exists to avoid.

### Lambdas

`Field(lambda: QueryType)` is Undine's answer to circular references between
query types. If the user were forced to declare a resolver function instead
of a lambda ref, they would routinely trip the optimizer and produce N+1 queries.
The lambda form keeps the reference declarative and lets the optimizer see it.
`singledispatch` cannot distinguish a lambda from a `def`: both are `FunctionType`.

### Literals

Sometimes the ref is a string, but the specific string value determines
the behavior, not just the fact that it is a string. `singledispatch`
dispatches by `type(value)`, so every string ref lands on the same handler
regardless of what it says. The choices at that point are (1) a growing
`if/elif` chain inside a single `str` handler, forfeiting the per-value
extension seam and reintroducing the exact structure the dispatch table
was there to avoid; or (2) a dispatcher that treats string values as
first-class dispatch keys. Undine's implementation offers the latter,
supporting dispatch using `Literal`.

## Consequences

### 1. Subsystem-locality at the cost of ref-locality

A converter tree organizes code *by concern*: one file per behavior, every
ref type's handling of that behavior lives inside it. A class hierarchy
would organize code *by ref kind*: one file per Field subclass, every
behavior's implementation for that ref lives inside it. Neither is
universally better, they optimize for different readers.

A library maintainer is well served by the converter layout. Every ref's
handling of, say, GraphQL type conversion is in one file. Under a class
hierarchy, the same maintainer would have to grep every subclass and
reconstruct the picture from N method overrides.

The newcomer studying one specific library ref ("how does `Connection`
actually behave?") is worse served. It participates in many converters
spread across different files. Reading its definition alone does not
tell a reader what it does. Under a class hierarchy, its behavior would
appear to live in one class, though "appear" is doing work here:
an inheritance-heavy hierarchy hides its own distribution behind MRO walks
and `super()` chains, so the "one class" locality is partly illusion.
But the illusion has real ergonomic value for newcomers, and the
converter layout does not offer it.

Undine accepts the trade because the maintainer axis is where hours are
spent and the newcomer papercut is documentable. To find all converter
implementations for a given ref:

```bash
just ref-find Connection
```

Users writing their own refs can dodge the newcomer papercut entirely by
co-locating the ref and its converter registrations in one module.
Undine itself cannot do this due to import loops and Django-app readiness issues.

### 2. Converter registration is a side effect of import

Undine's Django app config imports every converter implementation,
so library defaults are always in place before any user types are defined.

User-registered converters should be registered in one of two places:

1. **Co-located with the ref in one module.** The `.register` calls
   run the first time the ref itself is imported. This is the preferred
   pattern when the ref is not otherwise widely imported.

2. **Separate converter module + explicit import in `AppConfig.ready()`.**
   Similar to how you might have registered Django's signals.
   Use when you cannot co-locate the ref and its converter registrations.

> If a user's converter module is never imported, that converter implementation
will not be found and dispatch will either use the library default or fail.

### 3. Type erasure is bounded

The `ref` type in all descriptors is `Any`. Static tools cannot see the schema
behavior a Field is going to produce. This looks like a large cost on the surface.
For Undine, the cost it is actually small because user code never reads Field
instances at runtime. QueryTypes and MutationTypes are schema declarations,
not data classes. The Model instance is the runtime type everywhere hooks fire.

The one seam where `ref: Any` would leak into user-visible typing is the
return type of a resolver method having to match the ref. Undine's mypy
plugin can perform that check statically.

### 4. Registration is last-wins, deliberately

`FunctionDispatcher` registers without an "already-registered" guard.
The most recently registered implementation for a given key wins.
This is not an oversight; it is the mechanism by which users override
library behavior. If a user finds a bug in a library converter or wants
to change how the library handles a specific ref type, they can register
their own implementation in their own codebase and ship it without
waiting for a library release. This is Undine's alternative
to a plugin ecosystem that monkey-patches internals: the sanctioned
override lives at the same seam every other extension lives at,
and users can vendor a converter they like from the library and
diverge from there.

The honest cost is symmetric. Two Django apps registering for the same
ref type will silently clash in whatever order `AppConfig.ready()`
runs them, and Undine does not detect or arbitrate. Users who vendor
a library converter to patch it also opt out of future upstream fixes
to that converter until they re-vendor. Managing clashes and version drift
is the user's responsibility: register user converters in exactly one
place per project in a module whose import order is under the project's
control, and when vendoring a library converter, track the upstream
source so a future re-vendor can pick up subsequent fixes.

## Subclassing is not recommended, but allowed

Undine does not prevent you from subclassing its types.
If you really must subclass, do so to bundle configuration or add
structural constraints. Do not subclass to vary ref-dependent behavior.
Varying schema derivation is what converters are for.
