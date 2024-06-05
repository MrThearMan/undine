from typing import TypedDict, Unpack

import pytest
from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.db.models.functions import Left

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, create_schema
from undine.dataclasses import Calculated
from undine.typing import GQLInfo


@pytest.mark.django_db
def test_optimizer__fields__expression(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        first_letter = Field(Left("name", 1))

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            firstLetter
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"firstLetter": "f"}]}


@pytest.mark.django_db
def test_optimizer__fields__typename(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            __typename
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"__typename": "TaskType"}]}


@pytest.mark.django_db
def test_optimizer__fields__aliases(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    TaskFactory.create(name="foo")

    query = """
        query {
          tasks {
            foo: name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"foo": "foo"}]}


@pytest.mark.django_db
def test_optimizer__fields__calculated_field(graphql, undine_settings):
    class Arguments(TypedDict, total=False):
        value: int

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()

        calculated_number = Field(Calculated(Arguments, return_annotation=int | None))

        @calculated_number.calculate
        def calc(self: Field, queryset: QuerySet, info: GQLInfo, **kwargs: Unpack[Arguments]) -> QuerySet:
            return queryset.annotate(
                calculated_number=Case(
                    When(name="foo", then=Value(None)),
                    default=Value(kwargs["value"]),
                    output_field=IntegerField(null=True),
                ),
            )

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    query = """
        query {
          tasks {
            name
            calculatedNumber(value: 1)
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "foo",
                "calculatedNumber": None,
            },
            {
                "name": "bar",
                "calculatedNumber": 1,
            },
            {
                "name": "baz",
                "calculatedNumber": 1,
            },
        ],
    }
