# Schema registry / breaking-change CI support

## Context

Schema registries (GraphQL Hive, Apollo GraphOS) publish your SDL on merge and diff each PR's
schema against production to fail the build on breaking changes — a removed field, a narrowed
type — plus field-usage analytics so you know whether anyone still queries a field before you
remove it. Hot Chocolate, graphql-ruby and the JS ecosystem all have established stories here.

**This is mostly not Undine's job.** Publishing and diffing are the registry vendor's CLI
(`rover`, `hive`), run as CI steps. Undine's only responsibility is to emit correct SDL to a file,
and `python manage.py print_schema > schema.graphql` already does that
(`undine/management/commands/print_schema.py`, documented at `docs/schema.md:535-541`).

So this began as a documentation item. Investigating it turned up **one real bug** and one
smaller gap.

### Verified: `print_schema` emits the wrong SDL for federated subgraphs

For a schema built with `create_federation_schema`, the correct subgraph SDL is the one served by
`_service { sdl }` — that is what the router composes from, and what `rover subgraph publish`
expects. Undine computes it at schema-creation time and caches it in
`schema.extensions[FEDERATION_SDL_EXTENSIONS_KEY]` (`undine/federation/schema.py:93-100`),
applying three filters and `extend_schema=True`.

`manage.py print_schema` does none of that. It calls
`undine_settings.SDL_PRINTER.print_schema(undine_settings.SCHEMA)` with no filters, so the two
outputs differ. **Verified by experiment on this machine**, diffing the command's output against
the cached federation SDL for a `@key`-annotated `QueryType`:

```diff
--- manage.py print_schema
+++ _service sdl
-directive @key(
-  fields: FieldSet!
-  resolvable: Boolean! = true
-) repeatable on OBJECT | INTERFACE
-scalar FieldSet
-scalar _Any
-union _Entity = TaskType
 type TaskType @key(fields: "name") {
-type _Service {
-  sdl: String!
-}
 type Query {
-  _entities(representations: [_Any!]!): [_Entity]!
-  _service: _Service!
-schema @link(import: ["@key"], url: "https://specs.apollo.dev/federation/v2.15") {
-  query: Query
-}
+extend schema @link(import: ["@key"], url: "https://specs.apollo.dev/federation/v2.15")
```

So the command emits the federation *machinery* (`_Any`, `_Entity`, `_Service`, `_entities`,
`_service`), re-declares `@key` and `FieldSet` which the `@link` is supposed to provide, and uses
`schema` rather than `extend schema`. Publishing that to a registry is wrong, and the failure
mode is a confusing composition error rather than an obvious one.

The only current way to get correct subgraph SDL is to run the server and introspect
`_service { sdl }` — which is possible (`rover subgraph introspect`) but forces CI to boot a
server for something already computed at schema-creation time.

## The work

### 1. Make `print_schema` federation-aware

When the schema carries `FEDERATION_SDL_EXTENSIONS_KEY`, print that instead. Two shapes worth
weighing:

- **Automatic**: detect the extension and print federation SDL. Correct by default, but silently
  changes the output for existing federated users — which is the point, since that output is
  currently wrong.
- **A flag** (e.g. `--federation` / `--sdl-type`): explicit, but leaves the wrong output as the
  default and requires users to know they need it.

Recommendation: automatic, since there is no case where a federated subgraph wants the unfiltered
schema published, and mention it in the release notes. Confirm the extension key is only set by
`create_federation_schema` before relying on it as the discriminator.

**Corrected during implementation.** Implemented as automatic detection. `FEDERATION_SDL_EXTENSIONS_KEY`
is only ever written by `create_federation_schema` (`undine/federation/schema.py:100`) and only ever
read by `_service_resolver`, so it is a safe discriminator. The lookup lives in a module-level
`get_schema_sdl(schema)` in `undine/management/commands/print_schema.py`.

### 2. Consider a schema-check command

Breaking-change detection itself belongs to the registry vendor, but the cheapest useful thing
Undine can offer is a command that **fails if the schema cannot be built** — catching a broken
schema in CI before anything is published. `create_schema` already raises `UndineErrorGroup` on
validation failure (`undine/schema.py:92-97`), and `manage.py check undine` exists (see the
`justfile`'s `check` recipe). Verify whether `check undine` already covers this; if it does, this
step is documentation only, which would be the good outcome.

A `--check`-style flag on `print_schema` that diffs against a committed `schema.graphql` and exits
non-zero on drift is also plausible — it catches "someone changed the schema and forgot to
regenerate the file" without any vendor involvement. Treat as optional; the registry does the
harder version of this job.

**Corrected during implementation.** `manage.py check undine` does *not* cover this. It runs Django's
system checks for the `undine` app label and never touches `undine_settings.SCHEMA`, so a schema that
fails to build passes it. `print_schema` does build the schema, so it already fails non-zero on a
broken schema — that is the documented smoke test, and no new command was added.

The `--check` flag was added at the user's request, taking an optional path argument that defaults to
`schema.graphql` relative to the current directory (`--check` alone, or `--check path/to/schema.graphql`).
It compares stripped contents, so a trailing newline difference from shell redirection does not count
as drift, and raises `CommandError` when the file is missing or stale.

### 3. Documentation — the main deliverable

Extend the "Schema export" section of `docs/schema.md` (currently four lines) into a short guide
covering:

- Exporting SDL in CI, with a worked GitHub Actions snippet. This repo already has workflows under
  `.github/workflows/` to match style against.
- **Which SDL to publish for a federated subgraph**, and that `print_schema` handles this once
  step 1 lands. State it explicitly — it is the non-obvious part.
- Pointing at GraphQL Hive and Apollo GraphOS for publish/check, without recommending either.
- A note that visibility does **not** affect exported SDL: `print_schema` emits the full
  request-independent schema even when visibility is active (**verified by experiment**: a field
  hidden from all users is still present in the printed SDL). This is correct — a registry needs a
  stable view — and it matches the documented behaviour of `_service { sdl }` at
  `docs/visibility.md:246-252`. Worth stating so nobody assumes the export is filtered.
- Deprecation: `@deprecated` is standard GraphQL and already flows into the SDL, so usage-based
  removal workflows work through the registry with nothing extra from Undine. Confirm before
  claiming it.

**Confirmed during implementation.** A `Field(deprecation_reason=...)` prints as
`name: String! @deprecated(reason: "...")`, verified by experiment.

## Done when

- `manage.py print_schema` on a federation schema emits SDL byte-identical to what
  `_service { sdl }` returns. Assert equality against
  `schema.extensions[FEDERATION_SDL_EXTENSIONS_KEY]` directly — that is the definition of correct
  here.
- `manage.py print_schema` on a non-federation schema is unchanged.
- Exported SDL is unaffected by visibility, with a test pinning it, since it would be an easy
  thing to "fix" wrongly later.
- `docs/schema.md` explains CI export, the federated-subgraph case, and the visibility note.
- If a schema-drift check is added: it exits non-zero when the committed SDL is stale and zero
  when current.
