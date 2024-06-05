from __future__ import annotations

from django.apps import AppConfig


class UndinePersistedDocumentsConfig(AppConfig):
    """
    Add persisted documents to Undine as defined by the GraphQL over HTTP spec.
    See: https://github.com/graphql/graphql-over-http/blob/persisted-documents-get-url/spec/Appendix%20A%20--%20Persisted%20Documents.md
    """

    name = "undine.persisted_documents"
    label = "persisted_documents"
    verbose_name = "persisted documents"
    default_auto_field = "django.db.models.BigAutoField"
