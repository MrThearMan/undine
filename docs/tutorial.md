description: Tutorial for Undine.

# Tutorial

> Before starting the tutorial, read the [Getting Started](getting-started.md) section.

This tutorial will guide you through creating a simple GraphQL API using Undine.
You'll learn the fundamental aspects of creating a GraphQL schema:
queries, mutations, filtering, ordering, permissions, and validation.
This should give you familiarity with how Undine works so that
you can explore the rest of the documentation for more details.

The example application will be a project management system, where users can create
tasks with multiple steps and add them to projects. _Very exciting!_
The Django project will have a single app called `service` where you'll create
your models and schema. See the full directory structure below:

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

> A starting template is available in [docs/snippets/tutorial/template].

[docs/snippets/tutorial/template]: https://github.com/MrThearMan/undine/tree/main/docs/snippets/tutorial/template

## Part 1: Setup

First, install Undine using the [installation instructions](getting-started.md#installation).

Undine comes with an example schema that you can try out before
creating your own. To access it, add the following to your project's `urls.py` file:

```python
-8<- "tutorial/urls.py"
```

Next, configure Undine to enable [GraphiQL]{:target="_blank"},
a tool for exploring GraphQL schemas in the browser. Undine is configured using
the `UNDINE` setting in your Django project's `settings.py` file, so add the following to it:

[GraphiQL]: https://github.com/graphql/graphiql

```python
UNDINE = {
    "GRAPHIQL_ENABLED": True,
    "ALLOW_INTROSPECTION_QUERIES": True,
}
```

Now start the Django server and navigate to `/graphql/` to see the GraphiQL UI.
Make the following request:

```graphql
query {
  testing
}
```

/// details | You should see this response:

```json
{
  "data": {
    "testing": "Hello World"
  }
}
```

///

---

## Part 2: Creating the Schema

Next, let's replace the example schema with your own. Create a file called
`schema.py` in your `service` app directory and add the following to it:

```python
-8<- "tutorial/create_schema.py"
```

This creates the same schema as Undine's example schema. To make it your own,
simply modify the return value of the `testing` method with your own custom message.

In Undine, [`Entrypoints`](schema.md#entrypoints) are used in the class bodies of
[`RootTypes`](schema.md#roottypes) to define the operations that can be executed
from your GraphQL schema.

Now you need to tell Undine to use your custom schema instead of the example one.
Add the `SCHEMA` setting to Undine's configuration and set it to point
to the `schema` variable you created in your `schema.py` file.

```python hl_lines="4"
UNDINE = {
    "GRAPHIQL_ENABLED": True,
    "ALLOW_INTROSPECTION_QUERIES": True,
    "SCHEMA": "service.schema.schema",
}
```

/// details | How do I determine the value for `SCHEMA`?

The value for `SCHEMA` is a "dotted import path" — a string that can be imported with Django's
[`import_string`][import_string]{:target="_blank"} utility. In other words,
`"service.schema.schema"` points to a file `service/schema.py` with a variable `schema`.

[import_string]: https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.module_loading.import_string

///

Restart the Django server and make the same request as before.
You should see your own message instead of the example one.

---

## Part 3: Adding Queries

Now that you have your own schema, let's start exposing Django Models through it.
In your `models.py` file, add the following Model:

```python
-8<- "tutorial/models_1.py"
```

Create and run migrations for this Model.

To add the `Task` Model to the schema, let's add two `Entrypoints`:
one for fetching a single `Task`, and another for fetching all `Tasks`. Replace the
current `schema.py` file with the following:

```python
-8<- "tutorial/adding_query_type.py"
```

A [`QueryType`](queries.md#querytypes) is a class that represents a GraphQL `ObjectType` for
a Django Model in the GraphQL schema. By adding [`Fields`](queries.md#fields) to its class body,
you can expose the Model's fields in the GraphQL schema.

To create `Entrypoints` for this `QueryType`, you simply use the `QueryType` as an
argument to the `Entrypoint` class instead of decorating a method like you did before.
This creates an `Entrypoint` for fetching a single `Task` by its primary key.
For fetching all `Tasks`, pass `many=True` to indicate a list endpoint.

Now it's time to try out your new schema. But wait, first you need some data to query!
In your terminal, run `python manage.py shell` to start Django's shell and
create a few rows for the `Task` Model.

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

/// details | You should see this response:

```json
-8<- "tutorial/response_1.json"
```

///

Next, let's add a couple more Models to your project.

```python hl_lines="4 5 13 16 17 18 19 20"
-8<- "tutorial/models_2.py"
```

Create and run migrations for these Models, then create some data for them:

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

Then, add these Models to your schema by creating a `QueryType` for each of them.
Your can also link the `QueryTypes` to each other by adding `Fields` for the Model related fields.

```python hl_lines="6 7 8 9 17 18 21 22 23 24 25"
-8<- "tutorial/adding_more_query_types.py"
```

Reboot the Django server once more and make the following request:

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

/// details | You should see this response:

```json
-8<- "tutorial/response_2.json"
```

///

Now that you're are using relations, Undine will _automatically_ optimize the database queries
for those relations.

---

## Part 4: Adding Mutations

Next, let's add a mutation to your schema for creating `Tasks`.
Add the following to the `schema.py` file:

```python hl_lines="1 18 19 20 21 22 23 24 25 26 27"
-8<- "tutorial/adding_mutation_types.py"
```

Undine will know that the [`MutationType`](mutations.md#mutationtypes) `TaskCreateMutation`
is a create mutation because the class has the word _"create"_ in its name. Similarly,
having _"update"_ in the name will make an update mutation, and _"delete"_ will make a delete mutation.
Create, update and delete mutations are executed differently
(see the [Mutations](mutations.md) section for more details).

You could also use the `kind` argument in the `MutationType` class definition to be more explicit.

```python hl_lines="6"
-8<- "tutorial/mutation_type_explicit_kind.py"
```

The `TaskCreateMutation` `MutationType` will use the `TaskType` `QueryType` as the output type
since they share the same Model. In fact, all `MutationTypes` require a `QueryType` for the same Model
to be created, even if it's not otherwise usable from the GraphQL schema.

Let's try out the new mutation. Boot up the Django server and make the following request:

```graphql
mutation {
  createTask(input: {name: "New task"}) {
    name
  }
}
```

/// details | You should see this response:

```json
-8<- "tutorial/response_3.json"
```

///

You can also mutate related objects by using other `MutationTypes` as `Inputs`.
Modify the `TaskCreateMutation` by adding a `Project` Input.

```python hl_lines="24 25 26 32"
-8<- "tutorial/adding_related_mutation_type.py"
```

Here `TaskProjectInput` is a special _"related"_ `kind` of `MutationType`.
These `MutationTypes` allow you to freely modify the related objects during the mutation.
For example, using the above configuration, you could create a `Task` and a `Project` in a single mutation.

```graphql hl_lines="5 6 7"
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        name: "New project"
      }
    }
  ) {
    name
    project {
      name
    }
  }
}
```

Or you could link an existing `Project` to a new `Task`.

```graphql hl_lines="5 6 7"
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        pk: 1
      }
    }
  ) {
    name
    project {
      name
    }
  }
}
```

Or link an existing `Project` while renaming it.

```graphql hl_lines="5 6 7 8"
mutation {
  createTask(
    input: {
      name: "New task"
      project: {
        pk: 1
        name: "Renamed project"
      }
    }
  ) {
    name
    project {
      name
    }
  }
}
```

Undine also supports bulk mutations by using the `many` argument on the `Entrypoint`.
Let's add a bulk mutation for creating `Tasks` using the `TaskCreateMutation`.

```python hl_lines="37"
-8<- "tutorial/adding_bulk_mutation.py"
```

Bulk mutations work just like regular mutations.
Boot up the Django server and make the following request:

```graphql
mutation {
  bulkCreateTasks(
    input: [
      {
        name: "New Task"
        project: {
          name: "New Project"
        }
      }
      {
        name: "Other Task"
        project: {
          name: "Other Project"
        }
      }
    ]
  ) {
    name
    project {
      name
    }
  }
}
```

/// details | You should see this response:

```json
-8<- "tutorial/response_4.json"
```

///

---

## Part 5: Adding Permissions

In Undine, you can add permission checks to `QueryTypes` or `MutationTypes`
as well as individual `Fields` or `Inputs`. First, let's add a permission check for querying `Tasks`.

```python hl_lines="8 9 10 11 12"
-8<- "tutorial/query_type_permissions.py"
```

Now all users need to be logged in to access `Tasks` through `TaskType`.
Boot up the Django server and make the following request:

```graphql
query {
  tasks {
    name
  }
}
```

/// details | You should see this response:

```json
-8<- "tutorial/response_5.json"
```

///

The permission check will be called for each `Task` instance returned by the `QueryType`.

For `Field` permissions, decorate a method with `@<field_name>.permissions`.

```python hl_lines="10 11 12 13 14"
-8<- "tutorial/query_type_field_permissions.py"
```

Now users need to be logged in to be able to query `Task` names.

Mutation permissions using `MutationTypes` work similarly to query permissions using `QueryTypes`.

```python hl_lines="10 11 12 13 14"
-8<- "tutorial/mutation_type_permissions.py"
```

Now users need to be staff members to be able to create new `Tasks` using `TaskCreateMutation`.

You can also restrict the usage of specific `Inputs` by decorating a method with `@<input_name>.permissions`.

```python hl_lines="10 11 12 13 14"
-8<- "tutorial/mutation_type_input_permissions.py"
```

Now only superusers can add `Tasks` that are already done,
since in this case the default value of `Task.done` is `False`,
and `Input` permissions are only checked for non-default values.

---

## Part 6: Adding Validation

Mutations using `MutationTypes` can also be validated on both the `MutationType`
and individual `Input` level.

To add validation for a `MutationType`, add the `__validate__` classmethod to it.

```python hl_lines="10 11 12 13 14"
-8<- "tutorial/mutation_type_validation.py"
```

Now users cannot create `Tasks` that are already marked as done.
Boot up the Django server and make the following request:

```graphql
mutation {
  createTask(input: {name: "New task", done: true}) {
    name
  }
}
```

/// details | You should see this response:

```json
-8<- "tutorial/response_6.json"
```

///

To add validation for an `Input`, decorate a method with `@<input_name>.validate`.

```python hl_lines="10 11 12 13 14"
-8<- "tutorial/mutation_type_input_validate.py"
```

Now users cannot create `Tasks` with names that are less than 3 characters long.

---

## Part 7: Adding Filtering

Results from `QueryTypes` can be filtered using [`Filters`](filtering.md#filter)
defined in a [`FilterSet`](filtering.md#filterset). Create a `FilterSet` for the `Task` Model
and add it to your `TaskType`.

```python hl_lines="1 6 7 8 11"
-8<- "tutorial/adding_filters.py"
```

Now all `Entrypoints` created from this `QueryType` will have a `filter` argument that contains
the filtering options defined by the `FilterSet`.

Boot up the Django server and make the following request:

```graphql
query {
  tasks(
    filter: {
      nameContains: "a"
    }
  ) {
    pk
    name
  }
}
```

Check the response. You should only see `Tasks` with names that contain the letter "a".

Different `Filters` can also be combined to narrow down the results.

```graphql hl_lines="5"
query {
  tasks(
    filter: {
      nameContains: "a"
      done: false
    }
  ) {
    pk
    name
  }
}
```

With this query, you should only see `Tasks` that contain the letter "a" _and_ are not done.

If you wanted to see _either_ tasks containing the letter a _or_ tasks that are not done,
you could put the filters inside an `OR` block:

```graphql hl_lines="4 5 6 7"
query {
  tasks(
    filter: {
      OR: {
        nameContains: "a"
        done: false
      }
    }
  ) {
    pk
    name
  }
}
```

Similar logical blocks exist for `AND`, `NOT` and `XOR`, and they can be nested as deeply as needed.

---

## Part 8: Adding Ordering

Results from `QueryTypes` can be ordered using [`Orders`](ordering.md#order)
defined in an [`OrderSet`](ordering.md#orderset). Create an `OrderSet` for the `Task` Model
and add it to your `TaskType`.

```python hl_lines="1 6 7 8 11"
-8<- "tutorial/adding_ordering.py"
```

Now all `Entrypoints` created from this `QueryType` will have an `orderBy` argument that contains
the ordering options defined by the `OrderSet`.

Adding an ordering enables you to order by that fields in both ascending and descending directions.
Boot up the Django server and make the following request:

```graphql
query {
  tasks(
    orderBy: [
      nameAsc
      pkDesc
    ]
  ) {
    pk
    name
  }
}
```

With this ordering, you should see the `Tasks` ordered primarily by name in ascending order,
and secondarily by primary key in descending order.

---

## Next Steps

In this tutorial, you've learned the basics of creating a GraphQL schema using Undine.
It's likely your GraphQL schema has requirements outside of what has been covered here,
so it's recommended to read the [Queries](queries.md), [Mutations](mutations.md),
[Filtering](filtering.md), and [Ordering](ordering.md) sections next.
The [Pagination](pagination.md) section is also helpful to learn how to
paginate your `QueryTypes` using Relay Connections.

For more in-depth information on how Undine optimizes queries to your
GraphQL Schema, as well as how to provide custom optimizations for more complex use cases,
see the [Optimizer](optimizer.md) section.
