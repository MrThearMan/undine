# Undine feature audit

Goal: find features other GraphQL libraries have that Undine does not, and features Undine has that others do not.

## Instructions

1. Pick one pending one framework from the list below.

2. Read the docs, end to end, if they exist. Check for agent friendly docs using /llms.txt and content-type: text/plain or text/markdown.

3. Clone the repository to `/temp`, if one exists. Read the directory structure and check out any features the docs do not mention or are lightly documented. Only check out the repo more thoroughly if docs are missing entirely.

4. Read the changelog, if it exists. This is usually at `https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/main/CHANGELOG.md`

From these you should be able to get a picture of what the project offers.

Web fetches can fail. Do not stop at the first failure.

Findings go to `.agents/plans/findings/<source>.md`. Write dense markdown. One line per feature.
Name the real API so a reader can look it up. Say explicitly when an area is not supported.
List the doc URLs used. Once you are done, mark the framework status as `done`.

## Frameworks

### strawberry-django

> Status: pending

> Stack: Python/Django

> Repo: https://github.com/strawberry-graphql/strawberry-django

> Docs: https://strawberry.rocks/docs/django

Closest direct competitor: type-hint code-first Django ORM types, filters, ordering, relay connections, optimizer, permissions.

### graphene-django

> Status: pending

> Stack: Python/Django

> Repo: https://github.com/graphql-python/graphene-django

> Docs: https://docs.graphene-python.org/projects/django/en/latest/

The incumbent. Model-derived types, django-filter integration, Relay nodes. Maintenance has slowed, so it defines the baseline Undine replaces.

### graphene-django-cud

> Status: pending

> Stack: Python/Django

> Repo: https://github.com/tOgg1/graphene-django-cud

> Docs: https://graphene-django-cud.readthedocs.io/en/latest/

Auto-generated create/update/delete mutations from models, including nested writes and permission hooks

### django-graphql-jwt

> Status: pending

> Stack: Python/Django

> Repo: https://github.com/flavors/django-graphql-jwt

> Docs: https://django-graphql-jwt.domake.io/

The de-facto auth layer for Django GraphQL.

### graphene-sqlalchemy

> Status: pending

> Stack: Python

> Repo: https://github.com/graphql-python/graphene-sqlalchemy

> Docs: https://docs.graphene-python.org/projects/sqlalchemy/en/latest/

Non-Django ORM integration. Useful for how it maps relationships, enums and batching.

### strawberry-sqlalchemy

> Status: pending

> Stack: Python

> Repo: https://github.com/strawberry-graphql/strawberry-sqlalchemy

Modern ORM mapper with dataloader-based relationship resolution.

### graphene-pydantic

> Status: pending

> Stack: Python

> Repo: https://github.com/graphql-python/graphene-pydantic

Schema derived from Pydantic models. Relevant to input validation design.

### python-graphjoiner / graphlayer

> Status: pending

> Stack: Python

> Repos: https://github.com/mwilliamson/python-graphjoiner and https://github.com/mwilliamson/python-graphlayer

Effectively dead but influential. Solves N+1 with SQL joins instead of dataloaders. Novel alternative to Undine's optimizer strategy.

### Saleor

> Status: pending

> Stack: Python/Django

> Repo: https://github.com/saleor/saleor

> Docs: https://docs.saleor.io/api-usage/overview

Not a library, but the largest production Django GraphQL schema. Good source of real-world requirements: permissions, webhooks, federation, error codes.

### Strawberry

> Status: pending

> Stack: Python

> Repo: https://github.com/strawberry-graphql/strawberry

> Docs: https://strawberry.rocks/docs

Type-annotation code-first, federation, subscriptions, extensions/permissions, codegen.

### Graphene

> Status: pending

> Stack: Python

> Repo: https://github.com/graphql-python/graphene

> Docs: https://docs.graphene-python.org/en/latest/

Historical reference for Python code-first API design.

### Ariadne

> Status: pending

> Stack: Python

> Repo: https://github.com/mirumee/ariadne

> Docs: https://ariadnegraphql.org/server/Docs/intro

Schema-first SDL approach. Comparison point for SDL-first vs code-first ergonomics.

### Tartiflette

> Status: pending

> Stack: Python

> Repo: https://github.com/tartiflette/tartiflette

> Docs: https://tartiflette.io/docs/api/engine

Async-native engine with a strong directive/hook system.

### graphql-core

> Status: pending

> Stack: Python

> Repo: https://github.com/graphql-python/graphql-core

> Docs: https://graphql-core-3.readthedocs.io/en/latest/

The execution engine Undine and every other Python lib sits on. Defines the validation-rule and extension surface.

### graphql-js

> Status: pending

> Stack: JS

> Repo: https://github.com/graphql/graphql-js

> Docs: https://graphql.org/graphql-js/

Reference implementation. Source of incremental delivery (`@defer`/`@stream`) semantics.

### Apollo Server

> Status: pending

> Stack: TS

> Repo: https://github.com/apollographql/apollo-server

> Docs: https://www.apollographql.com/docs/apollo-server

Plugin lifecycle, persisted queries, error handling conventions.

### GraphQL Yoga + Envelop

> Status: pending

> Stack: TS

> Repo: https://github.com/dotansimha/graphql-yoga

> Docs: https://the-guild.dev/graphql/yoga-server/docs

Best-in-class plugin architecture, SSE subscriptions, file uploads, persisted operations.

### Pothos

> Status: pending

> Stack: TS

> Repo: https://github.com/hayes/pothos

> Docs: https://pothos-graphql.dev/

The gold standard for code-first plugin design: Relay, dataloader, auth-scopes, complexity, Prisma plugins.

### Nexus

> Status: pending

> Stack: TS

> Repo: https://github.com/graphql-nexus/nexus

> Docs: https://nexusjs.org/

Historically important code-first builder with schema-file generation.

### TypeGraphQL

> Status: pending

> Stack: TS

> Repo: https://github.com/MichalLytek/type-graphql

> Docs: https://typegraphql.com/

Decorator/class-based schema definition, middleware, auth, validation.

### Mercurius

> Status: pending

> Stack: TS/Fastify

> Repo: https://github.com/mercurius-js/mercurius

> Docs: https://mercurius.dev/

JIT compilation, caching, federation. Notable for performance ideas.

### graphql-ruby

> Status: pending

> Stack: Ruby

> Repo: https://github.com/rmosolgo/graphql-ruby

> Docs: https://graphql-ruby.org/

Arguably the richest feature set anywhere: query analyzers, complexity/depth limits, visibility (schema hiding per-viewer), dataloader, subscriptions, ActiveRecord integration.

### Absinthe

> Status: pending

> Stack: Elixir

> Repo: https://github.com/absinthe-graphql/absinthe

> Docs: https://hexdocs.pm/absinthe/overview.html

Compile-time schema verification, middleware pipeline, best-in-class subscriptions.

### Hot Chocolate

> Status: pending

> Stack: C#/.NET

> Repo: https://github.com/ChilliCream/graphql-platform

> Docs: https://chillicream.com/docs/hotchocolate

Very feature-rich: auto filtering/sorting/projections from IQueryable, cost analysis, federation, persisted ops. Closest philosophical match to Undine's ORM-projection approach.

### graphql-java

> Status: pending

> Stack: Java

> Repo: https://github.com/graphql-java/graphql-java

> Docs: https://www.graphql-java.com/documentation/getting-started

Instrumentation API, dataloader integration, execution strategies.

### Netflix DGS

> Status: pending

> Stack: Java/Kotlin

> Repo: https://github.com/Netflix/dgs-framework

> Docs: https://netflix.github.io/dgs/

Codegen, federation, error handling at scale.

### Spring for GraphQL

> Status: pending

> Stack: Java

> Repo: https://github.com/spring-projects/spring-graphql

> Docs: https://docs.spring.io/spring-graphql/reference/

Notable for `@Argument`/projection binding and Querydsl/QueryByExample auto-repositories.

### graphql-kotlin

> Status: pending

> Stack: Kotlin

> Repo: https://github.com/ExpediaGroup/graphql-kotlin

> Docs: https://opensource.expediagroup.com/graphql-kotlin/docs/

Reflection-based code-first, federation, coroutine dataloaders.

### gqlgen

> Status: pending

> Stack: Go

> Repo: https://github.com/99designs/gqlgen

> Docs: https://gqlgen.com/

Schema-first with generated type-safe resolvers. Strong on complexity limits and field-level directives.

### async-graphql

> Status: pending

> Stack: Rust

> Repo: https://github.com/async-graphql/async-graphql

> Docs: https://async-graphql.github.io/async-graphql/en/index.html

Full spec coverage including `@defer`/`@stream`, apollo tracing, federation, guards.

### Juniper

> Status: pending

> Stack: Rust

> Repo: https://github.com/graphql-rust/juniper

> Docs: https://graphql-rust.github.io/juniper/

Older Rust implementation. Useful for macro-based schema definition contrasts.

### graphql-php

> Status: pending

> Stack: PHP

> Repo: https://github.com/webonyx/graphql-php

> Docs: https://webonyx.github.io/graphql-php/

Straight port of graphql-js with good query-complexity tooling.

### Lighthouse

> Status: pending

> Stack: PHP/Laravel.

> Repo: https://github.com/nuwave/lighthouse

> Docs: https://lighthouse-php.com/

SDL-directive-driven ORM integration (`@all`, `@paginate`, `@whereConditions`). A very different take on the same problem Undine solves.

### Sangria

> Status: pending

> Stack: Scala

> Repo: https://github.com/sangria-graphql/sangria

> Docs: https://sangria-graphql.github.io/

Pioneered query complexity analysis, middleware, and deferred value resolution.

### Caliban

> Status: pending

> Stack: Scala

> Repo: https://github.com/ghostdogpr/caliban

> Docs: https://ghostdogpr.github.io/caliban/

Purely functional, derivation-based schemas, wrappers, federation, Tapir interop.

### Hasura

> Status: pending

> Stack: Haskell/Postgres

> Repo: https://github.com/hasura/graphql-engine

> Docs: https://hasura.io/docs/

The reference for DB-to-GraphQL generation: filter/order/aggregate argument grammar, row-level permissions, subscriptions. Its filter DSL is the one most schemas get compared to.

### PostGraphile / Grafast

> Status: pending

> Stack: Node/Postgres

> Repo: https://github.com/graphile/crystal

> Docs: https://postgraphile.org/

Novel planning-based execution (Grafast) that batches at plan level rather than resolver level. Relevant to Undine's optimizer.

### pg_graphql

> Status: pending

> Stack: Rust Postgres extension

> Repo: https://github.com/supabase/pg_graphql

> Docs: https://supabase.github.io/pg_graphql/

GraphQL resolved entirely inside Postgres as a single SQL query.

### Dgraph

> Status: pending

> Stack: Go

> Repo: https://github.com/hypermodeinc/dgraph

> Docs: https://docs.dgraph.io/

Native GraphQL graph database with `@auth`, `@lambda`, `@custom` directives.

### Neo4j GraphQL Library

> Status: pending

> Stack: TS

> Repo: https://github.com/neo4j/graphql

> Docs: https://neo4j.com/docs/graphql/current/

Generates full CRUD plus nested filtering from SDL, compiling whole queries to single Cypher statements.

### Apollo Router / Federation

> Status: pending

> Stack: Rust

> Repo: https://github.com/apollographql/router

> Docs: https://www.apollographql.com/docs/graphos/routing.

The federation spec reference. Relevant if Undine wants subgraph support.

### WunderGraph Cosmo

> Status: pending

> Stack: Go/TS

> Repo: https://github.com/wundergraph/cosmo

> Docs: https://cosmo-docs.wundergraph.com/

Open-source federation platform with schema checks, analytics, and composition rules.

### GraphQL Mesh / Hive Gateway

> Status: pending

> Stack: TS

> Repo: https://github.com/graphql-hive/gateway

> Docs: https://the-guild.dev/graphql/mesh

Generates GraphQL from OpenAPI, gRPC, SOAP and databases. Broadest source-adapter feature set.

### API Platform

> Status: pending

> Stack: PHP/Symfony

> Repo: https://github.com/api-platform/core

> Docs: https://api-platform.com/docs/core/graphql/

Generates REST and GraphQL from the same Doctrine entities plus attribute metadata. Very close in spirit to Undine.

### AWS AppSync

> Status: pending

> Stack: Managed

> Docs: https://docs.aws.amazon.com/appsync/latest/devguide/what-is-appsync.html

Notable for its authorization-mode model and subscription filtering.

### Graphweaver

> Status: pending

> Stack: TS

> Repo: https://github.com/exogee-technology/graphweaver

> Docs: https://graphweaver.com/docs

Generates a unified GraphQL API from multiple data sources with an admin UI. Directly markets against Hasura.

### WPGraphQL

> Status: pending

> Stack: PHP/WordPress

> Repo: https://github.com/wp-graphql/wp-graphql

> Docs: https://www.wpgraphql.com/docs/introduction

Large-scale schema generated from an existing legacy data model, with a heavily used extension/registry API.
