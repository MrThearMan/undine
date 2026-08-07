# Validation result caching

## Context

Undine re-parses and re-validates every non-persisted document on every request. Strawberry ships
`ValidationCache(maxsize=N)`, an LRU over validation results, and mirroring it looks like a
half-hour job.

**It is not, and the reason matters: a naive document-keyed cache is a security bug in Undine.**

Strawberry can cache on the query string because Strawberry has no per-request schema visibility.
Undine does. `_validate` (`undine/execution.py:665-695`) takes `document`, `variables` *and*
`request`, and two of the rules it runs depend on more than the document:

- `VisibilityRule` is only included when visibility is active and the call is inside a request
  (`undine/utils/graphql/validation_rules/__init__.py:29-36`), and it resolves visibility against
  `self.context.request` — i.e. against **the user**
  (`undine/utils/graphql/validation_rules/visibility_rule.py:51-54`).
- `VisibilityRule.enter_argument` reads **variable values** via
  `self.context.variable_as_ast(...)` (`visibility_rule.py:90-91`), which looks them up in
  `UndineValidationContext.variables` (`undine/execution.py:941-945`). So filter and order
  arguments passed as variables change the validation outcome.

**Verified by experiment on this machine.** A `QueryType` with a field visible only to
superusers, queried with the identical document `query { tasks { secret } }`:

```
anonymous -> ["Cannot query field 'secret' on type 'TaskType'."]
superuser -> NO ERRORS (field allowed)
```

Caching that result under the document alone would serve the anonymous user's rejection to the
superuser, or — far worse — serve the superuser's pass to an anonymous user, defeating the
visibility system entirely.

Note that `docs/visibility.md:12` states plainly that visibility is *not* a security boundary, so
this is a correctness-and-trust problem rather than a privilege-escalation hole. It would still
make the feature behave unpredictably in exactly the deployments that care about it most.

## The work

### 1. Decide the cache key

This is the whole design; the LRU itself is trivial. Options, in increasing order of usefulness
and risk:

- **Cache only when `VisibilityRule` is not in play.** `get_validation_rules` already computes
  `visibility_enabled` (`validation_rules/__init__.py:31`); when it is false, validation is a pure
  function of the document plus the schema, and a document-keyed cache is safe. This is the
  conservative option and covers every project that does not use visibility.
- **Include the user and the visibility-relevant variables in the key** when visibility is
  active. Undine already has this problem solved elsewhere and the prior art should be reused
  rather than reinvented: `VisibilityCacheHook` caches introspection per user with
  `VISIBILITY_CACHE_EXTRA_CONTEXT` for extra key components, and `RequestCacheHook` builds keys
  from document + variables + operation name + extensions + user. Read both in `undine/hooks.py`
  before designing a third scheme.

Recommendation: start with the conservative option, and treat the per-user variant as a separate
decision — the payoff is smaller (visibility users already pay for `VisibilityCacheHook`) and the
risk is higher.

### 2. Invalidate on schema change

The cached result is only valid for the schema it was computed against. `undine_settings.SCHEMA`
is swapped constantly in the test suite, and can change at runtime. Key on schema identity, or
clear the cache when the schema is replaced. Without this the suite will produce confusing
cross-test failures — treat a passing suite under this change as a meaningful signal.

### 3. Cache parse as well as validation

`on_parse` and `on_validation` are separate hooking points and parsing is not free either. The
parse cache is genuinely document-keyed with none of the above complications, so it may be worth
shipping first, on its own. `MAX_TOKENS` (`undine/settings.py`) bounds document size, which bounds
what the cache can hold.

### 4. Bound the cache

Use an LRU with a configurable `maxsize`, following Strawberry. An unbounded dict keyed on
arbitrary client-supplied documents is a memory-exhaustion vector — an attacker can send endless
distinct documents. This is the one place where getting it wrong turns a performance feature into
a denial-of-service surface.

Consider whether the cache belongs per-process or in Django's cache framework. `RequestCacheHook`
uses the latter (`REQUEST_CACHE_ALIAS`); an in-process LRU is faster and simpler but does not
share across workers. Either is defensible — say which and why.

### 5. Interaction with persisted documents

`PERSISTED_DOCUMENTS_ONLY` already restricts execution to a known document set, which caps the
key space and makes caching strictly safer. Worth noting in the docs: the two features compose
well, and the memory concern in step 4 largely evaporates when persisted documents are enforced.

### 6. Implementation shape

A `LifecycleHook` implementing `on_parse` / `on_validation`, added to `LIFECYCLE_HOOKS`, matching
the existing built-in hooks in `undine/hooks.py`. Follow how `RequestCacheHook` short-circuits by
setting `context.result` — though note this hook needs to skip *work*, not produce a result, so
the mechanism differs.

## Done when

- With the hook enabled and visibility inactive, validating the same document twice runs the
  validation rules only once. Assert on rule invocation, not on wall-clock timing.
- **With visibility active, two different users querying the same document get their own correct
  validation outcomes.** Reproduce the superuser/anonymous case from Context above; this is the
  regression guard for the whole feature and must fail against a naive document-keyed cache.
- A document whose validity depends on a variable value (a filter or order argument passed as a
  variable, per `VisibilityRule.enter_argument`) is not served a stale result from a different
  variable set.
- Replacing `undine_settings.SCHEMA` does not serve results validated against the old schema.
- The cache respects `maxsize` and evicts; sending many distinct documents does not grow memory
  without bound.
- The existing suite passes with the hook enabled by default in a test run, not only with it off.
  Given how often the suite swaps schemas, this is the strongest available check on step 2.
