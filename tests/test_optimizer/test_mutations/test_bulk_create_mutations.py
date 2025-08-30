from __future__ import annotations

from typing import Any

import pytest
from django.contrib.contenttypes.models import ContentType

from example_project.app.models import (
    Comment,
    Person,
    Project,
    Report,
    ServiceRequest,
    Task,
    TaskResult,
    TaskStep,
    TaskTypeChoices,
)
from tests.factories import PersonFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.utils.mutation_tree import mutate


@pytest.mark.django_db
def test_mutation_optimization__bulk_create(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
            },
        ],
    }

    response.assert_query_count(2)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__forward__one_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ServiceRequestType(QueryType[ServiceRequest], auto=False):
        details = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        request = Field(ServiceRequestType)

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            request {
              details
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "request": {
                "details": "Test request",
            },
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "request": {
                    "details": "Test request",
                },
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__forward__many_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    # MutationTypes

    class ProjectMutation(MutationType[Project], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        project = Input(ProjectMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            project {
              name
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "project": {
                "name": "Test project",
            },
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "project": {
                    "name": "Test project",
                },
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__forward__many_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        assignees = Field(PersonType)

    # MutationTypes

    class PersonMutation(MutationType[Person], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        assignees = Input(PersonMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            assignees {
              name
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "assignees": [
                {
                    "name": "Test person",
                },
            ],
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "assignees": [
                    {
                        "name": "Test person",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__reverse__one_to_one(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskResultType(QueryType[TaskResult], auto=False):
        details = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        result = Field(TaskResultType)

    # MutationTypes

    class TaskResultMutation(MutationType[TaskResult], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        result = Input(TaskResultMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            result {
              details
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "result": {
                "details": "Test result",
                "timeUsed": 0,
            },
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "result": {
                    "details": "Test result",
                },
            },
        ],
    }

    response.assert_query_count(3)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__reverse__one_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskStepType(QueryType[TaskStep], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        steps = Field(TaskStepType)

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            steps {
              name
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "steps": [
                {
                    "name": "Test step",
                },
            ],
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "steps": [
                    {
                        "name": "Test step",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(4)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__reverse__many_to_many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class ReportType(QueryType[Report], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        reports = Field(ReportType)

    # MutationTypes

    class ReportMutation(MutationType[Report], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        reports = Input(ReportMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_tasks = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTasks(input: $input) {
            name
            reports {
              name
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "reports": [
                {
                    "name": "Test report",
                    "content": "Test report content",
                },
            ],
        },
    ]

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTasks": [
            {
                "name": "Test task",
                "reports": [
                    {
                        "name": "Test report",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(7)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__generic_relation(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        comments = Field(CommentType)

    # MutationTypes

    class CommentMutation(MutationType[Comment], kind="related"): ...

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        comments = Input(CommentMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return mutate(model=Task, data=input_data)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create()

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
            comments {
              contents
            }
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.STORY.value,
            "comments": [
                {
                    "contents": "Test comment",
                    "commenter": person.pk,
                },
            ],
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test task",
                "comments": [
                    {
                        "contents": "Test comment",
                    },
                ],
            },
        ],
    }

    response.assert_query_count(5)


@pytest.mark.django_db
def test_mutation_optimization__bulk_create__generic_foreign_key(graphql, undine_settings) -> None:
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

    class CommentCreateMutation(MutationType[Comment], auto=False):
        contents = Input()
        target = Input()

        @classmethod
        def __bulk_mutate__(cls, instances: list[Comment], info: GQLInfo, input_data: list[dict[str, Any]]) -> Any:
            return mutate(model=Comment, data=input_data)

    # RootTypes

    class Query(RootType):
        comments = Entrypoint(CommentType)

    class Mutation(RootType):
        bulk_create_comment = Entrypoint(CommentCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test project")
    task = TaskFactory.create(name="Test task", project=project)

    # Cache content types
    ContentType.objects.get_for_model(Task)
    ContentType.objects.get_for_model(Project)
    ContentType.objects.get_for_model(Comment)

    query = """
        mutation ($input: [CommentCreateMutation!]!) {
          bulkCreateComment(input: $input) {
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
            "contents": "Test comment",
            "target": {
                "task": {
                    "pk": task.pk,
                },
            },
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.data == {
        "bulkCreateComment": [
            {
                "contents": "Test comment",
                "target": {
                    "name": "Test task",
                },
            },
        ],
    }

    # Check that total queries match
    response.assert_query_count(4)
