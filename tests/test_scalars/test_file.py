import re
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile

from undine.errors import GraphQLConversionError
from undine.scalars.file import parse_file, serialize


def test_scalar__file__parse__uploaded_file():
    file = SimpleUploadedFile(name="hello.txt", content=b"content", content_type="text/plain")
    assert parse_file(file) == file


def test_scalar__file__parse__unsupported_type():
    msg = "File cannot represent value 1.2: Type 'builtins.float' is not a supported input value"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_file(1.2)


def test_scalar__file__serialize__field_file():
    storage = SimpleNamespace(url=lambda name: f"https://example.com/{name}")
    file = FieldFile(None, SimpleNamespace(storage=storage), "hello.txt")
    assert serialize(file) == file.url


def test_scalar__file__serialize__str():
    assert serialize("https://example.com/hello.txt") == "https://example.com/hello.txt"


def test_scalar__file__serialize__str__not_an_url():
    msg = "File cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        serialize("hello world")


def test_scalar__file__serialize__unsupported_type():
    msg = "File cannot represent value 1.2: Type 'builtins.float' is not a supported output value"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        serialize(1.2)
