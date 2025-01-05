import datetime

import pytest
from django.db.models.functions import Reverse

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, Order, OrderSet, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_optimizer__ordering(graphql, undine_settings):
    class TaskOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    class TaskType(QueryType, model=Task, auto=False, orderset=TaskOrderSet):
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
def test_optimizer__ordering__multiple(graphql, undine_settings):
    class TaskOrderSet(OrderSet, model=Task, auto=False):
        name = Order()
        due_by = Order()

    class TaskType(QueryType, model=Task, auto=False, orderset=TaskOrderSet):
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
def test_optimizer__ordering__nulls_first(graphql, undine_settings):
    class TaskOrderSet(OrderSet, model=Task, auto=False):
        project = Order(null_placement="first")

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, orderset=TaskOrderSet):
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
def test_optimizer__ordering__nulls_last(graphql, undine_settings):
    class TaskOrderSet(OrderSet, model=Task, auto=False):
        project = Order(null_placement="last")

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False, orderset=TaskOrderSet):
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
def test_optimizer__ordering__expression(graphql, undine_settings):
    class TaskOrderSet(OrderSet, model=Task, auto=False):
        name_reversed = Order(Reverse("name"))

    class TaskType(QueryType, model=Task, auto=False, orderset=TaskOrderSet):
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
