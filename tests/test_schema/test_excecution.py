from __future__ import annotations

from inspect import isawaitable
from typing import Any

from graphql import ExecutionResult, GraphQLObjectType, GraphQLSchema, GraphQLString
from graphql.type.definition import GraphQLField, GraphQLNonNull

from tests.helpers import MockRequest
from undine.dataclasses import GraphQLHttpParams
from undine.execution import execute_graphql_http_sync
from undine.settings import example_schema


def test_execute_graphql(undine_settings) -> None:
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

    params = GraphQLHttpParams(
        document="query { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert not isawaitable(result)

    assert result == ExecutionResult(data={"hello": "Hello, World!"})


def test_execute_graphql__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { €hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert not isawaitable(result)

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "Syntax Error: Unexpected character: U+20AC."


def test_execute_graphql__non_query_operation_on_get_request(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="mutation { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="GET"))

    assert not isawaitable(result)

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "Only query operations are allowed on GET requests."
    assert result.errors[0].extensions == {"error_code": "INVALID_OPERATION_FOR_METHOD", "status_code": 405}


def test_execute_graphql__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { hello } query { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert not isawaitable(result)

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "This anonymous operation must be the only defined operation."


def test_execute_graphql__error_raised(undine_settings) -> None:
    def _raise_value_error(*args: Any, **kwargs: Any) -> Any:
        msg = "Error!"
        raise ValueError(msg)

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

    params = GraphQLHttpParams(
        document="query { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert not isawaitable(result)

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "Error!"
    assert result.errors[0].extensions == {"status_code": 400}
