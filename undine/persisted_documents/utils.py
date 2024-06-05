from __future__ import annotations

import hashlib
from typing import Any

from django.core.exceptions import ValidationError

from undine.exceptions import GraphQLErrorGroup, GraphQLRequestParseError, GraphQLValidationError

from .models import PersistedDocument

__all__ = [
    "parse_document_map",
    "register_persisted_documents",
    "to_document_id",
]


def to_document_id(document: str) -> str:
    payload = hashlib.sha256(document.encode("utf-8")).hexdigest()
    return f"sha256:{payload}"


def register_persisted_documents(document_map: dict[str, str]) -> dict[str, str]:
    """
    Register persisted documents.

    :param document_map: Mapping of user defined keys to GraphQL documents to persist.
    :return: Mapping where the keys are the same as given in 'document_map',
             but values have been changed to the 'document_ids' of the persisted documents.
    """
    document_id_map: dict[str, str] = {}
    docs: list[PersistedDocument] = []
    errors: list[GraphQLValidationError] = []

    for key, document in document_map.items():
        document_id = to_document_id(document)
        doc = PersistedDocument(document_id=document_id, document=document)

        try:
            doc.full_clean()
        except ValidationError as err:
            for message in err.messages:
                error = GraphQLValidationError(message, path=["documents", key])
                errors.append(error)
            continue

        docs.append(doc)
        document_id_map[key] = document_id

    if errors:
        raise GraphQLErrorGroup(errors)

    PersistedDocument.objects.bulk_create(
        docs,
        update_conflicts=True,
        update_fields=["document"],
        unique_fields=["document_id"],
    )

    return document_id_map


def parse_document_map(json_data: dict[str, Any]) -> dict[str, str]:
    documents = json_data.get("documents")
    if documents is None:
        msg = "Missing key."
        error = GraphQLRequestParseError(msg, path=["documents"])

        raise GraphQLErrorGroup([error])

    if not isinstance(documents, dict):
        msg = "Value is not a dictionary."
        error = GraphQLRequestParseError(msg, path=["documents"])

        raise GraphQLErrorGroup([error])

    errors: list[GraphQLRequestParseError] = []

    for key, value in documents.items():
        if not isinstance(value, str):
            msg = "Value is not a string."
            error = GraphQLRequestParseError(msg, path=["documents", key])
            errors.append(error)

    if errors:
        raise GraphQLErrorGroup(errors)

    return documents
