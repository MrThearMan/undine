from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.app.models import Comment, Person, Project, Report, ServiceRequest, Task, TaskResult, TaskStep
from tests.factories import CommentFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.utils.mutation_tree import bulk_mutate


@pytest.mark.django_db
def test_mutation_optimization__bulk_update(graphql, undine_settings) -> None:
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
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task")

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
            },
        ],
    }

    response.assert_query_count(4)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__forward__one_to_one(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", request__details="Test request")

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "request": {
                "pk": task.request.pk,
                "details": "Updated request",
            },
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "request": {
                    "details": "Updated request",
                },
            },
        ],
    }

    response.assert_query_count(6)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__forward__many_to_one(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", project__name="Test project")

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            project {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "project": {
                "pk": task.project.pk,
                "name": "Updated project",
            },
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "project": {
                    "name": "Updated project",
                },
            },
        ],
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__forward__many_to_many(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", assignees__name="Test person")
    assignee = task.assignees.first()

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            assignees {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "assignees": [
                {
                    "pk": assignee.pk,
                    "name": "Updated person",
                },
            ],
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "assignees": [
                    {
                        "name": "Updated person",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(10)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__reverse__one_to_one(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", result__details="Test result")

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            result {
              details
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "result": {
                "pk": task.result.pk,
                "details": "Updated result",
            },
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "result": {
                    "details": "Updated result",
                },
            },
        ],
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__reverse__one_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        steps = Input(TaskStepMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", steps__name="Test step")
    step = task.steps.first()

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "steps": [
                {
                    "pk": step.pk,
                    "name": "Updated step",
                },
            ],
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "steps": [
                    {
                        "name": "Updated step",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(8)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__reverse__many_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ReportType(QueryType[Report], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        reports = Field(ReportType)

    # MutationTypes

    class ReportMutation(MutationType[Report], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task], auto=False):
        pk = Input()
        name = Input()
        reports = Input(ReportMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_tasks = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Test task", reports__name="Test report")
    report = task.reports.first()

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTasks(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "reports": [
                {
                    "pk": report.pk,
                    "name": "Updated report",
                },
            ],
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTasks": [
            {
                "name": "Updated task",
                "reports": [
                    {
                        "name": "Updated report",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(10)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__generic_relation(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    comment = CommentFactory.create(target=task, contents="Test comment")

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskUpdateMutation!]!) {
          bulkUpdateTask(input: $input) {
            name
            comments {
              contents
            }
          }
        }
    """

    data = [
        {
            "pk": task.pk,
            "name": "Updated task",
            "comments": [
                {
                    "pk": comment.pk,
                    "contents": "Updated comment",
                },
            ],
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateTask": [
            {
                "name": "Updated task",
                "comments": [
                    {
                        "contents": "Updated comment",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(8)


@pytest.mark.django_db
def test_mutation_optimization__bulk_update__generic_foreign_key(graphql, undine_settings) -> None:
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

        @classmethod
        def __bulk_mutate__(cls, instances: list[Comment], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Comment, data=input_data)

    # RootTypes

    class Query(RootType):
        comments = Entrypoint(CommentType)

    class Mutation(RootType):
        bulk_update_comment = Entrypoint(CommentUpdateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test project")
    task = TaskFactory.create(name="Test task", project=project)

    comment = CommentFactory.create(target=task, contents="Test comment")

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [CommentUpdateMutation!]!) {
          bulkUpdateComment(input: $input) {
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

    data = [
        {
            "pk": comment.pk,
            "contents": "Updated comment",
            "target": {
                "task": {
                    "pk": task.pk,
                },
            },
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkUpdateComment": [
            {
                "contents": "Updated comment",
                "target": {
                    "name": "Test task",
                },
            },
        ],
    }

    response.assert_query_count(6)
