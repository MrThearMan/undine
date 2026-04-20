from __future__ import annotations

from typing import TypedDict

import pytest
from django.core.exceptions import PermissionDenied

from example_project.app.models import Comment, Person, Project, Task, TaskTypeChoices
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory, UserFactory
from undine import Entrypoint, Field, GQLInfo, QueryType, RootType, create_schema
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

    response = graphql(query, count_queries=True)
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

    response = graphql(query, count_queries=True)
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
def test_optimizer__manual_optimization__add_select_related(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_select_related("project", query_type=ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    ProjectFactory.create(name="Proj")
    TaskFactory.create(name="T1", project=Project.objects.first())

    query = "query { tasks { name } }"
    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)


@pytest.mark.django_db
def test_optimizer__manual_optimization__add_prefetch_related(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_prefetch_related("assignees", query_type=PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    person = PersonFactory.create(name="Bob")
    TaskFactory.create(name="T1", assignees=[person])

    query = "query { tasks { name } }"
    response = graphql(query, count_queries=True)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)


@pytest.mark.django_db
def test_optimizer__manual_optimization__add_generic_prefetch_related(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

        @classmethod
        def __optimizations__(cls, data: OptimizationData, info: GQLInfo) -> None:
            data.add_generic_prefetch_related("target", Task, query_type=TaskType)

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    CommentFactory.create(contents="c", target=task)

    query = "query { comments { target { ... on TaskType { type } } } }"
    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors

    response.assert_query_count(2)
