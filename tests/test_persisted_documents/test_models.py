from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from tests.factories import PersistedDocumentFactory
from undine.persisted_documents.admin import PersistedDocumentAdmin
from undine.persisted_documents.models import PersistedDocument
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


@pytest.mark.django_db
def test_persisted_document__str(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    doc = PersistedDocumentFactory.create()
    assert str(doc) == f"Persisted document '{doc.document_id}'"


@pytest.mark.django_db
def test_persisted_document_admin__permissions(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    factory = RequestFactory()
    request = factory.get("/admin/")
    request.user = AnonymousUser()

    admin_instance = PersistedDocumentAdmin(PersistedDocument, None)

    assert admin_instance.has_add_permission(request) is False
    assert admin_instance.has_change_permission(request) is False
    assert admin_instance.has_delete_permission(request) is False
