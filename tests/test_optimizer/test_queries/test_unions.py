from __future__ import annotations

import django
import pytest

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, Field, Filter, FilterSet, Order, OrderSet, QueryType, RootType, UnionType, create_schema
from undine.relay import Connection


@pytest.mark.django_db
def test_optimizer__union(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            ... on ProjectType {
              name
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"type": "TASK"},
            {"name": "Project 2"},
            {"type": "STORY"},
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__union__only_one(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            ... on ProjectType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"name": "Project 2"},
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__union__filtering(graphql, undine_settings) -> None:
    class ProjectFilterSet(FilterSet[Project], auto=False):
        name = Filter()

    class ProjectType(QueryType[Project], auto=False, filterset=ProjectFilterSet):
        name = Field()

    class TaskFilterSet(FilterSet[Task], auto=False):
        type = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=TaskFilterSet):
        type = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable(
            filterTask: {
              type: TASK
            }
            filterProject: {
              name: "Project 1"
            }
          ) {
            ... on ProjectType {
              name
            }
            ... on TaskType {
              type
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"type": "TASK"},
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__union__ordering(graphql, undine_settings) -> None:
    class ProjectOrderSet(OrderSet[Project], auto=False):
        name = Order()

    class ProjectType(QueryType[Project], auto=False, orderset=ProjectOrderSet):
        name = Field()

    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 3")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 3")
    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    query = """
        query {
          commentable(
            orderByTask: [nameAsc]
            orderByProject: [nameAsc]
          ) {
            ... on ProjectType {
              name
            }
            ... on TaskType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"name": "Project 1"},
            {"name": "Task 3"},
            {"name": "Project 3"},
            {"name": "Task 1"},
            {"name": "Project 2"},
            {"name": "Task 2"},
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__union__typename(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1")
    TaskFactory.create(name="Task 2")

    query = """
        query {
          commentable {
            __typename
            ... on ProjectType {
              name
            }
            ... on TaskType {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "commentable": [
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "ProjectType", "name": "Project 2"},
            {"__typename": "TaskType", "name": "Task 2"},
        ]
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__union__connection(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Connection(Commentable))

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            edges {
              node {
                ... on ProjectType {
                  name
                }
                ... on TaskType {
                  type
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.edges == [
        {
            "node": {
                "name": "Project 1",
            },
        },
        {
            "node": {
                "type": "TASK",
            },
        },
        {
            "node": {
                "name": "Project 2",
            },
        },
        {
            "node": {
                "type": "STORY",
            },
        },
    ]

    response.assert_query_count(3)


@pytest.mark.skipif(
    django.VERSION < (5, 2),
    reason="Union querysets with `.values()` don't work correctly before Django 5.2",
)
@pytest.mark.django_db
def test_optimizer__union__connection__total_count(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        commentable = Entrypoint(Connection(Commentable))

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Project 1")
    ProjectFactory.create(name="Project 2")
    TaskFactory.create(name="Task 1", type=TaskTypeChoices.TASK)
    TaskFactory.create(name="Task 2", type=TaskTypeChoices.STORY)

    query = """
        query {
          commentable {
            totalCount
            edges {
              node {
                ... on ProjectType {
                  name
                }
                ... on TaskType {
                  type
                }
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.results["totalCount"] == 4
    assert response.edges == [
        {
            "node": {
                "name": "Project 1",
            },
        },
        {
            "node": {
                "type": "TASK",
            },
        },
        {
            "node": {
                "name": "Project 2",
            },
        },
        {
            "node": {
                "type": "STORY",
            },
        },
    ]

    response.assert_query_count(4)
