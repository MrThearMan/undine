# Keyset cursor pagination for `Connection`

## Context

`Connection` advertises cursor pagination but implements offset pagination underneath.
`offset_to_cursor` (`undine/relay.py:95`) encodes `connection:{typename}:{index}` and
`cursor_to_offset` decodes it straight back into a list index, which `PaginationHandler.validate`
(`undine/pagination.py:121-137`) assigns to `self.after` / `self.before` and then uses for
queryset slicing (`apply_pagination`, `undine/pagination.py:242`).

A cursor therefore names a *position*, not a *row*. When rows are inserted or deleted between
page reads, positions shift and the client sees duplicated or missing rows.

**Verified by experiment on this machine**, 4 tasks named b/c/d/e ordered by name, page size 2:

```
page 1                -> ['b', 'c']
inserted 'a' (sorts first)
page 2 (after=cursor) -> ['c', 'd']      # 'c' delivered twice
```

```
page 1                -> ['b', 'c']
deleted 'b' (already seen, sorts first)
page 2 (after=cursor) -> ['e']
all rows              -> ['c', 'd', 'e']
NEVER SEEN            -> ['d']           # exists, never delivered
```

The second case is silent data loss: a client paginating to the end never receives 'd', with
no error. `docs/pagination.md:82-83` explicitly promises the opposite — that cursor pagination
is "more resilient to changes in the paginated list, since the cursors themselves do not change
when items are added or removed." That sentence describes keyset behaviour.

**The user has decided:** fix `Connection` itself to use keyset cursors rather than adding a
second connection type. Cursors are opaque, so their contents may change. This warrants a minor
version bump (the user said so; do not make the bump yourself — see Boundaries in `AGENTS.md`).
Splitting the pagination handler so offset pagination and cursor pagination no longer share one
code path is explicitly acceptable.

**Also decided by the user:** ordering must default to `pk` when no ordering is given.

**Not a concern** (user's call, and correct): cursors becoming invalid when the `OrderSet`
changes mid-pagination. No pagination scheme can return correct next-items when the ordering
changed underneath. The only requirement is that this degrades into a clean
`GraphQLPaginationArgumentValidationError`, not a crash or silent nonsense — a cursor carrying a
different number of ordering values than the current order expects is the detectable case.

## The work

### 1. Split the handler

`PaginationHandler.validate` currently folds `offset` into `after` (`undine/pagination.py:173`:
`after = offset - 1`) and rejects using both. That unification only makes sense while cursors are
indices. Separate the offset path from the cursor path.

Note `Connection.__init__` already takes a `pagination_handler` argument
(`undine/relay.py:67`), so the seam for a different handler class exists — check whether it is
the right seam rather than assuming it.

### 2. Encode ordering values in the cursor

Resolve the queryset's actual `ORDER BY` into a list of descriptors, then encode one value per
descriptor. `strawberry_django/relay/cursor_connection.py` is good prior art and worth reading
before writing this; the parts that matter:

- Get resolved `OrderBy` expressions from the compiler rather than from `query.order_by` strings,
  so annotations and expression ordering are handled uniformly.
- Serialise with the output field's `value_to_string`, decode with `to_python`.
- Non-column expressions need annotating so their value is available on the row.
- Fields used for ordering must not be deferred — Undine's optimizer applies `only()`
  (`DISABLE_ONLY_FIELDS_OPTIMIZATION` exists as an escape hatch), so an ordering column the
  client didn't select can be missing. Strawberry explicitly un-defers these; verify what
  Undine's optimizer does here rather than assuming it is a problem or that it isn't.

### 3. Guarantee a strict total order

Keyset comparison is ambiguous when two rows tie on every ordering field. Append `pk` to the
ordering whenever it is not already present.

Undine currently applies ordering only when something asked for it — `optimizer.py:693` runs
`queryset.order_by(*self.order_by)` inside `if self.order_by:`. With no `OrderSet` and no
`__filter_queryset__` ordering, the queryset falls back to the model's `Meta.ordering` or to
none at all, which makes keyset pagination undefined. Per the user's decision, default to `pk`.

### 4. Row-value comparison for `after` / `before`

Build the "greater than this tuple" predicate. The nested form
`cmp | (eq & next_level_cmp)` handles multi-field ordering; each level's direction comes from
that field's `descending` flag, and NULL handling depends on `nulls_first`/`nulls_last`, which
Undine already exposes on `Order`. Do not assume every database sorts NULLs identically —
this is why the comparison is built from the resolved `OrderBy` flags rather than hardcoded.

### 5. Rework `hasNextPage` / `hasPreviousPage`

This is the part most likely to be underestimated. Today both come from index arithmetic
(`undine/resolvers/query.py:788-793`: `stop < total_count`, `start > 0`). With keyset there are
no indices, so the standard approach is to overfetch one row beyond the requested page and use
its presence as `hasNextPage`. Backward pagination (`last`/`before`) reverses the ordering and
then re-reverses the results.

`first` and `last` in the same request is the awkward case; look at how Strawberry does it with
a `RowNumber` window before inventing something.

There are three `to_connection` implementations (`undine/resolvers/query.py:774`, `:870`,
`:1366`, `:1872` — QueryType, prefetched, interface, union). They all build cursors from
`offset_to_cursor(typename, start + index)`. All need to build cursors from row values instead.

### 6. Nested (prefetch) connections

**Do not treat this as "keyset vs. window functions" — they are orthogonal.** An earlier draft
of this plan framed it as a choice; that was wrong. In Strawberry, nested connections get keyset
cursors *and* window functions, because each solves a different problem:

- The **cursor** is a `WHERE` clause. `build_tuple_compare` produces a `Q` object applied with
  `qs.filter(...)`, and filters work fine on prefetch querysets. This is applied identically for
  top-level and nested.
- The **limit** is what differs. Top-level slices (`qs[slice_]` → SQL `LIMIT`). Nested cannot:
  a prefetch runs one query with `WHERE parent_id IN (...)`, so a `LIMIT` would cap total rows
  across all parents rather than per parent. Hence `ROW_NUMBER() OVER (PARTITION BY parent)`.

See `apply_cursor_pagination` in `strawberry_django/relay/cursor_connection.py`, which applies
the cursor filters first and then branches only on the limiting strategy:

```python
if related_field_id is not None:
    # we always apply window pagination for nested connections,
    # because we want its total count annotation
    qs = apply_window_pagination(qs, related_field_id=related_field_id, offset=offset, limit=...)
elif slice_ is not None:
    qs = qs[slice_]
```

`apply_window_pagination` lives in `strawberry_django/pagination.py`.

So for Undine: keep `_add_partition_index`'s `RowNumber` for the per-partition limit, and add the
keyset `WHERE` alongside it. `_add_start_index` / `_filter_by_start_index` currently derive
`self.start` from the cursor offset; with keyset the cursor is expressed in the `WHERE` clause,
so the row-number filter degenerates to "take the first N of what's left" — start becomes 0 for
cursor pagination, and `_add_stop_index` carries `first` rather than an absolute index.

Two concrete gotchas here:

**Total count must be captured before the cursor filter.** `_add_total_count` builds
`SubqueryCount(queryset.filter(**{related_name: OuterRef(related_name)}))` (`undine/pagination.py:355`),
closing over whatever the queryset is at that moment. `apply_prefetch_pagination` currently calls
it before the start/stop filters for exactly this reason. If the keyset `WHERE` is applied first,
`totalCount` silently becomes "rows after the cursor" instead of the true total. Add a test that
pins `totalCount` on a nested connection while paginating past the first page.

**`last` on nested connections.** Today it uses `Greatest(total_count - last, start)`
(`undine/pagination.py:272`), i.e. it counts from a known total. Keyset has no such index;
Strawberry instead reverses the ordering and adds a second reversed `RowNumber`
(`_strawberry_row_number_reversed`, the `reverse=True` branch of `apply_window_pagination`).

**Semantic change worth deciding on deliberately:** a nested connection's `after` cursor is shared
across every partition. Under offset semantics it means "skip N in each parent's list"; under
keyset it means "only rows ordered after this value, in each parent's list". Different parents
will therefore begin at different positions within their own lists. This is arguably more coherent
than the offset behaviour, but it *is* a behaviour change beyond the stability fix, and it should
be mentioned in the docs rather than discovered.

Also note `_add_partition_index` falls back to
`queryset.query.order_by or model._meta.ordering or None` (`undine/pagination.py:341`) — an
unordered `RowNumber` window is non-deterministic, which is a second reason the `pk` default from
step 3 matters.

### 7. Union and interface connections

`UnionType` connections paginate a combined `.values("__typename", "pk")` queryset
(`undine/resolvers/query.py:1211-1228`). Ordering there comes from `order_union` across
several models. Extracting per-model ordering values into a single cursor is materially harder
than the single-model case. Treat this as its own decision: it may be reasonable for unions to
keep index-based cursors initially, as long as that is documented. Flag it rather than forcing it.

### 8. Documentation

Rewrite the cursor section of `docs/pagination.md` (the claim at lines 82-83). Once keyset is in
place the resilience claim becomes true for the cases it covers — state which those are, and
state that cursors are tied to the ordering in effect when they were issued.

## Done when

- A test reproduces both scenarios above — insert-before-cursor and delete-before-cursor — and
  shows every row delivered exactly once across pages. Written against current code, that test
  must fail; confirm it does before fixing, or it isn't testing anything.
- Ties on the ordering field paginate correctly (rows with identical sort values are neither
  skipped nor repeated), which is what the `pk` tiebreaker is for.
- Descending order, and ordering with NULLs on both `nulls_first` and `nulls_last`, paginate
  correctly.
- Backward pagination (`last` / `before`) returns rows in the same order as forward pagination.
- A cursor issued under one ordering and replayed under a different one produces a clean
  `GraphQLPaginationArgumentValidationError`, not a crash or silently wrong rows.
- `hasNextPage` / `hasPreviousPage` are correct at both ends of a list, including the empty
  result and single-page cases.
- Offset pagination behaviour is unchanged — its existing tests pass untouched.
- Nested (prefetch) connections paginate correctly with keyset cursors, and a nested
  `totalCount` stays the true partition total while paginating past the first page — not the
  count of rows remaining after the cursor.
- Existing pagination tests still pass, except those asserting on literal cursor *contents*,
  which should be updated rather than deleted. Affected files:
  `tests/test_pagination.py`, `tests/test_relay.py`, `tests/test_resolvers/test_relay_resolvers.py`,
  `tests/test_optimizer/test_queries/test_relay.py`.
- `just coverage` (or the targeted equivalent) is green, and no new mypy errors.
