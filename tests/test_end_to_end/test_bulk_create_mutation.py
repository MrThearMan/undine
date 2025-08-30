from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import Person, Project, Task, TaskTypeChoices
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
                "message": "Cannot mutate more than 1 objects in a single mutation (counted 2).",
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
