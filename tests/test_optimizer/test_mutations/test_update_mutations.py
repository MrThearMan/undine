from __future__ import annotations

import pytest

from example_project.app.models import Comment, Person, Project, Report, ServiceRequest, Task, TaskResult, TaskStep
from tests.factories import CommentFactory, ProjectFactory, TaskFactory
from tests.helpers import cache_content_types
from undine import Entrypoint, Field, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_mutation_optimization__update(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
        },
    }

    response.assert_query_count(4)


@pytest.mark.django_db
def test_mutation_optimization__update__forward__one_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        request = Input(ServiceRequestMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "request": {
            "pk": task.request.pk,
            "details": "Updated request",
        },
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "request": {
                "details": "Updated request",
            },
        },
    }

    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_optimization__update__forward__many_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    # MutationTypes

    class ProjectMutation(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        project = Input(ProjectMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", project__name="Test project")

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            project {
              name
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "project": {
            "pk": task.project.pk,
            "name": "Updated project",
        },
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "project": {
                "name": "Updated project",
            },
        },
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__update__forward__many_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    # MutationTypes

    class PersonMutation(MutationType[Person], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        assignees = Input(PersonMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", assignees__name="Test person")
    assignee = task.assignees.first()

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            assignees {
              name
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "assignees": [
            {
                "pk": assignee.pk,
                "name": "Updated person",
            },
        ],
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "assignees": [
                {
                    "name": "Updated person",
                },
            ],
        },
    }

    response.assert_query_count(10)


@pytest.mark.django_db
def test_mutation_optimization__update__reverse__one_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskResultType(QueryType[TaskResult], auto=False):
        details = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        result = Field(TaskResultType)

    # MutationTypes

    class TaskResultMutation(MutationType[TaskResult], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        result = Input(TaskResultMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", result__details="Test result")

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            result {
              details
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "result": {
            "pk": task.result.pk,
            "details": "Updated result",
        },
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "result": {
                "details": "Updated result",
            },
        },
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__update__reverse__one_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        pk = Input()
        name = Input()
        steps = Input(TaskStepMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", steps__name="Test step")
    step = task.steps.first()

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "steps": [
            {
                "pk": step.pk,
                "name": "Updated step",
            },
        ],
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "steps": [
                {
                    "name": "Updated step",
                },
            ],
        },
    }

    response.assert_query_count(8)


@pytest.mark.django_db
def test_mutation_optimization__update__reverse__many_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ReportType(QueryType[Report], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        reports = Field(ReportType)

    # MutationTypes

    class ReportMutation(MutationType[Report], kind="related"):
        pk = Input()

    class TaskUpdateMutation(MutationType[Task]):
        pk = Input()
        name = Input()
        reports = Input(ReportMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", reports__name="Test report")
    report = task.reports.first()

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "reports": [
            {
                "pk": report.pk,
                "name": "Updated report",
            },
        ],
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "reports": [
                {
                    "name": "Updated report",
                },
            ],
        },
    }

    response.assert_query_count(10)


@pytest.mark.django_db
def test_mutation_optimization__update__generic_relation(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        comments = Field(CommentType)

    # MutationTypes

    class CommentMutation(MutationType[Comment], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        type = Input()
        comments = Input(CommentMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    comment = CommentFactory.create(target=task, contents="Test comment")

    cache_content_types()

    query = """
        mutation ($input: TaskUpdateMutation!) {
          updateTask(input: $input) {
            name
            comments {
              contents
            }
          }
        }
    """

    data = {
        "pk": task.pk,
        "name": "Updated task",
        "comments": [
            {
                "pk": comment.pk,
                "contents": "Updated comment",
            },
        ],
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateTask": {
            "name": "Updated task",
            "comments": [
                {
                    "contents": "Updated comment",
                },
            ],
        },
    }

    response.assert_query_count(8)


@pytest.mark.django_db
def test_mutation_optimization__update__generic_foreign_key(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    # MutationTypes

    class CommentUpdateMutation(MutationType[Comment], auto=False):
        pk = Input()
        contents = Input()
        target = Input()

    # RootTypes

    class Query(RootType):
        comments = Entrypoint(CommentType)

    class Mutation(RootType):
        update_comment = Entrypoint(CommentUpdateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test project")
    task = TaskFactory.create(name="Test task", project=project)

    comment = CommentFactory.create(target=task, contents="Test comment")

    cache_content_types()

    query = """
        mutation ($input: CommentUpdateMutation!) {
          updateComment(input: $input) {
            contents
            target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                name
              }
            }
          }
        }
    """

    data = {
        "pk": comment.pk,
        "contents": "Updated comment",
        "target": {
            "task": {
                "pk": task.pk,
            },
        },
    }

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "updateComment": {
            "contents": "Updated comment",
            "target": {
                "name": "Test task",
            },
        },
    }

    response.assert_query_count(6)
