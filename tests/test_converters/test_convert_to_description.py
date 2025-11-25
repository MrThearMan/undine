from __future__ import annotations

from typing import Any, NamedTuple

import pytest
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import CASCADE, CharField, Count, F, ForeignKey, Q, Value
from graphql import GraphQLNonNull, GraphQLScalarType, GraphQLString

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine import Calculation, CalculationArgument, DjangoExpression, GQLInfo, InterfaceField, InterfaceType, QueryType
from undine.converters import convert_to_description
from undine.dataclasses import LazyGenericForeignKey, LazyLambda, LazyRelation, TypeRef
from undine.pagination import OffsetPagination
from undine.relay import Connection, Node


class Params(NamedTuple):
    value: Any
    description: str | None


@pytest.mark.parametrize(
    **parametrize_helper({
        "model field": Params(
            value=CharField(help_text="Description."),
            description="Description.",
        ),
        "model field no help text": Params(
            value=CharField(),
            description=None,
        ),
        "expression": Params(
            value=Count("*"),
            description=None,
        ),
        "q expression": Params(
            value=Q(name__exact="foo"),
            description=None,
        ),
        "f expression": Params(
            value=F("name"),
            description=None,
        ),
        "type ref": Params(
            value=TypeRef(value=int),
            description=None,
        ),
        "laxy query type": Params(
            value=LazyRelation(field=ForeignKey("Task", on_delete=CASCADE, help_text="Description.")),
            description="Description.",
        ),
        "laxy query type no help text": Params(
            value=LazyRelation(field=ForeignKey("Task", on_delete=CASCADE)),
            description=None,
        ),
        "lazy query type union": Params(
            value=LazyGenericForeignKey(field=GenericForeignKey("Task")),
            description=None,
        ),
        "lazy lambda query type": Params(
            value=LazyLambda(callback=lambda: ...),
            description=None,
        ),
        "graphql type": Params(
            value=GraphQLScalarType(name="Foo", description="Description."),
            description=None,
        ),
        "graphql type no description": Params(
            value=GraphQLScalarType(name="Foo"),
            description=None,
        ),
        "graphql wrapping type": Params(
            value=GraphQLNonNull(GraphQLScalarType(name="Foo", description="Description.")),
            description=None,
        ),
    }),
)
def test_parse_description(value, description) -> None:
    assert convert_to_description(value) == description


def test_parse_description__class() -> None:
    class MyClass:
        """Description."""

    assert convert_to_description(MyClass) == "Description."


def test_parse_description__class__no_docstring() -> None:
    class MyClass: ...

    assert convert_to_description(MyClass) is None


def test_parse_description__connection() -> None:
    class TaskType(QueryType[Task], interfaces=[Node]): ...

    assert convert_to_description(Connection(TaskType)) is None


def test_parse_description__connection__has_docstring() -> None:
    class TaskType(QueryType[Task], interfaces=[Node]):
        """Description."""

    connection = Connection(TaskType, description="Connection.")

    assert convert_to_description(connection) == "Connection."


def test_parse_description__calculated() -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    assert convert_to_description(ExampleCalculation) == "Description."


def test_parse_description__model() -> None:
    assert convert_to_description(Task) is None


def test_convert_to_description__offset_pagination() -> None:
    class TaskType(QueryType[Task]):
        """foo"""

    pagination = OffsetPagination(TaskType, description="bar")

    result = convert_to_description(pagination)
    assert result == "bar"


def test_convert_to_description__offset_pagination__from_query_type() -> None:
    class TaskType(QueryType[Task]):
        """foo"""

    pagination = OffsetPagination(TaskType)

    result = convert_to_description(pagination)
    assert result == "foo"



def test_convert_to_description__interface_field() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString), description="foo")

    result = convert_to_description(Named.name)
    assert result == "foo"
