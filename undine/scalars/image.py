from __future__ import annotations

from typing import Any, NoReturn

from django.core.files import File
from django.core.files.uploadedfile import UploadedFile  # noqa: TC002
from django.db.models.fields.files import ImageFieldFile
from graphql import GraphQLScalarType

from undine.errors.error_handlers import handle_conversion_errors
from undine.utils.function_dispatcher import FunctionDispatcher
from undine.utils.text import dotpath
from undine.utils.urls import validate_image_url

__all__ = [
    "GraphQLImage",
    "parse_image",
]


error_wrapper = handle_conversion_errors("Image")
parse_image = FunctionDispatcher[Any, Any](wrapper=error_wrapper)


@parse_image.register
def _(input_value: Any) -> NoReturn:
    msg = f"Type '{dotpath(type(input_value))}' is not a supported input value"
    raise ValueError(msg)


@parse_image.register
def _(input_value: UploadedFile) -> Any:
    return input_value


@error_wrapper
def serialize(output_value: Any) -> str:
    if isinstance(output_value, ImageFieldFile):
        return output_value.url
    if isinstance(output_value, File):
        return output_value.name
    if isinstance(output_value, str):
        return validate_image_url(output_value)

    msg = f"Type '{dotpath(type(output_value))}' is not a supported output value"
    raise ValueError(msg)


GraphQLImage = GraphQLScalarType(
    name="Image",
    description="Represents an image file.",
    serialize=serialize,
    parse_value=parse_image,
)
