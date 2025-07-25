from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import Person, Project, Task, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory, TaskFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_update_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
            "name": "Test Task",
        },
    }


@pytest.mark.django_db
def test_update_mutation__relations__to_one(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": {
            "name": "Test Project",
        },
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
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
        "updateTask": {
            "pk": task.pk,
            "name": "Test Task",
            "project": {
                "name": "Test Project",
            },
        },
    }


@pytest.mark.django_db
def test_update_mutation__relations__to_one__existing(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Test Project")
    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": {
            "pk": project.pk,
        },
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                name
                project {
                    pk
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
            "name": "Test Task",
            "project": {
                "pk": project.pk,
                "name": "Test Project",
            },
        },
    }


@pytest.mark.django_db
def test_update_mutation__relations__to_many(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
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
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
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
        "updateTask": {
            "pk": task.pk,
            "name": "Test Task",
            "assignees": [
                {
                    "name": "Test Person",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_update_mutation__relations__to_many__existing(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class PersonType(QueryType[Person]): ...

    class RelatedAssignee(MutationType[Person], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        assignees = Input(RelatedAssignee)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    person = PersonFactory.create(name="Test Person")
    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "assignees": [
            {
                "pk": person.pk,
            },
        ],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                name
                assignees {
                    pk
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
            "name": "Test Task",
            "assignees": [
                {
                    "pk": person.pk,
                    "name": "Test Person",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_update_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 0

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
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
                "message": "Cannot mutate more than 0 objects in a single mutation.",
                "extensions": {
                    "error_code": "MUTATION_TOO_MANY_OBJECTS",
                    "status_code": 400,
                },
                "path": ["updateTask"],
            }
        ],
    }


@pytest.mark.django_db
def test_update_mutation__after(graphql, undine_settings):
    after_data: dict[str, Any] = {}

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data = previous_data

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create(name="Original Task", type=TaskTypeChoices.TASK)

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert after_data == {"pk": task.pk, "name": "Original Task", "type": "TASK"}


@pytest.mark.django_db
def test_update_mutation__after__relations(graphql, undine_settings):
    after_data: dict[str, Any] = {}
    related_after_data: dict[str, Any] = {}

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"):
        @classmethod
        def __after__(cls, instance: Project, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal related_after_data
            related_after_data = deepcopy(previous_data)

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(RelatedProject)

        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, previous_data: dict[str, Any]) -> None:
            nonlocal after_data
            after_data = deepcopy(previous_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    project = ProjectFactory.create(name="Original Project")
    task = TaskFactory.create(name="Original Task", type=TaskTypeChoices.STORY, project=project)

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "project": {
            "pk": project.pk,
            "name": "Test Project",
        },
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
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

    assert after_data == {
        "pk": task.pk,
        "name": "Original Task",
        "type": "STORY",
    }

    assert related_after_data == {
        "pk": project.pk,
        "name": "Original Project",
    }


@pytest.mark.django_db
def test_update_mutation__input_only(graphql, undine_settings):
    original_input_data: dict[str, Any] = {}

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal original_input_data
            original_input_data = deepcopy(input_data)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                name
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert original_input_data == {
        "pk": task.pk,
        "foo": "bar",
        "name": "Test Task",
        "type": "TASK",
    }
