description: Documentation on hiding schema entities per request in Undine.

# Visibility

Visibility is used to hide parts of your schema from selected users. Visibility acts on two layers:

1. Introspection queries omit anything the current request can't see.
2. Operations that reference a hidden entity fail in the validation phase of the graphql request cycle
   with the same error shape that `graphql-core` produces for genuinely nonexistent types and fields.

Use visibility to control **availability**, not **access**, for example to gradually roll out
a new field or phase out an old one. _**Visibility is not a security boundary.**_ Treat it as a way to shape
what the schema looks like, not as a way to protect data.

## Basic usage

Hide a `Field` from unauthenticated users by decorating a method with the
`<field_name>.visible` decorator:

```python hl_lines="10 11 12"
-8<- "visibility/field_example.py"
```

Using the following query:

```graphql
query {
  tasks {
    name
  }
}
```

An unauthenticated request that queries the `name` field sees:

```json
{
  "errors": [
    {
      "message": "Cannot query field 'name' on type 'TaskType'."
    }
  ]
}
```

Hide an entire `QueryType` by overriding the `__is_visible__` classmethod:

```python hl_lines="10 11 12"
-8<- "visibility/query_type_example.py"
```

An unauthenticated request that queries the `tasks` entrypoint sees:

```json
{
  "errors": [
    {
      "message": "Cannot query field 'tasks' on type 'Query'."
    }
  ]
}
```

Notice that hiding the `TaskType` also hid the `tasks` entrypoint, even though the
entrypoint itself has no visibility hook. Visibility **cascades** through type
references. You only need to hide the root of what you want to remove and the rest
follows. The exact cascade rules for each entity are described in the
[Supported entities](#supported-entities) section below.

## Supported entities

Every Undine class and member exposes the same shape. The paragraph below each
snippet describes what happens when that entity is hidden.

### `RootType`

```python
-8<- "visibility/root_type_class_hook.py"
```
When hidden, the root type resolves to `null` in introspection and
every `Entrypoint` on that root becomes unreachable.

### `Entrypoint`

```python
-8<- "visibility/entrypoint_decorator_hook.py"
```

Hides the entrypoint from its `RootType`. No further cascade.

### `QueryType`

```python
-8<- "visibility/query_type_class_hook.py"
```

Hides every `Entrypoint`, `Field`, `InterfaceField`, and `FederationField` that
returns it, every `MutationType` that has it as its output type, and removes it
from any `UnionType`'s member list. Cascade is transitive, so a `MutationType`
hidden this way in turn hides any `Input` or `Entrypoint` that references it.
`FilterSet` and `OrderSet` connected to the `QueryType` are hidden if not
other entrypoint references them.

### `Field`

```python
-8<- "visibility/field_decorator_hook.py"
```

Hides the field from its `QueryType`. No further cascade.

### `MutationType`

```python
-8<- "visibility/mutation_type_class_hook.py"
```

Hides the `Entrypoint` that references it. Hiding a [related `MutationType`](mutations.md#related-mutations)
hides the `Input` that references it instead.

### `Input`

```python
-8<- "visibility/input_decorator_hook.py"
```

Hides the input from its `MutationType`. No further cascade.

### `FilterSet`

```python
-8<- "visibility/filter_set_class_hook.py"
```

Hides all its `Filter` members and removes the `filter` argument from every
entrypoint that uses it, including when the entrypoint is wrapped by pagination
such as `Connection` or `OffsetPagination`.

### `Filter`

```python
-8<- "visibility/filter_decorator_hook.py"
```

Hides the filter from its `FilterSet`. No further cascade.

### `OrderSet`

```python
-8<- "visibility/order_set_class_hook.py"
```

Hides all its `Order` members and removes the `orderBy` argument from every
entrypoint that uses it, including when the entrypoint is wrapped by pagination
such as `Connection` or `OffsetPagination`.

### `Order`

```python
-8<- "visibility/order_decorator_hook.py"
```

Hides the order from its `OrderSet`. No further cascade.

### `InterfaceType`

```python
-8<- "visibility/interface_type_class_hook.py"
```

Hides every `Field`, `Entrypoint`, `InterfaceField`, and `FederationField` that
returns it. Implementing `QueryType`s stay visible and queryable directly, but
they no longer list the hidden interface in their interfaces, and any fields
they gained purely by inheriting the interface disappear as well. Fields defined
directly on the `QueryType` that happen to share a name with an interface field
stay visible.

### `InterfaceField`

```python
-8<- "visibility/interface_field_decorator_hook.py"
```

Hides the field from its `InterfaceType`. On every implementing `QueryType`,
the corresponding inherited `Field` is also hidden.

### `UnionType`

```python
-8<- "visibility/union_type_class_hook.py"
```

Hides every `Field`, `Entrypoint`, `InterfaceField`, and `FederationField` that
returns it. Member `QueryType`s stay visible on their own. When some (but not
all) members are hidden, they disappear from the union's member list, and a
single-member union is still valid. If every member is hidden at runtime, the
union collapses to empty and is treated as hidden itself, cascading up to every
field or entrypoint that returns it.

### `Directive`

```python
-8<- "visibility/directive_class_hook.py"
```

Removes the directive from `__schema.directives` and from every **type system location**
where it was applied. Queries that apply it in an **executable location** fail validation.
`DirectiveArgument` members hide with it.

### `DirectiveArgument`

```python
-8<- "visibility/directive_argument_decorator_hook.py"
```

Hides the argument from its `Directive`. No further cascade.

### `CalculationArgument`

```python
-8<- "visibility/calculation_argument_decorator_hook.py"
```

Hides the argument from the `Field` whose ref is a `Calculation` using this
argument. No further cascade.

### `FederationType`

```python
-8<- "visibility/federation_type_class_hook.py"
```

Hides every `Entrypoint`, `Field`, `InterfaceField`, and `FederationField`
that returns it, and its own `FederationField` members hide with it.

### `FederationField`

```python
-8<- "visibility/federation_field_decorator_hook.py"
```

Hides the field from its `FederationType`. No further cascade.

## Federation

Visibility hooks apply to `FederationType` and `FederationField` (see above), and the
`_entities` resolver honors them just like any other field: entries that the current
request can't see are filtered out of the response.

The `_service { sdl }` payload is **not** filtered, however. It always returns the full
subgraph SDL because the router uses it to compose the supergraph, and composition needs
a stable, request-independent view of the schema. Per-request visibility on federation
types therefore doesn't propagate to clients through the supergraph — the router remains
the source of truth for what clients see.

For hiding a federation element from the supergraph entirely, use the
[`InaccessibleDirective`](federation.md#inaccessibledirective) instead. It marks the
element as `@inaccessible`, so the router excludes it from the composed schema while it
remains available within the subgraph.

## Caching

Visibility forces response caching to be per-user, and a user's introspection response can be
cached on its own. See [visibility caching](caching.md#visibility-caching) for more details.

## Caveats

- **Sync only.** `__is_visible__` and `.visible` callbacks must be synchronous.
  `graphql-core`'s introspection resolvers and validation rules are sync, and
  cannot suspend on `await`. If your visibility check needs data that is only
  reachable through an async fetch, resolve it using a [lifecycle hook](lifecycle-hooks.md)
  and store the result on the request object.
- **Fail-closed on exception.** If a hook raises, the entity is treated as hidden
- **"did you mean" suggestions.** Auto-disabled globally when any schema uses
  visibility so hidden entities never leak through error messages. This is equivalent to setting
  [`ALLOW_DID_YOU_MEAN_SUGGESTIONS`](settings.md#allow_did_you_mean_suggestions) to `False`.
