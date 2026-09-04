from __future__ import annotations

import datetime
from collections import defaultdict
from copy import deepcopy
from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async

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
    Team,
)
from tests.factories import (
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskFactory,
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.utils.mutation_tree import mutate


@pytest.mark.django_db
def test_bulk_update_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "name": "Test Task",
            },
            {
                "pk": task_2.pk,
                "name": "Real Task",
            },
        ],
    }

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.name == "Test Task"
    assert task_1.type == TaskTypeChoices.TASK
    assert task_2.name == "Real Task"
    assert task_2.type == TaskTypeChoices.STORY


@pytest.mark.django_db
def test_bulk_update_mutation__relations__to_one(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
            return mutate(model=Task, data=input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": {
                "name": "Test Project",
            },
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": {
                "name": "Real Project",
            },
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
                project {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "name": "Test Task",
                "project": {
                    "name": "Test Project",
                },
            },
            {
                "pk": task_2.pk,
                "name": "Real Task",
                "project": {
                    "name": "Real Project",
                },
            },
        ],
    }

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.name == "Test Task"
    assert task_2.name == "Real Task"
    assert task_1.project == Project.objects.get(name="Test Project")
    assert task_2.project == Project.objects.get(name="Real Project")


@pytest.mark.django_db
def test_bulk_update_mutation__relations__to_many(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
            return mutate(model=Task, data=input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "assignees": [
                {
                    "name": "Test Person",
                    "email": "test@example.com",
                },
            ],
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "assignees": [
                {
                    "name": "Real Person",
                    "email": "real@example.com",
                },
            ],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
                assignees {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "name": "Test Task",
                "assignees": [
                    {
                        "name": "Test Person",
                    },
                ],
            },
            {
                "pk": task_2.pk,
                "name": "Real Task",
                "assignees": [
                    {
                        "name": "Real Person",
                    },
                ],
            },
        ],
    }

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.name == "Test Task"
    assert task_2.name == "Real Task"
    assert list(task_1.assignees.all()) == [Person.objects.get(name="Test Person")]
    assert list(task_2.assignees.all()) == [Person.objects.get(name="Real Person")]


@pytest.mark.django_db
def test_bulk_update_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Cannot mutate more than 1 objects in a single request (counted 2).",
                "extensions": {
                    "error_code": "MUTATION_TOO_MANY_OBJECTS",
                    "status_code": 400,
                },
                "path": ["bulkUpdateTask"],
            }
        ],
    }

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.name == "Original Task 1"
    assert task_2.name == "Original Task 2"


@pytest.mark.django_db
def test_bulk_update_mutation__after(graphql, undine_settings):
    after_data: list[dict[str, Any]] = []

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data.append(deepcopy(input_data))

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Original Task 2", type=TaskTypeChoices.STORY)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert after_data == [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]


@pytest.mark.django_db
def test_bulk_update_mutation__after__relations(graphql, undine_settings):
    after_data = []

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
            return mutate(model=Task, data=input_data)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data.append(deepcopy(input_data))

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project_1 = ProjectFactory.create(name="Test Project")
    project_2 = ProjectFactory.create(name="Real Project")

    task_1 = TaskFactory.create(name="Original Task 1", type=TaskTypeChoices.TASK, project=project_1)
    task_2 = TaskFactory.create(name="Original Task 2", type=TaskTypeChoices.STORY, project=project_2)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": {
                "pk": project_1.pk,
                "name": "New Test Project",
            },
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": {
                "pk": project_2.pk,
                "name": "New Real Project",
            },
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
                project {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert after_data == [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": {
                "pk": project_1.pk,
                "name": "New Test Project",
            },
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": {
                "pk": project_2.pk,
                "name": "New Real Project",
            },
        },
    ]


@pytest.mark.django_db
def test_bulk_update_mutation__input_only(graphql, undine_settings):
    original_input_data: list[dict[str, Any]] = []

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal original_input_data
            original_input_data.append(deepcopy(input_data))

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Original Task 2", type=TaskTypeChoices.STORY)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "foo": "bar",
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "foo": "baz",
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert original_input_data == [
        {
            "pk": task_1.pk,
            "foo": "bar",
            "name": "Test Task",
            "type": "TASK",
        },
        {
            "pk": task_2.pk,
            "foo": "baz",
            "name": "Real Task",
            "type": "STORY",
        },
    ]


@pytest.mark.django_db
def test_bulk_update_mutation__related_object_not_found(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Original Task", request=None)

    data = [
        {
            "pk": task.pk,
            "name": "Test Task",
            "request": 1,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": "Primary key 1 on model 'example_project.app.models.ServiceRequest' did not match any row.",
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["bulkUpdateTask", 0, "request"],
        }
    ]

    task.refresh_from_db()

    assert task.name == "Original Task"
    assert task.request is None


@pytest.mark.django_db
def test_bulk_update_mutation__instance_not_found(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Original Task")
    missing_pk = task.pk + 100

    data = [
        {
            "pk": task.pk,
            "name": "Test Task",
        },
        {
            "pk": missing_pk,
            "name": "Real Task",
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": (f"Primary key {missing_pk} on model 'example_project.app.models.Task' did not match any row."),
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["bulkUpdateTask"],
        }
    ]

    task.refresh_from_db()

    assert task.name == "Original Task"


@pytest.mark.django_db
def test_bulk_update_mutation__instances_not_found(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Original Task")
    missing_pk_1 = task.pk + 100
    missing_pk_2 = task.pk + 101

    data = [
        {
            "pk": task.pk,
            "name": "Test Task",
        },
        {
            "pk": missing_pk_1,
            "name": "Real Task",
        },
        {
            "pk": missing_pk_2,
            "name": "Fake Task",
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": (
                f"Primary keys '{missing_pk_1}' and '{missing_pk_2}' on model "
                f"'example_project.app.models.Task' did not match any row."
            ),
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["bulkUpdateTask"],
        }
    ]

    task.refresh_from_db()

    assert task.name == "Original Task"


@pytest.mark.django_db
def test_bulk_update_mutation__relations__forward_one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedRequest(MutationType[ServiceRequest], kind="related"):
        details = Input()

    class TaskUpdateMutation(MutationType[Task]):
        request = Input(RelatedRequest)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", request=None)
    task_2 = TaskFactory.create(name="Original Task 2", request=None)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "request": {
                "details": "Test Request",
            },
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "request": {
                "details": "Real Request",
            },
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1.refresh_from_db()
    task_2.refresh_from_db()
    request_1 = ServiceRequest.objects.get(details="Test Request")
    request_2 = ServiceRequest.objects.get(details="Real Request")

    assert task_1.name == "Test Task"
    assert task_2.name == "Real Task"
    assert task_1.request == request_1
    assert task_2.request == request_2
    assert request_1.task == task_1
    assert request_2.task == task_2

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "name": "Test Task",
                "request": {"details": "Test Request"},
            },
            {
                "pk": task_2.pk,
                "name": "Real Task",
                "request": {"details": "Real Request"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__forward_one_to_one__pk(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", request=None)
    task_2 = TaskFactory.create(name="Original Task 2", request=None)

    request_1 = ServiceRequestFactory.create(details="Test Request")
    request_2 = ServiceRequestFactory.create(details="Real Request")

    data = [
        {
            "pk": task_1.pk,
            "request": request_1.pk,
        },
        {
            "pk": task_2.pk,
            "request": request_2.pk,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.name == "Original Task 1"
    assert task_2.name == "Original Task 2"
    assert task_1.request == request_1
    assert task_2.request == request_2
    assert request_1.task == task_1
    assert request_2.task == task_2

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "request": {"details": "Test Request"},
            },
            {
                "pk": task_2.pk,
                "request": {"details": "Real Request"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__many_to_one(graphql, undine_settings):
    class TeamType(QueryType[Team]): ...

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        name = Input()
        team = Input(Team)

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", project=None)
    task_2 = TaskFactory.create(name="Original Task 2", project=None)

    team = TeamFactory.create(name="Test Team")

    data = [
        {
            "pk": task_1.pk,
            "project": {
                "name": "Test Project",
                "team": team.pk,
            },
        },
        {
            "pk": task_2.pk,
            "project": {
                "name": "Real Project",
                "team": team.pk,
            },
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                project {
                    name
                    team {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1.refresh_from_db()
    task_2.refresh_from_db()
    project_1 = Project.objects.get(name="Test Project")
    project_2 = Project.objects.get(name="Real Project")

    assert task_1.project == project_1
    assert task_2.project == project_2
    assert list(project_1.tasks.all()) == [task_1]
    assert list(project_2.tasks.all()) == [task_2]
    assert project_1.team == team
    assert project_2.team == team

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "project": {
                    "name": "Test Project",
                    "team": {"name": "Test Team"},
                },
            },
            {
                "pk": task_2.pk,
                "project": {
                    "name": "Real Project",
                    "team": {"name": "Test Team"},
                },
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__many_to_one__pk(graphql, undine_settings):
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", project=None)
    task_2 = TaskFactory.create(name="Original Task 2", project=None)

    project = ProjectFactory.create(name="Test Project")

    data = [
        {
            "pk": task_1.pk,
            "project": project.pk,
        },
        {
            "pk": task_2.pk,
            "project": project.pk,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                project {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1.refresh_from_db()
    task_2.refresh_from_db()

    assert task_1.project == project
    assert task_2.project == project
    assert list(project.tasks.all()) == [task_1, task_2]

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "project": {"name": "Test Project"},
            },
            {
                "pk": task_2.pk,
                "project": {"name": "Test Project"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__many_to_many__pk(graphql, undine_settings):
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    person = PersonFactory.create(name="Test Person")

    data = [
        {
            "pk": task_1.pk,
            "assignees": [person.pk],
        },
        {
            "pk": task_2.pk,
            "assignees": [person.pk],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                assignees {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert list(task_1.assignees.all()) == [person]
    assert list(task_2.assignees.all()) == [person]
    assert list(person.tasks.all()) == [task_1, task_2]

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "assignees": [{"name": "Test Person"}],
            },
            {
                "pk": task_2.pk,
                "assignees": [{"name": "Test Person"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_one_to_one(graphql, undine_settings):
    class TaskResultType(QueryType[TaskResult]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedResult(MutationType[TaskResult], kind="related"):
        details = Input()
        time_used = Input()

    class TaskUpdateMutation(MutationType[Task]):
        result = Input(RelatedResult)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    data = [
        {
            "pk": task_1.pk,
            "result": {
                "details": "Test Result",
                "timeUsed": 10,
            },
        },
        {
            "pk": task_2.pk,
            "result": {
                "details": "Real Result",
                "timeUsed": 20,
            },
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    result_1 = TaskResult.objects.get(details="Test Result")
    result_2 = TaskResult.objects.get(details="Real Result")

    assert result_1.task == task_1
    assert result_2.task == task_2
    assert result_1.time_used == datetime.timedelta(seconds=10)
    assert result_2.time_used == datetime.timedelta(seconds=20)

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "result": {"details": "Test Result"},
            },
            {
                "pk": task_2.pk,
                "result": {"details": "Real Result"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_one_to_one__pk(graphql, undine_settings):
    class TaskResultType(QueryType[TaskResult]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    result_1 = TaskResultFactory.create(details="Test Result")
    result_2 = TaskResultFactory.create(details="Real Result")

    data = [
        {
            "pk": task_1.pk,
            "result": result_1.pk,
        },
        {
            "pk": task_2.pk,
            "result": result_2.pk,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    result_1.refresh_from_db()
    result_2.refresh_from_db()

    assert result_1.task == task_1
    assert result_2.task == task_2

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "result": {"details": "Test Result"},
            },
            {
                "pk": task_2.pk,
                "result": {"details": "Real Result"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType[TaskStep]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedStep(MutationType[TaskStep], kind="related"):
        name = Input()

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedStep, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    data = [
        {
            "pk": task_1.pk,
            "steps": [{"name": "Test Step"}],
        },
        {
            "pk": task_2.pk,
            "steps": [{"name": "Real Step"}],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    step_1 = TaskStep.objects.get(name="Test Step")
    step_2 = TaskStep.objects.get(name="Real Step")

    assert list(task_1.steps.all()) == [step_1]
    assert list(task_2.steps.all()) == [step_2]
    assert step_1.task == task_1
    assert step_2.task == task_2

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "steps": [{"name": "Test Step"}],
            },
            {
                "pk": task_2.pk,
                "steps": [{"name": "Real Step"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_one_to_many__pk(graphql, undine_settings):
    class TaskStepType(QueryType[TaskStep]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    step_1 = TaskStepFactory.create(name="Test Step")
    step_2 = TaskStepFactory.create(name="Real Step")

    data = [
        {
            "pk": task_1.pk,
            "steps": [step_1.pk],
        },
        {
            "pk": task_2.pk,
            "steps": [step_2.pk],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    step_1.refresh_from_db()
    step_2.refresh_from_db()

    assert list(task_1.steps.all()) == [step_1]
    assert list(task_2.steps.all()) == [step_2]
    assert step_1.task == task_1
    assert step_2.task == task_2

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "steps": [{"name": "Test Step"}],
            },
            {
                "pk": task_2.pk,
                "steps": [{"name": "Real Step"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_many_to_many(graphql, undine_settings):
    class ReportType(QueryType[Report]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedReport(MutationType[Report], kind="related"):
        name = Input()
        content = Input()

    class TaskUpdateMutation(MutationType[Task]):
        reports = Input(RelatedReport, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    data = [
        {
            "pk": task_1.pk,
            "reports": [{"name": "Test Report", "content": "Test Content"}],
        },
        {
            "pk": task_2.pk,
            "reports": [{"name": "Real Report", "content": "Real Content"}],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    report_1 = Report.objects.get(name="Test Report")
    report_2 = Report.objects.get(name="Real Report")

    assert list(task_1.reports.all()) == [report_1]
    assert list(task_2.reports.all()) == [report_2]
    assert list(report_1.tasks.all()) == [task_1]
    assert list(report_2.tasks.all()) == [task_2]

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "reports": [{"name": "Test Report"}],
            },
            {
                "pk": task_2.pk,
                "reports": [{"name": "Real Report"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__relations__reverse_many_to_many__pk(graphql, undine_settings):
    class ReportType(QueryType[Report]): ...

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    report_1 = ReportFactory.create(name="Test Report")
    report_2 = ReportFactory.create(name="Real Report")

    data = [
        {
            "pk": task_1.pk,
            "reports": [str(report_1.pk)],
        },
        {
            "pk": task_2.pk,
            "reports": [str(report_2.pk)],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert list(task_1.reports.all()) == [report_1]
    assert list(task_2.reports.all()) == [report_2]
    assert list(report_1.tasks.all()) == [task_1]
    assert list(report_2.tasks.all()) == [task_2]

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "reports": [{"name": "Test Report"}],
            },
            {
                "pk": task_2.pk,
                "reports": [{"name": "Real Report"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__generic_relation(graphql, undine_settings):
    class PersonType(QueryType[Person]): ...

    class CommentType(QueryType[Comment]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedComment(MutationType[Comment], kind="related"):
        contents = Input()
        commenter = Input(Person)

    class TaskUpdateMutation(MutationType[Task]):
        comments = Input(RelatedComment, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    commenter = PersonFactory.create(name="Test Person")

    data = [
        {
            "pk": task_1.pk,
            "comments": [{"contents": "Test Comment", "commenter": commenter.pk}],
        },
        {
            "pk": task_2.pk,
            "comments": [{"contents": "Real Comment", "commenter": commenter.pk}],
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                comments {
                    contents
                    commenter {
                        name
                    }
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    comment_1 = Comment.objects.get(contents="Test Comment")
    comment_2 = Comment.objects.get(contents="Real Comment")

    assert list(task_1.comments.all()) == [comment_1]
    assert list(task_2.comments.all()) == [comment_2]
    assert comment_1.target == task_1
    assert comment_2.target == task_2
    assert comment_1.commenter == commenter
    assert comment_2.commenter == commenter

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "comments": [
                    {
                        "contents": "Test Comment",
                        "commenter": {"name": "Test Person"},
                    },
                ],
            },
            {
                "pk": task_2.pk,
                "comments": [
                    {
                        "contents": "Real Comment",
                        "commenter": {"name": "Test Person"},
                    },
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_update_mutation__hooks__call_order(graphql, undine_settings):
    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

        @name.validate
        def _(self: Task, info: GQLInfo, value: str) -> None:
            nonlocal input_validate_called
            input_validate_called = next(counter)

        @name.permissions
        def _(self: Task, info: GQLInfo, value: str) -> None:
            nonlocal input_permission_called
            input_permission_called = next(counter)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal validate_called
            validate_called = next(counter)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal permission_called
            permission_called = next(counter)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_called
            after_called = next(counter)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Original Task")

    data = [
        {
            "pk": task.pk,
            "name": "Test Task",
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {"bulkUpdateTask": [{"pk": task.pk, "name": "Test Task"}]}

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db
def test_bulk_update_mutation__hooks__correct_instance_pairing(graphql, undine_settings):
    # hook_name -> [instance.pk, ...] in the order each hook was called.
    recorded: dict[str, list[int]] = defaultdict(list)

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

        @name.permissions
        def _(self: Task, info: GQLInfo, value: str) -> None:
            recorded["field_permissions"].append(self.pk)

        @name.validate
        def _(self: Task, info: GQLInfo, value: str) -> None:
            recorded["field_validate"].append(self.pk)

        @Input
        def points(self: Task, info: GQLInfo, value: int) -> int:
            recorded["function_input"].append(self.pk)
            return value

        @Input(hidden=True)
        def type(self: Task, info: GQLInfo) -> str:
            recorded["hidden_input"].append(self.pk)
            return self.type

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["class_permissions"].append(instance.pk)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["class_validate"].append(instance.pk)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["after"].append(instance.pk)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1", type=TaskTypeChoices.TASK)
    task_2 = TaskFactory.create(name="Original Task 2", type=TaskTypeChoices.STORY)

    # Client input is in the reverse order of the tasks' creation (database) order.
    data = [
        {"pk": task_2.pk, "name": "Task Two", "points": 2},
        {"pk": task_1.pk, "name": "Task One", "points": 1},
    ]
    expected_pk_order = [row["pk"] for row in data]

    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert set(recorded) == {
        "field_permissions",
        "field_validate",
        "function_input",
        "hidden_input",
        "class_permissions",
        "class_validate",
        "after",
    }
    for hook_name, pks in recorded.items():
        assert pks == expected_pk_order, hook_name


@pytest.mark.django_db(transaction=True)
async def test_bulk_update_mutation__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = await sync_to_async(TaskFactory.create)(name="Original Task 1", type=TaskTypeChoices.STORY)
    task_2 = await sync_to_async(TaskFactory.create)(name="Original Task 2", type=TaskTypeChoices.BUG_FIX)

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
            "type": TaskTypeChoices.BUG_FIX,
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
                type
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkUpdateTask": [
            {
                "pk": task_1.pk,
                "name": "Test Task",
                "type": "BUG_FIX",
            },
            {
                "pk": task_2.pk,
                "name": "Real Task",
                "type": "STORY",
            },
        ],
    }

    await sync_to_async(task_1.refresh_from_db)()
    await sync_to_async(task_2.refresh_from_db)()

    assert task_1.name == "Test Task"
    assert task_1.type == TaskTypeChoices.BUG_FIX
    assert task_2.name == "Real Task"
    assert task_2.type == TaskTypeChoices.STORY


@pytest.mark.django_db(transaction=True)
async def test_bulk_update_mutation__mutation_instance_limit__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    task_1 = await sync_to_async(TaskFactory.create)(name="Original Task 1")
    task_2 = await sync_to_async(TaskFactory.create)(name="Original Task 2")

    data = [
        {
            "pk": task_1.pk,
            "name": "Test Task",
        },
        {
            "pk": task_2.pk,
            "name": "Real Task",
        },
    ]
    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Cannot mutate more than 1 objects in a single request (counted 2).",
                "extensions": {
                    "error_code": "MUTATION_TOO_MANY_OBJECTS",
                    "status_code": 400,
                },
                "path": ["bulkUpdateTask"],
            }
        ],
    }

    await sync_to_async(task_1.refresh_from_db)()
    await sync_to_async(task_2.refresh_from_db)()

    assert task_1.name == "Original Task 1"
    assert task_2.name == "Original Task 2"


@pytest.mark.django_db(transaction=True)
async def test_bulk_update_mutation__hooks__correct_instance_pairing__async(graphql_async, undine_settings):
    # hook_name -> [instance.pk, ...] in the order each hook was called.
    recorded: dict[str, list[int]] = defaultdict(list)

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        name = Input()

        @name.permissions
        def _(self: Task, info: GQLInfo, value: str) -> None:
            recorded["field_permissions"].append(self.pk)

        @name.validate
        def _(self: Task, info: GQLInfo, value: str) -> None:
            recorded["field_validate"].append(self.pk)

        @Input
        def points(self: Task, info: GQLInfo, value: int) -> int:
            recorded["function_input"].append(self.pk)
            return value

        @Input(hidden=True)
        def type(self: Task, info: GQLInfo) -> str:
            recorded["hidden_input"].append(self.pk)
            return self.type

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["class_permissions"].append(instance.pk)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["class_validate"].append(instance.pk)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            recorded["after"].append(instance.pk)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_update_task = Entrypoint(TaskUpdateMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = await sync_to_async(TaskFactory.create)(name="Original Task 1", type=TaskTypeChoices.TASK)
    task_2 = await sync_to_async(TaskFactory.create)(name="Original Task 2", type=TaskTypeChoices.STORY)

    # Client input is in the reverse order of the tasks' creation (database) order.
    data = [
        {"pk": task_2.pk, "name": "Task Two", "points": 2},
        {"pk": task_1.pk, "name": "Task One", "points": 1},
    ]
    expected_pk_order = [row["pk"] for row in data]

    query = """
        mutation($input: [TaskUpdateMutation!]!) {
            bulkUpdateTask(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert set(recorded) == {
        "field_permissions",
        "field_validate",
        "function_input",
        "hidden_input",
        "class_permissions",
        "class_validate",
        "after",
    }
    for hook_name, pks in recorded.items():
        assert pks == expected_pk_order, hook_name
