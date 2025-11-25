description: Documentation on lifecycle hooks in Undine.

# Lifecycle Hooks

In this section, we'll cover Undine's lifecycle hooks, which allow you to hook into the
execution of a GraphQL request.

## LifecycleHook

A GraphQL operation is executed in a series of steps. These steps are:

1. **Parsing** the GraphQL source document to a GraphQL AST.
2. **Validation** of the GraphQL AST against the GraphQL schema.
3. **Execution** of the GraphQL operation according to the GraphQL AST.

`LifecycleHooks` allow you to hook into the these steps to run custom logic
before or after them (or the whole operation). Here is a basic example of a `LifecycleHook`.

```python
-8<- "lifecycle_hooks/example_hook.py"
```

To implement a hook, you need to create a class that inherits from `LifecycleHook`
and implement the `run` method. `run` should be a generator function that yields once.
Anything before the yield statement will be executed before the hooking point,
and anything after the yield statement will be executed after the hooking point.

You can add this hook the different steps using settings:

```python
UNDINE = {
    "PARSE_HOOKS": ["path.to.ExampleHook"],
    "VALIDATION_HOOKS": ["path.to.ExampleHook"],
    "EXECUTION_HOOKS": ["path.to.ExampleHook"],
    "OPERATION_HOOKS": ["path.to.ExampleHook"],
}
```

When multiple hooks are registered for the same hooking point, they will be run
in the order they are registered. This means that the first hook registered will
have its "before" portion run first and its "after" portion run last. You can think
of them as a stack of context managers.

`LifecycleHooks` can have a different implementation in [async context](async.md)
using the `run_async` method. If no async implementation is provided,
the synchronous version will be used.

```python
-8<- "lifecycle_hooks/example_hook_async.py"
```

Async hooks are also used for [subscriptions](subscriptions.md).

## LifecycleHookContext

Each hook is passed a `LifecycleHookContext` object (`self.context`),
which contains information about the current state of the GraphQL request.
This includes:

- `source`: Source GraphQL document string.
- `document`: Parsed GraphQL document AST. Available after parsing is complete.
- `variables`: Variables passed to the GraphQL operation.
- `operation_name`: The name of the GraphQL operation.
- `extensions`: GraphQL operation extensions received from the client.
- `request`: Django request during which the GraphQL request is being executed.
- `result`: Execution result of the GraphQL operation. Adding a result to this will
  cause the operation to exit early with the result.

## Examples

Here's some more complex examples of possible lifecycle hooks.

```python
-8<- "lifecycle_hooks/error_hook.py"
```

```python
-8<- "lifecycle_hooks/caching_hook.py"
```
