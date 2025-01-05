# Schema

In the [getting started](getting-started.md) section, we started a basic GraphQL server using an
example schema. In this section, we'll learn how to create a schema for your own data.

Before we can create the schema itsef, we'll need to create some basic types for it,
mainly the `RootType` for supporting query operations in the schema, as well as
an `Entrypoint` in that `RootType` for actually fetching the data.

## RootTypes

A GraphQL schema defines a `RootType` for each kind of operation that it supports:

1. `Query`: For querying data (required).
2. `Mutation`: For mutating data (optional).
3. `Subscription`: For fetching real-time data (optional, not yet supported by Undine).

> In GraphQL terms, a `RootType` is just a regular `ObjectType` that just happens
> to be the root of the GraphQL schema. In Undine, we have a separate class for it
> for clarity and to better support things like optimizations and permissions.

To create the required `RootType` for querying, we'll create a class named `Query`
that subclasses `RootType`.

```python
from undine import RootType

class Query(RootType): ...
```

This isn't a valid `RootType` yet since all `RootTypes` need at least
one `Entrypoint` in their class body.

## Entrypoints

`Entrypoints` can be thought of as the _"API endpoints inside the GraphQL schema"_.
They are the fields in a `RootType` from which we can execute operations like queries
or mutations.

An `Entrypoint` always requires a _**reference**_ from which it will create the
proper GraphQL resolver, output type, and arguments for the operation.

### FunctionType references

Using a `FunctionType` (instances of `types.FunctionType` e.g. functions or methods)
as a reference is the most basic way of creating an `Entrypoint`.

`FunctionType` references can be used for both query and mutation `Entrypoints`.
As an example, let's create a query `Entrypoint` from a method on the Query `RootType`
that returns a greeting by decoraging a method with the `Entrypoint` class.

```python
from undine import Entrypoint, RootType, GQLInfo

class Query(RootType):
    @Entrypoint
    def testing(self, info: GQLInfo) -> str:
        return "Hello World!"
```

The `Entrypoint` will use the decorated method as its GraphQL resolver.
The method's return type will be used as the `Entrypoint's` output type, so annotating it is required.

/// details | About method signature

Note that the method's `self` argument is not actually the instance of the class, but the `root` argument
of a GraphQL field resolver. In fact, the decorated method is treated as a static method by the `Entrypoint`.

To clarify this, it's recommended to change the argument's name to `root`, as defined by the
`RESOLVER_ROOT_PARAM_NAME` setting. The value of the `root` argument is `None` by default,
but can be configured using the `ROOT_VALUE` setting.

The `root` and `info` arguments can all be left out if not needed.
When included, `root` is always the first argument of the method (typing not required) and `info`
always has the `GQLInfo` type annotation (typing required).

///

We can add arguments to the `Entrypoint` by adding them to the function signature.
Typing these arguments is required to determine their input type.

```python
from undine import Entrypoint, RootType

class Query(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        return f"Hello, {name}!"
```

This will add a non-null `name` string argument to the `Entrypoint`.
Note that non-null arguments are required by GraphQL, so if we want to make an argument
optional, we can do so by making it nullable, or adding a default value.

```python
from undine import Entrypoint, RootType

class Query(RootType):
    @Entrypoint
    def testing(self, name: str | None = None) -> str:
        return f"Hello, {name or 'World'}!"
```

We can add a description to the `Entrypoint` by adding a docstring to the method.
If the method has arguments, we can add descriptions to those arguments by using
[reStructuredText docstrings format](https://peps.python.org/pep-0287/).

> Other types of docstrings can be used by providing a parser to the `DOCSTRING_PARSER` setting
> that conforms to the `DocstringParserProtocol` from `undine.typing`.

```python
from undine import Entrypoint, RootType

class Query(RootType):
    @Entrypoint
    def testing(self, name: str) -> str:
        """
        Return a greeting.

        :param name: The name to greet.
        """
        return f"Hello, {name}!"
```

### QueryType references

A `QueryType` represents a GraphQL `ObjectType` for querying a Django model
in the GraphQL schema. You should first read more on `QueryTypes` in the [Queries](queries.md) section
since this section will only cover using them in `Entrypoints`.

For querying a single model instance, simply use the `QueryType` class
as the reference for the `Entrypoint`.

```python
from undine import Entrypoint, QueryType, RootType
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class Query(RootType):
    task = Entrypoint(TaskType)
```

This would create the following field in the Query `RootType`:

```graphql
type Query {
    task(pk: Int!): TaskType
}
```

To query a list of model instances, we simply add the `many` argument
to the `Entrypoint` in addition to the `QueryType`.

```python
from undine import Entrypoint, QueryType, RootType
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class Query(RootType):
    tasks = Entrypoint(TaskType, many=True)
```

This would create the following field in the Query `RootType`:

```graphql
type Query {
    tasks: [TaskType!]!
}
```

### MutationType references

A `MutationType` represents a possible mutation operation based on a Django model.
You should first read more on `MutationTypes` in the [Mutations](mutations.md) section
since this section will only cover using them in `Entrypoints`.

To create a mutation for a model instance (create mutation in this example),
simply use the `MutationType` class as the reference for the `Entrypoint`.

```python
from undine import Entrypoint, MutationType, RootType
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task): ...

class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
```

This would create the following field in the Mutation `RootType`:

```graphql
type Mutation {
    createTask(input: TaskCreateMutation!): TaskType!
}
```

To make this a bulk mutation, we can add the `many` argument to the `Entrypoint`.

```python
from undine import Entrypoint, MutationType, RootType
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task): ...

class Mutation(RootType):
    bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)
```

This would create the following field in the Mutation `RootType`:

```graphql
type Mutation {
    bulkCreateTask(
        batchSize: Int = null
        ignoreConflicts: Boolean = false
        updateConflicts: Boolean = false
        updateFields: [TaskCreateMutationBulkCreateField!] = null
        uniqueFields: [TaskCreateMutationBulkCreateField!] = null
        input: [TaskCreateMutation!]!
    ): [TaskType!]!
}
```

## Crating the Schema

Now that we have our `RootType` for querying, we'll create
the GraphQL schema using the `create_schema` function.

```python
from undine import create_schema, Entrypoint, RootType

class Query(RootType):
    @Entrypoint
    def testing(self) -> str:
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
