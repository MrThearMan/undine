from __future__ import annotations

from typing import TypedDict

import pytest
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet, Value
from django.db.models.functions import Left

from example_project.app.models import Project, Task, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory, TaskFactory, TeamFactory, UserFactory
from undine import (
    Calculation,
    CalculationArgument,
    DjangoExpression,
    Entrypoint,
    Field,
    FilterSet,
    GQLInfo,
    QueryType,
    RootType,
    create_schema,
)
from undine.optimizer import OptimizationData


@pytest.mark.django_db
def test_optimizer__manual_optimization__query_type(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            project_data = data.add_select_related("project")
            team_data = project_data.add_select_related("team")
            member_data = team_data.add_prefetch_related("members")
            member_data.only_fields.add("email")

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo) -> None:
            if info.context.user.is_anonymous:
                raise PermissionDenied

            if not instance.project:
                raise PermissionDenied

            if not instance.project.team:
                raise PermissionDenied

            member_emails = {member.email for member in instance.project.team.members.all()}
            if info.context.user.email not in member_emails:
                raise PermissionDenied

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person_1 = PersonFactory.create(name="person 1", email="me@example.com")
    person_2 = PersonFactory.create(name="person 2", email="you@example.com")

    team_1 = TeamFactory.create(name="team 1", members=[person_1])
    team_2 = TeamFactory.create(name="team 2", members=[person_1, person_2])

    project_1 = ProjectFactory.create(name="project", team=team_1)
    project_2 = ProjectFactory.create(name="project", team=team_2)

    TaskFactory.create(name="task 1", project=project_1)
    TaskFactory.create(name="task 2", project=project_1)
    TaskFactory.create(name="task 3", project=project_2)

    query = """
        query {
          tasks {
            name
          }
        }
    """

    user = UserFactory.create(email="me@example.com")
    graphql.force_login(user)

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {"name": "task 1"},
            {"name": "task 2"},
            {"name": "task 3"},
        ],
    }

    # Queries
    # 1. Fetch tasks with projects and teams
    # 2. Fetch members of teams
    # 3. Fetch user
    response.assert_query_count(3)


@pytest.mark.django_db
def test_optimizer__manual_optimization__field(graphql, undine_settings) -> None:
    class TaskStatus(TypedDict):
        name: str
        type: TaskTypeChoices

    class TaskType(QueryType[Task], auto=False):
        pk = Field()

        @Field
        def status(self: Task) -> TaskStatus:
            return TaskStatus(
                name=self.name,
                type=TaskTypeChoices(self.type),
            )

        @status.optimize
        def optimize_data(self, data: OptimizationData, info: GQLInfo) -> None:
            data.only_fields.add("name")
            data.only_fields.add("type")

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task_1 = TaskFactory.create(name="task 1", type=TaskTypeChoices.STORY)
    task_2 = TaskFactory.create(name="task 2", type=TaskTypeChoices.TASK)

    query = """
        query {
          tasks {
            pk
            status {
              name
              type
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {
        "tasks": [
            {
                "pk": task_1.pk,
                "status": {
                    "name": "task 1",
                    "type": "STORY",
                },
            },
            {
                "pk": task_2.pk,
                "status": {
                    "name": "task 2",
                    "type": "TASK",
                },
            },
        ],
    }

    # Queries
    # 1. Fetch tasks with correct fields
    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__multiple_queries(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)
        projects = Entrypoint(ProjectType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="foo", project=project)

    query = """
        query {
          tasks {
            name
          }
          projects {
            name
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"name": "foo"}], "projects": [{"name": "foo"}]}


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

    response = graphql(query)
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

    response = graphql(query)
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

    response = graphql(query)
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

    response = graphql(query)
    assert response.has_errors is False, response.errors

    assert response.data == {"tasks": [{"done": True}]}

    assert len(response.queries) == 1
    assert "name" not in response.queries[0]


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

    response = graphql(query)
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

    response = graphql(query)
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

    response = graphql(query)
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

    response = graphql(query)
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
