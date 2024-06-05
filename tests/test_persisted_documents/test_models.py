from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from tests.factories import PersistedDocumentFactory
from undine.settings import example_schema


@pytest.mark.django_db
def test_persisted_document(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    persisted_doc = PersistedDocumentFactory.create()

    persisted_doc.full_clean()

    assert persisted_doc.document_id == "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d"
    assert persisted_doc.document == "query { testing }"
    assert persisted_doc.created_at is not None


@pytest.mark.django_db
def test_persisted_document__invalid_document(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    persisted_doc = PersistedDocumentFactory.create(document="query { foo }")

    with pytest.raises(ValidationError) as exc_info:
        persisted_doc.full_clean()

    error: ValidationError = exc_info.value
    assert error.messages == ["Cannot query field 'foo' on type 'Query'."]


@pytest.mark.django_db
def test_persisted_document__invalid_document_id(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    persisted_doc = PersistedDocumentFactory.create(document_id="@Document=ID")

    with pytest.raises(ValidationError) as exc_info:
        persisted_doc.full_clean()

    error: ValidationError = exc_info.value
    assert error.messages == ["Document ID contains invalid characters: = @"]
