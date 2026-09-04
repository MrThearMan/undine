description: Documentation on caching in Undine.

# Caching

Undine can cache work at three levels.

1. Response caching stores the result of an operation.
2. Visibility caching stores which parts of the schema a user can see.
3. Document caching stores the parsed and validated form of a GraphQL document.

Every level is disabled by default and is enabled on its own.

## Response caching

Responses from `Entrypoints` connected to the `Query` `RootType` can be cached by giving
the `cache_time` argument to the `Entrypoint`.

```python
-8<- "caching/entrypoint_cache.py"
```

This caches the response for the given number of seconds in the cache set by the
[`REQUEST_CACHE_ALIAS`](settings.md#request_cache_alias) setting.

Note that response caching cannot be used for requests that use [incremental delivery](incremental.md).
Also, only responses without errors are cached, since an error can come from a transient issue such as
a database connection being down.

`Entrypoints` are not cached unless you set the `cache_time` argument.
To cache every `Entrypoint` of the `Query` root type by default, use the
[`ENTRYPOINT_DEFAULT_CACHE_TIME`](settings.md#entrypoint_default_cache_time) setting.

```python
UNDINE = {
    "ENTRYPOINT_DEFAULT_CACHE_TIME": 30,
}
```

An `Entrypoint` that sets its own `cache_time` keeps it. Set `cache_time=0` on an `Entrypoint`
to leave it out of the default.

### Per-user caching

Use the `cache_per_user` argument to cache the response for each user separately.

```python
-8<- "caching/entrypoint_cache_per_user.py"
```

Responses for authenticated and anonymous users are cached separately even without
`cache_per_user`. A schema commonly returns different results for unauthenticated users.

### Rules on other entities

You can also set caching rules on individual [`Fields`](queries.md#caching_1),
[`QueryTypes`](queries.md#caching), [`InterfaceTypes`](interfaces.md#caching),
[`InterfaceFields`](interfaces.md#caching_1) and [`UnionTypes`](unions.md#caching).
An entity that sets no rules of its own is cached using the `Entrypoint's` rules. When an
operation includes several entities that set rules, Undine uses the most restrictive rules
it finds.

For example, a `Field` can set a stricter rule than its `Entrypoint`.

```python
-8<- "caching/field_cache.py"
```

Queried like this:

```graphql
query {
  task(id: 1) {
    name
  }
}
```

The `name` `Field` has a cache time of 10 seconds and the `Entrypoint` has 60 seconds, so the
operation is cached for 10 seconds. The `name` `Field` also sets per-user caching, so the
operation is cached for each user separately.

If a `Field's` reference sets a caching rule, but the `Field` itself does not, the reference's
rule is used. This applies to `Fields` only, not to `Entrypoints`.

```python
-8<- "caching/query_type_cache.py"
```

Queried like this:

```graphql
query {
  task(id: 1) {
    project {
      name
    }
  }
}
```

The `project` `Field` uses `ProjectType`, which is cached for 10 seconds, so the operation is
cached for 10 seconds instead of the `Entrypoint's` 60 seconds.

### Cache keys

A response is cached based on the GraphQL source document, the variables, the operation name,
the GraphQL operation extensions, and the user's authentication status. Per-user caching adds
the user's primary key.

If your responses vary on something else, such as the accepted language, add that data to the
cache key with the [`REQUEST_CACHE_EXTRA_CONTEXT`](settings.md#request_cache_extra_context)
setting.

```python
-8<- "caching/cache_extra_context.py"
```

### Read and write predicates

Use the [`REQUEST_CACHE_READ_PREDICATE`](settings.md#request_cache_read_predicate) and
[`REQUEST_CACHE_WRITE_PREDICATE`](settings.md#request_cache_write_predicate) settings to control
whether a given request reads from or writes to the cache.

```python
-8<- "caching/cache_predicates.py"
```

### Client caching

Response caching also sends `Cache-Control` and `Age` headers to the client, so that browser
caches and CDN caches can store the response.

## Visibility caching

In a schema that uses [visibility](visibility.md), [response caching](#response-caching) is forced to be per-user when
the operation reaches an entity that uses visibility. This makes sure that hidden data cannot leak
between users through a cached response.

You can also cache a user's introspection response by setting
[`VISIBILITY_CACHE_TIMEOUT`](settings.md#visibility_cache_timeout). Cache keys are derived from the
user's primary key plus any extra context given by
[`VISIBILITY_CACHE_EXTRA_CONTEXT`](settings.md#visibility_cache_extra_context).

## Document caching

Parsing a document to an AST and validating that AST are pure functions of the document and the
schema. Undine has two built-in [lifecycle hooks](lifecycle-hooks.md) that reuse those results
between requests.

- `undine.hooks.ParseCacheHook` caches the parsed AST. Enable it by setting
  [`PARSE_CACHE_MAX_SIZE`](settings.md#parse_cache_max_size) above zero.
- `undine.hooks.ValidationCacheHook` caches the validation outcome. Enable it by setting
  [`VALIDATION_CACHE_MAX_SIZE`](settings.md#validation_cache_max_size) above zero.

Both keep their results in the memory of the process, so each worker fills its own cache. A shared cache would send the document over the network on
each request, which costs more than the parsing and the validation that it saves.

The setting is also the size limit. When a cache is full, it discards the document that was used
least recently. Keep the limit at a size that the process can hold, because a client can send an
unlimited number of different documents. With
[`PERSISTED_DOCUMENTS_ONLY`](settings.md#persisted_documents_only), the set of documents that a
client can send is known in advance, which makes the limit easier to choose.

Documents that fail to parse or fail to validate are not cached.

The validation cache is skipped for schemas that use [visibility](visibility.md). Visibility is
resolved against the user that makes the request and against the values of the variables that they
send, so the outcome is not a function of the document and the schema alone. Custom rules in
[`ADDITIONAL_VALIDATION_RULES`](settings.md#additional_validation_rules) must also depend on the
document and the schema only, or the validation cache must stay disabled.
