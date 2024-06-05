from __future__ import annotations

from inspect import cleandoc

import pytest
from graphql import GraphQLError

from undine.exceptions import GraphQLErrorGroup
from undine.persisted_documents.utils import register_persisted_documents, to_document_id
from undine.settings import example_schema


def test_query_to_document_id() -> None:
    document = """
        query {
          testing
        }
    """

    assert to_document_id(document) == "sha256:02a08cd258029e862a2a3120d4afe4b1eadc83a60dc271e6eb0b1a55a22cbbbb"


def test_query_to_document_id__same_document() -> None:
    document = """
        query {
          testing
        }
    """

    assert to_document_id(document) == to_document_id(document)


def test_query_to_document_id__different_spacing() -> None:
    document_1 = """
        query {
          testing
        }
    """

    document_2 = """query { testing }"""

    assert to_document_id(document_1) != to_document_id(document_2)


@pytest.mark.django_db
def test_register_persisted_document(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data = {
        "foo": cleandoc(
            """
            query {
              testing
            }
            """
        ),
    }

    doc = register_persisted_documents(data)

    assert doc == {
        "foo": "sha256:1ef24f421322adf6bfa56f9b736d0da74426faff33e985e9b254c074d0438f04",
    }


@pytest.mark.django_db
def test_register_persisted_document__invalid_query__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data = {
        "foo": cleandoc(
            """
            query {
              foo
            }
            """
        ),
    }

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        register_persisted_documents(data)

    exceptions: list[GraphQLError] = exc_info.value.exceptions  # type: ignore[assignment]
    assert len(exceptions) == 1

    assert exceptions[0].message == "Cannot query field 'foo' on type 'Query'."
    assert exceptions[0].path == ["documents", "foo"]


@pytest.mark.django_db
def test_register_persisted_document__invalid_query__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data = {
        "foo": cleandoc(
            """
            query {
              foo
            """
        ),
    }

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        register_persisted_documents(data)

    exceptions: list[GraphQLError] = exc_info.value.exceptions  # type: ignore[assignment]
    assert len(exceptions) == 1

    assert exceptions[0].message == "Syntax Error: Expected Name, found <EOF>."
    assert exceptions[0].path == ["documents", "foo"]


@pytest.mark.django_db
def test_register_persisted_document__invalid_query__multiple_errors(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    data = {
        "foo": cleandoc(
            """
            query {
              foo
            }
            """
        ),
        "bar": cleandoc(
            """
            query {
              foo
            """
        ),
    }

    with pytest.raises(GraphQLErrorGroup) as exc_info:
        register_persisted_documents(data)

    exceptions: list[GraphQLError] = exc_info.value.exceptions  # type: ignore[assignment]
    assert len(exceptions) == 2

    assert exceptions[0].message == "Cannot query field 'foo' on type 'Query'."
    assert exceptions[0].path == ["documents", "foo"]

    assert exceptions[1].message == "Syntax Error: Expected Name, found <EOF>."
    assert exceptions[1].path == ["documents", "bar"]
