from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import ServiceRequest, Task, TaskStep, TaskTypeChoices
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLPermissionError

# Entrypoint


@pytest.mark.django_db
def test_end_to_end__mutation__entrypoint__permission_error(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

        @create_task.permissions
        def create_task_permissions(self, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask"],
            },
        ],
    }

    response.assert_query_count(0)


# Single


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        @classmethod
        def __permissions__(cls, instance: ServiceRequest, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": {
            "details": "Test request",
        },
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "request"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "steps": [
            {"name": "Test step 1"},
            {"name": "Test step 2"},
        ],
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "steps", 0],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "steps", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__field(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "name"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__field__multiple(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @type.permissions
        def type_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "type"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__field__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        details = Input()

        @details.permissions
        def details_permissions(root: ServiceRequest, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "request": {
            "details": "Test request",
        },
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "request", "details"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__permission_error__field__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        name = Input()

        @name.permissions
        def name_permissions(root: TaskStep, info: GQLInfo, value: Any) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: TaskCreateMutation!) {
          createTask(input: $input) {
            name
          }
        }
    """

    data = {
        "name": "Test task",
        "type": TaskTypeChoices.STORY.value,
        "steps": [
            {"name": "Test step 1"},
            {"name": "Test step 2"},
        ],
    }

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "steps", 0, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["createTask", "steps", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)


# Many


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @classmethod
        def __permissions__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.TASK.value,
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        @classmethod
        def __permissions__(cls, instance: ServiceRequest, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "request": {
                "details": "Test request 1",
            },
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.TASK.value,
            "request": {
                "details": "Test request 2",
            },
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "request"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "request"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        @classmethod
        def __permissions__(cls, instance: TaskStep, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.TASK.value,
            "steps": [
                {"name": "Test steps 1"},
                {"name": "Test steps 2"},
            ],
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
            "steps": [
                {"name": "Test steps 3"},
                {"name": "Test steps 4"},
            ],
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "steps", 0],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "steps", 1],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "steps", 0],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "steps", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__field(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permission(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.TASK.value,
        },
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__field__multiple(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.permissions
        def name_permission(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

        @type.permissions
        def type_permission(self, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task",
            "type": TaskTypeChoices.TASK.value,
        },
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "type"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "type"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__field__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        details = Input()

        @details.permissions
        def details_permission(root: ServiceRequest, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.TASK.value,
            "request": {
                "details": "Test request 1",
            },
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
            "request": {
                "details": "Test request 2",
            },
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "request", "details"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "request", "details"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__permission_error__field__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        name = Input()

        @name.permissions
        def name_permission(root: TaskStep, info: GQLInfo, value: str) -> None:
            raise GraphQLPermissionError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

    # RootTypes

    class Query(RootType):
        task = Entrypoint(TaskType)

    class Mutation(RootType):
        bulk_create_task = Entrypoint(TaskCreateMutation, many=True)

    # Schema

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation ($input: [TaskCreateMutation!]!) {
          bulkCreateTask(input: $input) {
            name
          }
        }
    """

    data = [
        {
            "name": "Test task 1",
            "type": TaskTypeChoices.STORY.value,
            "steps": [
                {"name": "Test step 1"},
                {"name": "Test step 2"},
            ],
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
            "steps": [
                {"name": "Test step 3"},
                {"name": "Test step 4"},
            ],
        },
    ]

    response = graphql(query, variables={"input": data})

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "steps", 0, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 0, "steps", 1, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "steps", 0, "name"],
            },
            {
                "message": "Permission denied.",
                "extensions": {
                    "status_code": 403,
                    "error_code": "PERMISSION_DENIED",
                },
                "path": ["bulkCreateTask", 1, "steps", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)
