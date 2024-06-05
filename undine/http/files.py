"""
File upload handling utilities.

Compliant with the GraphQL multipart request specification:
https://github.com/jaydenseric/graphql-multipart-request-spec
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.core.files import File

from undine.exceptions import GraphQLFileNotFoundError, GraphQLFilePlacingError

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

__all__ = [
    "extract_files",
    "place_files",
]


def extract_files(variables: dict[str, Any]) -> dict[File, list[str]]:
    """
    Extract Django File objects paths in the given variables. Replace the file objects with None values.

    >>> file_1 = File(file=..., name="test_file_1.png")
    >>> file_2 = File(file=..., name="test_file_2.png")
    >>>
    >>> variables = {
    ...     "image": file_1,
    ...     "foo": [file_1, file_2],
    ...     "bar": {"one": file_2, "two": file_1},
    ... }
    >>> files = extract_files(variables)
    >>> files
    {
        <File: test_file_1.png>: ["variables.image", "variables.foo.0", "variables.bar.two"],
        <File: test_file_2.png>: ["variables.foo.1", "variables.bar.one"],
    }
    >>> variables
    {
        "image": None,
        "foo": [None, None],
        "bar": {"one": None, "two": None}
    }
    """
    files: dict[File, list[str]] = defaultdict(list)
    _extract_files_recursively(variables, variables, ["variables"], files)
    return files


def _extract_files_recursively(
    value: Any,
    data: dict[str, Any] | list[Any],
    path: list[str | int],
    files: dict[File, list[str]],
) -> None:
    if isinstance(value, File):
        key = path[-1]
        data[key] = None
        files[value].append(".".join(str(part) for part in path))

    elif isinstance(value, dict):
        for name, item in value.items():
            path.append(name)
            _extract_files_recursively(item, value, path, files)
            path.pop()

    elif isinstance(value, list):
        for index, item in enumerate(value):
            path.append(index)
            _extract_files_recursively(item, value, path, files)
            path.pop()


def place_files(operations: dict[str, Any], files_map: dict[str, list[str]], files: dict[str, UploadedFile]) -> None:
    """
    Place files in the given operations using the files map.

    >>> file_1 = UploadedFile(file=..., name="file_1.png", content_type="image/png")
    >>> file_2 = UploadedFile(file=..., name="file_2.png", content_type="image/png")
    >>>
    >>> operations = {
    ...     "image": None,
    ...     "foo": [None, None],
    ...     "bar": {"one": None, "two": None},
    ... }
    >>> files_map = {
    ...     "0": ["image", "foo.0", "bar.two"]
    ...     "1": ["foo.1", "bar.one"],
    ... }
    ...
    >>> files = {
    ...     "0": file_1,
    ...     "1": file_2,
    ... }
    >>> place_files(operations, files_map, files)
    >>> operations
    {
        "image": file_1,
        "foo": [file_1, file_2],
        "bar": {"one": file_2, "two": file_1},
    }
    """
    for key, values in files_map.items():
        file = files.get(key)
        if file is None:
            raise GraphQLFileNotFoundError(key=key)

        for value in values:
            _place_file(file, value, operations)


def _place_file(file: UploadedFile, value: str, operations: dict[str, Any] | list[Any]) -> None:
    """Handle placing a single file to a single path in the `operations` object."""
    path: list[str] = value.split(".")

    data: Any = operations

    while path:
        key: str | int = path.pop(0)

        try:
            match data:
                case dict():
                    nested_data = data[key]
                case list():
                    key = int(key)
                    nested_data = data[key]
                case _:
                    raise GraphQLFilePlacingError(value=value)

        except (KeyError, IndexError, TypeError) as error:
            raise GraphQLFilePlacingError(value=value) from error

        if path:
            data = nested_data
            continue

        if nested_data is not None:
            raise GraphQLFilePlacingError(value=value)

        data[key] = file
