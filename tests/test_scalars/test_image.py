from __future__ import annotations

import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile

from undine.errors import GraphQLConversionError
from undine.scalars.image import parse_image, serialize


@pytest.fixture(autouse=True)
def set_image_types():
    with patch("undine.validation.get_available_image_extensions", return_value=["png"]):
        yield


def test_scalar__image__parse__uploaded_file():
    file = SimpleUploadedFile(name="hello.png", content=b"content", content_type="image/png")
    assert parse_image(file) == file


def test_scalar__image__parse__unsupported_type():
    msg = "Image cannot represent value 1.2: Type 'builtins.float' is not a supported input value"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        parse_image(1.2)


def test_scalar__image__serialize__image_field_file():
    storage = SimpleNamespace(url=lambda name: f"https://example.com/{name}")
    file = ImageFieldFile(None, SimpleNamespace(storage=storage), "hello.png")
    assert serialize(file) == file.url


def test_scalar__image__serialize__str():
    serialize("https://example.com/hello.png")


def test_scalar__image__serialize__str__not_an_url():
    msg = "Image cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        serialize("hello world")


def test_scalar__image__serialize__str__unallowed_extension():
    msg = (
        "Image cannot represent value 'https://example.com/hello.txt': "
        "File extension 'txt' is not allowed. Allowed extensions are: 'png'."
    )
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        serialize("https://example.com/hello.txt")


def test_scalar__image__serialize__unsupported_type():
    msg = "Image cannot represent value 1.2: Type 'builtins.float' is not a supported output value"
    with pytest.raises(GraphQLConversionError, match=re.escape(msg)):
        serialize(1.2)
