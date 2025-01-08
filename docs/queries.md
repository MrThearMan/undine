# Queries

This section will cover how to connect your Django models to the GraphQL schema using
`QueryTypes` and `Fields`.

## QueryTypes

A `QueryType` represents a GraphQL `ObjectType` for querying a Django model
in the GraphQL schema. A basic configuration is done by subclassing `QueryType`
and adding a `model` argument to the class definition:

```python
from undine import QueryType
from example_project.app.models import Task

# We don't even need a class body at this point.
class TaskType(QueryType, model=Task): ...
```

By default, the name of the generated `ObjectType` is the same as the name of the `QueryType` class.
If you want to change the name, you can do so by setting the `typename` argument:

```python
from undine import QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task, typename="Task"): ...
```

#### Auto-generation

By default, `QueryType` automatically introspects the given model and makes its fields
available on the generated `ObjectType`. For example, if the `Task` model has the following fields:

```python
from django.db import models

class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Then the GraphQL `ObjectType` for the `QueryType` would be:

```graphql
type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
}
```

We can disable auto-generation by setting the `auto` argument to `False` in the class definition:

```python
from undine import QueryType
from example_project.app.models import Task

# This would create an empty `ObjectType`, which is not allowed in GraphQL.
class TaskType(QueryType, model=Task, auto=False): ...
```

Alternatively, we could exclude some fields from the auto-generation by setting the `exclude` argument:

```python
from undine import QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task, exclude=["name"]): ...
```

### Filtering

Results from `QueryTypes` can be filtered in two ways:

1) Adding a `FilterSet` to the `QueryType`.

`Filtersets` provide a way to queries to be filtered using defined filters.
They are explained in detail in the [Filtering](filtering.md) section.

2) Defining custom filtering in the `__filter_queryset__` classmethod.

This used to filter all results returned by the `QueryType`. Use it to filter out
items that should never be returned by the `QueryType`, e.g. archived items.

```python
from django.db.models import QuerySet
from undine import QueryType, GQLInfo
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        return queryset.filter(archived=False)
```

### Ordering

Results from `QueryTypes` can be ordered in two ways:

1) Adding an `OrderSet` to the `QueryType`.

OrderSets provide a way to queries to be ordered using defined orderings.
This is explained in detail in the [Ordering](ordering.md) section.

2) Defining custom ordering in the `__filter_queryset__` classmethod.

Same as custom [filtering](#filtering), this is used for all results returned by the `QueryType`.
However, since queryset ordering is reset when a new ordering is applied to the queryset,
ordering added here serves as the default ordering for the `QueryType`, and is overridden if
any ordering is applied using an `OrderSet`.

```python
from django.db.models import QuerySet
from undine import QueryType, GQLInfo
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @classmethod
    def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
        return queryset.order_by("name")
```

> Note: It's probably better to use [custom optimizations](#custom-optimizations)
> to add a default ordering for optimization reasons.

### QueryType registry

When a new `QueryType` is created, Undine automatically registers it for its given model.
This allows other `QueryTypes` to look up the `QueryType` for linking relations,
(see [Relations](#relations)) and `MutationTypes` to find out their matching output type
(see [Mutations output types](mutations.md#output-type)).

The QueryType registry only allows one `QueryType` to be registered for each model.
During `QueryType` registration, if a `QueryType` is already registered for the model,
an error will be raised.

If you need to create multiple `QueryTypes` for the same model, you can choose to not
register a `QueryType` for the model by setting the `register` argument to `False` in the
`QueryType` class definition.

```python
from undine import QueryType
from example_project.app.models import Task

class OtherTaskType(QueryType, model=Task, register=False): ...
```

You then need to use this `QueryType` explicitly in `Field` references
or in `MutationType.__output_type__`.

### Custom optimizations

Usually touching the `QueryType` optimizations is not necessary, but if required,
you can override a `__optimizations__` classmethod on the `QueryType` to do so.

```python
from undine import QueryType, GQLInfo
from undine.optimizer import OptimizationData
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @classmethod
    def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
        ... # Some optimization here
```

This hook can be helpful when you require data from outside the GraphQL execution context
to e.g. make permission checks. See [optimizer](optimizer.md) section for more information
on how the query optimizer works and [Permissions](permissions.md) on how permissions checks work.

## Fields

`Fields` on a `QueryType` correspond to either model fields or annotated expressions.
In th GraphQL schema, they represent fields on the `ObjectType` generated from a `QueryType`.

A `Field` always requires a _**reference**_ from which it will create the proper GraphQL resolver,
output type, and arguments for the `Field`.

### Model field references

If a `Field` has the same name on the `QueryType` as a model field on the `QueryType's` model,
the reference can be omitted.

```python
from undine import Field, QueryType
from example_project.app.models import Task

# Basically the same as using the `auto` argument
class TaskType(QueryType, model=Task):
    name = Field()
    done = Field()
    created_at = Field()
```

We could also use a string as a direct reference to the model field:

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field("name")
```

The model field itself works too:

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field(Task.name)
```

This would allow us to use some other name for the field in the GraphQL schema.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    title = Field("name")
```

We could also use the `model_field_name` argument instead of using the reference.
This is useful when linking `QueryTypes` together (see [Relations](#relations) below).

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    title = Field(model_field_name="name")
```

### Expression references

Django ORM expressions also work as the references (Subqueries are also supported).
These create an annotation on the model instances when fetched.

```python
from undine import Field, QueryType
from django.db.models.functions import Upper
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    upper_name = Field(Upper("name"))
```

### Function references

Functions (or methods) can also be used to create `Fields`.
This can be done by decorating a method with the `Field` class.

```python
from undine import Field, QueryType, GQLInfo
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @Field
    def greeting(self, info: GQLInfo) -> str:
        return "Hello World!"
```

The `Field` will use the decorated method as its GraphQL resolver.
The method's return type will be used as the `Field's` output type, so annotating it is required.

/// details | About method signature

Note that the method's `self` argument is not actually the instance of the class, but the `root` argument
of a GraphQL field resolver. In fact, the decorated method is treated as a static method by the `Field`.

To clarify this, it's recommended to change the argument's name to `root`, as defined by the
`RESOLVER_ROOT_PARAM_NAME` setting. The value of the `root` argument is the **model instance** being queried.

The `root` and `info` arguments can all be left out if not needed.
When included, `root` is always the first argument of the method (typing not required) and `info`
always has the `GQLInfo` type annotation (typing required).

///

You can add arguments to the `Field` by adding arguments to the function signature.
Typing these arguments is required to determine their input type.

```python
from undine import Field, QueryType, GQLInfo
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @Field
    def greeting(self, info: GQLInfo, *, name: str) -> str:
        return f"Hello, {name}!"
```

We can add a description to the `Field` by adding a docstring to the method.
If the method has arguments, we can add descriptions to those arguments by using
[reStructuredText docstrings format](https://peps.python.org/pep-0287/).

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @Field
    def testing(self, name: str) -> str:
        """
        Return a greeting.

        :param name: The name to greet.
        """
        return f"Hello, {name}!"
```

Other types of docstrings can be used by providing a parser to the `DOCSTRING_PARSER`
setting that conforms to the `DocstringParserProtocol` from `undine.typing`.

> If the method requires fields from the `root` argument instance, we should add custom optimization
> rules for the `Field` so that the fields are available when the resolver is called.
> See [custom optimizations](#custom-optimizations) for how to add these.
>
> It might be simpler to use [Calculated references](#calculated-references) instead, since they
> allow using the queryset directly.

### Calculated references

Using an instance of `Calculated` as a reference creates a field that is calculated based on user input.
These require a special calculation function to be defined.

```python
from typing import TypedDict, Unpack
from django.db.models import QuerySet, Value
from undine import Field, QueryType, GQLInfo, Calculated
from example_project.app.models import Task

class CalcInput(TypedDict):
    value: int

class TaskType(QueryType, model=Task):
    calc = Field(Calculated(takes=CalcInput, returns=int))

    @calc.calculate
    def _(self, queryset: QuerySet, info: GQLInfo, **kwargs: Unpack[CalcInput]) -> QuerySet:
        # Some impressive calculation here
        return queryset.annotate(calc=Value(kwargs["value"]))
```

`Calculated` takes two arguments:

1. `takes`: describes the input arguments needed for the calculation (`TypedDict`/`NamedTuple`/`dataclass`).
2. `returns`: describes its return type.

The calculation function is decorated with the `@<field_name>.calculate` decorator.
The function should annotate a value to the given queryset with the same name as the field.

/// details | About method signature

The `self` argument for the calculation function is not the instance of the `QueryType` class,
but the `Field` instance that the calculation function is added to.

///

The `Field` will look like this in the GraphQL schema:

```graphql
type TaskType {
    calc(value: Int!): Int!
}
```

### Relations

Let's say we add a `Project` model and a ForeignKey to the `Task` model:

```python hl_lines="3 4 11"
from django.db import models

class Project(models.Model):
    name = models.CharField(max_length=255)

class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
```

We can then create a `QueryType` for the `Project` model.

```python
from undine import QueryType
from example_project.app.models import Project, Task

class ProjectType(QueryType, model=Project): ...

class TaskType(QueryType, model=Task): ...
```

When `auto` is on for the `QueryTypes` they will be automatically linked together
in the GraphQL schema using relations:

```graphql
type ProjectType {
    pk: Int!
    name: String!
    tasks: [TaskType!]!
}

type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
    project: ProjectType!
}
```

We could also link them explicitly.

```python
from undine import Field, QueryType
from example_project.app.models import Project, Task

class ProjectType(QueryType, model=Project):
    tasks = Field(lambda: TaskType, many=True)  # lazy evaluation

class TaskType(QueryType, model=Task):
    project = Field(ProjectType)
```

### Descriptions

We can set the description of the `Field` in two ways:

1) By setting the `description` argument.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field(description="The name of the task.")
```

2) As class variable docstrings.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field()
    """The name of the task."""
```

When `Field` is referencing a model field, the field's `help_text` will be used as the
description if no description is provided in these ways.

### Nullable and many

Most of the time a `Field's` reference is enough to determine whether the `Field`
returns a nullable value and/or a list of values, but sometimes you might want to configure this manually.
This can be done by adding the `nullable` and `many` arguments to the `Field` respectively.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field(nullable=False, many=False)
```

### Custom resolvers

> Usually using a custom `Field` resolver is not necessary, and should be avoided
> if possible. This is because most modifications to resolvers can result in canceling
> query optimizations (see the [optimizer](optimizer.md) section for details).

You can override a `Field's` resolver by adding a method to the class body of the `QueryType`
and decorating it with the `@<field_name>.resolve` decorator.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field()

    @name.resolve
    def resolve_name(self: Task) -> str:
        return self.name.upper()
```

### Custom optimizations

Usually touching the `Field` optimizations is not necessary, but if required,
you can add a method to the class body of the `QueryType` and decorating it with the
`@<field_name>.optimize` decorator.

```python
from undine import Field, QueryType
from undine.optimizer import OptimizationData
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field()

    @name.optimize
    def optimize_name(self: Task, data: OptimizationData) -> None:
        ... # Some optimization here
```

This hook can be helpful when you require data from outside the GraphQL execution context
to e.g. make permission checks. See [optimizer](optimizer.md) section for more information
on how the query optimizer works and [Permissions](permissions.md) on how permissions checks work.
