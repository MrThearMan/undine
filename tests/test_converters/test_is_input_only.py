from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db import models

from example_project.app.models import Comment, Task
from tests.helpers import parametrize_helper
from undine import MutationType
from undine.converters import is_input_only
from undine.typing import TypeRef


class Params(NamedTuple):
    value: Any
    expected: bool


@pytest.mark.parametrize(
    **parametrize_helper(
        {
            "model field": Params(
                value=models.CharField(max_length=255),
                expected=False,
            ),
            "type ref": Params(
                value=TypeRef(int),
                expected=True,
            ),
            "foreign key": Params(
                value=Task._meta.get_field("project"),
                expected=False,
            ),
            "reverse foreign key": Params(
                value=Task._meta.get_field("steps"),
                expected=False,
            ),
            "generic relation": Params(
                value=Task._meta.get_field("comments"),
                expected=False,
            ),
            "generic foreign key": Params(
                value=Comment._meta.get_field("target"),
                expected=False,
            ),
        },
    ),
)
def test_is_input_only(value, expected):
    assert is_input_only(value) is expected


def test_is_input_only__mutation_type():
    class TaskMutation(MutationType, model=Task): ...

    assert is_input_only(TaskMutation) is False
