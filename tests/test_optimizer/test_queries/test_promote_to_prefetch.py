from __future__ import annotations

import pytest
from django.db.models import QuerySet, Value
from django.db.models.functions import Left

from example_project.app.models import Project, Task
from tests.factories import TaskFactory
from undine import (
    Calculation,
    CalculationArgument,
    Entrypoint,
    Field,
    FilterSet,
    GQLInfo,
    QueryType,
    RootType,
    create_schema,
)
from undine.typing import DjangoExpression


@pytest.mark.django_db
def test_optimizer__promote_to_prefetch__has_filter_queryset(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset.filter(name="foo")

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"name": "foo"},
            },
            {
                "name": "task 2",
                "project": None,
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the QueryType has a '__filter_queryset__' method,
    # we need to use 'prefetch_related' instead or 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_optimizer__promote_to_prefetch__has_annotations(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        first_letter = Field(Left("name", 1))

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              firstLetter
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"firstLetter": "f"},
            },
            {
                "name": "task 2",
                "project": {"firstLetter": "b"},
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the there is an annotation on project,
    # we need to use 'prefetch_related' instead or 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_optimizer__promote_to_prefetch__has_field_calculations(graphql, undine_settings) -> None:
    class ExampleCalculation(Calculation[int]):
        """Description."""

        value = CalculationArgument(int)
        """Value description."""

        def __call__(self, info: GQLInfo) -> DjangoExpression:
            return Value(self.value)

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        custom = Field(ExampleCalculation)

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              custom(value: 1)
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"custom": 1},
            },
            {
                "name": "task 2",
                "project": {"custom": 1},
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since there is a field calculation on project,
    # we need to use 'prefetch_related' instead of 'select_related'.
    assert len(response.queries) == 2


@pytest.mark.django_db
def test_optimizer__promote_to_prefetch__has_filterset_filter_queryset(graphql, undine_settings) -> None:
    class ProjectFilterSet(FilterSet[Project]):
        @classmethod
        def __filter_queryset__(cls, queryset: QuerySet, info: GQLInfo) -> QuerySet:
            return queryset.filter(name="foo")

    class ProjectType(QueryType[Project], auto=False, filterset=ProjectFilterSet):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="task 1", project__name="foo")
    TaskFactory.create(name="task 2", project__name="bar")

    query = """
        query {
          tasks {
            name
            project {
              name
            }
          }
        }
    """

    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "name": "task 1",
                "project": {"name": "foo"},
            },
            {
                "name": "task 2",
                "project": None,
            },
        ],
    }

    # Normally, project would be fetched in a single
    # query with the task since its a to-one relation,
    # but since the QueryType has a FilterSet with a '__filter_queryset__' method,
    # we need to use 'prefetch_related' instead of 'select_related'.
    assert len(response.queries) == 2
