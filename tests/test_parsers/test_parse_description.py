from __future__ import annotations

from typing import Any, NamedTuple, TypedDict

import pytest
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import CASCADE, CharField, Count, F, ForeignKey, Q
from graphql import GraphQLNonNull, GraphQLScalarType

from example_project.app.models import Task
from tests.helpers import parametrize_helper
from undine import QueryType
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion, TypeRef
from undine.parsers import parse_description
from undine.relay import Connection, Node


class Params(NamedTuple):
    value: Any
    description: str | None


@pytest.mark.parametrize(
    **parametrize_helper(
        {
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
                value=LazyQueryType(field=ForeignKey("Task", on_delete=CASCADE, help_text="Description.")),
                description="Description.",
            ),
            "laxy query type no help text": Params(
                value=LazyQueryType(field=ForeignKey("Task", on_delete=CASCADE)),
                description=None,
            ),
            "lazy query type union": Params(
                value=LazyQueryTypeUnion(field=GenericForeignKey("Task")),
                description=None,
            ),
            "lazy lambda query type": Params(
                value=LazyLambdaQueryType(callback=lambda: ...),
                description=None,
            ),
            "graphql type": Params(
                value=GraphQLScalarType(name="Foo", description="Description."),
                description="Description.",
            ),
            "graphql type no description": Params(
                value=GraphQLScalarType(name="Foo"),
                description=None,
            ),
            "graphql wrapping type": Params(
                value=GraphQLNonNull(GraphQLScalarType(name="Foo", description="Description.")),
                description="Description.",
            ),
        },
    ),
)
def test_parse_description(value, description):
    assert parse_description(value) == description


def test_parse_description__class():
    class MyClass:
        """Description."""

    assert parse_description(MyClass) == "Description."


def test_parse_description__class__no_docstring():
    class MyClass: ...

    assert parse_description(MyClass) is None


def test_parse_description__connection():
    class TaskType(QueryType, model=Task, interfaces=[Node]): ...

    assert parse_description(Connection(TaskType)) is None


def test_parse_description__connection__has_docstring():
    class TaskType(QueryType, model=Task, interfaces=[Node]):
        """Description."""

    assert parse_description(Connection(TaskType)) == "Description."


def test_parse_description__calculated():
    class Arguments(TypedDict):
        value: int

    value = Calculated(Arguments, returns=int)
    assert parse_description(value) is None


def test_parse_description__calculated__has_docstring():
    class Arguments(TypedDict):
        """Description."""

        value: int

    value = Calculated(Arguments, returns=int)
    assert parse_description(value) == "Description."
