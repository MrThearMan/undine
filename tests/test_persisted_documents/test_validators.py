from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from hypothesis import given, strategies

from tests.helpers import exact
from undine.persisted_documents.validators import VALID_CHARS, validate_document, validate_document_id
from undine.settings import example_schema


@given(strategies.text(VALID_CHARS))
def test_validate_document_id__valid(value: str) -> None:
    validate_document_id(value)


def test_validate_document_id__invalid__not_a_string() -> None:
    msg = "['Document ID must be a string']"

    with pytest.raises(ValidationError, match=exact(msg)):
        validate_document_id(1)


def test_validate_document_id__invalid__invalid_chars() -> None:
    msg = "['Document ID contains invalid characters: = @']"

    with pytest.raises(ValidationError, match=exact(msg)):
        validate_document_id("@Document=ID")


def test_validate_document__valid(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = """
        query {
          testing
        }
    """

    validate_document(document)


def test_validate_document__invalid__not_a_string(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    with pytest.raises(ValidationError) as exec_info:
        validate_document(1)

    assert exec_info.value.messages == ["Document must be a string"]


def test_validate_document__invalid__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = """
        query {
          foo
        }
    """

    with pytest.raises(ValidationError) as exec_info:
        validate_document(document)

    assert exec_info.value.messages == ["Cannot query field 'foo' on type 'Query'."]


def test_validate_document__invalid__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = """
        query {
          foo
    """

    with pytest.raises(ValidationError) as exec_info:
        validate_document(document)

    assert exec_info.value.messages == ["Syntax Error: Expected Name, found <EOF>."]
