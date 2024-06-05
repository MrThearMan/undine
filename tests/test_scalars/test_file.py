from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile

from tests.helpers import exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.file import file_scalar


@pytest.mark.parametrize("func", [file_scalar.parse, file_scalar.serialize])
def test_scalar__file__unsupported_type(func) -> None:
    msg = "'File' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__file__parse__uploaded_file() -> None:
    file = SimpleUploadedFile(name="hello.txt", content=b"content", content_type="text/plain")
    assert file_scalar.parse(file) == file


def test_scalar__file__parse__uploaded_file__no_name() -> None:
    file = SimpleUploadedFile(name=None, content=b"content", content_type="text/plain")

    msg = "'File' cannot represent value <SimpleUploadedFile instance>: No filename could be determined."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        assert file_scalar.parse(file) == file


def test_scalar__file__serialize__field_file() -> None:
    storage = SimpleNamespace(url=lambda name: f"https://example.com/{name}")
    file = FieldFile(None, SimpleNamespace(storage=storage), "hello.txt")
    assert file_scalar.serialize(file) == file.url


def test_scalar__file__serialize__file() -> None:
    file = File(file=io.BytesIO(), name="hello.txt")
    assert file_scalar.serialize(file) == file.name


def test_scalar__file__serialize__file__no_name() -> None:
    file = File(file=io.BytesIO())
    assert file_scalar.serialize(file) == ""


def test_scalar__file__serialize__str() -> None:
    assert file_scalar.serialize("https://example.com/hello.txt") == "https://example.com/hello.txt"


def test_scalar__file__serialize__str__not_an_url() -> None:
    msg = "'File' cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        file_scalar.serialize("hello world")


def test_scalar__file__serialize__str__no_extension() -> None:
    msg = "'File' cannot represent value 'https://www.example.com/file': File URLs must have a file extension."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        file_scalar.serialize("https://www.example.com/file")
