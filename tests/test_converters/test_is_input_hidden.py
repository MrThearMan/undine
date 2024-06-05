from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.db.models import CASCADE, CharField, ForeignKey, ManyToOneRel

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine import GQLInfo, MutationType, QueryType
from undine.converters import is_input_hidden
from undine.dataclasses import TypeRef


class Params(NamedTuple):
    value: Any
    expected: bool


@pytest.mark.parametrize(
    **parametrize_helper({
        "model field": Params(
            value=CharField(max_length=255),
            expected=False,
        ),
        "hidden field": Params(
            value=ManyToOneRel(ForeignKey(to="", on_delete=CASCADE), to="", field_name="", related_name="+"),
            expected=True,
        ),
        "type ref": Params(
            value=TypeRef(int),
            expected=False,
        ),
    }),
)
def test_is_input_only(value, expected) -> None:
    assert is_input_hidden(value) is expected


def test_is_input_only__function__no_input() -> None:
    def func(root: Any, info: GQLInfo) -> str: ...

    assert is_input_hidden(func) is True


def test_is_input_only__function__has_input() -> None:
    def func(root: Any, info: GQLInfo, value: str) -> str: ...

    assert is_input_hidden(func) is False


def test_is_input_only__mutation_type() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]): ...

    assert is_input_hidden(TaskMutation) is False
