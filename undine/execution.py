from __future__ import annotations

import copy
from asyncio import ensure_future
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from contextlib import aclosing, nullcontext
from functools import wraps
from http import HTTPStatus
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from graphql import ExecutionContext, ExecutionResult, GraphQLError, is_non_null_type, parse, validate
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
from undine.utils.graphql.utils import build_response, is_subscription_operation, validate_get_request_operation
from undine.utils.graphql.validation_rules import get_validation_rules
from undine.utils.logging import log_traceback
from undine.utils.model_utils import get_validation_error_messages
from undine.utils.reflection import get_traceback

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from graphql import DocumentNode, GraphQLOutputType
    from graphql.pyutils import AwaitableOrValue

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
        if isinstance(error.original_error, ValidationError):
            self.handle_django_validation_error(error, error.original_error)

        if not isinstance(error.original_error, GraphQLErrorGroup):
            return super().handle_field_error(error, return_type)

        error.original_error.located_by(error)

        if is_non_null_type(return_type):
            raise error.original_error

        for err in error.original_error.flatten():
            self.handle_field_error(err, return_type)

        return None

    def handle_django_validation_error(self, graphql_error: GraphQLError, original_error: ValidationError) -> None:
        graphql_error.extensions = graphql_error.extensions or {}
        graphql_error.extensions["status_code"] = HTTPStatus.BAD_REQUEST

        code = getattr(original_error, "code", None)
        if code:
            graphql_error.extensions["error_code"] = code.upper()

        error_messages = get_validation_error_messages(original_error)

        errors: list[GraphQLError] = []
        for field, messages in error_messages.items():
            for message in messages:
                path: list[Any] | None = graphql_error.path
                if field and graphql_error.path:
                    path = graphql_error.path + field.split(".")

                new_error = copy.deepcopy(graphql_error)
                new_error.message = message
                new_error.path = path
                errors.append(new_error)

        graphql_error.original_error = GraphQLErrorGroup(errors=errors)

    @staticmethod
    def build_response(data: dict[str, Any] | None, errors: list[GraphQLError]) -> ExecutionResult:
        for error in errors:
            extensions: dict[str, Any] = error.extensions  # type: ignore[union-attr,assignment]

            if error.original_error is None or isinstance(error.original_error, GraphQLError):
                extensions.setdefault("status_code", HTTPStatus.BAD_REQUEST)
            else:
                extensions.setdefault("status_code", HTTPStatus.INTERNAL_SERVER_ERROR)

            if error.__traceback__ is not None:
                log_traceback(error.__traceback__)

                if undine_settings.INCLUDE_ERROR_TRACEBACK:
                    extensions["traceback"] = get_traceback(error.__traceback__)

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
            return build_response(errors=[error])

        except GraphQLErrorGroup as error:
            return build_response(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            err = GraphQLUnexpectedError(message=str(error))
            return build_response(errors=[err])

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
        context.result = build_response(errors=[error])


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
        context.result = build_response(errors=validation_errors)
        return


def _validate_http(context: LifecycleHookContext) -> None:
    if context.request.method == "GET":
        try:
            validate_get_request_operation(
                document=context.document,  # type: ignore[arg-type]
                operation_name=context.operation_name,
            )
        except GraphQLError as err:
            context.result = build_response(errors=[err])
            return

    if is_subscription_operation(context.document):  # type: ignore[arg-type]
        error: GraphQLError = GraphQLUseWebSocketsForSubscriptionsError()
        context.result = build_response(errors=[error])
        return


@use_lifecycle_hooks_sync(hooks=undine_settings.EXECUTION_HOOKS)
def _execute_sync(context: LifecycleHookContext) -> ExecutionResult:
    exec_context = _get_execution_context(
        document=context.document,  # type: ignore[arg-type]
        root_value=undine_settings.ROOT_VALUE,
        context_value=context.request,
        variable_values=context.variables,
        operation_name=context.operation_name,
    )
    result = _execute(exec_context)

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
            return build_response(errors=[error])

        except GraphQLErrorGroup as error:
            return build_response(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            err = GraphQLUnexpectedError(message=str(error))
            return build_response(errors=[err])

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
        context.result = build_response(errors=[error])


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
        context.result = build_response(errors=validation_errors)
        return


@use_lifecycle_hooks_async(hooks=undine_settings.EXECUTION_HOOKS)
async def _execute_async(context: LifecycleHookContext) -> ExecutionResult:
    exec_context = _get_execution_context(
        document=context.document,  # type: ignore[arg-type]
        root_value=undine_settings.ROOT_VALUE,
        context_value=context.request,
        variable_values=context.variables,
        operation_name=context.operation_name,
    )
    result = _execute(exec_context)

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
            return build_response(errors=[error])

        except GraphQLErrorGroup as error:
            return build_response(errors=list(error.flatten()))

        except Exception as error:  # noqa: BLE001
            err = GraphQLUnexpectedError(message=str(error))
            return build_response(errors=[err])

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
        return build_response(errors=context_or_errors)

    try:
        event_stream = await execute_subscription(context_or_errors)
    except GraphQLError as error:
        return build_response(errors=[error])

    if not isinstance(event_stream, AsyncIterable):
        err = GraphQLUnexpectedError(message="Subscription did not return an event stream")
        return build_response(errors=[err])

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
                    context.result = build_response(errors=[payload])
                    yield context.result
                    continue

                if isinstance(payload, GraphQLErrorGroup):
                    context.result = build_response(errors=list(payload.flatten()))
                    yield context.result
                    continue

                exec_context = _get_execution_context(
                    document=context.document,
                    root_value=payload,
                    context_value=context.request,
                    variable_values=context.variables,
                    operation_name=context.operation_name,
                )
                result = _execute(exec_context)

                context.result = await result if isawaitable(result) else result
                yield context.result


# Helpers


def _get_execution_context(
    document: DocumentNode,
    root_value: Any,
    context_value: Any,
    variable_values: dict[str, Any],
    operation_name: str | None,
) -> UndineExecutionContext:
    context_or_errors = undine_settings.EXECUTION_CONTEXT_CLASS.build(
        schema=undine_settings.SCHEMA,
        document=document,
        root_value=root_value,
        context_value=context_value,
        raw_variable_values=variable_values,
        operation_name=operation_name,
        middleware=undine_settings.MIDDLEWARE,
    )

    if isinstance(context_or_errors, list):
        raise GraphQLErrorGroup(errors=context_or_errors)

    return context_or_errors


def _execute(context: UndineExecutionContext) -> AwaitableOrValue[ExecutionResult]:
    try:
        data_or_awaitable = context.execute_operation(context.operation, context.root_value)

    except GraphQLError as error:
        context.errors.append(error)
        return context.build_response(data=None, errors=context.errors)

    except GraphQLErrorGroup as error:
        context.errors.extend(error.flatten())
        return context.build_response(data=None, errors=context.errors)

    if context.is_awaitable(data_or_awaitable):

        async def await_result() -> ExecutionResult:
            try:
                data = await data_or_awaitable

            except GraphQLError as err:
                context.errors.append(err)
                return context.build_response(data=None, errors=context.errors)

            except GraphQLErrorGroup as err:
                context.errors.extend(err.flatten())
                return context.build_response(data=None, errors=context.errors)

            else:
                return context.build_response(data=data, errors=context.errors)

        return await_result()

    return context.build_response(data=data_or_awaitable, errors=context.errors)
