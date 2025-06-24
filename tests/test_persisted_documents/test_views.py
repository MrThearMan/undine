from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from undine.settings import example_schema


@pytest.mark.django_db
def test_register_persisted_documents_view(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "documents": {
            "foo": "query { testing }",
        },
    }

    response = client.post(path=url, data=data, content_type="application/json")

    assert response.status_code == 200, response.content
    assert response.json() == {
        "data": {
            "documents": {
                "foo": "sha256:75d3580309f2b2bbe92cecc1ff4faf7533e038f565895c8eef25dc23e6491b8d",
            }
        }
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__doesnt_accept_json(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "documents": {
            "foo": "query { testing }",
        },
    }

    response = client.post(path=url, data=data, content_type="application/json", headers={"Accept": "text/plain"})

    assert response.status_code == 406, response.content
    assert response.content.decode() == "Server does not support any of the requested content types."


@pytest.mark.django_db
def test_register_persisted_documents_view__doesnt_have_json(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    response = client.post(path=url, data="data", content_type="text/plain")

    assert response.status_code == 415, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "'text/plain' is not a supported content type.",
                "extensions": {
                    "error_code": "UNSUPPORTED_CONTENT_TYPE",
                    "status_code": 415,
                },
            }
        ],
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__REQUEST_DECODING_ERROR(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    response = client.post(path=url, data="data", content_type="application/json")

    assert response.status_code == 400, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Could not load JSON body.",
                "extensions": {
                    "error_code": "REQUEST_DECODING_ERROR",
                    "status_code": 400,
                },
            }
        ],
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__documents_not_found(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "document": "query { testing }",
    }

    response = client.post(path=url, data=data, content_type="application/json")

    assert response.status_code == 400, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Missing key.",
                "path": ["documents"],
                "extensions": {
                    "error_code": "REQUEST_PARSE_ERROR",
                    "status_code": 400,
                },
            }
        ],
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__documents_not_dict(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "documents": "query { testing }",
    }

    response = client.post(path=url, data=data, content_type="application/json")

    assert response.status_code == 400, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Value is not a dictionary.",
                "path": ["documents"],
                "extensions": {
                    "error_code": "REQUEST_PARSE_ERROR",
                    "status_code": 400,
                },
            }
        ],
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__documents_not_dict_of_strings(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "documents": {
            "a": 1,
            "b": 2,
        },
    }

    response = client.post(path=url, data=data, content_type="application/json")

    assert response.status_code == 400, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Value is not a string.",
                "path": ["documents", "a"],
                "extensions": {
                    "error_code": "REQUEST_PARSE_ERROR",
                    "status_code": 400,
                },
            },
            {
                "message": "Value is not a string.",
                "path": ["documents", "b"],
                "extensions": {
                    "error_code": "REQUEST_PARSE_ERROR",
                    "status_code": 400,
                },
            },
        ],
    }


@pytest.mark.django_db
def test_register_persisted_documents_view__errors_in_document(client: Client, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    url = f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"

    data = {
        "documents": {
            "foo": "query { testing",
        },
    }

    response = client.post(path=url, data=data, content_type="application/json")

    assert response.status_code == 400, response.content
    assert response.json() == {
        "data": None,
        "errors": [
            {
                "message": "Syntax Error: Expected Name, found <EOF>.",
                "path": ["documents", "foo"],
                "extensions": {
                    "error_code": "VALIDATION_ERROR",
                    "status_code": 400,
                },
            }
        ],
    }


def test_register_persisted_documents_view__reverse(undine_settings) -> None:
    path = reverse(f"undine.persisted_documents:{undine_settings.PERSISTED_DOCUMENTS_VIEW_NAME}")
    assert path == f"/{undine_settings.PERSISTED_DOCUMENTS_PATH}"
