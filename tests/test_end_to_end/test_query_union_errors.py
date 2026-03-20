from __future__ import annotations

from typing import Any

import pytest
from graphql import GraphQLError, GraphQLField, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.factories import TaskFactory
from undine import Entrypoint, Field, GQLInfo, Input, MutationType, QueryType, RootType, create_schema
from undine.exceptions import GraphQLStatusError, GraphQLValidationError
from undine.typing import TModel


@pytest.mark.django_db
def test_end_to_end__union_errors__field(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(errors=[GraphQLError])
        def points(self: Task) -> int:
            if self.points is None:
                msg = "No points set for this task"
                raise GraphQLError(msg)
            return self.points

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="A", points=1)
    TaskFactory.create(name="B", points=None)

    query = """
        query {
          tasks {
            name
            points {
              __typename
              ... on TaskTypePointsValue {
                value
              }
              ... on GraphQLError {
                message
              }
            }
          }
        }
    """

    response = graphql(query, count_queries=True)

    assert response.has_errors is False, response.errors
    assert response.results == [
        {
            "name": "A",
            "points": {
                "__typename": "TaskTypePointsValue",
                "value": 1,
            },
        },
        {
            "name": "B",
            "points": {
                "__typename": "GraphQLError",
                "message": "No points set for this task",
            },
        },
    ]

    assert response.query_count == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "errors",
    [
        # Order should not matter, we sort by mro
        [GraphQLStatusError, GraphQLError],
        [GraphQLError, GraphQLStatusError],
    ],
    ids=["more specific first", "less specific first"],
)
def test_end_to_end__union_errors__field__multiple(graphql, undine_settings, errors) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(errors=errors)
        def points(self: Task) -> int:
            if self.points is None:
                msg = "No points set for this task"
                raise GraphQLError(msg)
            if self.points < 0:
                msg = "Task points are negative"
                raise GraphQLStatusError(msg, code="POINTS_NEGATIVE")
            return self.points

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="A", points=1)
    TaskFactory.create(name="B", points=-1)
    TaskFactory.create(name="C", points=None)

    query = """
        query {
          tasks {
            name
            points {
              __typename
              ... on TaskTypePointsValue {
                value
              }
              ... on GraphQLStatusError {
                message
                code
                status
              }
              ... on GraphQLError {
                message
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.results == [
        {
            "name": "A",
            "points": {
                "__typename": "TaskTypePointsValue",
                "value": 1,
            },
        },
        {
            "name": "B",
            "points": {
                "__typename": "GraphQLStatusError",
                "message": "Task points are negative",
                "code": "POINTS_NEGATIVE",
                "status": 500,
            },
        },
        {
            "name": "C",
            "points": {
                "__typename": "GraphQLError",
                "message": "No points set for this task",
            },
        },
    ]


class MyError(Exception):
    def __init__(self, message: str, /, *, custom: str) -> None:
        self.custom = custom
        super().__init__(message)

    @staticmethod
    def graphql_fields() -> dict[str, GraphQLField]:
        return {
            "message": GraphQLField(GraphQLNonNull(GraphQLString)),
            "custom": GraphQLField(GraphQLNonNull(GraphQLString)),
        }

    @staticmethod
    def graphql_resolve(root: MyError, info: GQLInfo, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG004
        """Resolve the given GraphQL error for field unions."""
        return {
            "message": str(root),
            "custom": root.custom,
        }


@pytest.mark.django_db
def test_end_to_end__union_errors__field__custom_exception(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(errors=[MyError])
        def points(self: Task) -> int:
            if self.points is None:
                msg = "No points set for this task"
                raise MyError(msg, custom="Custom message")
            return self.points

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="A", points=1)
    TaskFactory.create(name="B", points=None)

    query = """
        query {
          tasks {
            name
            points {
              __typename
              ... on TaskTypePointsValue {
                value
              }
              ... on MyError {
                message
                custom
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.results == [
        {
            "name": "A",
            "points": {
                "__typename": "TaskTypePointsValue",
                "value": 1,
            },
        },
        {
            "name": "B",
            "points": {
                "__typename": "MyError",
                "message": "No points set for this task",
                "custom": "Custom message",
            },
        },
    ]


@pytest.mark.django_db
def test_end_to_end__union_errors__field__exception_not_in_errors(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

        @Field(errors=[MyError])
        def points(self: Task) -> int:
            if self.points is None:
                msg = "No points set for this task"
                raise GraphQLError(msg)
            return self.points

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    TaskFactory.create(name="A", points=1)
    TaskFactory.create(name="B", points=None)

    query = """
        query {
          tasks {
            name
            points {
              __typename
              ... on TaskTypePointsValue {
                value
              }
              ... on MyError {
                message
                custom
              }
            }
          }
        }
    """

    response = graphql(query)

    assert response.json == {
        "data": None,
        "errors": [
            {
                "message": "No points set for this task",
                "path": ["tasks", 1, "points"],
                "extensions": {"status_code": 400},
            }
        ],
    }


def test_end_to_end__union_errors__entrypoint__query(graphql, undine_settings) -> None:
    class Query(RootType):
        @Entrypoint(errors=[GraphQLError])
        def say_hello(self, info: GQLInfo, name: str) -> str:
            if not name:
                msg = "No name provided"
                raise GraphQLError(msg)
            return f"Hello {name}"

    undine_settings.SCHEMA = create_schema(query=Query)

    query = """
        query {
          one: sayHello(name: "World") {
            __typename
            ... on QuerySayHelloValue {
              value
            }
            ... on GraphQLError {
              message
            }
          }
          two: sayHello(name: "") {
            __typename
            ... on QuerySayHelloValue {
              value
            }
            ... on GraphQLError {
              message
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "one": {
            "__typename": "QuerySayHelloValue",
            "value": "Hello World",
        },
        "two": {
            "__typename": "GraphQLError",
            "message": "No name provided",
        },
    }


@pytest.mark.django_db
def test_end_to_end__union_errors__entrypoint__mutation(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    class CreateTaskMutation(MutationType[Task], auto=True):
        name = Input()
        type = Input(default_value="TASK")

        @classmethod
        def __validate__(cls, instance: TModel, info: GQLInfo, input_data: dict[str, Any]) -> None:
            if len(input_data["name"]) < 3:
                msg = "Task name must be at least 3 characters"
                raise GraphQLValidationError(msg)

    class Mutation(RootType):
        create_task = Entrypoint(CreateTaskMutation, errors=[GraphQLValidationError])

    undine_settings.SCHEMA = create_schema(query=Query, mutation=Mutation)

    query = """
        mutation {
          one: createTask(input: {name: "foo"}) {
            __typename
            ... on MutationCreateTaskValue {
              value {
                name
              }
            }
            ... on GraphQLValidationError {
              message
              code
            }
          }
          two: createTask(input: {name: ""}) {
            __typename
            ... on MutationCreateTaskValue {
              value {
                name
              }
            }
            ... on GraphQLValidationError {
              message
              code
              status
            }
          }
        }
    """

    response = graphql(query)

    assert response.has_errors is False, response.errors
    assert response.data == {
        "one": {
            "__typename": "MutationCreateTaskValue",
            "value": {
                "name": "foo",
            },
        },
        "two": {
            "__typename": "GraphQLValidationError",
            "message": "Task name must be at least 3 characters",
            "code": "VALIDATION_ERROR",
            "status": 400,
        },
    }
