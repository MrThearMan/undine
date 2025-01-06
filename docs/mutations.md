# Mutations

This section will cover how to create mutations for Django models using
`MutationTypes` and `Inputs`.

## MutationTypes

A `MutationType` is a class that represents a GraphQL `InputObjectType` for mutating
a Django model in the GraphQL schema. All `MutationTypes` require the `model`
argument to be passed to the class definition.

```python
from undine import MutationType
from example_project.app.models import Task

class TaskMutation(MutationType, model=Task): ...
```

`MutationType` supports `create`, `update`, `delete` as well as `custom` mutations.
The kind of mutation a certain `MutationType` is for is determined by its
`mutation_kind`, which can be set in the `MutationType` class definition.

```python
from undine import MutationType
from example_project.app.models import Task

class TaskMutation(MutationType, model=Task, mutation_kind="create"): ...
```

However, `mutation_kind` can also be omitted, in which case the `MutationType`
will first check if the `__mutate__` method has been defined on the `MutationType`,
and if so, treat the mutation as a `custom` mutation.

```python
from typing import Any
from undine import MutationType, GQLInfo
from example_project.app.models import Task

class TaskMutation(MutationType, model=Task):
    @classmethod
    def __mutate__(cls, root: Any, info: GQLInfo, input_data: dict[str, Any]) -> Any:
        ... # Some custom mutation logic here
```

If `__mutate__` is not defined, the `MutationType` will then check if the word `create`, `update`, or `delete`
can be found in the name of the `MutationType`, and if so, treat the mutation as that kind of mutation.

```python
from undine import MutationType
from example_project.app.models import Task

# Create mutation, since has "create" in the name.
class TaskCreateMutation(MutationType, model=Task): ...
```

By default, the name of the generated `InputObjectType` is the same as the name of the `MutationType` class.
If you want to change the name, you can do so by setting the `typename` argument:

```python
from undine import MutationType
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task, typename="Task"): ...
```

### Autogeneration

By default `MutationType` automatically introspects the given model and makes its fields
available on the generated `InputObjectType`. For example, if the `Task` model has the following fields:

```python
from django.db import models

class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Then the GraphQL `InputObjectType` for a `MutationType` for a `create` mutation would be:

```graphql
input TaskCreateMutation {
    name: String!
    done: Boolean = true
    # `createdAt` not included since it has `auto_now_add=True`
}
```

For an `update` mutation, the `pk` field is included for selecting the
mutation target, the rest of the fields are all made nullable (=not required),
and no default values are added.

```graphql
input TaskUpdateMutation {
    pk: Int!
    name: String
    done: Boolean
}
```

For a `delete` mutation, only the `pk` field is included for selecting the
mutation target.

```graphql
input TaskDeleteMutation {
    pk: Int!
}
```

We can disable autogeneration by setting the `auto` argument to `False` in the class definition:

```python
from undine import MutationType
from example_project.app.models import Task

# This would create an empty `InputObjectType`, which is not allowed in GraphQL.
class TaskCreateMutation(MutationType, model=Task, auto=False): ...
```

Alternatively, we could exclude some fields from the autogeneration by setting the `exclude` argument:

```python
from undine import MutationType
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task, exclude=["name"]): ...
```

### Output type

A `MutationType` requires a `QueryType` for the same model to exist in the schema,
since the `MutationType` will use the `ObjectType` generated from the `QueryType`
as the output type of the mutation.

We don't need to explicitly link the `QueryType` to the `MutationType`,
since `MutationType` will automatically look up the `QueryType` for the same model
from the [QueryType registry](queries.md#querytype-registry).

```python
from undine import MutationType, QueryType, RootType, Entrypoint
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class TaskCreateMutation(MutationType, model=Task): ...

class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
```

This would generate the following mutation in the GraphQL schema:

```graphql
type TaskType {
    pk: Int!
    name: String!
    done: Boolean!
    createdAt: DateTime!
}

input TaskCreateMutation {
    name: String!
    done: Boolean = true
}

type Mutation {
    createTask(input: TaskCreateMutation!): TaskType!
}
```

If we wanted to link the `QueryType` explicitly, we could do so by overriding the
`MutationType.__output_type__` classmethod.

```python
from graphql import GraphQLObjectType
from undine import MutationType, QueryType
from example_project.app.models import Task

class TaskType(QueryType, model=Task): ...

class TaskCreateMutation(MutationType, model=Task):
    @classmethod
    def __output_type__(cls) -> GraphQLObjectType:
        return TaskType.__output_type__()
```

### Validation

You can link custom validation to a `MutationType` by adding a `__validate__` classmethod.

```python
from typing import Any
from undine import MutationType, GQLInfo
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task):
    @classmethod
    def __validate__(cls, info: GQLInfo, input_data: dict[str, Any]) -> None:
        ...  # Some validation here
```

The `__validate__` classmethod can raise any type of exception, but it's recommended to
raise a `GraphQLValidationError` from the `undine.errors.exceptions` module.

### After mutation handling

You can add custom handling that happens after the mutation is done by adding a `__after__`
classmethod to the `MutationType`. This can be useful for doing things like sending emails.

```python
from typing import Any
from undine import MutationType, GQLInfo
from example_project.app.models import Task

class TaskCreateMutation(MutationType, model=Task):
    @classmethod
    def __after__(cls, info: GQLInfo, value: Any) -> None:
        ...  # Some post-mutation handling here
```

## Inputs

`Inputs` on a `MutationType` correspond to the input arguments of the `InputObjectType`
for the mutation.


### Model field references

### Function references

### Input-only inputs

### Hidden inputs

### Descriptions

### Default values
