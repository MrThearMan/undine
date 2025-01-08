# Getting Started

## New to GraphQL?

We recommend reading the [official GraphQL docs](https://graphql.org/learn/)
first to get a better understanding of what GraphQL is and how it works, and use the
[GraphQL spec](https://spec.graphql.org/) as a reference when necessary.

## New to Django?

We recommend going though the [official Django tutorial](https://docs.djangoproject.com/en/5.2/intro/)
first before diving into Undine, since we'll assume you have some familiarity with Django.

## New to Undine?

After going thought the [installation steps](#installation) below, we have a
[tutorial](tutorial.md) that will walk you through creating a simple GraphQL server using Undine.

## Installation

Undine is available on PyPI and can be installed with `pip`:

```shell
pip install undine
```

Next, you'll need to add Undine it to your `INSTALLED_APPS` setting in your
Django project's `settings.py` file:

```python
INSTALLED_APPS = [
    "undine",
]
```

Undine requires the `"django.contrib.contenttypes"` app to be installed,
but there is no need to place `"undine"` in any specific order in the `INSTALLED_APPS` setting.
