# Queries

This section will cover how to create a queryable `ObjectType` using `QueryTypes`.

## QueryType

To query data from a Django model, you need to create a `QueryType` for it.
A `QueryType` is a class that represents a GraphQL `ObjectType` in the GraphQL schema.
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

You can disable this behavior by setting the `auto` argument to `False` in the class definition:

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

Note that the name of the `ObjectType` is the same as the name of the `QueryType` class.
If you want to change the name, you can do so by setting the `typename` argument:

```python
from undine import QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task, typename="Task"): ...
```

Other `QueryType` class arguments will be explained when we cover their relevant features.

## Field

### Basics

A `Field` is a class that represents a field on a GraphQL `ObjectType` for the `QueryType` it is added to.

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field()
    done = Field()
    created_at = Field()
```

This is basically the same as using the `auto` argument on the `QueryType` class.
We don't need to add any arguments to the Field instances, since they automatically
introspect all relevant data from the model field they correspond to.

### References

A `Field`'s "reference" is actual "thing" the Field is built from.
Without arguments, `None` is used as the reference, which means the `Field` is built from the model field
with the same name as the `Field` instance on the `QueryType` class.

As an example, we could use a string as the reference to the model field:

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    name = Field("name")
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

We can then add a `ProjectType` to the `QueryType` class to query the `Project` model,
and use it as the reference for the `project` field on the `TaskType`:

```python
from undine import Field, QueryType
from example_project.app.models import Project, Task

class ProjectType(QueryType, model=Project): ...

class TaskType(QueryType, model=Task):
    project = Field(ProjectType)
```

This will link the models together in the GraphQL schema:

```graphql
type ProjectType {
    name: String!
}

type TaskType {
    name: String!
    project: ProjectType!
}
```

### Field description

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

### Renaming fields

If we wanted to use some other name for a field in the GraphQL schema,
we could use the `model_field_name` argument:

```python
from undine import Field, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task):
    title = Field(model_field_name="name")
```
