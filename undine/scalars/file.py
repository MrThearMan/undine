from __future__ import annotations

from typing import Any, NoReturn

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile  # noqa: TCH002
from django.core.validators import URLValidator
from django.db.models.fields.files import FieldFile
from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.dispatcher import TypeDispatcher
from undine.utils.text import dotpath
from undine.utils.urls import validate_file_url

__all__ = [
    "GraphQLFile",
    "parse_file",
]


error_wrapper = handle_conversion_errors("File")
parse_file = TypeDispatcher[Any, Any](wrapper=error_wrapper)
validator = URLValidator()


@parse_file.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not a supported input value"
    raise ValueError(msg)


@parse_file.register
def _(input_value: UploadedFile) -> Any:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    if isinstance(output_value, FieldFile):
        return output_value.url
    if isinstance(output_value, File):
        return output_value.name
    if isinstance(output_value, str):
        return validate_file_url(output_value)

    msg = f"Type '{dotpath(type(output_value))}' is not a supported output value"
    raise ValueError(msg)


GraphQLFile = GraphQLScalarType(
    name="File",
    description="Represents a regular file.",
    serialize=serialize,
    parse_value=parse_file,
)
