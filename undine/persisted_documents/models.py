from __future__ import annotations

from django.db.models import CharField, DateTimeField, Model, TextField

from .validators import validate_document, validate_document_id

__all__ = [
    "PersistedDocument",
    "PersistedDocumentBase",
]


class PersistedDocumentBase(Model):
    """Persisted document base class."""

    document_id = CharField(max_length=255, primary_key=True, validators=[validate_document_id])
    document = TextField(validators=[validate_document])
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        verbose_name = "persisted document"
        verbose_name_plural = "persisted documents"

    def __str__(self) -> str:
        return f"Persisted document '{self.document_id}'"


class PersistedDocument(PersistedDocumentBase):
    """Persisted document."""

    class Meta(PersistedDocumentBase.Meta):
        swappable = "UNDINE_PERSISTED_DOCUMENTS_MODEL"
