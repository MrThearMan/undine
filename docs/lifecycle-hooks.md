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

Created hooks need to be registered using the [`LIFECYCLE_HOOKS`](settings.md#lifecycle_hooks) setting.
When there are multiple hooks that run logic on the same step, they will be run
in the order they are added in the `LIFECYCLE_HOOKS` setting list.
Specifically, the first hook registered will have its "before" portion run first
and its "after" portion run last. You can think of them as a stack of context managers.

## LifecycleHookContext

Each hook is passed a `LifecycleHookContext` object (`self.context`),
which contains information about the current state of the GraphQL request.
This includes:

- `source`: Source GraphQL document string.
- `document`: Parsed GraphQL AST. Available after parsing is complete.
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
