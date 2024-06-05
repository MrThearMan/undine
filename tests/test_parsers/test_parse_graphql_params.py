from __future__ import annotations

import urllib.parse
from typing import Generator

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import QueryDict

from tests.factories import PersistedDocumentFactory
from tests.helpers import MockRequest, create_graphql_multipart_spec_request, create_multipart_form_data_request, exact
from undine.dataclasses import GraphQLHttpParams
from undine.exceptions import (
    GraphQLMissingContentTypeError,
    GraphQLMissingDocumentIDError,
    GraphQLMissingFileMapError,
    GraphQLMissingOperationsError,
    GraphQLMissingQueryAndDocumentIDError,
    GraphQLMissingQueryError,
    GraphQLPersistedDocumentNotFoundError,
    GraphQLRequestDecodingError,
    GraphQLStatusError,
)
from undine.parsers import GraphQLRequestParamsParser
from undine.persisted_documents.apps import UndinePersistedDocumentsConfig


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


def test_parse_graphql_params__get_request() -> None:
    data = {
        "query": "query MyQuery { hello }",
        "variables": "{}",
        "operationName": "MyQuery",
        "extensions": "{}",
    }
    query = urllib.parse.urlencode(data, quote_via=urllib.parse.quote)

    request = MockRequest(
        method="GET",
        GET=QueryDict(query, encoding="utf-8"),
    )

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name == "MyQuery"
    assert params.extensions == {}


def test_parse_graphql_params__no_content_type_header() -> None:
    data = {
        "query": "query MyQuery { hello }",
        "variables": "{}",
    }
    query = urllib.parse.urlencode(data, quote_via=urllib.parse.quote)

    request = MockRequest(
        method="POST",
        GET=QueryDict(query, encoding="utf-8"),
        content_type=None,
    )

    with pytest.raises(GraphQLMissingContentTypeError):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"query": "query MyQuery { hello }", "variables": {}}',
    )

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


def test_parse_graphql_params__json_content__decode_error() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b"\xd3\x01Z\x05\xce\x18i\xaa\xadA\xfe)\\\xcc\xf7C",
    )

    msg = "Could not decode body with encoding 'utf-8'."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content__not_json() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"query": query MyQuery { hello }',
    )

    msg = "Could not load JSON body."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__json_content__not_dict() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'[{"query": "query MyQuery { hello }"}]',
    )

    msg = "JSON body should convert to a dictionary."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__graphql_content() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/graphql",
        body=b"query MyQuery { hello }",
    )

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


def test_parse_graphql_params__form_urlencoded_content() -> None:
    data = {
        "query": "query MyQuery { hello }",
        "variables": "{}",
    }
    query = urllib.parse.urlencode(data, quote_via=urllib.parse.quote)

    request = MockRequest(
        method="POST",
        content_type="application/x-www-form-urlencoded",
        POST=QueryDict(query, encoding="utf-8"),
    )

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


def test_parse_graphql_params__multipart_content() -> None:
    data: dict[str, str | bytes] = {
        "query": "query MyQuery { hello }",
        "variables": "{}",
    }
    request = create_multipart_form_data_request(data=data)

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


def test_parse_graphql_params__multipart_content__file_upload() -> None:
    request = create_graphql_multipart_spec_request()

    params = GraphQLRequestParamsParser.run(request)

    assert isinstance(params, GraphQLHttpParams)
    assert params.document == "mutation($file: File!) { files(files: $file) { id } }"
    assert params.variables is not None
    assert list(params.variables.keys()) == ["file"]
    assert isinstance(params.variables["file"], InMemoryUploadedFile)
    assert params.operation_name is None
    assert params.extensions == {}


def test_parse_graphql_params__multipart_content__file_upload__missing_operations() -> None:
    request = create_graphql_multipart_spec_request(operations=None)

    with pytest.raises(GraphQLMissingOperationsError):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__operations_not_a_mapping() -> None:
    request = create_graphql_multipart_spec_request(operations="hello world")

    msg = "The `operations` value is not a mapping."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__missing_map() -> None:
    request = create_graphql_multipart_spec_request(operations_map=None)

    with pytest.raises(GraphQLMissingFileMapError):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__map_not_a_mapping() -> None:
    request = create_graphql_multipart_spec_request(operations_map="hello world")

    msg = "The `map` value is not a mapping."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__multipart_content__file_upload__values_must_be_a_list() -> None:
    request = create_graphql_multipart_spec_request(operations_map={"0": "variables.file"})

    msg = "The `map` value is not a mapping from string to list of strings."
    with pytest.raises(GraphQLRequestDecodingError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


def test_parse_graphql_params__unsupported_content() -> None:
    request = MockRequest(
        method="POST",
        content_type="text/plain",
    )

    msg = "'text/plain' is not a supported content type."
    with pytest.raises(GraphQLStatusError, match=exact(msg)):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.usefixtures("_no_persisted_documents")
def test_parse_graphql_params__mising_query() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"variables": {}}',
    )

    with pytest.raises(GraphQLMissingQueryError):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.usefixtures("_no_persisted_documents")
def test_parse_graphql_params__null_query() -> None:
    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"query": null, "variables": {}}',
    )

    with pytest.raises(GraphQLMissingQueryError):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.django_db
def test_parse_graphql_params__mising_query__has_document() -> None:
    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"documentId": "1", "variables": {}}',
    )

    params = GraphQLRequestParamsParser.run(request)

    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


@pytest.mark.django_db
def test_parse_graphql_params__mising_query__no_document_id() -> None:
    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"variables": {}}',
    )

    with pytest.raises(GraphQLMissingQueryAndDocumentIDError):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.django_db
def test_parse_graphql_params__mising_query__no_document_matching_id() -> None:
    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"documentId": "2", "variables": {}}',
    )

    with pytest.raises(GraphQLPersistedDocumentNotFoundError):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.django_db
def test_parse_graphql_params__persisted_documents_only__no_document_id(undine_settings) -> None:
    undine_settings.PERSISTED_DOCUMENTS_ONLY = True

    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"variables": {}}',
    )

    with pytest.raises(GraphQLMissingDocumentIDError):
        GraphQLRequestParamsParser.run(request)


@pytest.mark.django_db
def test_parse_graphql_params__persisted_documents_only__query_ignored(undine_settings) -> None:
    undine_settings.PERSISTED_DOCUMENTS_ONLY = True

    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"query": "query OtherQuery { hello }", "documentId": "1", "variables": {}}',
    )

    params = GraphQLRequestParamsParser.run(request)

    assert params.document == "query MyQuery { hello }"
    assert params.variables == {}
    assert params.operation_name is None
    assert params.extensions == {}


@pytest.mark.django_db
def test_parse_graphql_params__persisted_documents_only__query_ignored__no_document_id(undine_settings) -> None:
    undine_settings.PERSISTED_DOCUMENTS_ONLY = True

    PersistedDocumentFactory.create(document_id="1", document="query MyQuery { hello }")

    request = MockRequest(
        method="POST",
        content_type="application/json",
        body=b'{"query": "query OtherQuery { hello }", "variables": {}}',
    )

    with pytest.raises(GraphQLMissingDocumentIDError):
        GraphQLRequestParamsParser.run(request)
