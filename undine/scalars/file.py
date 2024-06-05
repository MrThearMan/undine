from __future__ import annotations

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import FieldFile

from undine.utils.validators import validate_file_upload, validate_file_url

from ._definition import ScalarType

__all__ = [
    "GraphQLFile",
    "file_scalar",
]


file_scalar: ScalarType[UploadedFile, str] = ScalarType(
    name="File",
    description="Represents any kind of file.",
)

GraphQLFile = file_scalar.as_graphql_scalar()


@file_scalar.parse.register
def _(value: UploadedFile) -> UploadedFile:
    validate_file_upload(value)
    return value


@file_scalar.serialize.register
def _(value: FieldFile) -> str:
    return value.url


@file_scalar.serialize.register
def _(value: File) -> str:
    return value.name or ""


@file_scalar.serialize.register
def _(value: str) -> str:
    validate_file_url(value)
    return value
