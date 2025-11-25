from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from django.db.models import CharField, DateTimeField, F, Q, Value
from django.db.models.functions import Cast, Now
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Comment, Person, Project, Task
from tests.helpers import parametrize_helper
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Field,
    GQLInfo,
    InterfaceField,
    InterfaceType,
    QueryType,
)
from undine.converters import is_field_nullable
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation
from undine.pagination import OffsetPagination


class Params(NamedTuple):
    value: Any
    expected: bool


def func_1() -> int: ...
def func_2() -> int | None: ...
def func_3() -> int | str: ...


class Arguments(TypedDict):
    value: int


@pytest.mark.parametrize(
    **parametrize_helper({
        "func": Params(
            value=func_1,
            expected=False,
        ),
        "func nullable": Params(
            value=func_2,
            expected=True,
        ),
        "model field": Params(
            value=CharField(max_length=255),
            expected=False,
        ),
        "model field nullable": Params(
            value=CharField(max_length=255, null=True),
            expected=True,
        ),
        "reverse one-to-one": Params(
            value=Task._meta.get_field("result"),
            expected=True,
        ),
        "reverse foreign key": Params(
            value=Task._meta.get_field("steps"),
            expected=False,
        ),
        "reverse many-to-many key": Params(
            value=Task._meta.get_field("reports"),
            expected=False,
        ),
        "expression": Params(
            value=Now(),
            expected=False,
        ),
        "q-expression": Params(
            value=Q(name="foo"),
            expected=False,
        ),
        "expression nullable": Params(
            value=Cast(Now(), output_field=DateTimeField(null=True)),
            expected=True,
        ),
        "lazy query type": Params(
            value=LazyRelation(field=Task._meta.get_field("project")),
            expected=True,
        ),
        "lazy query type union": Params(
            value=LazyGenericForeignKey(field=Comment._meta.get_field("target")),
            expected=False,
        ),
        "generic relation": Params(
            value=Task._meta.get_field("comments"),
            expected=True,
        ),
        "generic foreign key": Params(
            value=Comment._meta.get_field("target"),
            expected=False,
        ),
    }),
)
def test_is_field_nullable(value, expected) -> None:
    assert is_field_nullable(value) is expected


def test_is_field_nullable__f_expression() -> None:
    f = F("name")

    class TaskType(QueryType[Task]):
        name = Field(f)

    assert is_field_nullable(f, caller=TaskType.name) is False


def test_is_field_nullable__f_expression__nullable() -> None:
    f = F("due_by")

    class TaskType(QueryType[Task]):
        due_by = Field(f)

    assert is_field_nullable(f, caller=TaskType.due_by) is True


def test_is_field_nullable__query_type() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType)

    assert is_field_nullable(TaskType, caller=TaskType.assignees) is False


def test_is_field_nullable__query_type__nullable() -> None:
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]):
        project = Field(ProjectType)

    assert is_field_nullable(TaskType, caller=TaskType.project) is True


def test_is_field_nullable__query_type__lambda() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(lambda: PersonType)

    lazy = LazyLambda(callback=lambda: PersonType)
    assert is_field_nullable(lazy, caller=TaskType.assignees) is False


def test_is_field_nullable__calculation() -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert is_field_nullable(ExampleCalculation) is False


def test_is_field_nullable__calculation__null() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value([self.value])

    assert is_field_nullable(ExampleCalculation) is True


def test_is_field_nullable__offset_pagination() -> None:
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]):
        assignees = Field(PersonType)

    assert is_field_nullable(OffsetPagination(TaskType), caller=TaskType.assignees) is False


def test_is_field_nullable__interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]):
        name = Field()

    assert is_field_nullable(Named.name, caller=TaskType.name) is False
