from __future__ import annotations

import datetime
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
    TaskResultFactory,
    TaskStepFactory,
    TeamFactory,
)
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.utils.mutation_tree import mutate


@pytest.mark.django_db
def test_bulk_create_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
            },
            {
                "name": "Real Task",
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__to_one(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
            return mutate(model=Task, data=input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": {
                "name": "Test Project",
            },
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": {
                "name": "Real Project",
            },
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
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
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "project": {
                    "name": "Test Project",
                },
            },
            {
                "name": "Real Task",
                "project": {
                    "name": "Real Project",
                },
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__to_many(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: list[dict[str, Any]]) -> list[Task]:
            return mutate(model=Task, data=input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
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
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
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
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "assignees": [
                    {
                        "name": "Test Person",
                    },
                ],
            },
            {
                "name": "Real Task",
                "assignees": [
                    {
                        "name": "Real Person",
                    },
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
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
                "path": ["bulkCreateTask"],
            }
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__after(graphql, undine_settings):
    after_data: list[dict[str, Any]] = []

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data.append(deepcopy(input_data))

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert after_data == [
        {
            "attachment": None,
            "check_time": None,
            "contact_email": None,
            "demo_url": None,
            "done": False,
            "due_by": None,
            "external_uuid": None,
            "extra_data": None,
            "image": None,
            "name": "Test Task",
            "points": None,
            "progress": 0,
            "project": None,
            "request": None,
            "type": TaskTypeChoices.TASK,
        },
        {
            "attachment": None,
            "check_time": None,
            "contact_email": None,
            "demo_url": None,
            "done": False,
            "due_by": None,
            "external_uuid": None,
            "extra_data": None,
            "image": None,
            "name": "Test Task",
            "points": None,
            "progress": 0,
            "project": None,
            "request": None,
            "type": TaskTypeChoices.TASK,
        },
    ]


@pytest.mark.django_db
def test_bulk_create_mutation__input_only(graphql, undine_settings):
    original_input_data: list[dict[str, Any]] = []

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal original_input_data
            original_input_data.append(deepcopy(input_data))

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "foo": "bar",
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "foo": "baz",
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert original_input_data == [
        {
            "attachment": None,
            "check_time": None,
            "contact_email": None,
            "demo_url": None,
            "done": False,
            "due_by": None,
            "external_uuid": None,
            "extra_data": None,
            "foo": "bar",
            "image": None,
            "name": "Test Task",
            "points": None,
            "progress": 0,
            "project": None,
            "request": None,
            "type": "TASK",
        },
        {
            "attachment": None,
            "check_time": None,
            "contact_email": None,
            "demo_url": None,
            "done": False,
            "due_by": None,
            "external_uuid": None,
            "extra_data": None,
            "foo": "baz",
            "image": None,
            "name": "Real Task",
            "points": None,
            "progress": 0,
            "project": None,
            "request": None,
            "type": "STORY",
        },
    ]


@pytest.mark.django_db
def test_bulk_create_mutation__related_object_not_found(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "request": 1,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
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
            "path": ["bulkCreateTask", 0, "request"],
        }
    ]

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_bulk_create_mutation__relations__forward_one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedRequest(MutationType[ServiceRequest], kind="related"):
        details = Input()

    class TaskCreateMutation(MutationType[Task]):
        request = Input(RelatedRequest)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "request": {
                "details": "Test Request",
            },
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "request": {
                "details": "Real Request",
            },
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    request_1 = ServiceRequest.objects.get(details="Test Request")
    request_2 = ServiceRequest.objects.get(details="Real Request")

    assert task_1.request == request_1
    assert task_2.request == request_2
    assert request_1.task == task_1
    assert request_2.task == task_2

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "request": {
                    "details": "Test Request",
                },
            },
            {
                "name": "Real Task",
                "request": {
                    "details": "Real Request",
                },
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__forward_one_to_one__pk(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    request_1 = ServiceRequestFactory.create(details="Test Request")
    request_2 = ServiceRequestFactory.create(details="Real Request")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "request": request_1.pk,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "request": request_2.pk,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")

    assert task_1.request == request_1
    assert task_2.request == request_2
    assert request_1.task == task_1
    assert request_2.task == task_2

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "request": {
                    "details": "Test Request",
                },
            },
            {
                "name": "Real Task",
                "request": {
                    "details": "Real Request",
                },
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__many_to_one(graphql, undine_settings):
    class TeamType(QueryType[Team]): ...

    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        name = Input()
        team = Input(Team)

    class TaskCreateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    team = TeamFactory.create(name="Test Team")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": {
                "name": "Test Project",
                "team": team.pk,
            },
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": {
                "name": "Real Project",
                "team": team.pk,
            },
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
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

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    project_1 = Project.objects.get(name="Test Project")
    project_2 = Project.objects.get(name="Real Project")

    assert task_1.project == project_1
    assert task_2.project == project_2
    assert list(project_1.tasks.all()) == [task_1]
    assert list(project_2.tasks.all()) == [task_2]
    assert project_1.team == team
    assert project_2.team == team

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "project": {
                    "name": "Test Project",
                    "team": {"name": "Test Team"},
                },
            },
            {
                "name": "Real Task",
                "project": {
                    "name": "Real Project",
                    "team": {"name": "Test Team"},
                },
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__many_to_one__pk(graphql, undine_settings):
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test Project")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "project": project.pk,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "project": project.pk,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                project {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")

    assert task_1.project == project
    assert task_2.project == project
    assert list(project.tasks.all()) == [task_1, task_2]

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "project": {"name": "Test Project"},
            },
            {
                "name": "Real Task",
                "project": {"name": "Test Project"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__many_to_many__pk(graphql, undine_settings):
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create(name="Test Person")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "assignees": [person.pk],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "assignees": [person.pk],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                assignees {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")

    assert list(task_1.assignees.all()) == [person]
    assert list(task_2.assignees.all()) == [person]
    assert list(person.tasks.all()) == [task_1, task_2]

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "assignees": [{"name": "Test Person"}],
            },
            {
                "name": "Real Task",
                "assignees": [{"name": "Test Person"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_one_to_one(graphql, undine_settings):
    class TaskResultType(QueryType[TaskResult]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedResult(MutationType[TaskResult], kind="related"):
        details = Input()
        time_used = Input()

    class TaskCreateMutation(MutationType[Task]):
        result = Input(RelatedResult)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "result": {
                "details": "Test Result",
                "timeUsed": 10,
            },
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "result": {
                "details": "Real Result",
                "timeUsed": 20,
            },
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    result_1 = TaskResult.objects.get(details="Test Result")
    result_2 = TaskResult.objects.get(details="Real Result")

    assert task_1.result == result_1
    assert task_2.result == result_2
    assert result_1.task == task_1
    assert result_2.task == task_2
    assert result_1.time_used == datetime.timedelta(seconds=10)
    assert result_2.time_used == datetime.timedelta(seconds=20)

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "result": {"details": "Test Result"},
            },
            {
                "name": "Real Task",
                "result": {"details": "Real Result"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_one_to_one__pk(graphql, undine_settings):
    class TaskResultType(QueryType[TaskResult]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    result_1 = TaskResultFactory.create(details="Test Result")
    result_2 = TaskResultFactory.create(details="Real Result")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "result": result_1.pk,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "result": result_2.pk,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    result_1.refresh_from_db()
    result_2.refresh_from_db()

    assert task_1.result == result_1
    assert task_2.result == result_2
    assert result_1.task == task_1
    assert result_2.task == task_2

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "result": {"details": "Test Result"},
            },
            {
                "name": "Real Task",
                "result": {"details": "Real Result"},
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_one_to_many(graphql, undine_settings):
    class TaskStepType(QueryType[TaskStep]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedStep(MutationType[TaskStep], kind="related"):
        name = Input()

    class TaskCreateMutation(MutationType[Task]):
        steps = Input(RelatedStep, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "steps": [{"name": "Test Step"}],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "steps": [{"name": "Real Step"}],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    step_1 = TaskStep.objects.get(name="Test Step")
    step_2 = TaskStep.objects.get(name="Real Step")

    assert list(task_1.steps.all()) == [step_1]
    assert list(task_2.steps.all()) == [step_2]
    assert step_1.task == task_1
    assert step_2.task == task_2

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "steps": [{"name": "Test Step"}],
            },
            {
                "name": "Real Task",
                "steps": [{"name": "Real Step"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_one_to_many__pk(graphql, undine_settings):
    class TaskStepType(QueryType[TaskStep]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    step_1 = TaskStepFactory.create(name="Test Step")
    step_2 = TaskStepFactory.create(name="Real Step")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "steps": [step_1.pk],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "steps": [step_2.pk],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    step_1.refresh_from_db()
    step_2.refresh_from_db()

    assert list(task_1.steps.all()) == [step_1]
    assert list(task_2.steps.all()) == [step_2]
    assert step_1.task == task_1
    assert step_2.task == task_2

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "steps": [{"name": "Test Step"}],
            },
            {
                "name": "Real Task",
                "steps": [{"name": "Real Step"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_many_to_many(graphql, undine_settings):
    class ReportType(QueryType[Report]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedReport(MutationType[Report], kind="related"):
        name = Input()
        content = Input()

    class TaskCreateMutation(MutationType[Task]):
        reports = Input(RelatedReport, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "reports": [{"name": "Test Report", "content": "Test Content"}],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "reports": [{"name": "Real Report", "content": "Real Content"}],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    report_1 = Report.objects.get(name="Test Report")
    report_2 = Report.objects.get(name="Real Report")

    assert list(task_1.reports.all()) == [report_1]
    assert list(task_2.reports.all()) == [report_2]
    assert list(report_1.tasks.all()) == [task_1]
    assert list(report_2.tasks.all()) == [task_2]

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "reports": [{"name": "Test Report"}],
            },
            {
                "name": "Real Task",
                "reports": [{"name": "Real Report"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__relations__reverse_many_to_many__pk(graphql, undine_settings):
    class ReportType(QueryType[Report]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    report_1 = ReportFactory.create(name="Test Report")
    report_2 = ReportFactory.create(name="Real Report")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "reports": [str(report_1.pk)],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "reports": [str(report_2.pk)],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")

    assert list(task_1.reports.all()) == [report_1]
    assert list(task_2.reports.all()) == [report_2]
    assert list(report_1.tasks.all()) == [task_1]
    assert list(report_2.tasks.all()) == [task_2]

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "reports": [{"name": "Test Report"}],
            },
            {
                "name": "Real Task",
                "reports": [{"name": "Real Report"}],
            },
        ],
    }


@pytest.mark.django_db
def test_bulk_create_mutation__generic_relation(graphql, undine_settings):
    class PersonType(QueryType[Person]): ...

    class CommentType(QueryType[Comment]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedComment(MutationType[Comment], kind="related"):
        contents = Input()
        commenter = Input(Person)

    class TaskCreateMutation(MutationType[Task]):
        comments = Input(RelatedComment, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    commenter = PersonFactory.create(name="Test Person")

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
            "comments": [{"contents": "Test Comment", "commenter": commenter.pk}],
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
            "comments": [{"contents": "Real Comment", "commenter": commenter.pk}],
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
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

    task_1 = Task.objects.get(name="Test Task")
    task_2 = Task.objects.get(name="Real Task")
    comment_1 = Comment.objects.get(contents="Test Comment")
    comment_2 = Comment.objects.get(contents="Real Comment")

    assert list(task_1.comments.all()) == [comment_1]
    assert list(task_2.comments.all()) == [comment_2]
    assert comment_1.target == task_1
    assert comment_2.target == task_2
    assert comment_1.commenter == commenter
    assert comment_2.commenter == commenter

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "comments": [
                    {
                        "contents": "Test Comment",
                        "commenter": {"name": "Test Person"},
                    },
                ],
            },
            {
                "name": "Real Task",
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
def test_bulk_create_mutation__hooks__call_order(graphql, undine_settings):
    counter = count()

    input_validate_called: int = -1
    input_permission_called: int = -1
    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
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
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {"bulkCreateTask": [{"name": "Test Task"}]}

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db(transaction=True)
async def test_bulk_create_mutation__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
                name
                type
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "bulkCreateTask": [
            {
                "name": "Test Task",
                "type": "TASK",
            },
            {
                "name": "Real Task",
                "type": "STORY",
            },
        ],
    }

    assert await sync_to_async(Task.objects.count)() == 2


@pytest.mark.django_db(transaction=True)
async def test_bulk_create_mutation__mutation_instance_limit__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    data = [
        {
            "name": "Test Task",
            "type": TaskTypeChoices.TASK,
        },
        {
            "name": "Real Task",
            "type": TaskTypeChoices.STORY,
        },
    ]
    query = """
        mutation($input: [TaskCreateMutation!]!) {
            bulkCreateTask(input: $input) {
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
                "path": ["bulkCreateTask"],
            }
        ],
    }

    assert await sync_to_async(Task.objects.count)() == 0
