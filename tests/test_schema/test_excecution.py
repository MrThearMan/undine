from typing import Any
from unittest.mock import patch

import pytest
from graphql import ExecutionResult, GraphQLObjectType, GraphQLSchema, GraphQLString
from graphql.type.definition import GraphQLField, GraphQLNonNull

from example_project.app.models import Task
from undine import Entrypoint, MutationType, QueryType, create_schema
from undine.dataclasses import GraphQLParams
from undine.registies import GRAPHQL_TYPE_REGISTRY
from undine.schema import RootOperationType, execute_graphql
from undine.settings import example_schema


def test_create_schema():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query(RootOperationType):
        task = Entrypoint(TaskType)

    class Mutation(RootOperationType):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation)

    assert isinstance(schema.query_type, GraphQLObjectType)
    assert schema.query_type.name == "Query"
    assert sorted(schema.query_type.fields) == ["task"]

    assert isinstance(schema.mutation_type, GraphQLObjectType)
    assert schema.mutation_type.name == "Mutation"
    assert sorted(schema.mutation_type.fields) == ["createTask"]


def test_create_schema__registered():
    assert "Query" not in GRAPHQL_TYPE_REGISTRY
    assert "Mutation" not in GRAPHQL_TYPE_REGISTRY

    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query(RootOperationType):
        task = Entrypoint(TaskType)

    class Mutation(RootOperationType):
        create_task = Entrypoint(TaskCreateMutation)

    create_schema(query=Query, mutation=Mutation)

    assert "Query" in GRAPHQL_TYPE_REGISTRY
    assert isinstance(GRAPHQL_TYPE_REGISTRY["Query"], GraphQLObjectType)

    assert "Mutation" in GRAPHQL_TYPE_REGISTRY
    assert isinstance(GRAPHQL_TYPE_REGISTRY["Mutation"], GraphQLObjectType)


def test_create_schema__descriptions():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query(RootOperationType):
        """Query description."""

        task = Entrypoint(TaskType)

    class Mutation(RootOperationType):
        """Mutation description."""

        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(query=Query, mutation=Mutation, description="Description.")

    assert schema.description == "Description."
    assert schema.query_type.description == "Query description."
    assert schema.mutation_type.description == "Mutation description."


def test_create_schema__extensions():
    class TaskType(QueryType, model=Task, auto=False): ...

    class TaskCreateMutation(MutationType, model=Task): ...

    class Query(RootOperationType, extensions={"foo": "2"}):
        task = Entrypoint(TaskType)

    class Mutation(RootOperationType, extensions={"foo": "3"}):
        create_task = Entrypoint(TaskCreateMutation)

    schema = create_schema(
        query=Query,
        mutation=Mutation,
        extensions={"foo": "1"},
    )

    assert schema.extensions == {"foo": "1"}
    assert schema.query_type.extensions == {"foo": "2", "undine_root_operation_type": Query}
    assert schema.mutation_type.extensions == {"foo": "3", "undine_root_operation_type": Mutation}


def test_create_schema__query_type_required():
    with pytest.raises(TypeError):
        create_schema()


def test_execute_graphql(undine_settings):
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: "Hello, World!",  # noqa: ARG005
                ),
            },
        ),
    )

    params = GraphQLParams(query="query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result == ExecutionResult(data={"hello": "Hello, World!"})


def test_execute_graphql__schema_error(undine_settings):
    invalid_schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "__hello": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: "Hello, World!",  # noqa: ARG005
                ),
            },
        ),
    )

    undine_settings.SCHEMA = invalid_schema

    params = GraphQLParams(query="query { __hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == (
        "Name '__hello' must not begin with '__', which is reserved by GraphQL introspection."
    )


def test_execute_graphql__parse_error(undine_settings):
    undine_settings.SCHEMA = example_schema

    params = GraphQLParams(query="query { €hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Syntax Error: Unexpected character: U+20AC."


def test_execute_graphql__non_query_operation_on_get_request(undine_settings):
    undine_settings.SCHEMA = example_schema

    params = GraphQLParams(query="mutation { hello }")
    result = execute_graphql(params=params, method="GET", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Only query operations are allowed on GET requests."
    assert result.errors[0].extensions == {"error_code": "INVALID_OPERATION_FOR_METHOD", "status_code": 405}


def test_execute_graphql__validation_error(undine_settings):
    undine_settings.SCHEMA = example_schema

    params = GraphQLParams(query="query { hello } query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "This anonymous operation must be the only defined operation."


def _raise_value_error(*args: Any, **kwargs: Any) -> Any:
    msg = "Error!"
    raise ValueError(msg)


def test_execute_graphql__error_raised(undine_settings):
    error_schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLNonNull(GraphQLString),
                    resolve=_raise_value_error,
                ),
            },
        ),
    )

    undine_settings.SCHEMA = error_schema

    params = GraphQLParams(query="query { hello }")
    result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Error!"
    assert result.errors[0].extensions == {"status_code": 400}


def test_execute_graphql__unexpected_error(undine_settings):
    undine_settings.SCHEMA = example_schema

    params = GraphQLParams(query="query { hello }")

    with patch("undine.schema.validate", side_effect=ValueError("Error!")):
        result = execute_graphql(params=params, method="POST", context_value=None)

    assert result.data is None
    assert result.errors[0].message == "Error!"
    assert result.errors[0].extensions == {"status_code": 500}
