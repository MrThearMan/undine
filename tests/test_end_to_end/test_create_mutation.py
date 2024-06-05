from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import Person, Project, Task, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema


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
def test_create_mutation__relations__to_one(graphql, undine_settings):
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
def test_create_mutation__relations__to_one__existing(graphql, undine_settings):
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
def test_create_mutation__relations__to_many(graphql, undine_settings):
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
def test_create_mutation__relations__to_many__existing(graphql, undine_settings):
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
def test_create_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 0

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

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Cannot mutate more than 0 objects in a single mutation.",
                "extensions": {
                    "error_code": "MUTATION_TOO_MANY_OBJECTS",
                    "status_code": 400,
                },
                "path": ["createTask"],
            }
        ],
    }


@pytest.mark.django_db
def test_create_mutation__after(graphql, undine_settings):
    after_data: dict[str, Any] = {}

    class TaskType(QueryType[Task]): ...

    class TaskCreateMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data = deepcopy(previous_data)

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

    assert after_data == {}


@pytest.mark.django_db
def test_create_mutation__input_only(graphql, undine_settings):
    original_input_data: dict[str, Any] = {}

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
        "comments": None,
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
