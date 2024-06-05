from __future__ import annotations

import pytest
from django.db.models import Case, IntegerField, Value, When
from django.db.models.functions import Left

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Entrypoint,
    Field,
    GQLInfo,
    QueryType,
    RootType,
    create_schema,
)


@pytest.mark.django_db
def test_optimizer__fields__expression(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        first_letter = Field(Left("name", 1))

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__fields__schema_name(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__fields__calculated_field(graphql, undine_settings) -> None:
    class ExampleCalculation(Calculation[int | None]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Case(
                When(name="foo", then=Value(None)),
                default=Value(self.value),
                output_field=IntegerField(null=True),
            )

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        calculated_number = Field(ExampleCalculation)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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


@pytest.mark.django_db
def test_optimizer__fields__to_one_field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        project = Field(Task.project)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="foo", project__name="bar")
    project = task.project

    query = """
        query {
          tasks {
            project
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"project": project.pk}]}


@pytest.mark.django_db
def test_optimizer__fields__to_many_field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        assignees = Field(Task.assignees)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(name="foo", assignees__name="bar")
    assignee = task.assignees.first()

    query = """
        query {
          tasks {
            assignees
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"assignees": [assignee.pk]}]}
