from __future__ import annotations

from typing import Any

import pytest
from django.core.files.uploadedfile import UploadedFile

from tests.helpers import create_png
from undine.exceptions import GraphQLFileNotFoundError, GraphQLFilePlacingError
from undine.http.files import extract_files, place_files

pytestmark = [
    pytest.mark.django_db,
]


def test_extract_files() -> None:
    file_1 = create_png(name="file_1.png")
    file_2 = create_png(name="file_1.png")

    variables: dict[str, Any] = {
        "image": file_1,
        "foo": [file_1, 5, file_2],
        "bar": {"one": file_2, "two": file_1, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }

    files = extract_files(variables)

    assert files == {
        file_1: ["variables.image", "variables.foo.0", "variables.bar.two"],
        file_2: ["variables.foo.2", "variables.bar.one"],
    }
    assert variables == {
        "image": None,
        "foo": [None, 5, None],
        "bar": {"one": None, "two": None, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }


def test_place_files() -> None:
    file_1 = UploadedFile(file=create_png(name="file_1.png"))
    file_2 = UploadedFile(file=create_png(name="file_1.png"))

    operations: dict[str, Any] = {
        "image": None,
        "foo": [None, 5, None],
        "bar": {"one": None, "two": None, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }
    files_map: dict[str, list[str]] = {
        "0": ["image", "foo.0", "bar.two"],
        "1": ["foo.2", "bar.one"],
    }
    files: dict[str, UploadedFile] = {
        "0": file_1,
        "1": file_2,
    }

    place_files(operations, files_map, files)

    assert operations == {
        "image": file_1,
        "foo": [file_1, 5, file_2],
        "bar": {"one": file_2, "two": file_1, "three": 1},
        "fizz": "buzz",
        "1": None,
        "2": type(None),
    }


def test_place_files__no_file() -> None:
    operations: dict[str, Any] = {
        "image": None,
    }
    files_map: dict[str, list[str]] = {
        "0": ["image"],
    }
    files: dict[str, UploadedFile] = {}

    with pytest.raises(GraphQLFileNotFoundError):
        place_files(operations, files_map, files)


def test_place_files__incorrect_path() -> None:
    file = UploadedFile(file=create_png(name="file_1.png"))

    operations: dict[str, Any] = {
        "image": None,
    }
    files_map: dict[str, list[str]] = {
        "0": ["foo"],
    }
    files: dict[str, UploadedFile] = {
        "0": file,
    }

    with pytest.raises(GraphQLFilePlacingError):
        place_files(operations, files_map, files)


def test_place_files__incorrect_sub_path() -> None:
    file = UploadedFile(file=create_png(name="file_1.png"))

    operations: dict[str, Any] = {
        "image": None,
    }
    files_map: dict[str, list[str]] = {
        "0": ["image.0"],
    }
    files: dict[str, UploadedFile] = {
        "0": file,
    }

    with pytest.raises(GraphQLFilePlacingError):
        place_files(operations, files_map, files)


def test_place_files__value_at_end_is_not_none() -> None:
    file = UploadedFile(file=create_png(name="file_1.png"))

    operations: dict[str, Any] = {
        "image": "foo",
    }
    files_map: dict[str, list[str]] = {
        "0": ["image"],
    }
    files: dict[str, UploadedFile] = {
        "0": file,
    }

    with pytest.raises(GraphQLFilePlacingError):
        place_files(operations, files_map, files)
