description: Documentation on lifecycle hooks in Undine.

# Lifecycle Hooks

In this section, we'll cover Undine's lifecycle hooks, which allow you to hook into the
execution of a GraphQL request.

## LifecycleHook

A GraphQL **operation** is executed in a series of steps. These steps are:

1. **Parsing** the GraphQL source document to a GraphQL AST.
2. **Validation** of the GraphQL AST against the GraphQL schema.
3. **Execution** of the GraphQL operation according to the GraphQL AST.

`LifecycleHooks` allow you to hook into the these steps.
To implement a hook, you need to create a class that inherits from `LifecycleHook`
and implement the the appropriate methods based on the steps you want to hook into.
The points you can hook into are:

`on_operation` / `on_operation_async`: Encompasses the entire GraphQL **operation**.

```python
-8<- "lifecycle_hooks/example_hook_on_operation.py"
```

`on_parse` / `on_parse_async`: Encompasses the **parsing** step.

```python
-8<- "lifecycle_hooks/example_hook_on_parse.py"
```

`on_validation` / `on_validation_async`: Encompasses the **validation** step.

```python
-8<- "lifecycle_hooks/example_hook_on_validation.py"
```

`on_execution` / `on_execution_async`: Encompasses the **execution** step.

```python
-8<- "lifecycle_hooks/example_hook_on_execution.py"
```

`resolve`: Encompasses each field resolver (see `graphql-core` [custom middleware]{:target="_blank"}).

[custom middleware]: https://graphql-core-3.readthedocs.io/en/latest/diffs.html#custom-middleware

```python
-8<- "lifecycle_hooks/example_hook_resolve.py"
```

## Registering hooks

Created hooks need to be registered using the
[`ADDITIONAL_LIFECYCLE_HOOKS`](settings.md#additional_lifecycle_hooks) setting.

```python
UNDINE = {
    "ADDITIONAL_LIFECYCLE_HOOKS": [
        "myproj.hooks.TimingHook",
    ],
}
```

## Priority

When multiple hooks run logic on the same step, they run in the order set by their **priority**.
A hook with a lower priority runs its "before" portion first and its "after" portion last,
so it wraps the hooks with a higher priority. You can think of them as a stack of context managers.

A hook has a priority of `1000` unless it sets one, which places it inside all of the built-in
hooks. To run a hook somewhere else, set the `priority` class attribute.

```python
-8<- "lifecycle_hooks/hook_priority.py"
```

These are the priorities of the built-in hooks, available as `undine.hooks.HookPriority`.

- `TRACING` (`100`): The [OpenTelemetry](integrations.md#opentelemetry),
  [Datadog](integrations.md#datadog), [Sentry](integrations.md#sentry) and
  [federated tracing](federation.md#federated-tracing) hooks.
- `PARSE_CACHE` (`200`): `undine.hooks.ParseCacheHook`.
- `VALIDATION_CACHE` (`300`): `undine.hooks.ValidationCacheHook`.
- `RESPONSE_CACHE` (`400`): `undine.hooks.RequestCacheHook`.
- `VISIBILITY_CACHE` (`500`): `undine.hooks.VisibilityCacheHook`.
- `ATOMIC_MUTATION` (`600`): `undine.hooks.AtomicMutationHook`.
- `PERSISTED_QUERIES` (`700`): `undine.hooks.AutomaticPersistedQueriesHook`.
- `DEFAULT` (`1000`): Every other hook.

## LifecycleHookContext

Each hook is passed a `LifecycleHookContext` object (`self.context`),
which contains information about the current state of the GraphQL request.
This includes:

- `source`: Source GraphQL document string.
- `document`: Parsed GraphQL AST. Available after parsing is complete.
- `validation_errors`: Errors found when validating the GraphQL document.
  Available after validation is complete. Adding errors to this in a `LifecycleHook`
  will skip validation and exit the operation early with those errors.
- `variables`: Variables passed to the GraphQL operation.
- `operation_name`: The name of the GraphQL operation to run from the document.
  Can be empty if there is only one operation in the document.
- `extensions`: GraphQL operation extensions received from the client.
- `request`: Django request during which the GraphQL operation is being executed.
- `result`: Execution result of the GraphQL operation. Adding a result to this
  in a `LifecycleHook` will cause the operation to exit early with the result.
- `lifecycle_hooks`: `LifecycleHooks` in use for this operation.

## Examples

Here's some more complex examples of possible lifecycle hooks.

```python
-8<- "lifecycle_hooks/caching_hook.py"
```

```python
-8<- "lifecycle_hooks/timing_hook.py"
```
