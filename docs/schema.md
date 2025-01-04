# Schema

In the [getting started](getting-started.md) section, we started a basic GraphQL server using an
example schema. In this section, we'll learn how to create a schema for your own data.

## RootOperationType

A GraphQL schema defines a `RootOperationType` for each kind of operation that it supports:

1. `Query`: For querying data (required).
2. `Mutation`: For mutating data (optional).
3. `Subscription`: For fetching real-time data (optional, not yet supported by Undine).

To create the required `RootOperationType` for querying, we'll create a class named `Query`
that subclasses `RootOperationType`.

```python
from undine import RootOperationType

class Query(RootOperationType): ...
```

This isn't a valid `RootOperationType` yet since all `RootOperationTypes` need at least
one `Entrypoint` in their class body.

## Entrypoints

In Undine, `Entrypoints` are simply the fields in a `RootOperationType`.
You can think them as the _"API endpoints inside the GraphQL schema"_.
`Entrypoints` can be created by using one of three types of objects as a "reference":
a `FunctionType`, a `QueryType`, or a `MutationType`.

> A "reference" is simply the first argument given to the `Entrypoint` class,
> from which the GraphQL field for that `Entrypoint` will be created.

### FunctionType Entrypoints

An `Entrypoint` for a `FunctionType` is created by using any function-like object as the
reference of an `Entrypoint` class. This can be done either by decorating a method in the
`RootOperationType` class with the `Entrypoint` class, or by using a function as the first argument
of the `Entrypoint` class.

As an example, let's create a simple query `Entrypoint` that returns a greeting
(although the process would be the same for a mutation `Entrypoint`).

```python
from typing import Any
from undine import Entrypoint, RootOperationType, GQLInfo

class Query(RootOperationType):
    @Entrypoint
    def testing(root: None, info: GQLInfo, **kwargs: Any) -> str:
        return "Hello, World!"
```

Note that the first argument of the method is not `self` but `root`. This is because
when used as the `FunctionType` for an `Entrypoint`, the decorated method is treated as a
static method, where the first argument is the `root` argument of a GraphQL field resolver.
We could have used `self` as well, but chose to rename it to keep things more clear.
The value of the `root` argument is `None` by default, but can be configured using the `ROOT_VALUE` setting.

The output type for this `Entrypoint` will be determined by the return type of the method.
Not including a return type will result in an error.

The `root` and `info` arguments, as well as `**kwargs`, can all be left out if not needed,
as the `Entrypoint` will create an intermediary layer between the GraphQL resolver signature and the method.
When included, `root` is always the first argument of the method (typing not required) and `info`
always has the `GQLInfo` type annotation (typing required).

#### Arguments

We can add arguments to the `Entrypoint` by adding them to the function signature.
Typing these arguments is also required to determine their input type.

```python
from undine import Entrypoint, RootOperationType

class Query(RootOperationType):
    @Entrypoint
    def testing(root, name: str) -> str:
        return f"Hello, {name}!"
```

This will add a non-null `name` string argument to the `Entrypoint`.
Note that non-null arguments are required by GraphQL, so if we want to make an argument
optional, we can do so by making it nullable, or adding a default value.

```python
from undine import Entrypoint, RootOperationType

class Query(RootOperationType):
    @Entrypoint
    def testing(root, name: str | None = None) -> str:
        return f"Hello, {name or 'World'}!"
```

#### Descriptions

We can also a description to the `Entrypoint` by adding a docstring to the method.
If the method has arguments, we can add descriptions to those arguments by using
[reStructuredText docstrings format](https://peps.python.org/pep-0287/).

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(root, name: str) -> str:
        """
        Return a greeting.

        :param name: The name to greet.
        """
        return f"Hello, {name}!"
```

> Other types of docstrings can be used by providing a parser to the `DOCSTRING_PARSER` setting
> that conforms to the `DocstringParserProtocol` from `undine.typing`.

### QueryType and MutationType Entrypoints

`Entrypoint` can also be used with `QueryType` and `MutationType` classes
to create `Entrypoints` for querying and mutating Django model data.
We'll cover these more thoroughly in the [Queries](queries.md) and
[Mutations](mutations.md) sections, but here is a quick example:

```python
from undine import Entrypoint
from example_project.app.types import TaskType
from example_project.app.mutations import TaskCreateMutationType

class Query:
    task = Entrypoint(TaskType)

class Mutation:
    create_task = Entrypoint(TaskCreateMutationType)
```

## Crating the Schema

Now that we have our `RootOperationType` for querying, we'll create
the GraphQL schema using the `create_schema` function.

```python
from undine import create_schema, Entrypoint, RootOperationType

class Query(RootOperationType):
   @Entrypoint
   def testing(root) -> str:
      return "Hello, World!"

schema = create_schema(query=Query)
```

Next, we'll need to make Undine to use this Schema.
Add the following configuration in your `settings.py` file:

```python
UNDINE = {
    "SCHEMA": "<path to schema instance>",
}
```

Here `"<path to schema instance>"` should be a dotted path to the `schema` _variable_
we created earlier. For example, if we created the schema in a file `example/schema.py`
to a variable `schema`, we would use `"example.schema.schema"`.
