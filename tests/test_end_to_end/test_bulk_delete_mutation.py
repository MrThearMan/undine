from __future__ import annotations

from collections import defaultdict
from itertools import count
from typing import Any

import pytest
from asgiref.sync import sync_to_async

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, GQLInfo, Input, MutationType, QueryType, RootType, create_schema


@pytest.mark.django_db
def test_bulk_delete_mutation(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": task_2.pk},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTasks": [
            {"pk": task_1.pk},
            {"pk": task_2.pk},
        ],
    }

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_bulk_delete_mutation__missing_instances(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": -1},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.errors == [
        {
            "message": "Primary key -1 on model 'example_project.app.models.Task' did not match any row.",
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["deleteTasks"],
        }
    ]

    assert list(Task.objects.values_list("pk", flat=True)) == [task_1.pk]


@pytest.mark.django_db
def test_bulk_delete_mutation__multiple_missing_instances(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": -1},
        {"pk": -2},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.error_message(0) == (
        "Primary keys '-1' and '-2' on model 'example_project.app.models.Task' did not match any row."
    )

    assert sorted(Task.objects.values_list("pk", flat=True)) == sorted([task_1.pk, task_2.pk])


@pytest.mark.django_db
def test_bulk_delete_mutation__hooks__call_order(graphql, undine_settings):
    counter = count()

    validate_called: int = -1
    permission_called: int = -1
    after_called: int = -1

    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
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
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task = TaskFactory.create()

    data = [{"pk": task.pk}]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = graphql(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {"deleteTasks": [{"pk": task.pk}]}

    assert permission_called == 0
    assert validate_called == 1
    assert after_called == 2

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_bulk_delete_mutation__hooks__correct_instance_pairing(graphql, undine_settings):
    # hook_name -> [instance.pk, ...] in the order each hook was called.
    recorded: dict[str, list[int]] = defaultdict(list)

    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
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
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = TaskFactory.create(name="Original Task 1")
    task_2 = TaskFactory.create(name="Original Task 2")

    # Client input is in the reverse order of the tasks' creation (database) order.
    data = [
        {"pk": task_2.pk, "name": "Task Two", "points": 2},
        {"pk": task_1.pk, "name": "Task One", "points": 1},
    ]
    expected_pk_order = [row["pk"] for row in data]

    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
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

    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_bulk_delete_mutation__mutation_instance_limit(graphql, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    task_1 = TaskFactory.create()
    task_2 = TaskFactory.create()

    data = [
        {"pk": task_1.pk},
        {"pk": task_2.pk},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
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
                "path": ["deleteTasks"],
            }
        ],
    }

    assert sorted(Task.objects.values_list("pk", flat=True)) == sorted([task_1.pk, task_2.pk])


@pytest.mark.django_db(transaction=True)
async def test_bulk_delete_mutation__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
        @classmethod
        def __after__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            after_called.append(instance.pk)

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    after_called: list[int] = []

    task_1 = await sync_to_async(TaskFactory.create)()
    task_2 = await sync_to_async(TaskFactory.create)()
    task_3 = await sync_to_async(TaskFactory.create)()

    data = [
        {"pk": task_1.pk},
        {"pk": task_2.pk},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.has_errors is False, response.errors

    assert response.data == {
        "deleteTasks": [
            {"pk": task_1.pk},
            {"pk": task_2.pk},
        ],
    }

    assert after_called == [task_1.pk, task_2.pk]

    remaining = [task.pk async for task in Task.objects.all()]
    assert remaining == [task_3.pk]


@pytest.mark.django_db(transaction=True)
async def test_bulk_delete_mutation__missing_instances__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = await sync_to_async(TaskFactory.create)()

    data = [
        {"pk": task_1.pk},
        {"pk": -1},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
            }
        }
    """

    response = await graphql_async(query, variables={"input": data})

    assert response.errors == [
        {
            "message": "Primary key -1 on model 'example_project.app.models.Task' did not match any row.",
            "extensions": {
                "error_code": "MODEL_INSTANCE_NOT_FOUND",
                "status_code": 404,
            },
            "path": ["deleteTasks"],
        }
    ]

    assert await Task.objects.acount() == 1


@pytest.mark.django_db(transaction=True)
async def test_bulk_delete_mutation__hooks__correct_instance_pairing__async(graphql_async, undine_settings):
    # hook_name -> [instance.pk, ...] in the order each hook was called.
    recorded: dict[str, list[int]] = defaultdict(list)

    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]):
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
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    task_1 = await sync_to_async(TaskFactory.create)(name="Original Task 1")
    task_2 = await sync_to_async(TaskFactory.create)(name="Original Task 2")

    # Client input is in the reverse order of the tasks' creation (database) order.
    data = [
        {"pk": task_2.pk, "name": "Task Two", "points": 2},
        {"pk": task_1.pk, "name": "Task One", "points": 1},
    ]
    expected_pk_order = [row["pk"] for row in data]

    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
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

    assert await Task.objects.acount() == 0


@pytest.mark.django_db(transaction=True)
async def test_bulk_delete_mutation__mutation_instance_limit__async(graphql_async, undine_settings):
    class TaskType(QueryType[Task]): ...

    class TaskDeleteMutation(MutationType[Task]): ...

    class Query(RootType):
        tasks = Entrypoint(TaskType)

    class Mutation(RootType):
        delete_tasks = Entrypoint(TaskDeleteMutation, many=True)

    undine_settings.ASYNC = True
    undine_settings.GRAPHQL_PATH = "graphql/async/"
    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)
    undine_settings.MUTATION_INSTANCE_LIMIT = 1

    task_1 = await sync_to_async(TaskFactory.create)()
    task_2 = await sync_to_async(TaskFactory.create)()

    data = [
        {"pk": task_1.pk},
        {"pk": task_2.pk},
    ]
    query = """
        mutation($input: [TaskDeleteMutation!]!) {
            deleteTasks(input: $input) {
                pk
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
                "path": ["deleteTasks"],
            }
        ],
    }

    assert await Task.objects.acount() == 2
