from __future__ import annotations

import pytest

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
from undine import (
    Entrypoint,
    Field,
    Filter,
    FilterSet,
    GQLInfo,
    Order,
    OrderSet,
    QueryType,
    RootType,
    UnionType,
    create_schema,
)


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
            {"type": "TASK"},
            {"type": "STORY"},
            {"name": "Project 1"},
            {"name": "Project 2"},
        ],
    }

    response.assert_query_count(2)


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

    response.assert_query_count(1)


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
            {"type": "TASK"},
            {"name": "Project 1"},
        ],
    }

    response.assert_query_count(2)


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
            {"name": "Task 1"},
            {"name": "Task 2"},
            {"name": "Task 3"},
            {"name": "Project 1"},
            {"name": "Project 2"},
            {"name": "Project 3"},
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__union__process_results(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Commentable(UnionType[TaskType, ProjectType]):
        @classmethod
        def __process_results__(cls, instances: list[Task | Project], info: GQLInfo) -> list[Task | Project]:
            return sorted(instances, key=lambda x: x.name)

    class Query(RootType):
        commentable = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="1")
    ProjectFactory.create(name="4")
    ProjectFactory.create(name="3")
    TaskFactory.create(name="2")
    TaskFactory.create(name="5")
    TaskFactory.create(name="6")

    query = """
        query {
          commentable {
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
            {"name": "1"},
            {"name": "2"},
            {"name": "3"},
            {"name": "4"},
            {"name": "5"},
            {"name": "6"},
        ],
    }

    response.assert_query_count(2)


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
            {"__typename": "TaskType", "name": "Task 1"},
            {"__typename": "TaskType", "name": "Task 2"},
            {"__typename": "ProjectType", "name": "Project 1"},
            {"__typename": "ProjectType", "name": "Project 2"},
        ],
    }

    response.assert_query_count(2)
