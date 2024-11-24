import io
from types import SimpleNamespace

import pytest
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile

from tests.helpers import exact
from undine.errors.exceptions import GraphQLConversionError
from undine.scalars.file import parse_file, serialize


def test_scalar__file__parse__uploaded_file():
    file = SimpleUploadedFile(name="hello.txt", content=b"content", content_type="text/plain")
    assert parse_file(file) == file


def test_scalar__file__parse__unsupported_type():
    msg = "'File' cannot represent value 1.2: Type 'builtins.float' is not a supported input value"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        parse_file(1.2)


def test_scalar__file__serialize__field_file():
    storage = SimpleNamespace(url=lambda name: f"https://example.com/{name}")
    file = FieldFile(None, SimpleNamespace(storage=storage), "hello.txt")
    assert serialize(file) == file.url


def test_scalar__file__serialize__file():
    file = File(file=io.BytesIO(), name="hello.txt")
    assert serialize(file) == file.name


def test_scalar__file__serialize__str():
    assert serialize("https://example.com/hello.txt") == "https://example.com/hello.txt"


def test_scalar__file__serialize__str__not_an_url():
    msg = "'File' cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        serialize("hello world")


def test_scalar__file__serialize__unsupported_type():
    msg = "'File' cannot represent value 1.2: Type 'builtins.float' is not a supported output value"
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        serialize(1.2)


def test_scalar__file__serialize__no_extension():
    msg = "'File' cannot represent value 'https://www.example.com/file': File URLs must have a file extension."
    with pytest.raises(GraphQLConversionError, match=exact(msg)):
        serialize("https://www.example.com/file")
