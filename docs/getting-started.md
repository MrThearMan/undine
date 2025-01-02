# Getting Started

## Installation

Undine is available on PyPI and can be installed with `pip`:

```shell
pip install undine
```

After adding Undine to your environment, you also need to add it to your
`INSTALLED_APPS` setting in your Django project's `settings.py` file:

```python
INSTALLED_APPS = [
    "undine",
]
```

Undine requires the `"django.contrib.contenttypes"` app to be installed,
but there is no need to place `"undine"` in any specific order in the `INSTALLED_APPS` setting.

## Configuration

Undine is configured using the `UNDINE` setting in your Django project's `settings.py` file.
Let's add a few settings to get started:

```python
UNDINE = {
    "SCHEMA": "undine.settings.example_schema",
    "GRAPHIQL_ENABLED": True,
}
```

`SCHEMA` will point to an example schema, which we'll replace with our own later.
`GRAPHIQL_ENABLED` will enable GraphiQL, which is a tool for exploring the schema on the browser.

More information on available settings can be found in the [settings](settings.md) section.

## Adding an endpoint

Next, we need to add an endpoint to Django for our GraphQL. Add the following to your `urls.py` file:

```python
from django.urls import path
from undine import GraphQLView

urlpatterns = [
    path("graphql/", GraphQLView.as_view(), name="graphql"),
]
```

This will add a `/graphql/` endpoint to your project that will serve the GraphQL schema.

Test that everything worked by starting your Django server and navigate to `/graphql/` to see GraphiQL UI.
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
    "testing": "Hello, World!"
  }
}
```

## Next steps

Now that you have a basic GraphQL server up and running, you can start adding more features to it.
Check out the [Queries](queries.md), [Mutations](mutations.md), and [Schema](schema.md) sections
to learn more about how to use Undine to build your GraphQL API.
