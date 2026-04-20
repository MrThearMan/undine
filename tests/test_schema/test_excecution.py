from __future__ import annotations

import dataclasses
from inspect import isawaitable
from typing import Any, AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import pytest
from django.http.request import MediaType
from graphql import (
    ExecutionResult,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    TypeInfo,
    parse,
)
from graphql.type.definition import GraphQLArgument, GraphQLField, GraphQLList, GraphQLNonNull

from tests.helpers import MockRequest
from undine.dataclasses import GraphQLHttpParams
from undine.exceptions import GraphQLError, GraphQLErrorGroup
from undine.execution import (
    UndineValidationContext,
    _get_execution_context,  # noqa: PLC2701
    _is_incremental_request,  # noqa: PLC2701
    _is_multipart_mixed_request,  # noqa: PLC2701
    _is_sse_request,  # noqa: PLC2701
    _map_source_to_response,  # noqa: PLC2701
    _validate_http,  # noqa: PLC2701
    _validate_incremental,  # noqa: PLC2701
    _validate_multipart_mixed,  # noqa: PLC2701
    _validate_sse,  # noqa: PLC2701
    _validate_websockets,  # noqa: PLC2701
    execute_graphql_http_async,
    execute_graphql_http_sync,
    execute_graphql_with_subscription,
    raised_exceptions_as_execution_results_async,
    raised_exceptions_as_execution_results_sync,
    raised_exceptions_as_execution_results_with_subscriptions,
)
from undine.hooks import LifecycleHook, LifecycleHookContext
from undine.settings import example_schema
from undine.utils.graphql.utils import get_error_execution_result


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
    assert result.errors[0].message == "Cannot use HTTP for mutations if not sent as a POST request."
    assert result.errors[0].extensions == {
        "error_code": "CANNOT_USE_HTTP_FOR_MUTATIONS_NON_POST_REQUEST",
        "status_code": 405,
    }


def test_execute_graphql__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { testing } query { testing }",
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
    assert result.errors[0].extensions == {"status_code": 500}


def test_raised_exceptions_as_execution_results_sync__graphql_error() -> None:
    error = GraphQLError("test error")

    @raised_exceptions_as_execution_results_sync
    def raises_graphql_error() -> ExecutionResult:
        raise error

    result = raises_graphql_error()

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0] is error


def test_raised_exceptions_as_execution_results_sync__graphql_error_group() -> None:
    error1 = GraphQLError("error 1")
    error2 = GraphQLError("error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    @raised_exceptions_as_execution_results_sync
    def raises_error_group() -> ExecutionResult:
        raise error_group

    result = raises_error_group()

    assert result.data is None
    assert result.errors is not None
    assert len(result.errors) == 2


def test_raised_exceptions_as_execution_results_sync__generic_exception() -> None:
    @raised_exceptions_as_execution_results_sync
    def raises_generic() -> ExecutionResult:
        msg = "unexpected!"
        raise ValueError(msg)

    result = raises_generic()

    assert result.data is None
    assert result.errors is not None
    assert "unexpected!" in result.errors[0].message


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_async__graphql_error() -> None:
    error = GraphQLError("async test error")

    @raised_exceptions_as_execution_results_async
    async def raises_graphql_error() -> ExecutionResult:  # noqa: RUF029
        raise error

    result = await raises_graphql_error()

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0] is error


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_async__graphql_error_group() -> None:
    error1 = GraphQLError("error 1")
    error2 = GraphQLError("error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    @raised_exceptions_as_execution_results_async
    async def raises_error_group() -> ExecutionResult:  # noqa: RUF029
        raise error_group

    result = await raises_error_group()

    assert result.data is None
    assert result.errors is not None
    assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_async__generic_exception() -> None:
    @raised_exceptions_as_execution_results_async
    async def raises_generic() -> ExecutionResult:  # noqa: RUF029
        msg = "unexpected async!"
        raise ValueError(msg)

    result = await raises_generic()

    assert result.data is None
    assert result.errors is not None
    assert "unexpected async!" in result.errors[0].message


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_with_subscriptions__graphql_error() -> None:
    error = GraphQLError("subscription test error")

    @raised_exceptions_as_execution_results_with_subscriptions
    async def raises_graphql_error() -> ExecutionResult:  # noqa: RUF029
        raise error

    result = await raises_graphql_error()

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0] is error


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_with_subscriptions__graphql_error_group() -> None:
    error1 = GraphQLError("error 1")
    error2 = GraphQLError("error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    @raised_exceptions_as_execution_results_with_subscriptions
    async def raises_error_group() -> ExecutionResult:  # noqa: RUF029
        raise error_group

    result = await raises_error_group()

    assert result.data is None
    assert result.errors is not None
    assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_raised_exceptions_as_execution_results_with_subscriptions__generic_exception() -> None:
    @raised_exceptions_as_execution_results_with_subscriptions
    async def raises_generic() -> ExecutionResult:  # noqa: RUF029
        msg = "unexpected sub!"
        raise ValueError(msg)

    result = await raises_generic()

    assert result.data is None
    assert result.errors is not None
    assert "unexpected sub!" in result.errors[0].message


@pytest.mark.asyncio
async def test_execute_graphql_http_async__basic(undine_settings) -> None:
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
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"hello": "Hello, World!"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { €bad }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert "Syntax Error" in result.errors[0].message


@pytest.mark.asyncio
async def test_execute_graphql_http_async__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { testing } query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "This anonymous operation must be the only defined operation."


@pytest.mark.asyncio
async def test_execute_graphql_http_async__mutation_non_post(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="GET"))

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "Cannot use HTTP for mutations if not sent as a POST request."


@pytest.mark.asyncio
async def test_execute_graphql_http_async__subscription_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
    )

    params = GraphQLHttpParams(
        document="subscription { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert (
        "subscription" in result.errors[0].message.lower() or result.errors[0].extensions.get("error_code") is not None
    )


@pytest.mark.asyncio
async def test_execute_graphql_http_async__result_pre_set_as_awaitable(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    async def _awaitable_result() -> ExecutionResult:  # noqa: RUF029
        return ExecutionResult(data={"pre": "set"})

    # We use a lifecycle hook that sets the result to an awaitable

    class PreSetResultHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            self.context.result = _awaitable_result()
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetResultHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"pre": "set"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__result_pre_set_as_async_iterator(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    async def _async_gen() -> AsyncGenerator[ExecutionResult, None]:  # noqa: RUF029
        yield ExecutionResult(data={})

    class PreSetAsyncIteratorHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            self.context.result = _async_gen()
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetAsyncIteratorHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "UNSUPPORTED_PROTOCOL_FOR_SUBSCRIPTIONS"


def test_execute_graphql_http_sync__result_pre_set_as_awaitable(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    async def _awaitable_result() -> ExecutionResult:  # noqa: RUF029
        return ExecutionResult(data={"pre": "set"})

    class PreSetResultHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            self.context.result = _awaitable_result()
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetResultHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "ASYNC_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_execute_graphql_http_async__result_pre_set_in_parse(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInParseHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"preparse": "result"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInParseHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"preparse": "result"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__document_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: "World",  # noqa: ARG005
                ),
            },
        ),
    )

    pre_parsed_doc = parse("query { hello }")

    class PreSetDocumentHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            self.context.document = pre_parsed_doc
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetDocumentHook]

    params = GraphQLHttpParams(
        document="query { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"hello": "World"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__validate_result_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInValidationHook(LifecycleHook):
        def on_validation(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"prevalidation": "result"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInValidationHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"prevalidation": "result"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__execute_context_error_group(undine_settings) -> None:
    error1 = GraphQLError("context error 1")
    error2 = GraphQLError("context error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    with patch("undine.execution._get_execution_context", side_effect=error_group):
        undine_settings.SCHEMA = example_schema

        params = GraphQLHttpParams(
            document="query { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None


def test_validate_http__subscription_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
    )

    params = GraphQLHttpParams(
        document="subscription { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))
    context.document = parse("subscription { testing }")

    _validate_http(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "UNSUPPORTED_PROTOCOL_FOR_SUBSCRIPTIONS"


def test_validate_multipart_mixed__query_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_MULTIPART_MIXED = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(
        method="POST",
        response_content_type=MediaType("multipart/mixed"),
    )
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("query { testing }")

    _validate_multipart_mixed(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_MULTIPART_MIXED_FOR_QUERIES"


def test_validate_multipart_mixed__mutation_non_post(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(
        method="GET",
        response_content_type=MediaType("multipart/mixed"),
    )
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_multipart_mixed(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert (
        context.result.errors[0].extensions.get("error_code")
        == "CANNOT_USE_MULTIPART_MIXED_FOR_MUTATIONS_NON_POST_REQUEST"
    )


def test_validate_incremental__disabled(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("query { testing }")

    _validate_incremental(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "INCREMENTAL_DELIVERY_NOT_SUPPORTED"


def test_validate_incremental__mutation_non_post(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="GET")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_incremental(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_HTTP_FOR_MUTATIONS_NON_POST_REQUEST"


def test_validate_incremental__subscription(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY = True

    params = GraphQLHttpParams(
        document="subscription { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("subscription { testing }")

    _validate_incremental(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "UNSUPPORTED_PROTOCOL_FOR_SUBSCRIPTIONS"


def test_validate_sse__mutation_non_post(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="GET")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_sse(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_SSE_FOR_MUTATIONS_NON_POST_REQUEST"


def test_is_multipart_mixed_request__no_response_content_type() -> None:
    @dataclasses.dataclass
    class MinimalRequest:
        method: str = "GET"

    request = MinimalRequest()
    result = _is_multipart_mixed_request(request)  # type: ignore[arg-type]
    assert result is False


def test_is_incremental_request__no_response_content_type() -> None:
    @dataclasses.dataclass
    class MinimalRequest:
        method: str = "GET"

    request = MinimalRequest()
    result = _is_incremental_request(request)  # type: ignore[arg-type]
    assert result is False


def test_is_sse_request__no_response_content_type() -> None:
    @dataclasses.dataclass
    class MinimalRequest:
        method: str = "GET"
        META: dict = dataclasses.field(default_factory=dict)
        headers: dict = dataclasses.field(default_factory=dict)
        GET: dict = dataclasses.field(default_factory=dict)

    request = MinimalRequest()
    result = _is_sse_request(request)  # type: ignore[arg-type]
    assert result is False


def test_validate__max_errors_reached(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.MAX_ERRORS = 1

    params = GraphQLHttpParams(
        # Two anonymous operations will generate multiple validation errors
        document="query { testing } query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    # Should have errors including the aborted error
    assert len(result.errors) >= 1


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__basic_query(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: "Hello!",  # noqa: ARG005
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
    result = await execute_graphql_with_subscription(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"hello": "Hello!"})


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__result_pre_set_as_awaitable(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    async def _awaitable_result() -> ExecutionResult:  # noqa: RUF029
        return ExecutionResult(data={"pre": "set"})

    class PreSetResultHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            self.context.result = _awaitable_result()
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetResultHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_with_subscription(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"pre": "set"})


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__parse_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    params = GraphQLHttpParams(
        document="query { €bad }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_with_subscription(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None
    assert "Syntax Error" in result.errors[0].message


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__subscription_execution_result(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    error = GraphQLError("subscription setup error")
    execution_result = get_error_execution_result(error)

    # Mock _subscribe to return ExecutionResult instead of a stream
    with patch("undine.execution._subscribe", return_value=execution_result):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_create_source_event_stream__graphql_error_group_in_execution_context(undine_settings) -> None:
    error1 = GraphQLError("sub error 1")
    error2 = GraphQLError("sub error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    with patch("undine.execution._get_execution_context", side_effect=error_group):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_create_source_event_stream__graphql_error_from_execute_subscription(undine_settings) -> None:
    error = GraphQLError("subscription stream error")

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    with patch("undine.execution.execute_subscription", side_effect=error):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_create_source_event_stream__graphql_error_group_from_execute_subscription(undine_settings) -> None:
    error1 = GraphQLError("stream error 1")
    error2 = GraphQLError("stream error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    with patch("undine.execution.execute_subscription", side_effect=error_group):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_create_source_event_stream__not_async_iterable(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    # Return a non-AsyncIterable (e.g., a plain string)
    with patch("undine.execution.execute_subscription", return_value="not-an-async-iterable"):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "NO_EVENT_STREAM"


@pytest.mark.asyncio
async def test_map_source_to_response__pre_existing_result(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
    )

    preset_result = ExecutionResult(data={"preset": "value"})

    class PreSetExecutionHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            self.context.result = preset_result
            yield

    params = GraphQLHttpParams(
        document="subscription { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("subscription { testing }")
    # Replace lifecycle hooks with our custom one
    context.lifecycle_hooks = [PreSetExecutionHook(context=context)]

    async def _source() -> AsyncGenerator[Any, None]:  # noqa: RUF029
        yield ExecutionResult(data={"payload": "value"})

    results = []
    async for item in _map_source_to_response(source=_source(), context=context):
        results.append(item)
        break  # Only get first result

    assert len(results) == 1
    assert results[0] == preset_result


@pytest.mark.asyncio
async def test_execute_graphql_http_async__sse_mutation_non_post(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = True

    class SSERequestHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            self.context.request = MockRequest(
                method="GET",
                response_content_type=MediaType("text/event-stream"),
            )
            yield

    undine_settings.LIFECYCLE_HOOKS = [SSERequestHook]

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="GET",
            response_content_type=MediaType("text/event-stream"),
        ),
    )

    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_execute_graphql_http_async__websocket_query_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(method="WEBSOCKET"),
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "CANNOT_USE_WEBSOCKETS_FOR_QUERIES"


@pytest.mark.asyncio
async def test_execute_graphql_http_async__sse_query_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_SSE = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="POST",
            response_content_type=MediaType("text/event-stream"),
        ),
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "CANNOT_USE_SSE_FOR_QUERIES"


@pytest.mark.asyncio
async def test_execute_graphql_http_async__multipart_mixed_query_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_MULTIPART_MIXED = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="POST",
            response_content_type=MediaType("multipart/mixed; boundary=graphql; subscriptionSpec=1.0"),
        ),
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "CANNOT_USE_MULTIPART_MIXED_FOR_QUERIES"


@pytest.mark.asyncio
async def test_execute_graphql_http_async__incremental_disabled(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY = False

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="POST",
            response_content_type=MediaType("multipart/mixed; boundary=graphql"),
        ),
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "INCREMENTAL_DELIVERY_NOT_SUPPORTED"


def test_undine_validation_context__variable_as_ast__none_value(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"myVar": None},
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    result = context.variable_as_ast("myVar", GraphQLString)
    assert result is None


def test_undine_validation_context__variable_as_ast__orderset_enum_string(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    # Create a GraphQLEnumType that looks like an OrderSet (has the extensions key)
    fake_orderset_class = type("FakeOrderSet", (), {})
    enum_type = GraphQLEnumType(
        name="FakeOrder",
        values={
            "NAME_ASC": GraphQLEnumValue(value="name_asc"),
            "NAME_DESC": GraphQLEnumValue(value="name_desc"),
        },
        extensions={undine_settings.ORDERSET_EXTENSIONS_KEY: fake_orderset_class},
    )

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"order": "NAME_ASC"},
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    result = context.variable_as_ast("order", enum_type)
    # Should convert "NAME_ASC" -> "name_asc" and return ast node
    assert result is not None


def test_undine_validation_context__variable_as_ast__orderset_enum_list(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    fake_orderset_class = type("FakeOrderSet", (), {})
    enum_type = GraphQLEnumType(
        name="FakeOrder",
        values={
            "NAME_ASC": GraphQLEnumValue(value="name_asc"),
            "NAME_DESC": GraphQLEnumValue(value="name_desc"),
        },
        extensions={undine_settings.ORDERSET_EXTENSIONS_KEY: fake_orderset_class},
    )

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"order": ["NAME_ASC", "NAME_DESC"]},
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    result = context.variable_as_ast("order", GraphQLList(enum_type))
    # Should return some ast node for the list
    assert result is not None


def test_undine_validation_context__variable_as_ast__orderset_enum_non_string_value(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    fake_orderset_class = type("FakeOrderSet", (), {})
    enum_type = GraphQLEnumType(
        name="FakeOrder",
        values={
            "NAME_ASC": GraphQLEnumValue(value="name_asc"),
        },
        extensions={undine_settings.ORDERSET_EXTENSIONS_KEY: fake_orderset_class},
    )

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"order": 123},  # Not a string or list of strings
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    result = context.variable_as_ast("order", enum_type)
    assert result is None


def test_undine_validation_context__variable_as_ast__orderset_enum_key_not_found(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    fake_orderset_class = type("FakeOrderSet", (), {})
    enum_type = GraphQLEnumType(
        name="FakeOrder",
        values={
            "NAME_ASC": GraphQLEnumValue(value="name_asc"),
        },
        extensions={undine_settings.ORDERSET_EXTENSIONS_KEY: fake_orderset_class},
    )

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"order": "INVALID_KEY"},
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    result = context.variable_as_ast("order", enum_type)
    assert result is None


def test_undine_validation_context__variable_as_ast__ast_from_value_exception(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    document = parse("query { testing }")
    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables={"myVar": "some_value"},
        request=None,
        type_info=type_info,
        on_error=lambda _: None,
    )

    with patch("undine.execution.ast_from_value", side_effect=ValueError("ast error")):
        result = context.variable_as_ast("myVar", GraphQLString)

    assert result is None


def test_execute_graphql_http_sync__result_pre_set_in_parse_hook(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInParseHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"preparse": "sync"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInParseHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"preparse": "sync"})


def test_execute_graphql_http_sync__document_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: "World",  # noqa: ARG005
                ),
            },
        ),
    )

    pre_parsed_doc = parse("query { hello }")

    class PreSetDocumentHook(LifecycleHook):
        def on_parse(self) -> Generator[None, None, None]:
            self.context.document = pre_parsed_doc
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetDocumentHook]

    params = GraphQLHttpParams(
        document="query { hello }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"hello": "World"})


def test_execute_graphql_http_sync__validate_result_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInValidationHook(LifecycleHook):
        def on_validation(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"prevalidation": "sync"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInValidationHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"prevalidation": "sync"})


def test_execute_graphql_http_sync__execute_result_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInExecutionHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"preexecution": "sync"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInExecutionHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"preexecution": "sync"})


def test_execute_graphql_http_sync__execute_context_error_group(undine_settings) -> None:
    error1 = GraphQLError("context error 1")
    error2 = GraphQLError("context error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    undine_settings.SCHEMA = example_schema

    with patch("undine.execution._get_execution_context", side_effect=error_group):
        params = GraphQLHttpParams(
            document="query { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = execute_graphql_http_sync(params=params, request=MockRequest(method="POST"))

    assert result.data is None
    assert result.errors is not None


def test_execute_graphql_http_sync__async_resolver_in_sync_mode(undine_settings) -> None:
    async def async_resolver(obj: Any, info: Any) -> str:  # noqa: RUF029
        return "async result"

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=async_resolver,
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

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "ASYNC_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_execute_graphql_http_async__execute_result_pre_set(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema

    class PreSetInExecutionHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            self.context.result = ExecutionResult(data={"preexecution": "async"})
            yield

    undine_settings.LIFECYCLE_HOOKS = [PreSetInExecutionHook]

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"preexecution": "async"})


@pytest.mark.asyncio
async def test_execute_graphql_http_async__async_resolver(undine_settings) -> None:
    async def async_resolver(obj: Any, info: Any) -> str:  # noqa: RUF029
        return "async result"

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLString,
                    resolve=async_resolver,
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
    result = await execute_graphql_http_async(params=params, request=MockRequest(method="POST"))

    assert result == ExecutionResult(data={"hello": "async result"})


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__subscription_stream(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _mock_event_stream() -> AsyncGenerator[Any, None]:  # noqa: RUF029
        yield "event1"

    with patch("undine.execution.execute_subscription", return_value=_mock_event_stream()):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    # The result should be an async generator (GraphQLStream)
    assert hasattr(result, "__aiter__")


def test_validate_multipart_mixed__mutation_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = False

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(
        method="POST",
        response_content_type=MediaType("multipart/mixed"),
    )
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_multipart_mixed(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_MULTIPART_MIXED_FOR_MUTATIONS"


def test_validate_multipart_mixed__mutation_allowed_post(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(
        method="POST",
        response_content_type=MediaType("multipart/mixed"),
    )
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_multipart_mixed(context)

    # No error - mutation is allowed with POST
    assert context.result is None


def test_validate_sse__mutation_not_allowed(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = False

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_sse(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_SSE_FOR_MUTATIONS"


def test_validate_sse__mutation_allowed_post(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_sse(context)

    # No error for allowed POST mutation
    assert context.result is None


def test_validate_websockets__mutation_not_allowed(undine_settings) -> None:
    undine_settings.ALLOW_MUTATIONS_WITH_WEBSOCKETS = False

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="WEBSOCKET")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_websockets(context)

    assert context.result is not None
    assert context.result.errors is not None
    assert context.result.errors[0].extensions.get("error_code") == "CANNOT_USE_WEBSOCKETS_FOR_MUTATIONS"


def test_validate_websockets__query_allowed_mutation_allowed(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True
    undine_settings.ALLOW_MUTATIONS_WITH_WEBSOCKETS = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="WEBSOCKET")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("mutation { testing }")

    _validate_websockets(context)

    assert context.result is None


def test_is_sse_request__with_token(undine_settings) -> None:
    @dataclasses.dataclass
    class MinimalRequest:
        method: str = "GET"
        META: dict = dataclasses.field(default_factory=dict)
        headers: dict = dataclasses.field(default_factory=dict)
        GET: dict = dataclasses.field(default_factory=dict)

    request = MinimalRequest()

    with patch("undine.execution.get_graphql_event_stream_token", return_value="some-token"):
        result = _is_sse_request(request)  # type: ignore[arg-type]

    assert result is True


def test_get_execution_context__success(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"hello": GraphQLField(GraphQLString)},
        ),
    )

    document = parse("query { hello }")
    context = _get_execution_context(
        document=document,
        root_value=None,
        context_value=MockRequest(method="POST"),
        variable_values={},
        operation_name=None,
        middleware=None,
    )

    assert context is not None


@pytest.mark.asyncio
async def test_map_source_to_response__full_loop(undine_settings) -> None:
    payloads = ["event_payload_1", "event_payload_2"]

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={
                "testing": GraphQLField(
                    GraphQLString,
                    resolve=lambda root, info: root,  # noqa: ARG005
                ),
            },
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _mock_event_stream() -> AsyncGenerator[str, None]:  # noqa: RUF029
        for payload in payloads:
            yield payload

    with patch("undine.execution.execute_subscription", return_value=_mock_event_stream()):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert hasattr(result, "__aiter__")
    results = [item async for item in result]

    assert len(results) == 2


@pytest.mark.asyncio
async def test_execute_graphql_http_async__sse_mutation_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_SSE = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="POST",
            response_content_type=MediaType("text/event-stream"),
        ),
    )

    # Should proceed past validation (will likely get a field error but not SSE validation error)
    assert result.errors is not None
    for error in result.errors:
        assert error.extensions.get("error_code") not in {
            "CANNOT_USE_SSE_FOR_MUTATIONS",
            "CANNOT_USE_SSE_FOR_MUTATIONS_NON_POST_REQUEST",
        }


@pytest.mark.asyncio
async def test_execute_graphql_http_async__multipart_mixed_mutation_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_MULTIPART_MIXED = True

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(
            method="POST",
            response_content_type=MediaType("multipart/mixed; boundary=graphql; subscriptionSpec=1.0"),
        ),
    )

    assert result.errors is not None
    for error in result.errors:
        assert error.extensions.get("error_code") not in {
            "CANNOT_USE_MULTIPART_MIXED_FOR_MUTATIONS",
            "CANNOT_USE_MULTIPART_MIXED_FOR_QUERIES",
        }


@pytest.mark.asyncio
async def test_execute_graphql_http_async__websocket_mutation_not_allowed(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_MUTATIONS_WITH_WEBSOCKETS = False

    params = GraphQLHttpParams(
        document="mutation { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_http_async(
        params=params,
        request=MockRequest(method="WEBSOCKET"),
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].extensions.get("error_code") == "CANNOT_USE_WEBSOCKETS_FOR_MUTATIONS"


def test_validate_multipart_mixed__query_allowed_fall_through(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_MULTIPART_MIXED = True

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("query { testing }")

    _validate_multipart_mixed(context)

    assert context.result is None


def test_validate_incremental__query_post_fall_through(undine_settings) -> None:
    undine_settings.EXPERIMENTAL_INCREMENTAL_DELIVERY = True

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("query { testing }")

    _validate_incremental(context)

    assert context.result is None


def test_validate_sse__query_allowed_fall_through(undine_settings) -> None:
    undine_settings.ALLOW_QUERIES_WITH_SSE = True

    params = GraphQLHttpParams(
        document="query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )

    request = MockRequest(method="POST")
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    context.document = parse("query { testing }")

    _validate_sse(context)

    assert context.result is None


@pytest.mark.asyncio
async def test_execute_graphql_with_subscription__validation_error(undine_settings) -> None:
    undine_settings.SCHEMA = example_schema
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    params = GraphQLHttpParams(
        document="query { testing } query { testing }",
        variables={},
        operation_name=None,
        extensions={},
    )
    result = await execute_graphql_with_subscription(
        params=params,
        request=MockRequest(method="WEBSOCKET"),
    )

    # Validation should fail
    assert result.data is None
    assert result.errors is not None


@pytest.mark.asyncio
async def test_create_source_event_stream__awaitable_event_stream(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _mock_event_stream() -> AsyncGenerator[str, None]:  # noqa: RUF029
        yield "event"

    stream = _mock_event_stream()

    async def _awaitable_stream() -> AsyncGenerator[str, None]:
        async for item in stream:
            yield item

    # Return an awaitable that resolves to an async iterable
    async def _mock_execute_subscription(exec_context: Any) -> Any:  # noqa: RUF029
        return _awaitable_stream()

    with patch("undine.execution.execute_subscription", side_effect=_mock_execute_subscription):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    # The result should be a stream
    assert hasattr(result, "__aiter__")


@pytest.mark.asyncio
async def test_create_source_event_stream__non_awaitable_event_stream(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _mock_event_stream() -> AsyncGenerator[str, None]:  # noqa: RUF029
        yield "event"

    stream = _mock_event_stream()

    # Verify the stream is not awaitable
    assert not isawaitable(stream)

    # Return the stream directly (NOT an awaitable coroutine) → is_awaitable is False → 451->460
    # Use new_callable=MagicMock to prevent AsyncMock (which wraps in a coroutine)
    with patch("undine.execution.execute_subscription", new_callable=MagicMock, return_value=stream):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    # The result should be the stream directly (not awaited)
    assert hasattr(result, "__aiter__")


@pytest.mark.asyncio
async def test_map_source_to_response__graphql_error_payload(undine_settings) -> None:
    error = GraphQLError("event error")

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _error_event_stream() -> AsyncGenerator[Any, None]:  # noqa: RUF029
        yield error

    with patch("undine.execution.execute_subscription", return_value=_error_event_stream()):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert hasattr(result, "__aiter__")
    results = [item async for item in result]

    assert len(results) == 1
    assert results[0].data is None
    assert results[0].errors is not None
    assert results[0].errors[0] is error


@pytest.mark.asyncio
async def test_map_source_to_response__graphql_error_group_payload(undine_settings) -> None:
    error1 = GraphQLError("event error 1")
    error2 = GraphQLError("event error 2")
    error_group = GraphQLErrorGroup(errors=[error1, error2])

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True

    async def _error_group_event_stream() -> AsyncGenerator[Any, None]:  # noqa: RUF029
        yield error_group

    with patch("undine.execution.execute_subscription", return_value=_error_group_event_stream()):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert hasattr(result, "__aiter__")
    results = [item async for item in result]

    assert len(results) == 1
    assert results[0].data is None
    assert results[0].errors is not None


@pytest.mark.asyncio
async def test_map_source_to_response__pre_existing_result_via_execution_hook(undine_settings) -> None:
    preset_result = ExecutionResult(data={"preset": "hook"})

    _calls = [0]

    class PreSetExecutionHook(LifecycleHook):
        def on_execution(self) -> Generator[None, None, None]:
            # Only pre-set on the first call; subsequent calls let the loop consume from stream
            if _calls[0] == 0:
                self.context.result = preset_result
            _calls[0] += 1
            yield

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={"testing": GraphQLField(GraphQLString)},
        ),
    )
    undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS = True
    undine_settings.LIFECYCLE_HOOKS = [PreSetExecutionHook]

    async def _empty_stream() -> AsyncGenerator[str, None]:  # noqa: RUF029
        return
        yield  # make it an async generator

    with patch("undine.execution.execute_subscription", return_value=_empty_stream()):
        params = GraphQLHttpParams(
            document="subscription { testing }",
            variables={},
            operation_name=None,
            extensions={},
        )
        result = await execute_graphql_with_subscription(
            params=params,
            request=MockRequest(method="WEBSOCKET"),
        )

    assert hasattr(result, "__aiter__")
    results = [item async for item in result]

    # The execution hook pre-sets the result on the first call, then the empty stream terminates
    assert len(results) == 1
    assert results[0] == preset_result


def test_get_execution_context__invalid_variable_values(undine_settings) -> None:
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "hello": GraphQLField(
                    GraphQLNonNull(GraphQLString),
                    args={
                        "name": GraphQLArgument(GraphQLNonNull(GraphQLString)),
                    },
                )
            },
        ),
    )

    document = parse("query($name: String!) { hello(name: $name) }")

    # Pass wrong type for the variable to trigger coercion errors
    with pytest.raises(GraphQLErrorGroup):
        _get_execution_context(
            document=document,
            root_value=None,
            context_value=MockRequest(method="POST"),
            variable_values={"name": 123},  # Wrong type - should be String
            operation_name=None,
            middleware=None,
        )
