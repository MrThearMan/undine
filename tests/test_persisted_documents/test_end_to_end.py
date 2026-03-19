from __future__ import annotations

import hashlib
from typing import Generator

import pytest

from pytest_undine.client import GraphQLClientHTTPResponse
from pytest_undine.query_logging import DBQueryData
from tests.factories import PersistedDocumentFactory
from undine import Entrypoint, RootType, create_schema
from undine.persisted_documents.apps import UndinePersistedDocumentsConfig
from undine.persisted_documents.models import PersistedDocument
from undine.persisted_documents.utils import to_document_id


@pytest.fixture
def _no_persisted_documents(settings) -> Generator[None, None, None]:
    """Disable persisted documents for the duration of a test."""
    app_name = UndinePersistedDocumentsConfig.name

    try:
        index: int = settings.INSTALLED_APPS.index(app_name)
    except ValueError:
        yield
        return

    settings.INSTALLED_APPS.pop(index)
    yield
    settings.INSTALLED_APPS.insert(index, app_name)


# Persisted documents


@pytest.mark.django_db
def test_persisted_documents(graphql, undine_settings) -> None:
    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(document, use_persisted_document=True)

    assert response.has_errors is False, response.errors
    assert response.json == {"data": {"hello": "Hello World"}}


@pytest.mark.django_db
def test_persisted_documents__not_found(graphql, undine_settings) -> None:
    document = "query { hello }"
    document_id = to_document_id(document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(document, use_persisted_document=True)

    assert response.errors == [
        {
            "message": f"Persisted document '{document_id}' not found.",
            "extensions": {
                "code": "PERSISTED_DOCUMENT_NOT_FOUND",
                "error_code": "PERSISTED_DOCUMENT_NOT_FOUND",
                "status_code": 404,
            },
        }
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_persisted_documents")
def test_persisted_documents__not_supported(graphql, undine_settings) -> None:
    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(document, use_persisted_document=True)

    assert response.errors == [
        {
            "message": "Request data must contain a `query` string describing the graphql document.",
            "extensions": {
                "error_code": "MISSING_GRAPHQL_QUERY_PARAMETER",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__only__cannot_use_query(graphql, undine_settings) -> None:
    undine_settings.PERSISTED_DOCUMENTS_ONLY = True

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(document)

    assert response.errors == [
        {
            "message": "Could not find persisted document based on request data.",
            "extensions": {
                "error_code": "MISSING_GRAPHQL_DOCUMENT_PARAMETER",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("_no_persisted_documents")
def test_persisted_documents__only__not_installed(graphql, undine_settings) -> None:
    undine_settings.PERSISTED_DOCUMENTS_ONLY = True

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    response = graphql(document)

    assert response.errors == [
        {
            "message": "Server does not support persisted documents.",
            "extensions": {
                "code": "PERSISTED_QUERY_NOT_SUPPORTED",
                "error_code": "PERSISTED_DOCUMENTS_NOT_SUPPORTED",
                "status_code": 400,
            },
        }
    ]


# APQ (save)


@pytest.mark.django_db
def test_persisted_documents__apq__save(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    sha_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha_hash}}
    response = graphql(document, extensions=extensions)

    assert response.has_errors is False, response.errors
    assert response.json == {"data": {"hello": "Hello World"}}

    persisted_document = PersistedDocument.objects.get(document_id=to_document_id(document))
    assert persisted_document.document == document


@pytest.mark.django_db
def test_persisted_documents__apq__save__missing_version(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    sha_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"sha256Hash": sha_hash}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query version information is missing.",
            "extensions": {
                "error_code": "APQ_VERSION_MISSING",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__save__invalid_version(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    sha_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"version": "foo", "sha256Hash": sha_hash}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query version information is invalid.",
            "extensions": {
                "error_code": "APQ_VERSION_INVALID",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__save__unsupported_version(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    sha_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"version": 2, "sha256Hash": sha_hash}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query version 2 is not supported.",
            "extensions": {
                "error_code": "APQ_VERSION_NOT_SUPPORTED",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__save__missing_hash(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"version": 1}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query hash information is missing.",
            "extensions": {
                "error_code": "APQ_HASH_MISSING",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__save__invalid_hash(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    hashlib.sha256(document.encode("utf-8")).hexdigest()
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": 1}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query hash is invalid.",
            "extensions": {
                "error_code": "APQ_HASH_INVALID",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__save__document_does_not_match_hash(graphql, undine_settings) -> None:

    document = "query { hello }"

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    extensions = {"persistedQuery": {"version": 1, "sha256Hash": "foo"}}
    response = graphql(document, extensions=extensions)

    assert response.errors == [
        {
            "message": "Automated Persisted Query hash is invalid.",
            "extensions": {
                "error_code": "APQ_HASH_INVALID",
                "status_code": 400,
            },
        }
    ]


# APQ (use)


@pytest.mark.django_db
def test_persisted_documents__apq__use(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.has_errors is False, response.errors
    assert response.json == {"data": {"hello": "Hello World"}}


@pytest.mark.django_db
def test_persisted_documents__apq__use__missing_version(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "sha256Hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Query version information is missing.",
            "extensions": {
                "error_code": "APQ_VERSION_MISSING",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__invalid_version(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": "foo",
                "sha256Hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Query version information is invalid.",
            "extensions": {
                "error_code": "APQ_VERSION_INVALID",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__unsupported_version(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 2,
                "sha256Hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Query version 2 is not supported.",
            "extensions": {
                "error_code": "APQ_VERSION_NOT_SUPPORTED",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__missing_hash(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 1,
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Query hash information is missing.",
            "extensions": {
                "error_code": "APQ_HASH_MISSING",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__invalid_hash(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": 1,
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Query hash is invalid.",
            "extensions": {
                "error_code": "APQ_HASH_INVALID",
                "status_code": 400,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__not_found(graphql, undine_settings) -> None:

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "foo",
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Persisted document 'sha256:foo' not found.",
            "extensions": {
                "code": "PERSISTED_DOCUMENT_NOT_FOUND",
                "error_code": "PERSISTED_DOCUMENT_NOT_FOUND",
                "status_code": 404,
            },
        }
    ]


@pytest.mark.django_db
def test_persisted_documents__apq__use__not_enabled(graphql, undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = []

    document = "query { hello }"
    PersistedDocumentFactory.create(document_id=to_document_id(document), document=document)

    class Query(RootType):
        @Entrypoint
        def hello() -> str:
            return "Hello World"

    undine_settings.SCHEMA = create_schema(query=Query)

    data = {
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hashlib.sha256(document.encode("utf-8")).hexdigest(),
            },
        },
    }

    resp = graphql.post(
        path=f"/{undine_settings.GRAPHQL_PATH}",
        data=data,
        content_type="application/json",
    )
    response = GraphQLClientHTTPResponse(resp, DBQueryData(queries=[]))

    assert response.errors == [
        {
            "message": "Automated Persisted Queries are not supported.",
            "extensions": {
                "code": "PERSISTED_QUERY_NOT_SUPPORTED",
                "error_code": "APQ_NOT_SUPPORTED",
                "status_code": 400,
            },
        }
    ]
