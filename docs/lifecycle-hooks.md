# Lifecycle Hooks

In this section, we'll cover Undine's lifecycle hooks, which allow you to hook into the
execution of a GraphQL request.

## LifecycleHook

A GraphQL operation is executed in a series of steps. These steps are:

1. **Parsing** the GraphQL source document to a GraphQL AST.
2. **Validation** of the GraphQL AST against the GraphQL schema.
3. **Execution** of the GraphQL operation.

`LifecycleHooks` allow you to hook into the these steps to run custom logic
before or after each of these steps, or before and after the whole operation.
Here is a basic example of a `LifecycleHook`.

```python
-8<- "lifecycle_hooks/example_hook.py"
```

To implement a hook, you need to create a class that inherits from `LifecycleHook`
and implement the `run` method. `run` should be a generator function that yields
once, marking the point in which the hook should run. Anything before the yield
statement will be executed before the hooking point, and anything after the yield
statement will be executed after the hooking point.

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
- `result`: Execution result of the GraphQL operation.

## Examples

Here's some more complex examples of possible lifecycle hooks.

```python
-8<- "lifecycle_hooks/error_hook.py"
```

```python
-8<- "lifecycle_hooks/caching_hook.py"
```
