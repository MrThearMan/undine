from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from example_project.app.models import Comment, Person, Project, Task, TaskStep, TaskTypeChoices
from tests.factories import PersonFactory, ProjectFactory
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema


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
