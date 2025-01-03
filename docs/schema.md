# Schema

In the [getting started](getting-started.md) section, we started a basic GraphQL server using an
example schema. In this section, we'll learn how to create a schema for your own data.

## Entrypoints

Undine `Entrypoints` are fields in the root operation types (`Query` and `Mutation`)
of the GraphQL schema. You can think them as "API endpoints inside the GraphQL schema".

Entrypoints are divided into three categories: queries, mutations and subscriptions.
Queries are used for fetching data from the database, while mutations are used for
modifying the database. To create a query entrypoint, we'll need to create a class
named `Query` and add the entrypoints to its class body. To create a mutation entrypoint,
we'll do the same, but to the class body of a class named `Mutation`. Subscriptions
are not yet supported.

### Function Entrypoints

Function entrypoints are created by decorating a method with the `Entrypoint` decorator.
Let's explore this by creating a simple query entrypoint that returns a greeting.

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"
```

This entrypoint's output type will be determined by the return type of the method.
Not including a return type will result in an error.

We can add arguments to the entrypoint by adding them to the method signature.
Typing these arguments is also required to determine their input type.

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
```

This will add a non-null `name` string argument to the entrypoint.
Note that non-null arguments are required by GraphQL, so if we want to make an argument
optional, we can do so by making it nullable, or adding a default value.

```python
from undine import Entrypoint

class Query:
    @Entrypoint
    def testing(self, name: str | None = None) -> str:
        return f"Hello, {name or 'World'}!"
```

We can also a description to the entrypoint by adding a docstring to the method.
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

When using function entrypoints, there is no real difference between creating a query
entrypoint or a mutation entrypoint. The only difference is that mutations are added to
a class named `Mutation` instead of `Query`.

```python
from undine import Entrypoint

class Mutation:
    @Entrypoint
    def testing(self, name: str) -> str:
        # Mutation here...
        return "Success!"
```

### QueryType and MutationType Entrypoints

`Entrypoint` can also be used with `QueryType` and `MutationType` classes
to create entrypoints for querying and mutating Django model data.
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
Every GraphQL schema needs to have at least the `Query` root operation type,
so let's use the `Query` class we created in the [`Entrypoints`](#entrypoints) section.

```python
from undine import create_schema, Entrypoint

class Query:
    @Entrypoint
    def testing(self) -> str:
        return "Hello, World!"

schema = create_schema(query_class=Query)
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
