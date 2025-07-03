from __future__ import annotations

from asyncio import ensure_future
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from contextlib import aclosing, nullcontext
from functools import wraps
from http import HTTPStatus
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from graphql import ExecutionContext, ExecutionResult, GraphQLError, execute, is_non_null_type, parse, validate
from graphql.execution.subscribe import execute_subscription

from undine.exceptions import (
    GraphQLAsyncNotSupportedError,
    GraphQLErrorGroup,
    GraphQLNoExecutionResultError,
    GraphQLUnexpectedError,
    GraphQLUseWebSocketsForSubscriptionsError,
)
from undine.hooks import LifecycleHookContext, LifecycleHookManager, use_lifecycle_hooks_async, use_lifecycle_hooks_sync
from undine.settings import undine_settings
from undine.utils.graphql.utils import is_subscription_operation, validate_get_request_operation
from undine.utils.graphql.validation_rules import get_validation_rules

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from graphql import GraphQLOutputType

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, ExecutionResultGen, P, WebSocketResult

__all__ = [
    "execute_graphql_http_async",
    "execute_graphql_http_sync",
    "execute_graphql_websocket",
]


class UndineExecutionContext(ExecutionContext):
    """Custom GraphQL execution context class."""

    def handle_field_error(self, error: GraphQLError, return_type: GraphQLOutputType) -> None:
        if not isinstance(error.original_error, GraphQLErrorGroup):
            return super().handle_field_error(error, return_type)

        error.original_error.located_by(error)

        if is_non_null_type(return_type):
            raise error.original_error

        for err in error.original_error.flatten():
            self.handle_field_error(err, return_type)

        return None

    @staticmethod
    def build_response(data: dict[str, Any] | None, errors: list[GraphQLError]) -> ExecutionResult:
        for error in errors:
            error.extensions.setdefault("status_code", HTTPStatus.BAD_REQUEST)  # type: ignore[union-attr]
        return ExecutionContext.build_response(data, errors)


# HTTP sync execution


def raised_exceptions_as_execution_results_sync(
    func: Callable[P, ExecutionResult],
) -> Callable[P, ExecutionResult]:
    """Wraps raised exceptions as GraphQL ExecutionResults if they happen in `execute_graphql_sync`."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return func(*args, **kwargs)

        except GraphQLError as error:
            return ExecutionResult(errors=[error])

        except GraphQLErrorGroup as error:
            return ExecutionResult(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLUnexpectedError(message=str(error))])

    return wrapper


@raised_exceptions_as_execution_results_sync
def execute_graphql_http_sync(params: GraphQLHttpParams, request: DjangoRequestProtocol) -> ExecutionResult:
    """
    Executes a GraphQL operation received from an HTTP request synchronously.
    Assumes that the schema has been validated (e.g. created using `undine.schema.create_schema`).

    :param params: GraphQL request parameters.
    :param request: The Django request object to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return _run_operation_sync(context)


@use_lifecycle_hooks_sync(hooks=undine_settings.OPERATION_HOOKS)
def _run_operation_sync(context: LifecycleHookContext) -> ExecutionResult:
    _parse_source_sync(context)
    if context.result is None:
        _validate_document_sync(context)
        if context.result is None:
            return _execute_sync(context)

    if context.result is None:  # pragma: no cover
        raise GraphQLNoExecutionResultError

    if isawaitable(context.result):
        ensure_future(context.result).cancel()
        raise GraphQLAsyncNotSupportedError

    return context.result


@use_lifecycle_hooks_sync(hooks=undine_settings.PARSE_HOOKS)
def _parse_source_sync(context: LifecycleHookContext) -> None:
    if context.result is not None:
        return

    if context.document is not None:
        return

    try:
        context.document = parse(
            source=context.source,
            no_location=undine_settings.NO_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )
    except GraphQLError as error:
        context.result = ExecutionResult(errors=[error])


@use_lifecycle_hooks_sync(hooks=undine_settings.VALIDATION_HOOKS)
def _validate_document_sync(context: LifecycleHookContext) -> None:
    if context.result is not None:
        return

    _validate_http(context)
    if context.result is not None:
        return

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=context.document,  # type: ignore[arg-type]
        rules=get_validation_rules(),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        context.result = ExecutionResult(errors=validation_errors)
        return


def _validate_http(context: LifecycleHookContext) -> None:
    if context.request.method == "GET":
        try:
            validate_get_request_operation(
                document=context.document,  # type: ignore[arg-type]
                operation_name=context.operation_name,
            )
        except GraphQLError as err:
            context.result = ExecutionResult(errors=[err])
            return

    if is_subscription_operation(context.document):  # type: ignore[arg-type]
        error: GraphQLError = GraphQLUseWebSocketsForSubscriptionsError()
        context.result = ExecutionResult(errors=[error])
        return


@use_lifecycle_hooks_sync(hooks=undine_settings.EXECUTION_HOOKS)
def _execute_sync(context: LifecycleHookContext) -> ExecutionResult:
    result = execute(
        schema=undine_settings.SCHEMA,
        document=context.document,  # type: ignore[arg-type]
        root_value=undine_settings.ROOT_VALUE,
        context_value=context.request,
        variable_values=context.variables,
        operation_name=context.operation_name,
        middleware=undine_settings.MIDDLEWARE,
        execution_context_class=undine_settings.EXECUTION_CONTEXT_CLASS,
    )

    if result is None:  # pragma: no cover
        raise GraphQLNoExecutionResultError

    if isawaitable(result):
        ensure_future(result).cancel()
        raise GraphQLAsyncNotSupportedError

    context.result = result
    return context.result


# HTTP async execution


def raised_exceptions_as_execution_results_async(
    func: Callable[P, Awaitable[ExecutionResult]],
) -> Callable[P, Awaitable[ExecutionResult]]:
    """Wraps raised exceptions as GraphQL ExecutionResults if they happen in `execute_graphql_async`."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> ExecutionResult:
        try:
            return await func(*args, **kwargs)

        except GraphQLError as error:
            return ExecutionResult(errors=[error])

        except GraphQLErrorGroup as error:
            return ExecutionResult(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLUnexpectedError(message=str(error))])

    return wrapper


@raised_exceptions_as_execution_results_async
async def execute_graphql_http_async(params: GraphQLHttpParams, request: DjangoRequestProtocol) -> ExecutionResult:
    """
    Executes a GraphQL operation received from an HTTP request asynchronously.
    Assumes that the schema has been validated (e.g. created using `undine.schema.create_schema`).

    :param params: GraphQL request parameters.
    :param request: The Django request object to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return await _run_operation_async(context)


@use_lifecycle_hooks_async(hooks=undine_settings.OPERATION_HOOKS)
async def _run_operation_async(context: LifecycleHookContext) -> ExecutionResult:
    await _parse_source_async(context)
    if context.result is None:
        await _validate_document_async(context)
        if context.result is None:
            return await _execute_async(context)

    if context.result is None:  # pragma: no cover
        raise GraphQLNoExecutionResultError

    if isinstance(context.result, AsyncIterator):
        raise GraphQLUseWebSocketsForSubscriptionsError

    if isawaitable(context.result):
        context.result = await context.result  # type: ignore[assignment]

    return context.result  # type: ignore[return-value]


@use_lifecycle_hooks_async(hooks=undine_settings.PARSE_HOOKS)
async def _parse_source_async(context: LifecycleHookContext) -> None:  # noqa: RUF029
    if context.result is not None:
        return

    if context.document is not None:
        return

    try:
        context.document = parse(
            source=context.source,
            no_location=undine_settings.NO_ERROR_LOCATION,
            max_tokens=undine_settings.MAX_TOKENS,
        )
    except GraphQLError as error:
        context.result = ExecutionResult(errors=[error])


@use_lifecycle_hooks_async(hooks=undine_settings.VALIDATION_HOOKS)
async def _validate_document_async(context: LifecycleHookContext) -> None:  # noqa: RUF029
    if context.result is not None:
        return

    if context.request.method != "WEBSOCKET":
        _validate_http(context)
        if context.result is not None:
            return

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=context.document,  # type: ignore[arg-type]
        rules=get_validation_rules(),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        context.result = ExecutionResult(errors=validation_errors)
        return


@use_lifecycle_hooks_async(hooks=undine_settings.EXECUTION_HOOKS)
async def _execute_async(context: LifecycleHookContext) -> ExecutionResult:
    result = execute(
        schema=undine_settings.SCHEMA,
        document=context.document,  # type: ignore[arg-type]
        root_value=undine_settings.ROOT_VALUE,
        context_value=context.request,
        variable_values=context.variables,
        operation_name=context.operation_name,
        middleware=undine_settings.MIDDLEWARE,
        execution_context_class=undine_settings.EXECUTION_CONTEXT_CLASS,
    )

    if result is None:  # pragma: no cover
        raise GraphQLNoExecutionResultError

    context.result = await result if isawaitable(result) else result
    return context.result


# WebSocket execution


def raised_exceptions_as_execution_results_websocket(
    func: Callable[P, Awaitable[WebSocketResult]],
) -> Callable[P, Awaitable[WebSocketResult]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> WebSocketResult:
        try:
            return await func(*args, **kwargs)

        except GraphQLError as error:
            return ExecutionResult(errors=[error])

        except GraphQLErrorGroup as error:
            return ExecutionResult(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            return ExecutionResult(errors=[GraphQLUnexpectedError(message=str(error))])

    return wrapper


@raised_exceptions_as_execution_results_websocket
async def execute_graphql_websocket(params: GraphQLHttpParams, request: DjangoRequestProtocol) -> WebSocketResult:
    """
    Executes a GraphQL operation received from an WebSocket asynchronously.
    Assumes that the schema has been validated (e.g. created using `undine.schema.create_schema`).

    :param params: GraphQL request parameters.
    :param request: The `WebSocketRequest` object to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return await _run_operation_websocket(context)


@use_lifecycle_hooks_async(hooks=undine_settings.OPERATION_HOOKS)
async def _run_operation_websocket(context: LifecycleHookContext) -> WebSocketResult:
    await _parse_source_async(context)
    if context.result is None:
        await _validate_document_async(context)
        if context.result is None:
            if is_subscription_operation(context.document):  # type: ignore[arg-type]
                return await _subscribe(context)
            return await _execute_async(context)

    if context.result is None:  # pragma: no cover
        raise GraphQLNoExecutionResultError

    if isawaitable(context.result):
        context.result = await context.result  # type: ignore[assignment]

    return context.result  # type: ignore[return-value]


async def _subscribe(context: LifecycleHookContext) -> WebSocketResult:
    """Executes a subscription operation. See: `graphql.execution.subscribe.subscribe`."""
    result_or_stream = await _create_source_event_stream(context=context)
    if isinstance(result_or_stream, ExecutionResult):
        return result_or_stream

    return _map_source_to_response(source=result_or_stream, context=context)


async def _create_source_event_stream(context: LifecycleHookContext) -> AsyncIterable[Any] | ExecutionResult:
    """
    A source event stream represents a sequence of events,
    each of which triggers a GraphQL execution for that event.
    """
    context_or_errors = undine_settings.EXECUTION_CONTEXT_CLASS.build(
        schema=undine_settings.SCHEMA,
        document=context.document,  # type: ignore[arg-type]
        root_value=undine_settings.ROOT_VALUE,
        context_value=context.request,
        raw_variable_values=context.variables,
        operation_name=context.operation_name,
        middleware=undine_settings.MIDDLEWARE,
    )
    if isinstance(context_or_errors, list):
        return ExecutionResult(data=None, errors=context_or_errors)

    try:
        event_stream = await execute_subscription(context_or_errors)
    except GraphQLError as error:
        return ExecutionResult(data=None, errors=[error])

    if not isinstance(event_stream, AsyncIterable):
        err = GraphQLUnexpectedError(message="Subscription did not return an event stream")
        return ExecutionResult(data=None, errors=[err])

    return event_stream


async def _map_source_to_response(source: AsyncIterable, context: LifecycleHookContext) -> ExecutionResultGen:
    """
    For each payload yielded from a subscription,
    map it over the normal GraphQL `execute` function, with `payload` as the `root_value`.
    """
    manager = aclosing(source) if isinstance(source, AsyncGenerator) else nullcontext()

    async with manager:
        stream = aiter(source)

        while True:
            context.result = None

            async with LifecycleHookManager(hooks=undine_settings.EXECUTION_HOOKS, context=context):
                if context.result is not None:
                    yield context.result
                    continue

                try:
                    payload = await anext(stream)
                except StopAsyncIteration:
                    break

                if isinstance(payload, GraphQLError):
                    context.result = ExecutionResult(errors=[payload])
                    yield context.result
                    continue

                if isinstance(payload, GraphQLErrorGroup):
                    context.result = ExecutionResult(errors=list(payload.flatten()))
                    yield context.result
                    continue

                result = execute(
                    schema=undine_settings.SCHEMA,
                    document=context.document,  # type: ignore[arg-type]
                    root_value=payload,
                    context_value=context.request,
                    variable_values=context.variables,
                    operation_name=context.operation_name,
                    middleware=undine_settings.MIDDLEWARE,
                    execution_context_class=undine_settings.EXECUTION_CONTEXT_CLASS,
                )
                context.result = await result if isawaitable(result) else result
                yield context.result
