# Tutorial

This tutorial will walk you through creating a simple GraphQL API using Undine.
It should hopefully give you some familiarity with how Undine works so that
you can dive into the rest of the documentation for more details.

We'll assume you have read the [Getting Started](getting-started.md) section
and installed Undine using the [installation instructions](getting-started.md#installation).

Our example application will be a project management system, where users can create
tasks and assign them to projects and teams of people. _Very exiting!_
Our Django project will have a single app called `service` where we'll create
our models and schema. See the full directory structure below:

```
system/
├─ config/
│  ├─ __init__.py
│  ├─ settings.py
│  ├─ urls.py
│  ├─ wsgi.py
├─ service/
│  ├─ migrations/
│  │  ├─ __init__.py
│  ├─ __init__.py
│  ├─ apps.py
│  ├─ models.py
├─ manage.py
```

## Part 1: Setup

When first installed, Undine comes with an example schema that we can try out before
creating our own. To access it, add an endpoint to the project's `urls.py` file:

```python
from django.urls import path
from undine import GraphQLView

urlpatterns = [
    path("graphql/", GraphQLView.as_view(), name="graphql"),
]
```

Next, configure Undine to enable [GraphiQL](https://github.com/graphql/graphiql),
a tool for exploring our GraphQL schema on the browser. Undine is configured using
the `UNDINE` setting in your Django project's `settings.py` file, so add the following to it:

```python
UNDINE = {
    "GRAPHIQL_ENABLED": True,
}
```

Now start the Django server and navigate to `/graphql/` to see GraphiQL UI.
Make the following request:

```graphql
query {
  testing
}
```

You should see the following response:

```json
{
  "data": {
    "testing": "Hello World"
  }
}
```

---

## Part 2: Creating the Schema

Let's replace the example schema with our own. Create a file called
`schema.py` in our app directory, and add the following to it:

```python
from undine import create_schema, Entrypoint, RootType

class Query(RootType):
    @Entrypoint
    def testing(self) -> str:
        return "Hello World"

schema = create_schema(query=Query)
```

This will create the same schema as Undine's example schema. To make it your own,
replace the return value of the `testing` method with a message of your choosing!

In Undine, [`Entrypoints`](schema.md#entrypoints) are used in the class bodies of
[`RootTypes`](schema.md#roottypes) to define the GraphQL operations that can be
executed at the root of the schema.

Now we need to tell Undine to use our schema instead of the example one.
Add the `SCHEMA` setting to Undine's configuration, and set it to point
to the `schema` variable we created in our `schema.py` file.

```python hl_lines="3"
UNDINE = {
    "GRAPHIQL_ENABLED": True,
    "SCHEMA": "service.schema.schema",
}
```

Restart the Django server and make the same request as before.
You should see you own message instead of the example one.

---

## Part 3: Adding Queries

Now that we have our own schema, let's start exposing Django models through it.
In our `models.py` file, add the following model:

```python
from django.db.models import *  # for brevity

class Task(Model):
    name = CharField(max_length=255)
    done = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

Create and run migrations for this model.

Next, we'll connect our `Task` model to the schema and exposing two `Entrypoints`:
one for fetching a single `Task` and another for fetching all `Tasks`. Replace the
current `schema.py` file with the following:

```python
from undine import create_schema, Entrypoint, RootType, QueryType

from .models import Task

class TaskType(QueryType, model=Task): ...

class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)

schema = create_schema(query=Query)
```

A [`QueryType`](queries.md#querytypes) is a class that represents a GraphQL `ObjectType` for querying
a Django model in the GraphQL schema. `QueryTypes` automatically introspect their model to create fields
for their generated `ObjectType` — that's why we don't need to add anything to the `TaskType` class body
to expose the model in this basic way.

To make the `Entrypoints` for this `QueryType`, we simply use the `QueryType` as an
argument to the `Entrypoint` class instead of decorating a method like we did before.
This creates an `Entrypoint` for fetching a single `Task` by its primary key.
For the `Entrypoint` for fetching all `Tasks`, we pass the `many=True` additionally
to indicate a list endpoint.

Let's try our new schema. But wait, first we need some data to query!
In your terminal, run `python manage.py shell` to start Django's shell and
create a few rows for the `Task` model.

```pycon
>>> from service.models import Task
>>> Task.objects.create(name="Task 1", done=False)
>>> Task.objects.create(name="Task 2", done=True)
>>> Task.objects.create(name="Task 3", done=False)
```

Now reboot the Django server and make the following request:

```graphql
query {
  tasks {
    pk
    name
    done
  }
}
```

You should see the following response:

```json
{
  "data": {
    "tasks": [
      {
        "pk": 1,
        "name": "Task 1",
        "done": false
      },
      {
        "pk": 2,
        "name": "Task 2",
        "done": true
      },
      {
        "pk": 3,
        "name": "Task 3",
        "done": false
      }
    ]
  }
}
```

Let's add a couple more models to our project to test relations:

```python hl_lines="3 4 11 13 14 15 16 17"
from django.db.models import *  # for brevity

class Project(Model):
    name = CharField(max_length=255)

class Task(Model):
    name = CharField(max_length=255)
    done = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    project = ForeignKey(Project, on_delete=SET_NULL, null=True, blank=True, related_name="tasks")

class Step(Model):
    name = CharField(max_length=255)
    done = BooleanField(default=False)

    task = ForeignKey(Task, on_delete=CASCADE, related_name="steps")
```

Create and run migrations for these models, then create some data for them:

```pycon
>>> from service.models import Project, Step, Task
>>> project_1 = Project.objects.create(name="Project 1")
>>> project_2 = Project.objects.create(name="Project 2")
>>> task_1 = Task.objects.get(name="Task 1")
>>> task_2 = Task.objects.get(name="Task 2")
>>> task_3 = Task.objects.get(name="Task 3")
>>> task_1.project = project_1
>>> task_1.save()
>>> task_2.project = project_2
>>> task_2.save()
>>> step_1 = Step.objects.create(name="Step 1", done=false, task=task_1)
>>> step_2 = Step.objects.create(name="Step 2", done=true, task=task_1)
>>> step_3 = Step.objects.create(name="Step 3", done=false, task=task_2)
>>> step_4 = Step.objects.create(name="Step 4", done=true, task=task_3)
>>> step_5 = Step.objects.create(name="Step 5", done=true, task=task_3)
```

Then we'll add these models to our schema by creating a `QueryType` for each of them.

```python hl_lines="3 5 9"
from undine import create_schema, Entrypoint, RootType, QueryType

from .models import Project, Step, Task

class ProjectType(QueryType, model=Project): ...

class TaskType(QueryType, model=Task): ...

class StepType(QueryType, model=Step): ...

class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)

schema = create_schema(query=Query)
```

`QueryTypes` will automatically link to each other through their model relations,
so we don't need to do anything else here.

Let's reboot the Django server once more and make the following request:

```graphql
query {
  tasks {
    pk
    name
    done
    project {
      pk
      name
    }
    steps {
      pk
      name
      done
    }
  }
}
```

You should see the following response:

```json
{
  "data": {
    "tasks": [
      {
        "pk": 1,
        "name": "Task 1",
        "done": false,
        "project": {
          "pk": 1,
          "name": "Project 1"
        },
        "steps": [
          {
            "pk": 1,
            "name": "Step 1",
            "done": false
          },
          {
            "pk": 2,
            "name": "Step 2",
            "done": true
          }
        ]
      },
      {
        "pk": 2,
        "name": "Task 2",
        "done": true,
        "project": {
          "pk": 2,
          "name": "Project 2"
        },
        "steps": [
          {
            "pk": 3,
            "name": "Step 3",
            "done": false
          }
        ]
      },
      {
        "pk": 3,
        "name": "Task 3",
        "done": false,
        "project": null,
        "steps": [
          {
            "pk": 4,
            "name": "Step 4",
            "done": true
          },
          {
            "pk": 5,
            "name": "Step 5",
            "done": true
          }
        ]
      }
    ]
  }
}
```

Now that our queries are using relations, Undine will _automatically_ optimize them
by adding the necessary joins to the database query.

---

## Part 4: Adding Mutations

Next we'll add mutations to our schema to allow us to create, update, and delete
`Task` and `Project` instances. Add the following to the `schema.py` file:

```python hl_lines="1 11 12 13 14 15 21 22 23 24 26"
from undine import create_schema, Entrypoint, RootType, QueryType, MutationType

from .models import Project, Step, Task

class ProjectType(QueryType, model=Project): ...

class TaskType(QueryType, model=Task): ...

class StepType(QueryType, model=Step): ...

class TaskCreateMutation(MutationType, model=Task): ...

class TaskUpdateMutation(MutationType, model=Task): ...

class TaskDeleteMutation(MutationType, model=Task): ...

class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)

class Mutation(RootType):
    create_task = Entrypoint(TaskCreateMutation)
    update_task = Entrypoint(TaskUpdateMutation)
    delete_task = Entrypoint(TaskDeleteMutation)

schema = create_schema(query=Query, mutation=Mutation)
```

Undine will know that the [`MutationType`](mutations.md#mutationtype) `TaskCreateMutation`
is a create mutation because the class has the word "create" in its name.
You could also use the `mutation_kind` argument in the `MutationType` class
definition to be more explicit.

Undine will generate different resolvers and `ObjectTypes` based on the `MutationType's`
`mutation_kind`, for example the primary key for the model is not included in the create
mutations, while in update mutations all fields are not required to support partial updates.
Undine will also use the `TaskType` as output type for the `MutationTypes` automatically since
they share the same model.

Let's try out our new mutations. Boot up the Django server and make the following request:

```graphql
mutation {
  createTask(input: {name: "New task"}) {
    pk
    name
  }
}
```

You should see the following response (`pk` will be different):

```json
{
  "data": {
    "createTask": {
      "pk": 1,
      "name": "New task"
    }
  }
}
```

Take note of the `pk` value, and use it to update the task:

```graphql
mutation {
  updateTask(input: {pk: 1, name: "Updated task"}) {
    name
  }
}
```

You should see the following response:

```json
{
  "data": {
    "updateTask": {
      "name": "Updated task"
    }
  }
}
```

Finally, let's delete the task. Note delete mutations only add the primary key
to the input arguments as well as to the output types by default.

```graphql
mutation {
  deleteTask(input: {pk: 1}) {
    pk
  }
}
```

You should see the following response:

```json
{
  "data": {
    "deleteTask": {
      "pk": 1
    }
  }
}
```
