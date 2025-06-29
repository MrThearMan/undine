# Integrations

In this section, we'll cover the integrations to other libraries that
Undine includes.

## channels

```
pip install undine[channels]
```

Undine provides support for the [GraphQL over WebSocket]{:target="_blank"} protocol
by integrating with [channels]{:target="_blank"} library. Using the channels integration
requires turning on Undine's [Async Support](async.md).

[channels]: https://github.com/django/channels
[GraphQL over WebSocket]: https://github.com/graphql/graphql-over-http/blob/main/rfcs/GraphQLOverWebSocket.md

Additionally, you need to configure the Django in `asgi.py` so that
websocket requests are sent to Undine's channels consumer.

```python
-8<- "integrations/channels.py"
```

This will add a new route to the Django application that will handle
the WebSocket requests. The path for this route is defined using the
[`WEBSOCKET_PATH`](settings.md#websocket_path) setting.

## django-debug-toolbar

```
pip install undine[debug]
```

Undine integrates with [django-debug-toolbar]{:target="_blank"}
by modifying the debug toolbar so that it works with [GraphiQL].
After [installing the debug toolbar], Undine should automatically
patch the toolbar without any additional configuration.

[django-debug-toolbar]: https://github.com/django-commons/django-debug-toolbar
[GraphiQL]: https://github.com/graphql/graphiql
[installing the debug toolbar]: https://django-debug-toolbar.readthedocs.io/en/stable/installation.html

## django-modeltranslation

Undine integrates with [django-modeltranslation]{:target="_blank"}
by allowing you to modify how auto-generated `Fields`, `Inputs`, `Filters`
and `Orders` are created. Specifically, this happens using two settings:
`MODELTRANSLATION_INCLUDE_TRANSLATABLE` and `MODELTRANSLATION_INCLUDE_TRANSLATIONS`.

[django-modeltranslation]: https://github.com/deschler/django-modeltranslation

Let's say you the following model and translation options:

```python
-8<- "integrations/model_translation.py"
```

As noted in the example, due to the way that `django-modeltranslation` works,
your models will get additional fields for each language you have defined.
We'll call the fields for which the translations are created _"translatable"_ fields,
and the fields that are created for each language _"translation"_ fields.

Using the `MODELTRANSLATION_INCLUDE_TRANSLATABLE` and `MODELTRANSLATION_INCLUDE_TRANSLATIONS`
settings, you can control which of these fields undine will add to your schema
using auto-generation. By default, only the translation fields are added.
You can of course always add the translatable fields manually.

> Note that due to the way that `django-modeltranslation` works,
> the translation fields are always nullable, even for the default language.

## pytest

Undine comes with a pytest plugin that includes a testing client and few fixtures
to help you write tests for your GraphQL APIs.

The `GraphQLClient` class is wrapper around Django's test client that
makes testing your GraphQL API easier. It can be added to a test using
the `graphql` fixture. Here is a simple example:

```python
-8<- "integrations/graphql_test_client.py"
```

GraphQL requests can be made by calling the client as shown above.
This makes a request to the GraphQL endpoint set by the `GRAPHQL_PATH` setting.

GraphQL variables can be passed using the `variables` argument. If these variables
include any files, the client will automatically create a GraphQL multipart request
instead of a normal GraphQL request.

The client returns a custom response object `GraphQLClientResponse`,
which has a number of useful properties for introspecting the response.
The response object also has details on the database queries that were executed
during the request, which can be useful for debugging the performance of your
GraphQL API.

The plugin also includes a `undine_settings` fixture that allows modifying
Undine's settings during testing more easily.

If the [channels](#channels) integration is installed, the test client can
also send GraphQL over WebSocket requests using the `over_websocket` method.

```python
-8<- "integrations/graphql_test_client_over_websocket.py"
```
