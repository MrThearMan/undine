# Queries

This section will cover how to connect your Django models to the GraphQL schema through
Undine `QueryTypes` and `Fields`.

## QueryType

A `QueryType` class represents a GraphQL `ObjectType` for a Django model.
A basic configuration is done by subclassing `QueryType` and adding a `model` argument
to the class definition:

```python
from undine import QueryType
from example_project.app.models import Task

# We don't even need a class body at this point.
class TaskType(QueryType, model=Task): ...
```

`QueryType` has some automatic behaviors that introspect the given model
and makes its fields available on the generated `ObjectType`.

For example, if the `Task` model has the following fields:

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
    name: String!
    done: Boolean!
    createdAt: DateTime!
}
```

### Creating an Entrypoint

To be able to query our model data using a `QueryType`, we need to create an `Entrypoint`
for that `QueryType` (see more on creating the schema in the [Schema](schema.md) section).

For querying a single model instance, simply use the `QueryType` class
as the reference for the `Entrypoint`.

```python
from undine import Entrypoint, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class Query:
    task = Entrypoint(TaskType)
```

This will create the following field in the `Query` root operation type:

```graphql
type Query {
    task(pk: Int!): TaskType
}
```

To query a list of model instances, we simply add the `many` argument
to the `Entrypoint` in addition to the `QueryType`.

```python
from undine import Entrypoint, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class Query:
    tasks = Entrypoint(TaskType, many=True)
```

This will create the following field in the `Query` root operation type:

```graphql
type Query {
    tasks: [TaskType!]!
}
```

### Configuration

We can disable automatic field generation by setting the `auto` argument to `False` in the class definition:

```python
from undine import QueryType
from example_project.app.models import Task

# This would create an empty `ObjectType`, which is not allowed in GraphQL.
class TaskType(QueryType, model=Task, auto=False): ...
```

Alternatively, we could exclude some fields from the `ObjectType` by setting the `exclude` argument:

```python
from undine import QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task, exclude=["name"]): ...
```

By default, the name of the generated `ObjectType` is the same as the name of the `QueryType` class.
If you want to change the name, you can do so by setting the `typename` argument:

```python
from undine import QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task, typename="Task"): ...
```

### Filtering

Results from `QueryTypes` can be filtered in two ways:

1) Adding a `FilterSet` to the `QueryType`.

This is explained in detail in the [Filtering](filtering.md) section.

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

This is explained in detail in the [Ordering](ordering.md) section.

2) Defining custom ordering in the  `__filter_queryset__` classmethod.

Same as custom [filtering](#filtering), this is used for all results returned by the `QueryType`.
However, since queryset ordering is reset when a new ordering is applied to the queryset,
ordering added here serves as the default ordering for the `QueryType`.

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

### Custom optimizations

Usually touching the `QueryType` optimizations is not necessary, but if required,
you can override a `__optimizer_hook__` classmethod to do so.

```python
from undine import QueryType, GQLInfo
from undine.optimizer import OptimizationData
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    @classmethod
    def __optimizer_hook__(cls, data: OptimizationData, info: GQLInfo) -> None:
        ... # Some optimization here
```

This hook can be helpful when you require data from outside the GraphQL execution context
to e.g. make permission checks. See [optimizer](optimizer.md) section for more information
on how the query optimizer works and [Permissions](permissions.md) on how permissions checks work.

## Field

A `Field` is a class that represents a field on a GraphQL `ObjectType`. `Fields` should
be added to the class body of a `QueryType` class, like so:

```python
from undine import Field, QueryType
from example_project.app.models import Task

# Basically the same as using the `auto` argument
class TaskType(QueryType, model=Task):
    name = Field()
    done = Field()
    created_at = Field()
```

We don't need to add any arguments to the `Field` instances, since they automatically
introspect all relevant data from the model field they correspond to.

### References

A `Field's` "reference" is actual "thing" the Field is built from.
Without arguments, `None` is used as the reference, which means the `Field` is built from the model field
with the same name as the `Field` instance on the `QueryType` class.

As an example, we could use a string as the reference to the model field:

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
This is useful when linking `QueryTypes` together (see [Relations](#relations)).

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    title = Field(model_field_name="name")
```

Django ORM expressions also work as the references. These create an
annotation on the model instances when fetched.

```python
from undine import Field, QueryType
from django.db.models.functions import Upper
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    upper_name = Field(Upper("name"))
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

When `auto` is on for the `QueryTypes`, they will be automatically linked together
in the GraphQL schema:

```graphql
type ProjectType {
    name: String!
    tasks: [TaskType!]!
}

type TaskType {
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
returns a nullable value and/or a list of values, but sometimes this needs to be configured manually.
This can be done by adding the `nullable` and `many` arguments to the `Field` respectively.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field(nullable=False, many=False)
```

### Custom resolvers

> Usually overriding the `Field` resolver is not necessary, and should be avoided
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

### Calculated fields

A calculated field is a field that is calculated based on user input.
These require a special setup and a calculation function to be defined.

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

`Calculated` takes two arguments: `takes`, which describes the input arguments needed for the 
calculation (a `TypedDict`, a `NamedTuple` or a `dataclass`), and `returns`, which describes
its return type.

The calculation function is decorated with the `@<field_name>.calculate` decorator.
The function should annotate a value to the given queryset with the same name as the field.

The calculated field will look like this in the GraphQL schema:

```graphql
type TaskType {
    calc(value: Int!): Int!
}
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
