from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.images import ImageFile
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.db.models.fields.files import ImageFieldFile

from tests.helpers import create_png, exact
from undine.exceptions import GraphQLScalarConversionError
from undine.scalars.image import image_scalar
from undine.utils import validators


@pytest.fixture(autouse=True)
def set_image_types() -> None:
    msg = f"Did not find 'get_available_image_extensions' function in {validators.__name__!r}"
    assert hasattr(validators, "get_available_image_extensions"), msg

    path = f"{validators.__name__}.{validators.get_available_image_extensions.__qualname__}"

    with patch(path, return_value=["png"]):
        yield


@pytest.mark.parametrize("func", [image_scalar.parse, image_scalar.serialize])
def test_scalar__image__unsupported_type(func) -> None:
    msg = "'Image' cannot represent value 1.2: Type 'builtins.float' is not supported"
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        func(1.2)


def test_scalar__image__parse__uploaded_file() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/png",
        size=png.size,
    )
    file.seek(0)

    assert image_scalar.parse(file) == file


def test_scalar__image__parse__uploaded_file__no_name() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/png",
        size=png.size,
    )
    file.seek(0)

    file.name = None

    msg = "'Image' cannot represent value <UploadedFile instance>: No filename could be determined."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__parse__uploaded_file__no_extension() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/png",
        size=png.size,
    )
    file.seek(0)

    file.name = "foo"

    msg = (
        "'Image' cannot represent value <UploadedFile instance>: "
        "Filename must have two parts: the name and the extension."
    )
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__parse__uploaded_file__empty_extensions() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/png",
        size=png.size,
    )
    file.seek(0)

    file.name = "foo."

    msg = "'Image' cannot represent value <UploadedFile instance>: Filename must have an extension."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__parse__uploaded_file__empty_name() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/png",
        size=png.size,
    )
    file.seek(0)

    file.name = ".foo"

    msg = "'Image' cannot represent value <UploadedFile instance>: Filename must not be empty."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__parse__uploaded_file__unallowed_extension() -> None:
    png = create_png()

    file = UploadedFile(
        file=png,
        content_type="image/jpeg",
        size=png.size,
    )
    file.seek(0)

    file.name = "image.jpeg"

    msg = (
        "'Image' cannot represent value <UploadedFile instance>: "
        "File extension 'jpeg' is not allowed. Allowed extensions are: 'png'."
    )
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__parse__uploaded_file__not_real_image() -> None:
    file = SimpleUploadedFile(name="hello.png", content=b"content", content_type="image/png")

    msg = "'Image' cannot represent value <SimpleUploadedFile instance>: File either not an image or a corrupted image."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.parse(file)


def test_scalar__image__serialize__image_field_file() -> None:
    storage = SimpleNamespace(url=lambda name: f"https://example.com/{name}")
    file = ImageFieldFile(None, SimpleNamespace(storage=storage), "hello.png")
    assert image_scalar.serialize(file) == file.url


def test_scalar__image__serialize__image_file() -> None:
    file = ImageFile(file=io.BytesIO(), name="hello.png")
    assert image_scalar.serialize(file) == file.name


def test_scalar__image__serialize__str() -> None:
    image_scalar.serialize("https://example.com/hello.png")


def test_scalar__image__serialize__str__not_an_url() -> None:
    msg = "'Image' cannot represent value 'hello world': Enter a valid URL."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.serialize("hello world")


def test_scalar__image__serialize__str__no_file_extension() -> None:
    msg = "'Image' cannot represent value 'https://example.com/hello': Image URLs must have a file extension."
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.serialize("https://example.com/hello")


def test_scalar__image__serialize__str__unallowed_extension() -> None:
    msg = (
        "'Image' cannot represent value 'https://example.com/hello.txt': "
        "File extension 'txt' is not allowed. Allowed extensions are: 'png'."
    )
    with pytest.raises(GraphQLScalarConversionError, match=exact(msg)):
        image_scalar.serialize("https://example.com/hello.txt")
