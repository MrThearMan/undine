# Apollo Federation compatibility subgraph

This directory contains a runnable Django project that implements Apollo's `products` subgraph for the
[Apollo Federation subgraph compatibility harness][compat repo]{:target="_blank"} using Undine.

Its two jobs are:

1. Serve as the Docker deliverable for landing Undine on Apollo's
   [supported subgraphs matrix][matrix]{:target="_blank"} — the harness composes
   this `products` service with Apollo's own `users` and `inventory` subgraphs
   and a router, then runs the query set from [COMPATIBILITY.md][compat md]{:target="_blank"}
   against the composed supergraph.
2. Give Undine maintainers a local certification target — `just up` boots the
   subgraph on `localhost:4001`, `just compliance` runs the harness, and
   `just export` regenerates `schema.graphql` from the Undine schema.

## Layout

- `config/` — Django project (settings, URL conf, WSGI entry point).
- `products/` — Django app: models, Undine schema, seed migration, and the `export` management command.
- `Dockerfile` + `docker-compose.yaml` — matrix-shaped container packaging. Builds from the repo
  root so the container installs Undine from the local checkout.
- `justfile` — `just up` / `just down` / `just clean` / `just export` / `just compliance`.
- `schema.graphql` — Undine-exported SDL, checked in. A pytest smoke test
  (`tests/test_federation/test_compatibility_schema.py`) fails if the file drifts from what
  `render_schema()` produces; re-run `just export` and commit the update.
- `metadata.json` — matrix submission metadata (name, language, links).

## Local workflows

```shell
just up          # docker compose up --build, port 4001
just down        # docker compose down --remove-orphans --volumes
just export      # regenerate schema.graphql via `manage.py export`
just compliance  # run Apollo's compliance harness (see below)
```

Once the container is up, GraphQL is served at the root (not `/graphql/`) so Apollo's harness
can reach it:

```shell
curl -sS -H 'content-type: application/json' \
  --data '{"query":"{ product(id: \"apollo-federation\") { id sku package } }"}' \
  http://localhost:4001/
```

## Running Apollo's compliance runner

`just compliance` runs Apollo's `@apollo/federation-subgraph-compatibility` harness against a
running container. It mirrors the CI workflow at
[`.github/workflows/test-subgraph.yaml`][ci workflow]{:target="_blank"}: it composes with
Apollo's canonical `products.graphql` (federation v2.3), so the harness-bundled rover version
handles composition without needing `APOLLO_ROVER_DEV_COMPOSITION_VERSION`.

Boot the subgraph first, then run:

```shell
just up
just compliance
```

The runner boots Apollo's `users` / `inventory` / router alongside our `products` service,
composes the supergraph, and reports pass/fail. That report is what the Phase 7 upstream PR
attaches when Undine is submitted to the matrix. See [SUBGRAPH_GUIDE.md][guide]{:target="_blank"}
for the full submission workflow.

[compat repo]: https://github.com/apollographql/apollo-federation-subgraph-compatibility
[compat md]: https://github.com/apollographql/apollo-federation-subgraph-compatibility/blob/main/COMPATIBILITY.md
[ci workflow]: https://github.com/apollographql/apollo-federation-subgraph-compatibility/blob/main/.github/workflows/test-subgraph.yaml
[guide]: https://github.com/apollographql/apollo-federation-subgraph-compatibility/blob/main/SUBGRAPH_GUIDE.md
[matrix]: https://www.apollographql.com/docs/federation/building-supergraphs/supported-subgraphs
