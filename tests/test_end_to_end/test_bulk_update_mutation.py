from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import Person, Project, Task, TaskTypeChoices
from tests.factories import ProjectFactory, TaskFactory
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

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Cannot mutate more than 1 objects in a single mutation (counted 2).",
                "extensions": {
                    "error_code": "MUTATION_TOO_MANY_OBJECTS",
                    "status_code": 400,
                },
                "path": ["bulkUpdateTask"],
            }
        ],
    }


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
