# Getting Started

## New to GraphQL?

If you are new to GraphQL, we recommend reading the [official GraphQL docs](https://graphql.org/learn/)
first to get a better understanding of what GraphQL is and how it works. Undine's documentation will
assume you know the basic concepts of GraphQL (types, query syntax, fields, arguments, resolvers, etc.),
and focuses on how these concepts can be implemented with Undine.

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
Let's add a settings to enable GraphiQL, a tool for exploring our GraphQL schema on the browser.

```python
UNDINE = {
    "GRAPHIQL_ENABLED": True,
}
```

More information on available settings can be found in the [settings](settings.md) section.

## Adding an endpoint

Next, we need to add an endpoint for our GraphQL schema. Add the following to your `urls.py` file:

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

Now that we have a basic GraphQL server up and running, we can start to add more features to it.
Check out the [Schema](schema.md), [Queries](queries.md), and [Mutations](mutations.md)  sections
to learn more about how to use Undine to build your GraphQL API.
