from __future__ import annotations

from django.db.models import Field
from graphql import Undefined

from example_project.app.models import Comment, Task
from undine import MutationType, QueryType
from undine.converters import convert_to_default_value
from undine.dataclasses import LazyLambda, TypeRef


def test_convert_to_default_value__field() -> None:
    result = convert_to_default_value(Field())
    assert result is Undefined


def test_convert_to_default_value__field__null() -> None:
    result = convert_to_default_value(Field(null=True))
    assert result is None


def test_convert_to_default_value__field__default() -> None:
    result = convert_to_default_value(Field(default="foo"))
    assert result == "foo"


def test_convert_to_default_value__field__blank() -> None:
    result = convert_to_default_value(Field(blank=True))
    assert result == ""


def test_convert_to_default_value__rel() -> None:
    rel = Task._meta.get_field("steps")
    result = convert_to_default_value(rel)
    assert result is Undefined


def test_convert_to_default_value__type_ref() -> None:
    ref = TypeRef(value=int)
    result = convert_to_default_value(ref)
    assert result is Undefined


def test_convert_to_default_value__lazy_lambda() -> None:
    lazy = LazyLambda(callback=lambda _: 0)
    result = convert_to_default_value(lazy)
    assert result is Undefined


def test_convert_to_default_value__func() -> None:
    def foo() -> None: ...

    result = convert_to_default_value(foo)
    assert result is Undefined


def test_convert_to_default_value__mutation_type() -> None:
    class TaskType(QueryType[Task]): ...

    class TaskMutation(MutationType[Task]): ...

    result = convert_to_default_value(TaskMutation)
    assert result is Undefined


def test_convert_to_default_value__generic_foreign_key() -> None:
    field = Comment._meta.get_field("target")

    result = convert_to_default_value(field)
    assert result is Undefined


def test_convert_to_default_value__model() -> None:
    result = convert_to_default_value(Task)
    assert result is Undefined
