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

## Part 1: Setting up the server

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

Now we can start the Django server and navigate to `/graphql/` to see GraphiQL UI.
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

## Part 2: Creating our own schema

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

This will create the same schema as Undine's example schema, so replace the
return value of the `testing` method with your own message to make it your own.

Now we need to tell Undine to use our schema instead of the example one.
Add the `SCHEMA` setting to Undine's configuration, and set it to point
to the `schema` variable we created in our `schema.py` file.

```python hl_lines="3"
UNDINE = {
    "GRAPHIQL_ENABLED": True,
    "SCHEMA": "service.schema.schema",
}
```

We can now restart the server and make the same request as before.
You should see you own message instead of the example one.

---

## Part 3: Adding our models

Now that we have our own schema, let's get started adding our models to it.
In our `models.py` file, add the following model:

```python
from django.db import models

class Task(models.Model):
    name = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Create and run migrations for this model.

Next, we'll modify our schema by adding a `QueryType` for the `Task` model,
and exposing it from two `Entrypoints` in our schema: one for fetching a
single Task and another for fetching all tasks.

```python hl_lines="3 5 8"
from undine import create_schema, Entrypoint, RootType, QueryType

from .models import Task

class TaskType(QueryType, model=Task): ...

class Query(RootType):
    task = Entrypoint(TaskType)
    tasks = Entrypoint(TaskType, many=True)

schema = create_schema(query=Query)
```

The `TaskType` class may look a bit strange, since it doesn't have a class body.
We also pass the `model` argument to it in the class definition.
