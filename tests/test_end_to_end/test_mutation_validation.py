from __future__ import annotations

from typing import Any

import pytest

from example_project.app.models import ServiceRequest, Task, TaskStep, TaskTypeChoices
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLValidationError
from undine.utils.mutation_tree import bulk_mutate

# Single


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "request"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "steps", 0],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "steps", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__field(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.validate
        def name_validation(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "name"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__field__multiple(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @name.validate
        def name_validation(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

        @type.validate
        def type_validation(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "type"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__field__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        details = Input()

        @details.validate
        def details_validation(self: Task, info: GQLInfo, value: Any) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "request", "details"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__single__validation_error__field__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        name = Input()

        @name.validate
        def name_validation(self: Task, info: GQLInfo, value: Any) -> None:
            raise GraphQLValidationError

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "steps", 0, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["createTask", "steps", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)


# Many


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()

        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

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
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        @classmethod
        def __validate__(cls, instance: Task, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "request"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "request"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        @classmethod
        def __validate__(cls, instance: TaskStep, info: GQLInfo, input_data: dict[str, Any]) -> None:
            raise GraphQLValidationError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "steps", 0],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "steps", 1],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "steps", 0],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "steps", 1],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__field(graphql, undine_settings) -> None:
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
            raise GraphQLValidationError

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
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__field__multiple(graphql, undine_settings) -> None:
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
            raise GraphQLValidationError

        @type.permissions
        def type_permissions(self, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

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
        },
        {
            "name": "Test task 2",
            "type": TaskTypeChoices.STORY.value,
        },
    ]

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "type"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "type"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__field__nested__single(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class ServiceRequestMutation(MutationType[ServiceRequest], kind="related"):
        details = Input()

        @details.permissions
        def details_permissions(self: Task, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        request = Input(ServiceRequestMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "request", "details"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "request", "details"],
            },
        ],
    }

    response.assert_query_count(0)


@pytest.mark.django_db
def test_end_to_end__mutation__many__validation_error__field__nested__many(graphql, undine_settings) -> None:
    undine_settings.MUTATION_FULL_CLEAN = False

    # QueryTypes

    class TaskType(QueryType[Task], auto=False):
        name = Field()

    # MutationTypes

    class TaskStepMutation(MutationType[TaskStep], kind="related"):
        name = Input()

        @name.permissions
        def name_permissions(self: Task, info: GQLInfo, value: str) -> None:
            raise GraphQLValidationError

    class TaskCreateMutation(MutationType[Task], auto=False):
        name = Input()
        type = Input()
        steps = Input(TaskStepMutation)

        @classmethod
        def __bulk_mutate__(cls, instances: list[Task], info: GQLInfo, input_data: Any) -> Any:
            return bulk_mutate(model=Task, data=input_data)

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

    response = graphql(query, variables={"input": data}, count_queries=True)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "steps", 0, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 0, "steps", 1, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "steps", 0, "name"],
            },
            {
                "message": "Validation error.",
                "extensions": {
                    "status_code": 400,
                    "error_code": "VALIDATION_ERROR",
                },
                "path": ["bulkCreateTask", 1, "steps", 1, "name"],
            },
        ],
    }

    response.assert_query_count(0)
