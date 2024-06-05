# Persisted Documents

In this section, we'll cover Undine's support for [persisted documents]{:target="_blank"}
— a way to persist known GraphQL documents on the server for caching, reducing network traffic,
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

Before running migrations, you should have a look at the `PersistedDocument` model
in `undine.persisted_documents.model`. This model can be swapped out with your own
implementation using the `UNDINE_PERSISTED_DOCUMENTS_MODEL` setting, similar to
how the `User` model can be swapped out with `AUTH_USER_MODEL`. Whether you decide to
do this or not, remember to run migrations afterwards.

## Usage

Once the app is installed, Undine is ready to accept persisted documents.
This can be done from the same GraphQL endpoint used for regular GraphQL requests
by providing a `documentId` instead of a `query` string.

```json
{
  "documentId": "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d",
  "variables": {}
}
```

A `documentId` can be obtained by registering a persisted document using the
`PersistedDocument` model. This can be using the `PersistedDocumentsView` view
provided by the app, but do note that it should be extended to add permission checks!

```python
-8<- "persisted_documents/view.py"
```

The view accepts a dictionary of `documents` like this:

```json
{
  "documents": {
    "foo": "query { example }",
    "bar": "query { testing }"
  }
}
```

...and returns a dictionary of `documentIds` like this:

```json
{
  "documents": {
    "foo": "sha256:1ce1ad479d1905f8d89262a1bccb87b9b4fe6b85161cd8cecb00b87d21d8889f",
    "bar": "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d"
  }
}
```

...where each key in the `documents` dictionary is defined by the user,
so that the corresponding `documentId` is returned in in the same key.
The keys are not used for anything else.

Note that a document with the same selection set produces a different `documentId`
if they have different whitespace, newlines, or comments. This is to ensure that
error locations stay consistent.

## Allow-list mode

As mentioned, persisted documents can be used to create an allow-list for GraphQL
operations. Usually this is done to enhance security of a system by preventing
malicious queries from being executed. Undine can be configured to only accept
persisted documents by setting the `PERSISTED_DOCUMENTS_ONLY` setting to `True`.

```python
UNDINE = {
    "PERSISTED_DOCUMENTS_ONLY": True,
}
```

When operating in this mode, your clients should call `PersistedDocumentsView`
during build time to register their queries and mutations.
