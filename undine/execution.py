from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from contextlib import aclosing, nullcontext
from functools import wraps
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from graphql import ExecutionContext, ExecutionResult, GraphQLError, is_non_null_type, parse, validate, version_info

from undine.exceptions import (
    GraphQLAsyncNotSupportedError,
    GraphQLErrorGroup,
    GraphQLNoExecutionResultError,
    GraphQLSubscriptionNoEventStreamError,
    GraphQLUnexpectedError,
    GraphQLUseWebSocketsForSubscriptionsError,
)
from undine.hooks import LifecycleHookContext, LifecycleHookManager, use_lifecycle_hooks_async, use_lifecycle_hooks_sync
from undine.settings import undine_settings
from undine.utils.graphql.utils import (
    get_error_execution_result,
    graphql_errors_hook,
    is_subscription_operation,
    located_validation_error,
    validate_get_request_operation,
)
from undine.utils.graphql.validation_rules import get_validation_rules
from undine.utils.reflection import cancel_awaitable

try:
    # graphql-core >= 3.3.0
    from graphql.execution.execute import execute_subscription
except ImportError:
    from graphql.execution.subscribe import execute_subscription


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from graphql import DocumentNode, GraphQLOutputType, Node
    from graphql.execution.build_field_plan import FieldGroup
    from graphql.execution.execute import IncrementalContext
    from graphql.pyutils import AwaitableOrValue, Path

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, ExecutionResultGen, P, WebSocketResult

__all__ = [
    "execute_graphql_http_async",
    "execute_graphql_http_sync",
    "execute_graphql_websocket",
]


class UndineExecutionContext(ExecutionContext):
    """Custom GraphQL execution context class."""

    if version_info >= (3, 3, 0):

        def handle_field_error(
            self,
            raw_error: Exception,
            return_type: GraphQLOutputType,
            field_group: FieldGroup,
            path: Path,
            incremental_context: IncrementalContext | None = None,
        ) -> None:
            from graphql.execution.execute import to_nodes  # noqa: PLC0415

            match raw_error:
                case ValidationError():
                    error_group = located_validation_error(raw_error, to_nodes(field_group), path.as_list())
                    self.handle_field_errors_group(error_group, return_type, field_group, path, incremental_context)

                case GraphQLErrorGroup():
                    self.handle_field_errors_group(raw_error, return_type, field_group, path, incremental_context)

                case _:
                    super().handle_field_error(
                        raw_error=raw_error,
                        return_type=return_type,
                        field_group=field_group,
                        path=path,
                        incremental_context=incremental_context,
                    )

        def handle_field_errors_group(
            self,
            raw_error: GraphQLErrorGroup,
            return_type: GraphQLOutputType,
            field_group: FieldGroup,
            path: Path,
            incremental_context: IncrementalContext | None = None,
        ) -> None:
            from graphql.execution.execute import to_nodes  # noqa: PLC0415

            for err in raw_error.flatten():
                if not err.path:
                    err.path = path.as_list()
                if not err.nodes:
                    err.nodes = to_nodes(field_group)

            if is_non_null_type(return_type):
                raise raw_error

            for err in raw_error.flatten():
                self.handle_field_error(
                    raw_error=err,
                    return_type=return_type,
                    field_group=field_group,
                    path=path,
                    incremental_context=incremental_context,
                )

    else:

        def handle_field_error(self, error: GraphQLError, return_type: GraphQLOutputType) -> None:
            raw_error: Exception = error.original_error or error
            path = error.path or []
            field_nodes = error.nodes or []

            match raw_error:
                case ValidationError():
                    error_group = located_validation_error(raw_error, field_nodes, path)
                    self.handle_field_errors_group(error_group, return_type, field_nodes, path)

                case GraphQLErrorGroup():
                    self.handle_field_errors_group(raw_error, return_type, field_nodes, path)

                case _:
                    super().handle_field_error(error=error, return_type=return_type)

        def handle_field_errors_group(
            self,
            raw_error: GraphQLErrorGroup,
            return_type: GraphQLOutputType,
            field_nodes: list[Node],
            path: list[str | int],
        ) -> None:
            for err in raw_error.flatten():
                if not err.path:
                    err.path = path
                if not err.nodes:
                    err.nodes = field_nodes

            if is_non_null_type(return_type):
                raise raw_error

            for err in raw_error.flatten():
                self.handle_field_error(err, return_type)


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
            return get_error_execution_result(error)

        except GraphQLErrorGroup as error:
            return get_error_execution_result(error)

        except Exception as error:  # noqa: BLE001
            return get_error_execution_result(GraphQLUnexpectedError(message=str(error)))

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
        context.result = get_error_execution_result(GraphQLNoExecutionResultError())
        return context.result

    if isawaitable(context.result):
        cancel_awaitable(context.result)
        context.result = get_error_execution_result(GraphQLAsyncNotSupportedError())
        return context.result

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
        context.result = get_error_execution_result(error)


@use_lifecycle_hooks_sync(hooks=undine_settings.VALIDATION_HOOKS)
def _validate_document_sync(context: LifecycleHookContext) -> None:
    if context.result is not None:
        return

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=context.document,  # type: ignore[arg-type]
        rules=get_validation_rules(context.request),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        context.result = get_error_execution_result(validation_errors)
        return

    _validate_http(context)
    if context.result is not None:
        return


def _validate_http(context: LifecycleHookContext) -> None:
    if context.request.method == "GET":
        try:
            validate_get_request_operation(
                document=context.document,  # type: ignore[arg-type]
                operation_name=context.operation_name,
            )
        except GraphQLError as error:
            context.result = get_error_execution_result(error)
            return

    if is_subscription_operation(context.document, context.operation_name):  # type: ignore[arg-type]
        context.result = get_error_execution_result(GraphQLUseWebSocketsForSubscriptionsError())
        return


@use_lifecycle_hooks_sync(hooks=undine_settings.EXECUTION_HOOKS)
def _execute_sync(context: LifecycleHookContext) -> ExecutionResult:
    try:
        exec_context = _get_execution_context(
            document=context.document,  # type: ignore[arg-type]
            root_value=undine_settings.ROOT_VALUE,
            context_value=context.request,
            variable_values=context.variables,
            operation_name=context.operation_name,
        )
    except GraphQLErrorGroup as error:
        context.result = get_error_execution_result(error)
        return context.result

    result = _execute(exec_context)

    if result is None:  # pragma: no cover
        context.result = get_error_execution_result(GraphQLNoExecutionResultError())
        return context.result

    if exec_context.is_awaitable(result):
        cancel_awaitable(result)
        context.result = get_error_execution_result(GraphQLAsyncNotSupportedError())
        return context.result

    if version_info >= (3, 3, 0):
        from graphql import ExperimentalIncrementalExecutionResults  # noqa: PLC0415
        from graphql.execution.execute import UNEXPECTED_MULTIPLE_PAYLOADS  # noqa: PLC0415

        if isinstance(result, ExperimentalIncrementalExecutionResults):
            context.result = get_error_execution_result(GraphQLError(UNEXPECTED_MULTIPLE_PAYLOADS))
            return context.result

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
            return get_error_execution_result(error)

        except GraphQLErrorGroup as error:
            return get_error_execution_result(error)

        except Exception as error:  # noqa: BLE001
            return get_error_execution_result(GraphQLUnexpectedError(message=str(error)))

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
        context.result = get_error_execution_result(GraphQLNoExecutionResultError())
        return context.result

    if isinstance(context.result, AsyncIterator):
        context.result = get_error_execution_result(GraphQLUseWebSocketsForSubscriptionsError())
        return context.result

    if isawaitable(context.result):
        context.result = await context.result  # type: ignore[assignment]

    if version_info >= (3, 3, 0):
        from graphql import ExperimentalIncrementalExecutionResults  # noqa: PLC0415
        from graphql.execution.execute import UNEXPECTED_MULTIPLE_PAYLOADS  # noqa: PLC0415

        if isinstance(context.result, ExperimentalIncrementalExecutionResults):
            context.result = get_error_execution_result(GraphQLError(UNEXPECTED_MULTIPLE_PAYLOADS))
            return context.result

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
        context.result = get_error_execution_result(error)


@use_lifecycle_hooks_async(hooks=undine_settings.VALIDATION_HOOKS)
async def _validate_document_async(context: LifecycleHookContext) -> None:  # noqa: RUF029
    if context.result is not None:
        return

    validation_errors = validate(
        schema=undine_settings.SCHEMA,
        document_ast=context.document,  # type: ignore[arg-type]
        rules=get_validation_rules(context.request),
        max_errors=undine_settings.MAX_ERRORS,
    )
    if validation_errors:
        context.result = get_error_execution_result(validation_errors)
        return

    if context.request.method != "WEBSOCKET":
        _validate_http(context)
        if context.result is not None:
            return


@use_lifecycle_hooks_async(hooks=undine_settings.EXECUTION_HOOKS)
async def _execute_async(context: LifecycleHookContext) -> ExecutionResult:
    try:
        exec_context = _get_execution_context(
            document=context.document,  # type: ignore[arg-type]
            root_value=undine_settings.ROOT_VALUE,
            context_value=context.request,
            variable_values=context.variables,
            operation_name=context.operation_name,
        )
    except GraphQLErrorGroup as error:
        context.result = get_error_execution_result(error)
        return context.result

    result = _execute(exec_context)

    if result is None:  # pragma: no cover
        context.result = get_error_execution_result(GraphQLNoExecutionResultError())
        return context.result

    context.result = await result if exec_context.is_awaitable(result) else result

    if version_info >= (3, 3, 0):
        from graphql import ExperimentalIncrementalExecutionResults  # noqa: PLC0415
        from graphql.execution.execute import UNEXPECTED_MULTIPLE_PAYLOADS  # noqa: PLC0415

        if isinstance(context.result, ExperimentalIncrementalExecutionResults):
            context.result = get_error_execution_result(GraphQLError(UNEXPECTED_MULTIPLE_PAYLOADS))
            return context.result

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
            return get_error_execution_result(error)

        except GraphQLErrorGroup as error:
            return get_error_execution_result(error)

        except Exception as error:  # noqa: BLE001
            return get_error_execution_result(GraphQLUnexpectedError(message=str(error)))

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
            if is_subscription_operation(context.document, context.operation_name):  # type: ignore[arg-type]
                return await _subscribe(context)
            return await _execute_async(context)

    if context.result is None:  # pragma: no cover
        context.result = get_error_execution_result(GraphQLNoExecutionResultError())
        return context.result

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
    try:
        exec_context = _get_execution_context(
            document=context.document,  # type: ignore[arg-type]
            root_value=undine_settings.ROOT_VALUE,
            context_value=context.request,
            variable_values=context.variables,
            operation_name=context.operation_name,
        )
    except GraphQLErrorGroup as error:
        return get_error_execution_result(error)

    try:
        event_stream = execute_subscription(exec_context)
        if exec_context.is_awaitable(event_stream):
            event_stream = await event_stream

    except GraphQLError as error:
        return get_error_execution_result(error)

    except GraphQLErrorGroup as error:
        return get_error_execution_result(error)

    if not isinstance(event_stream, AsyncIterable):
        return get_error_execution_result(GraphQLSubscriptionNoEventStreamError())

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
                    context.result = get_error_execution_result(payload)
                    yield context.result
                    continue

                if isinstance(payload, GraphQLErrorGroup):
                    context.result = get_error_execution_result(payload)
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

                context.result = await result if exec_context.is_awaitable(result) else result
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


def _execute(context: UndineExecutionContext) -> ExecutionResult:
    if version_info < (3, 3, 0):
        return _execute_old(context)
    return _execute_new(context)


def _execute_old(context: UndineExecutionContext) -> AwaitableOrValue[ExecutionResult]:
    """Execution for graphql-core < 3.3.0."""
    try:
        data_or_awaitable = context.execute_operation(context.operation, context.root_value)

    except GraphQLError as error:
        context.errors.append(error)
        return get_error_execution_result(context.errors)

    except GraphQLErrorGroup as error:
        context.errors.extend(error.flatten())
        return get_error_execution_result(context.errors)

    if context.is_awaitable(data_or_awaitable):

        async def await_result() -> ExecutionResult:
            try:
                data = await data_or_awaitable

            except GraphQLError as err:
                context.errors.append(err)
                return get_error_execution_result(context.errors)

            except GraphQLErrorGroup as err:
                context.errors.extend(err.flatten())
                return get_error_execution_result(context.errors)

            else:
                graphql_errors_hook(context.errors)
                return ExecutionResult(data=data, errors=context.errors or None)

        return await_result()

    graphql_errors_hook(context.errors)
    return ExecutionResult(data=data_or_awaitable, errors=context.errors or None)


def _execute_new(context: UndineExecutionContext) -> AwaitableOrValue[ExecutionResult]:
    """Execution for graphql-core >= 3.3.0a10."""
    from graphql import ExperimentalIncrementalExecutionResults  # noqa: PLC0415

    try:
        data = context.execute_operation()

    except GraphQLError as error:
        context.errors = context.errors or []
        context.errors.append(error)
        return get_error_execution_result(context.errors)

    except GraphQLErrorGroup as err:
        context.errors = context.errors or []
        context.errors.extend(err.flatten())
        return get_error_execution_result(context.errors)

    if context.is_awaitable(data):

        async def await_result() -> ExecutionResult:
            try:
                awaited_data = await data

            except GraphQLError as error:
                context.errors = context.errors or []
                context.errors.append(error)
                return get_error_execution_result(context.errors)

            except GraphQLErrorGroup as err:
                context.errors = context.errors or []
                context.errors.extend(err.flatten())
                return get_error_execution_result(context.errors)

            if isinstance(awaited_data, ExecutionResult) and awaited_data.errors is not None:
                graphql_errors_hook(awaited_data.errors)

            if (
                isinstance(awaited_data, ExperimentalIncrementalExecutionResults)
                and awaited_data.initial_result.errors is not None
            ):
                graphql_errors_hook(awaited_data.initial_result.errors)

            return awaited_data

        return await_result()

    if isinstance(data, ExecutionResult) and data.errors is not None:
        graphql_errors_hook(data.errors)

    if isinstance(data, ExperimentalIncrementalExecutionResults) and data.initial_result.errors is not None:
        graphql_errors_hook(data.initial_result.errors)

    return data
