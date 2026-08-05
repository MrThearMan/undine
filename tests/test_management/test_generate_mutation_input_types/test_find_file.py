from __future__ import annotations

import pytest
from django.conf import settings

from undine.exceptions import (
    MutationInputDataTypesModuleImportError,
    MutationInputDataTypesModuleNoParentError,
    MutationInputDataTypesModuleNotOverridableError,
    MutationInputDataTypesModuleNotSetError,
    MutationInputDataTypesModuleParentNotPackageError,
)
from undine.management.commands.generate_mutation_input_types import find_mutation_input_data_typing_file

from . import correct_marker_module, incorrect_marker_module


def test_find_file__target_correct__missing_file(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = "example_project.does_not_exist"

    target = find_mutation_input_data_typing_file()

    assert target.exists() is False

    assert target == settings.BASE_DIR / "does_not_exist.py"


def test_find_file__correct_target__missing_marker(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = correct_marker_module.__name__

    target = find_mutation_input_data_typing_file()

    assert target.exists() is True

    assert str(target) == correct_marker_module.__file__


def test_find_file__correct_target__incorrect_marker(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = incorrect_marker_module.__name__

    with pytest.raises(MutationInputDataTypesModuleNotOverridableError):
        find_mutation_input_data_typing_file()


def test_find_file__setting_not_set(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = None

    with pytest.raises(MutationInputDataTypesModuleNotSetError):
        find_mutation_input_data_typing_file()


def test_find_file__not_in_a_package(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = "does_not_exist"

    with pytest.raises(MutationInputDataTypesModuleNoParentError):
        find_mutation_input_data_typing_file()


def test_find_file__import_error(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = ".relative.does_not_exist"

    with pytest.raises(MutationInputDataTypesModuleImportError):
        find_mutation_input_data_typing_file()


def test_find_file__parent_does_not_exist(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = "does_not_exist.does_not_exist"

    with pytest.raises(MutationInputDataTypesModuleParentNotPackageError):
        find_mutation_input_data_typing_file()


def test_find_file__parent_not_a_package(undine_settings) -> None:
    undine_settings.MUTATION_INPUT_DATA_TYPES_MODULE = "example_project.app.schema.gen"

    with pytest.raises(MutationInputDataTypesModuleParentNotPackageError):
        find_mutation_input_data_typing_file()
