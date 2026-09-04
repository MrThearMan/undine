from __future__ import annotations

import datetime
from copy import deepcopy
from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async
from graphql import GraphQLField, GraphQLInt, GraphQLNonNull, GraphQLObjectType

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
from tests.factories import (
    PersonFactory,
    ProjectFactory,
    ReportFactory,
    ServiceRequestFactory,
    TaskResultFactory,
    TaskStepFactory,
)
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError
from undine.utils.graphql.type_registry import get_or_create_graphql_object_type


@pytest.mark.django_db
def test_create_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "createTask": {
            "name": "Test Task",
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_one(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": {
            "name": "Test Project",
        },
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
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
        "createTask": {
            "name": "Test Task",
            "project": {
                "name": "Test Project",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_one__existing(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test Project")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": {
            "pk": project.pk,
        },
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
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
        "createTask": {
            "name": "Test Task",
            "project": {
                "name": "Test Project",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__one_to_many(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskStepType(QueryType[TaskStep]): ...

    class RelatedTaskStep(MutationType[TaskStep], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        steps = Input(RelatedTaskStep)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "steps": [
            {
                "name": "Test Step",
            },
        ],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "createTask": {
            "name": "Test Task",
            "steps": [
                {
                    "name": "Test Step",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_many(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "assignees": [
            {
                "name": "Test Person",
                "email": "test@example.com",
            },
        ],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
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
        "createTask": {
            "name": "Test Task",
            "assignees": [
                {
                    "name": "Test Person",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_many__existing(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskCreateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create(name="Test Person")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "assignees": [
            {
                "pk": person.pk,
            },
        ],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
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
        "createTask": {
            "name": "Test Task",
            "assignees": [
                {
                    "name": "Test Person",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__after(graphql, undine_settings):
    after_data = {}

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data = deepcopy(input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert after_data == {
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
        "type": "TASK",
    }


@pytest.mark.django_db
def test_create_mutation__input_only(graphql, undine_settings):
    original_input_data = {}

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal original_input_data
            original_input_data = deepcopy(input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert original_input_data == {
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
    }


@pytest.mark.django_db
def test_create_mutation__related_int(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(int, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create()

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(pk=response.results["pk"])

    assert task.project == project

    assert related_input == project.pk

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "name": "Test Task",
        },
    }


@pytest.mark.django_db
def test_create_mutation__related_model(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(Project, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create()

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(pk=response.results["pk"])

    assert task.project == project

    assert related_input == project

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "name": "Test Task",
        },
    }


@pytest.mark.django_db
def test_create_mutation__related_hidden_input(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @Input(hidden=True)
        def project(self, info: GQLInfo) -> Project:
            return project

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create()

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(pk=response.results["pk"])

    assert task.project == project

    assert response.data == {
        "createTask": {
            "pk": task.pk,
        },
    }


@pytest.mark.django_db
def test_create_mutation__related_different_name(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        project = Input(schema_name="group")

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create()

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "group": project.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(pk=response.results["pk"])
    assert task.project == project

    assert response.data == {
        "createTask": {
            "pk": task.pk,
        },
    }


@pytest.mark.django_db
def test_create_mutation__hidden_input(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @Input(hidden=True)
        def type(self, info: GQLInfo) -> TaskTypeChoices:
            return TaskTypeChoices.TASK

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
                type
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "createTask": {
            "name": "Test Task",
            "type": "TASK",
        },
    }


@pytest.mark.django_db
def test_create_mutation__input_only_input(graphql, undine_settings):
    input_only_data = None

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = input_data["foo"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.STORY,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "createTask": {
            "name": "Test Task",
        },
    }

    assert input_only_data == "bar"


@pytest.mark.django_db
def test_create_mutation__generic_relation(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task]):
        name = Field()

    class CommentType(QueryType[Comment]):
        contents = Field()
        target = Field()

    class CommentCreateMutation(MutationType[Comment]):
        contents = Input()
        target = Input()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    class Mutation(RootType):
        create_comment = Entrypoint(CommentCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation($input: CommentCreateMutation!) {
            createComment(input: $input) {
                contents
                target {
                    __typename
                    ... on TaskType {
                        name
                    }
                }
            }
        }
    """
    input_data = {
        "contents": "Comment",
        "target": {
            "task": {
                "name": "Test Task",
                "type": TaskTypeChoices.TASK,
            }
        },
    }
    response = graphql(query, variables={"input": input_data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "createComment": {
            "contents": "Comment",
            "target": {
                "__typename": "TaskType",
                "name": "Test Task",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__atomic_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class ProjectCreateMutation(MutationType[Project]):
        @classmethod
        def __permissions__(cls, instance: Project, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class Query(RootType):
        tasks = Entrypoint(TaskType)
        projects = Entrypoint(ProjectType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)
        create_project = Entrypoint(ProjectCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    project_data = {
        "name": "Test Project",
    }
    # Important: create task first and project second
    query = """
        mutation($taskInput: TaskCreateMutation! $projectInput: ProjectCreateMutation!) @atomic {
            createTask(input: $taskInput) {
                name
            }
            createProject(input: $projectInput) {
                name
            }
        }
    """

    assert Task.objects.count() == 0
    assert Project.objects.count() == 0

    response = graphql(query, variables={"taskInput": task_data, "projectInput": project_data})

    if undine_settings.ASYNC:
        assert response.errors == [
            {
                "message": "Atomic mutations are not supported when using async views.",
                "extensions": {"error_code": "ASYNC_ATOMIC_MUTATION_NOT_SUPPORTED", "status_code": 500},
            }
        ]
    else:
        assert response.errors == [
            {
                "message": "Permission denied.",
                "path": ["createProject"],
                "extensions": {"error_code": "PERMISSION_DENIED", "status_code": 403},
            }
        ]

    # Since project creation fails, task creation is rolled back with atomic.
    assert Task.objects.count() == 0
    assert Project.objects.count() == 0


@pytest.mark.django_db(transaction=True)
async def test_create_mutation__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.STORY,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                name
                type
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = await sync_to_async(Task.objects.get)(name="Test Task")

    assert task.type == TaskTypeChoices.STORY

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "name": "Test Task",
            "type": "STORY",
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__forward_one_to_one(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class RelatedRequest(MutationType[ServiceRequest], kind="related"):
        details = Input()

    class TaskCreateMutation(MutationType[Task]):
        request = Input(RelatedRequest)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "request": {
            "details": "Test Request",
        },
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")
    request = ServiceRequest.objects.get(details="Test Request")

    assert task.request == request

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "request": {
                "details": "Test Request",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__forward_one_to_one__pk(graphql, undine_settings):
    class ServiceRequestType(QueryType[ServiceRequest]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    request = ServiceRequestFactory.create(details="Test Request")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "request": request.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                request {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")

    assert task.request == request

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "request": {
                "details": "Test Request",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_one__pk(graphql, undine_settings):
    class ProjectType(QueryType[Project]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test Project")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                project {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")

    assert task.project == project
    assert list(project.tasks.all()) == [task]

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "project": {
                "name": "Test Project",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__many_to_many__pk(graphql, undine_settings):
    class PersonType(QueryType[Person]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create(name="Test Person")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "assignees": [person.pk],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                assignees {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")

    assert list(task.assignees.all()) == [person]
    assert list(person.tasks.all()) == [task]

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "assignees": [
                {
                    "name": "Test Person",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__reverse_one_to_one(graphql, undine_settings):
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
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "result": {
            "details": "Test Result",
            "timeUsed": 10,
        },
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")
    result = TaskResult.objects.get(details="Test Result")

    assert task.result == result
    assert result.task == task
    assert result.time_used == datetime.timedelta(seconds=10)

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "result": {
                "details": "Test Result",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__reverse_one_to_one__pk(graphql, undine_settings):
    class TaskResultType(QueryType[TaskResult]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    result = TaskResultFactory.create(details="Test Result")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "result": result.pk,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                result {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")
    result.refresh_from_db()

    assert task.result == result
    assert result.task == task

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "result": {
                "details": "Test Result",
            },
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__reverse_one_to_many__pk(graphql, undine_settings):
    class TaskStepType(QueryType[TaskStep]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    step = TaskStepFactory.create(name="Test Step")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "steps": [step.pk],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")
    step.refresh_from_db()

    assert list(task.steps.all()) == [step]
    assert step.task == task

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "steps": [
                {
                    "name": "Test Step",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__reverse_many_to_many(graphql, undine_settings):
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
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "reports": [
            {
                "name": "Test Report",
                "content": "Test Report Content",
            },
        ],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")
    report = Report.objects.get(name="Test Report")

    assert list(task.reports.all()) == [report]
    assert list(report.tasks.all()) == [task]

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "reports": [
                {
                    "name": "Test Report",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__relations__reverse_many_to_many__pk(graphql, undine_settings):
    class ReportType(QueryType[Report]): ...

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    report = ReportFactory.create(name="Test Report")

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "reports": [str(report.pk)],
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
                reports {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")

    assert list(task.reports.all()) == [report]
    assert list(report.tasks.all()) == [task]

    assert response.data == {
        "createTask": {
            "pk": task.pk,
            "reports": [
                {
                    "name": "Test Report",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_create_mutation__hooks__call_order(graphql, undine_settings):
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
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.STORY,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(name="Test Task")

    assert response.data == {"createTask": {"pk": task.pk}}

    assert permission_called == 0
    assert input_permission_called == 1
    assert input_validate_called == 2
    assert validate_called == 3
    assert after_called == 4


@pytest.mark.django_db
def test_create_mutation__non_model_return(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            return {"foo": 1}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"foo": GraphQLField(GraphQLNonNull(GraphQLInt))}
            return get_or_create_graphql_object_type(name="TaskCreateMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.STORY,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                foo
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {"createTask": {"foo": 1}}

    assert Task.objects.count() == 0


@pytest.mark.django_db(transaction=True)
async def test_create_mutation__non_model_return__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __mutate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> dict[str, Any]:
            return {"foo": 1}

        @classmethod
        def __output_type__(cls) -> GraphQLObjectType:
            fields = {"foo": GraphQLField(GraphQLNonNull(GraphQLInt))}
            return get_or_create_graphql_object_type(name="TaskCreateMutationOutput", fields=fields)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    data = {
        "name": "Test Task",
        "type": TaskTypeChoices.STORY,
    }
    query = """
        mutation($input: TaskCreateMutation!) {
            createTask(input: $input) {
                foo
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {"createTask": {"foo": 1}}

    assert await sync_to_async(Task.objects.count)() == 0
