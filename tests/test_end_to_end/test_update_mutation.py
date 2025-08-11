from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import AcceptanceCriteria, Person, Project, Task, TaskStep, TaskTypeChoices
from tests.factories import AcceptanceCriteriaFactory, PersonFactory, ProjectFactory, TaskFactory, TaskStepFactory
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
def test_update_mutation__relations__many_to_one(graphql, undine_settings):
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
def test_update_mutation__relations__many_to_one__existing(graphql, undine_settings):
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
def test_update_mutation__relations__one_to_many__nullable(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class AcceptanceCriteriaType(QueryType[AcceptanceCriteria]): ...

    class RelatedAcceptanceCriteria(MutationType[AcceptanceCriteria], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        acceptancecriteria_set = Input(RelatedAcceptanceCriteria)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    AcceptanceCriteriaFactory.create(task=task)

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "acceptancecriteriaSet": [
            {
                "details": "Test Criteria",
            },
        ],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                name
                acceptancecriteriaSet {
                    details
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "name": "Test Task",
            "acceptancecriteriaSet": [
                {
                    "details": "Test Criteria",
                },
            ],
        },
    }


@pytest.mark.django_db
def test_update_mutation__relations__one_to_many__not_nullable(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskStepType(QueryType[TaskStep]): ...

    class RelatedTaskStep(MutationType[TaskStep], kind="related"): ...

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedTaskStep)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    TaskStepFactory.create(task=task)

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "steps": [
            {
                "name": "Test Step",
            },
        ],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": (
                "Field 'example_project.app.models.TaskStep.task' is not nullable. "
                "Existing relation cannot be set to null."
            ),
            "path": ["updateTask"],
            "extensions": {
                "status_code": 400,
                "error_code": "FIELD_NOT_NULLABLE",
            },
        }
    ]


@pytest.mark.django_db
def test_update_mutation__relations__one_to_many__not_nullable__remove_related(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskStepType(QueryType[TaskStep]): ...

    class RelatedTaskStep(MutationType[TaskStep], kind="related", related_action="delete"): ...

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedTaskStep)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    TaskStepFactory.create(task=task)

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "steps": [
            {
                "name": "Test Step",
            },
        ],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False

    assert response.results == {
        "name": "Test Task",
        "steps": [
            {
                "name": "Test Step",
            },
        ],
    }

    assert task.steps.count() == 1


@pytest.mark.django_db
def test_update_mutation__relations__one_to_many__not_nullable__ignore(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskStepType(QueryType[TaskStep]): ...

    class RelatedTaskStep(MutationType[TaskStep], kind="related", related_action="ignore"): ...

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedTaskStep)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    TaskStepFactory.create(task=task, name="Real Step")

    data = {
        "pk": task.pk,
        "name": "Test Task",
        "type": TaskTypeChoices.TASK,
        "steps": [
            {
                "name": "Test Step",
            },
        ],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                name
                steps {
                    name
                }
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False

    assert response.results == {
        "name": "Test Task",
        "steps": [
            {
                "name": "Real Step",
            },
            {
                "name": "Test Step",
            },
        ],
    }

    assert task.steps.count() == 2


@pytest.mark.django_db
def test_update_mutation__relations__many_to_many(graphql, undine_settings):
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
def test_update_mutation__relations__many_to_many__existing(graphql, undine_settings):
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
                "message": "Cannot mutate more than 0 objects in a single mutation (counted 1).",
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
    after_data = {}

    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class RelatedProject(MutationType[Project], kind="related"): ...

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
        "project": {
            "pk": project.pk,
            "name": "Original Project",
        },
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


@pytest.mark.django_db
def test_update_mutation__related_int(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(int, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    project = ProjectFactory.create()

    data = {
        "pk": task.pk,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task.refresh_from_db()
    assert task.project == project

    assert related_input == project.pk

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
        },
    }


@pytest.mark.django_db
@pytest.mark.skipif(os.getenv("ASYNC", "false").lower() == "true", reason="Does not work with async")  # TODO: Async
def test_update_mutation__related_model(graphql, undine_settings):
    related_input = None

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        project = Input(Project, required=True)

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal related_input
            related_input = input_data["project"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    project = ProjectFactory.create()

    data = {
        "pk": task.pk,
        "project": project.pk,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task.refresh_from_db()
    assert task.project == project

    assert related_input == project

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
        },
    }


@pytest.mark.django_db
def test_update_mutation__related_empty_list__not_nullable(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class RelatedStep(MutationType[TaskStep], related_action="delete"): ...

    class TaskUpdateMutation(MutationType[Task]):
        steps = Input(RelatedStep, many=True)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()
    TaskStepFactory.create(task=task)

    data = {
        "pk": task.pk,
        "steps": [],
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    task = Task.objects.get(pk=response.results["pk"])
    assert task.steps.count() == 0

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
        },
    }


@pytest.mark.django_db
def test_update_mutation__hidden_input(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        @Input(hidden=True)
        def type(self, info: GQLInfo) -> TaskTypeChoices:
            return TaskTypeChoices.BUG_FIX

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
                type
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
            "type": "BUG_FIX",
        },
    }


@pytest.mark.django_db
def test_update_mutation__input_only_input(graphql, undine_settings):
    input_only_data = None

    class TaskType(QueryType[Task]): ...

    class TaskUpdateMutation(MutationType[Task]):
        foo = Input(str, input_only=True)

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            nonlocal input_only_data
            input_only_data = input_data["foo"]

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        update_task = Entrypoint(TaskUpdateMutation)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = {
        "pk": task.pk,
        "foo": "bar",
    }
    query = """
        mutation($input: TaskUpdateMutation!) {
            updateTask(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "updateTask": {
            "pk": task.pk,
        },
    }

    assert input_only_data == "bar"
