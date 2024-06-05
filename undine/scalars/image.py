from __future__ import annotations

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import ImageFieldFile

from undine.utils.validators import validate_image_upload, validate_image_url

from ._definition import ScalarType

__all__ = [
    "GraphQLImage",
    "image_scalar",
]


image_scalar: ScalarType[UploadedFile, str] = ScalarType(
    name="Image",
    description="Represents an image file.",
)

GraphQLImage = image_scalar.as_graphql_scalar()


@image_scalar.parse.register
def _(value: UploadedFile) -> UploadedFile:
    validate_image_upload(value)
    return value


@image_scalar.serialize.register
def _(value: ImageFieldFile) -> str:
    return value.url


@image_scalar.serialize.register
def _(value: File) -> str:
    return value.name or ""


@image_scalar.serialize.register
def _(value: str) -> str:
    validate_image_url(value)
    return value
