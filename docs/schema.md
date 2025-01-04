# Schema

In the [getting started](getting-started.md) section, we started a basic GraphQL server using an
example schema. In this section, we'll learn how to create a schema for your own data.

## RootOperationType

At the top level of a GraphQL schema there are objects called `RootOperationTypes`, which 
contain all the possible `Entrypoints` for the schema. All GraphQL schemas must support
a `RootOperationType` for querying data from the schema, usually called `Query`.
A schema may also support a `RootOperationType` for mutating data, usually called `Mutation`,
or a `RootOperationType` for fetching real-time data, usually called `Subscription`
(not yet supported by Undine).

To create the required RootOperationType for querying, we'll create a class named `Query`
that subclasses `RootOperationType`. All `RootOperationType` classes must have at least
one `Entrypoint` in their class body, which we'll add in [Entrypoints](#entrypoints) section.

```python
from undine import RootOperationType

class Query(RootOperationType): ...
```

By default, the name of the generated `ObjectType` is the same as the name of the `RootOperationType` class.
If you want to change the name, you can do so by setting the `typename` argument:

```python
from undine import RootOperationType

class Query(RootOperationType, typename="Query"): ...
```

## Entrypoints

Undine `Entrypoints` are fields in a `RootOperationType` of the GraphQL schema.
You can think them as "API endpoints inside the GraphQL schema".

### Function Entrypoints

Function `Entrypoints` are created by decorating a method with the `Entrypoint` class.
Let's explore this by creating a simple query `Entrypoint` that returns a greeting.

```python
from undine import Entrypoint, RootOperationType

class Query(RootOperationType):
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
```

This `Entrypoint's` output type will be determined by the return type of the method.
Not including a return type will result in an error.

When using function `Entrypoints`, there is no real difference between creating a query
`Entrypoint` or a mutation `Entrypoint`. The only difference is that mutations are added to
a class named `Mutation` instead of `Query`.

```python
from undine import Entrypoint, RootOperationType


class Mutation(RootOperationType):
   @Entrypoint
   def testing(self) -> str:
      # Mutation here...
      return "Success!"
```

### Signature

An function `Entrypoint's` method has one of the following signatures:

```python
from typing import Any
from undine import Entrypoint, GQLInfo, RootOperationType
from undine.typing import Root

def g_ext(root: Root, **kwargs: Any) -> Any: ...

class Query(RootOperationType):
    @Entrypoint
    def a(self: Root, **kwargs: Any) -> Any: ...
    
    @Entrypoint
    def b(self: Root, info: GQLInfo, **kwargs: Any) -> Any: ...
    
    @Entrypoint
    @staticmethod
    def c(root: Root, **kwargs: Any) -> Any: ...
    
    @Entrypoint
    @staticmethod
    def d(root: Root, info: GQLInfo, **kwargs: Any) -> Any: ...
    
    @Entrypoint
    @staticmethod
    def e(info: GQLInfo, **kwargs: Any) -> Any: ...
    
    @Entrypoint
    @staticmethod
    def f(**kwargs: Any) -> Any: ...

    g = Entrypoint(g_ext)
```

Notice with signature `a` and `b` that `self` is not the instance variable of the method,
but the `Root` object of the GraphQL execution context. This value can be configured
using the `ROOT_VALUE` setting, and is `None` by default.

We actually never initialize the `Query` or `Mutation` classes, but simply treat it as a convenient
way to organize the `Entrypoints`. This means that the method is treated just like a static method.
If this is too confusing, you can use the other signatures with explicit `@staticmethod` decorators,
or take the function from outside the class body like with option `g`.

In any case, the `root` and `info` arguments can both be left out if not needed,
as the `Entrypoint` will create an intermediary layer between the GraphQL resolver and the method.

`root` is always the first argument of the method if present (typing not required) and `info`
always has the `GQLInfo` type annotation (typing required).

### Arguments

We can add arguments to the `Entrypoint` by adding them to the method signature.
Typing these arguments is also required to determine their input type.

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
```

This will add a non-null `name` string argument to the `Entrypoint`.
Note that non-null arguments are required by GraphQL, so if we want to make an argument
optional, we can do so by making it nullable, or adding a default value.

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self, name: str | None = None) -> str:
        return f"Hello, {name or 'World'}!"
```

### Descriptions

We can also a description to the `Entrypoint` by adding a docstring to the method.
If the method has arguments, we can add descriptions to those arguments by using
[reStructuredText docstrings format](https://peps.python.org/pep-0287/).

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self, name: str) -> str:
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

## Crating a Schema

To create a Schema in Undine, we'll use the `create_schema` function.
Every GraphQL schema needs to have at least the `Query` `RootOperationType`,
so let's use the `Query` class we created in the [`Entrypoints`](#entrypoints) section.

```python
from undine import create_schema, Entrypoint, RootOperationType


class Query(RootOperationType):
   @Entrypoint
   def testing(self) -> str:
      return "Hello, World!"


schema = create_schema(query=Query)
```

Now we'll need to point Undine to use this Schema.
Add the following configuration in your `settings.py` file:

```python
UNDINE = {
    "SCHEMA": "<path to schema instance>",
}
```

Here `"<path to schema instance>"` should be a dotted path to the `schema` variable
we created earlier. For example, if we created the schema in a file `example/schema.py`
to a variable `schema`, we would use `"example.schema.schema"`.
