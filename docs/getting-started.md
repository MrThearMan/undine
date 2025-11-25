description: Getting started with Undine.

# Getting Started

## New to GraphQL?

It's recommended to read the [official GraphQL docs]{:target="_blank"}
first to get a better understanding of what GraphQL is and how it works, and use the
[GraphQL spec]{:target="_blank"} as a reference when necessary.

[official GraphQL docs]: https://graphql.org/learn/
[GraphQL spec]: https://spec.graphql.org/

## New to Django?

It's recommended to go through the [official Django tutorial]{:target="_blank"}
first before trying to learn Undine, since these docs assume you have some familiarity with Django.

[official Django tutorial]: https://docs.djangoproject.com/en/stable/intro/

## New to Undine?

After going through the [installation steps](#installation) below, we have a
[tutorial](tutorial.md) that will walk you through creating a simple GraphQL server using Undine.

Undine is built on top of [graphql-core]{:target="_blank"},
which is port of the [GraphQL.js] reference implementation of GraphQL. Knowing how graphql-core
works can help you understand how Undine works, but is not required to get started.

[graphql-core]: https://github.com/graphql-python/graphql-core
[GraphQL.js]: https://github.com/graphql/graphql-js

## Installation

Undine is available on PyPI and can be installed with `pip`:

```shell
pip install undine
```

Next, you'll need to add Undine it to your `INSTALLED_APPS` setting in your
Django project's `settings.py` file:

```python
INSTALLED_APPS = [
    # ...
    "undine",
]
```

To test that Undine is working, you can run the following command:

```shell
python manage.py check undine
```

You should see the message _"System check identified no issues (0 silenced)."_

Undine requires the `"django.contrib.contenttypes"` app to be installed,
but there is no need to place `"undine"` in any specific order in the `INSTALLED_APPS` setting.
