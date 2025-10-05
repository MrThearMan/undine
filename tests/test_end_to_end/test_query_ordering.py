from __future__ import annotations

import datetime

import pytest
from django.db.models.functions import Reverse

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
from undine import Entrypoint, Field, Order, OrderSet, QueryType, RootType, UnionType, create_schema
from undine.relay import Connection


@pytest.mark.django_db
def test_end_to_end__ordering(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="1")
    TaskFactory.create(name="3")
    TaskFactory.create(name="2")

    query = """
        query {
          tasks(orderBy: nameAsc) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "1"},
            {"name": "2"},
            {"name": "3"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__multiple(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        due_by = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        due_by = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="1", due_by=datetime.date(2025, 1, 1))
    TaskFactory.create(name="3", due_by=datetime.date(2025, 1, 1))
    TaskFactory.create(name="2", due_by=datetime.date(2025, 1, 1))

    TaskFactory.create(name="2", due_by=datetime.date(2025, 1, 2))
    TaskFactory.create(name="3", due_by=datetime.date(2025, 1, 2))
    TaskFactory.create(name="1", due_by=datetime.date(2025, 1, 2))

    query = """
        query {
          tasks(orderBy: [nameAsc, dueByDesc]) {
            name
            dueBy
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "1", "dueBy": "2025-01-02"},
            {"name": "1", "dueBy": "2025-01-01"},
            {"name": "2", "dueBy": "2025-01-02"},
            {"name": "2", "dueBy": "2025-01-01"},
            {"name": "3", "dueBy": "2025-01-02"},
            {"name": "3", "dueBy": "2025-01-01"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__nulls_first(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        project = Order(null_placement="first")

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="1", project__name="1")
    TaskFactory.create(name="3", project=None)
    TaskFactory.create(name="2", project__name="2")

    query = """
        query {
          tasks(orderBy: projectAsc) {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "3", "project": None},
            {"name": "1", "project": {"name": "1"}},
            {"name": "2", "project": {"name": "2"}},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__nulls_last(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        project = Order(null_placement="last")

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="1", project__name="1")
    TaskFactory.create(name="3", project=None)
    TaskFactory.create(name="2", project__name="2")

    query = """
        query {
          tasks(orderBy: projectAsc) {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "1", "project": {"name": "1"}},
            {"name": "2", "project": {"name": "2"}},
            {"name": "3", "project": None},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__expression(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name_reversed = Order(Reverse("name"))

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="1")
    TaskFactory.create(name="3")
    TaskFactory.create(name="2")

    query = """
        query {
          tasks(orderBy: nameReversedAsc) {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "1"},
            {"name": "2"},
            {"name": "3"},
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__max_orders(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        name = Order()
        done = Order()

    class TaskType(QueryType[Task], auto=False, orderset=TaskOrderSet):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)
    undine_settings.MAX_ORDERS_PER_TYPE = 1

    TaskFactory.create(name="1")
    TaskFactory.create(name="3")
    TaskFactory.create(name="2")

    query = """
        query {
          tasks(orderBy: [nameAsc, doneAsc]) {
            name
          }
        }
    """

    response = graphql(query)

    assert response.errors == [
        {
            "message": "'TaskOrderSet' received 2 orders which is more than the maximum allowed of 1.",
            "extensions": {
                "status_code": 400,
                "error_code": "TOO_MANY_ORDERS",
            },
            "path": ["tasks"],
        }
    ]


@pytest.mark.django_db
def test_end_to_end__ordering__union_type(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

    @CommentableOrderSet
    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        comments = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    ProjectFactory.create(name="foo")
    ProjectFactory.create(name="bar")
    ProjectFactory.create(name="baz")

    query = """
        query {
          comments(
            orderBy: nameAsc
          ) {
            __typename
            ... on TaskType {
              name
            }
            ... on ProjectType {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "__typename": "ProjectType",
                "name": "bar",
            },
            {
                "__typename": "TaskType",
                "name": "bar",
            },
            {
                "__typename": "ProjectType",
                "name": "baz",
            },
            {
                "__typename": "TaskType",
                "name": "baz",
            },
            {
                "__typename": "ProjectType",
                "name": "foo",
            },
            {
                "__typename": "TaskType",
                "name": "foo",
            },
        ],
    }


@pytest.mark.django_db
def test_end_to_end__ordering__union_type__with_query_type_ordering(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        type = Order("type")

    @TaskOrderSet
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class ProjectOrderSet(OrderSet[Project], auto=False):
        team_name = Order("team__name")

    @ProjectOrderSet
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class CommentableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

    @CommentableOrderSet
    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        comments = Entrypoint(Commentable, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="foo", type=TaskTypeChoices.BUG_FIX)
    task_3 = TaskFactory.create(name="bar", type=TaskTypeChoices.TASK)

    project_1 = ProjectFactory.create(name="foo", team__name="c")
    project_2 = ProjectFactory.create(name="foo", team__name="b")
    project_3 = ProjectFactory.create(name="bar", team__name="a")

    query = """
        query {
          comments(
            orderBy: nameAsc
            orderByTask: typeAsc
            orderByProject: teamNameAsc
          ) {
            __typename
            ... on TaskType {
              pk
              name
            }
            ... on ProjectType {
              pk
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "comments": [
            {
                "__typename": "ProjectType",
                "pk": project_3.pk,
                "name": "bar",
            },
            {
                "__typename": "TaskType",
                "pk": task_3.pk,
                "name": "bar",
            },
            {
                "__typename": "ProjectType",
                "pk": project_1.pk,
                "name": "foo",
            },
            {
                "__typename": "ProjectType",
                "pk": project_2.pk,
                "name": "foo",
            },
            {
                "__typename": "TaskType",
                "pk": task_1.pk,
                "name": "foo",
            },
            {
                "__typename": "TaskType",
                "pk": task_2.pk,
                "name": "foo",
            },
        ]
    }


@pytest.mark.django_db
def test_end_to_end__ordering__union_type__connection(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

    @CommentableOrderSet
    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        comments = Entrypoint(Connection(Commentable))

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="foo")
    TaskFactory.create(name="bar")
    TaskFactory.create(name="baz")

    ProjectFactory.create(name="foo")
    ProjectFactory.create(name="bar")
    ProjectFactory.create(name="baz")

    query = """
        query {
          comments(
            orderBy: nameAsc
          ) {
            edges {
              node {
                __typename
                ... on TaskType {
                  name
                }
                ... on ProjectType {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.edges == [
        {
            "node": {
                "__typename": "ProjectType",
                "name": "bar",
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "bar",
            },
        },
        {
            "node": {
                "__typename": "ProjectType",
                "name": "baz",
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "baz",
            },
        },
        {
            "node": {
                "__typename": "ProjectType",
                "name": "foo",
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "foo",
            },
        },
    ]


@pytest.mark.django_db
def test_end_to_end__ordering__union_type__connection__with_query_type_ordering(graphql, undine_settings) -> None:
    class TaskOrderSet(OrderSet[Task], auto=False):
        type = Order("type")

    @TaskOrderSet
    class TaskType(QueryType[Task], auto=False):
        pk = Field()
        name = Field()

    class ProjectOrderSet(OrderSet[Project], auto=False):
        team_name = Order("team__name")

    @ProjectOrderSet
    class ProjectType(QueryType[Project], auto=False):
        pk = Field()
        name = Field()

    class CommentableOrderSet(OrderSet[Task, Project], auto=False):
        name = Order("name")

    @CommentableOrderSet
    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        comments = Entrypoint(Connection(Commentable))

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="foo", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="foo", type=TaskTypeChoices.BUG_FIX)
    task_3 = TaskFactory.create(name="bar", type=TaskTypeChoices.TASK)

    project_1 = ProjectFactory.create(name="foo", team__name="c")
    project_2 = ProjectFactory.create(name="foo", team__name="b")
    project_3 = ProjectFactory.create(name="bar", team__name="a")

    query = """
        query {
          comments(
            orderBy: nameAsc
            orderByTask: typeAsc
            orderByProject: teamNameAsc
          ) {
            edges {
              node {
                __typename
                ... on TaskType {
                  pk
                  name
                }
                ... on ProjectType {
                  pk
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.edges == [
        {
            "node": {
                "__typename": "ProjectType",
                "name": "bar",
                "pk": project_3.pk,
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "bar",
                "pk": task_3.pk,
            },
        },
        {
            "node": {
                "__typename": "ProjectType",
                "name": "foo",
                "pk": project_1.pk,
            },
        },
        {
            "node": {
                "__typename": "ProjectType",
                "name": "foo",
                "pk": project_2.pk,
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "foo",
                "pk": task_1.pk,
            },
        },
        {
            "node": {
                "__typename": "TaskType",
                "name": "foo",
                "pk": task_2.pk,
            },
        },
    ]
