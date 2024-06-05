from __future__ import annotations

from factory import LazyAttribute

from undine.persisted_documents.models import PersistedDocument
from undine.persisted_documents.utils import to_document_id

from ._base import GenericDjangoModelFactory

__all__ = [
    "PersistedDocumentFactory",
]


class PersistedDocumentFactory(GenericDjangoModelFactory[PersistedDocument]):
    class Meta:
        model = PersistedDocument

    document_id = LazyAttribute(lambda obj: to_document_id(obj.document))
    document = "query { testing }"
