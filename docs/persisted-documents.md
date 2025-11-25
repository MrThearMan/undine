description: Documentation on persisted documents in Undine.

# Persisted Documents

In this section, we'll cover Undine's support for [persisted documents]{:target="_blank"},
which offer a way to persist known GraphQL documents on the server for caching, reducing network traffic,
or to use as an operation allow-list.

[persisted documents]: https://github.com/graphql/graphql-over-http/blob/persisted-documents-get-url/spec/Appendix%20A%20--%20Persisted%20Documents.md

## Installation

To enable persisted documents, you must first add the `undine.persisted_documents` app to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "undine",
    "undine.persisted_documents",
    # ...
]
```

Then, add the persisted document registration view to your URLconf:

```python hl_lines="5"
-8<- "persisted_documents/urls.py"
```

Before running migrations, you should have a look at the `PersistedDocument` Model
in `undine.persisted_documents.model`. This Model can be swapped out with your own
implementation using the [`UNDINE_PERSISTED_DOCUMENTS_MODEL`](settings.md#undine_persisted_documents_model)
setting, similar to how the `User` model can be swapped out with [`AUTH_USER_MODEL`][AUTH_USER_MODEL]{:target="_blank"}.
Whether you decide to do this or not, remember to run migrations afterwards.

[AUTH_USER_MODEL]: https://docs.djangoproject.com/en/stable/topics/auth/customizing/#substituting-a-custom-user-model

## Usage

Once the app is installed, Undine is ready to accept persisted documents.
Persisted documents work though the same GraphQL endpoint used for regular GraphQL requests,
but instead of a `query` string, you must provide a `documentId` instead.

```json
{
  "documentId": "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d",
  "variables": {}
}
```

A `documentId` can be obtained by registering a new persisted document using the persisted document
registration view, as specified by the [`PERSISTED_DOCUMENTS_PATH`](settings.md#persisted_documents_path)
setting. The view accepts a dictionary of `documents` like this

```json
{
  "documents": {
    "foo": "query { example }",
    "bar": "query { testing }"
  }
}
```

...and returns a dictionary of `documentIds` like this

```json
{
  "data": {
    "documents": {
      "foo": "sha256:1ce1ad479d1905f8d89262a1bccb87b9b4fe6b85161cd8cecb00b87d21d8889f",
      "bar": "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d"
    }
  }
}
```

...where each key in the `documents` dictionary is defined by the user,
so that a `documentId` corresponding to a `query` is returned in the same key.
The keys are not used for anything else.
Response for this view follows the [GraphQL response format],
so any errors are returned in the _"errors"_ key.

[GraphQL response format]: https://spec.graphql.org/draft/#sec-Response-Format.Response

> Note that a document with the same selection set produces a different `documentId`
> if they have different whitespace, newlines, or comments. This is to ensure that
> error locations stay consistent.

## Permissions

You'll likely want to protect the persisted documents registration view with a permission check
so that only some users can register new persisted documents. This can be done by setting the
[`PERSISTED_DOCUMENTS_PERMISSION_CALLBACK`](settings.md#persisted_documents_permission_callback)
setting to a function that accepts a `request` and a `document_map` as arguments.

```python
-8<- "persisted_documents/persisted_documents_permissions.py"
```

## Allow-list mode

Persisted documents can be used to create an allow-list for GraphQL operations.
Usually this is done to enhance security of a system by preventing
malicious queries from being executed. Undine can be configured to only accept
persisted documents by setting the [`PERSISTED_DOCUMENTS_ONLY`](settings.md#persisted_documents_only)
setting to `True`.

```python
UNDINE = {
    "PERSISTED_DOCUMENTS_ONLY": True,
}
```

When operating in this mode, your clients should call `PersistedDocumentsView`
during build time to register their queries and mutations.
