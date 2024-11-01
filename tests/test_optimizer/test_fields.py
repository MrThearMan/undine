import pytest
from django.db.models.functions import Left

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, create_schema


@pytest.mark.django_db
def test_fields__expression(graphql, undine_settings):
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
def test_fields__typename(graphql, undine_settings):
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
