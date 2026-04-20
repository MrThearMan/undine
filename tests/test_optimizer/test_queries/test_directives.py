from __future__ import annotations

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_optimizer__directives__include__false(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @include(if: false)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"done": True}]}

    assert len(response.queries) == 1
    assert "name" not in response.queries[0]


@pytest.mark.django_db
def test_optimizer__directives__include__true(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @include(if: true)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo", "done": True}]}

    assert len(response.queries) == 1
    assert "name" in response.queries[0]


@pytest.mark.django_db
def test_optimizer__directives__skip__false(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @skip(if: false)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo", "done": True}]}

    assert len(response.queries) == 1
    assert "name" in response.queries[0]


@pytest.mark.django_db
def test_optimizer__directives__skip__true(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()
        done = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo", done=True)

    query = """
        query {
          tasks {
            name @skip(if: true)
            done
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"done": True}]}

    assert len(response.queries) == 1
    assert "name" not in response.queries[0]
