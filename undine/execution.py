from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from contextlib import aclosing, nullcontext, suppress
from functools import wraps
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from graphql import (
    ExecutionContext,
    ExecutionResult,
    GraphQLEnumType,
    GraphQLError,
    MiddlewareManager,
    OperationType,
    ParallelVisitor,
    TypeInfo,
    TypeInfoVisitor,
    ValidationContext,
    ast_from_value,
    is_non_null_type,
    parse,
    version_info,
    visit,
)

from undine.exceptions import (
    GraphQLAsyncNotSupportedError,
    GraphQLCannotUseHTTPForMutationsNonPostRequestError,
    GraphQLCannotUseHTTPForSubscriptionsError,
    GraphQLCannotUseSSEForMutationsError,
    GraphQLCannotUseSSEForMutationsNonPostRequestError,
    GraphQLCannotUseSSEForQueriesError,
    GraphQLCannotUseWebSocketsForMutationsError,
    GraphQLCannotUseWebSocketsForQueriesError,
    GraphQLErrorGroup,
    GraphQLNoExecutionResultError,
    GraphQLSubscriptionNoEventStreamError,
    GraphQLUnexpectedError,
    GraphQLValidationAbortedError,
)
from undine.hooks import (
    ExecutionLifecycleHookManager,
    LifecycleHook,
    LifecycleHookContext,
    with_execution_lifecycle_hooks_manager,
    with_execution_lifecycle_hooks_manager_async,
    with_operation_lifecycle_hooks_manager,
    with_operation_lifecycle_hooks_manager_async,
    with_parse_lifecycle_hooks_manager,
    with_parse_lifecycle_hooks_manager_async,
    with_validation_lifecycle_hooks_manager,
    with_validation_lifecycle_hooks_manager_async,
)
from undine.http.utils import is_sse_request, is_websocket_request
from undine.settings import undine_settings
from undine.utils.graphql.undine_extensions import get_undine_orderset
from undine.utils.graphql.utils import (
    get_error_execution_result,
    get_operation_type,
    get_underlying_type,
    graphql_errors_hook,
    located_validation_error,
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

    from graphql import DocumentNode, GraphQLInputType, GraphQLOutputType, GraphQLSchema, Node, ValueNode
    from graphql.execution.build_field_plan import FieldGroup
    from graphql.execution.execute import IncrementalContext
    from graphql.pyutils import AwaitableOrValue, Path

    from undine.dataclasses import GraphQLHttpParams
    from undine.typing import DjangoRequestProtocol, ExecutionResultGen, P, SubscriptionResult


__all__ = [
    "execute_graphql_http_async",
    "execute_graphql_http_sync",
    "execute_graphql_with_subscription",
]


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
    :param request: The request to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return _run_operation_sync(context)


@with_operation_lifecycle_hooks_manager
def _run_operation_sync(context: LifecycleHookContext) -> ExecutionResult:
    if context.result is None:
        _parse_source_sync(context)
        if context.result is None:
            _validate_document_sync(context)
            if context.result is None:
                return _execute_sync(context)

    if isawaitable(context.result):
        cancel_awaitable(context.result)
        context.result = get_error_execution_result(GraphQLAsyncNotSupportedError())
        return context.result

    return context.result


@with_parse_lifecycle_hooks_manager
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


@with_validation_lifecycle_hooks_manager
def _validate_document_sync(context: LifecycleHookContext) -> None:
    if context.result is not None:
        return

    validation_errors = _validate(
        document=context.document,
        variables=context.variables,
        request=context.request,
    )
    if validation_errors:
        context.result = get_error_execution_result(validation_errors)
        return

    _validate_http(context)
    if context.result is not None:
        return


@with_execution_lifecycle_hooks_manager
def _execute_sync(context: LifecycleHookContext) -> ExecutionResult:
    try:
        exec_context = _get_execution_context(
            document=context.document,  # type: ignore[arg-type]
            root_value=undine_settings.ROOT_VALUE,
            context_value=context.request,
            variable_values=context.variables,
            operation_name=context.operation_name,
            middleware=_get_middleware_manager(context.lifecycle_hooks),
        )
    except GraphQLErrorGroup as error:
        context.result = get_error_execution_result(error)
        return context.result

    result = _execute(exec_context)

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
    :param request: The request to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return await _run_operation_async(context)


@with_operation_lifecycle_hooks_manager_async
async def _run_operation_async(context: LifecycleHookContext) -> ExecutionResult:
    if context.result is None:
        await _parse_source_async(context)
        if context.result is None:
            await _validate_document_async(context)
            if context.result is None:
                return await _execute_async(context)

    if isinstance(context.result, AsyncIterator):
        context.result = get_error_execution_result(GraphQLCannotUseHTTPForSubscriptionsError())
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


@with_parse_lifecycle_hooks_manager_async
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


@with_validation_lifecycle_hooks_manager_async
async def _validate_document_async(context: LifecycleHookContext) -> None:  # noqa: RUF029
    if context.result is not None:
        return

    validation_errors = _validate(
        document=context.document,
        variables=context.variables,
        request=context.request,
    )
    if validation_errors:
        context.result = get_error_execution_result(validation_errors)
        return

    if is_websocket_request(context.request):
        _validate_websockets(context)
    elif is_sse_request(context.request):
        _validate_sse(context)
    else:
        _validate_http(context)


@with_execution_lifecycle_hooks_manager_async
async def _execute_async(context: LifecycleHookContext) -> ExecutionResult:
    try:
        exec_context = _get_execution_context(
            document=context.document,  # type: ignore[arg-type]
            root_value=undine_settings.ROOT_VALUE,
            context_value=context.request,
            variable_values=context.variables,
            operation_name=context.operation_name,
            middleware=_get_middleware_manager(context.lifecycle_hooks),
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


# Subscription enabled execution


def raised_exceptions_as_execution_results_with_subscriptions(
    func: Callable[P, Awaitable[SubscriptionResult]],
) -> Callable[P, Awaitable[SubscriptionResult]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> SubscriptionResult:
        try:
            return await func(*args, **kwargs)

        except GraphQLError as error:
            return get_error_execution_result(error)

        except GraphQLErrorGroup as error:
            return get_error_execution_result(error)

        except Exception as error:  # noqa: BLE001
            return get_error_execution_result(GraphQLUnexpectedError(message=str(error)))

    return wrapper


@raised_exceptions_as_execution_results_with_subscriptions
async def execute_graphql_with_subscription(
    params: GraphQLHttpParams,
    request: DjangoRequestProtocol,
) -> SubscriptionResult:
    """
    Executes a GraphQL operation with subscriptions support asynchronously.
    Assumes that the schema has been validated (e.g. created using `undine.schema.create_schema`).

    :param params: GraphQL request parameters.
    :param request: The request to use as the GraphQL execution context value.
    """
    context = LifecycleHookContext.from_graphql_params(params=params, request=request)
    return await _run_operation_with_subscription(context)


@with_operation_lifecycle_hooks_manager_async
async def _run_operation_with_subscription(context: LifecycleHookContext) -> SubscriptionResult:
    if context.result is None:
        await _parse_source_async(context)
        if context.result is None:
            await _validate_document_async(context)
            if context.result is None:
                operation_type = get_operation_type(context.document, context.operation_name)
                if operation_type == OperationType.SUBSCRIPTION:
                    return await _subscribe(context)
                return await _execute_async(context)

    if isawaitable(context.result):
        context.result = await context.result  # type: ignore[assignment]

    return context.result  # type: ignore[return-value]


async def _subscribe(context: LifecycleHookContext) -> SubscriptionResult:
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
            middleware=_get_middleware_manager(context.lifecycle_hooks),
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

            async with ExecutionLifecycleHookManager(hooks=context.lifecycle_hooks):
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
                    middleware=_get_middleware_manager(context.lifecycle_hooks),
                )
                result = _execute(exec_context)

                context.result = await result if exec_context.is_awaitable(result) else result
                yield context.result


# Helpers


def _validate_http(context: LifecycleHookContext) -> None:
    operation_type = get_operation_type(context.document, context.operation_name)

    if operation_type == OperationType.MUTATION and context.request.method != "POST":
        context.result = get_error_execution_result(GraphQLCannotUseHTTPForMutationsNonPostRequestError())
        return

    if operation_type == OperationType.SUBSCRIPTION:
        context.result = get_error_execution_result(GraphQLCannotUseHTTPForSubscriptionsError())
        return


def _validate_sse(context: LifecycleHookContext) -> None:
    operation_type = get_operation_type(context.document, context.operation_name)

    if operation_type == OperationType.QUERY and not undine_settings.ALLOW_QUERIES_WITH_SSE:
        context.result = get_error_execution_result(GraphQLCannotUseSSEForQueriesError())
        return

    if operation_type == OperationType.MUTATION:
        if not undine_settings.ALLOW_MUTATIONS_WITH_SSE:
            context.result = get_error_execution_result(GraphQLCannotUseSSEForMutationsError())
            return

        if context.request.method != "POST":
            context.result = get_error_execution_result(GraphQLCannotUseSSEForMutationsNonPostRequestError())
            return


def _validate_websockets(context: LifecycleHookContext) -> None:
    operation_type = get_operation_type(context.document, context.operation_name)

    if operation_type == OperationType.QUERY and not undine_settings.ALLOW_QUERIES_WITH_WEBSOCKETS:
        context.result = get_error_execution_result(GraphQLCannotUseWebSocketsForQueriesError())
        return

    if operation_type == OperationType.MUTATION and not undine_settings.ALLOW_MUTATIONS_WITH_WEBSOCKETS:
        context.result = get_error_execution_result(GraphQLCannotUseWebSocketsForMutationsError())
        return


def _get_execution_context(
    *,
    document: DocumentNode,
    root_value: Any,
    context_value: Any,
    variable_values: dict[str, Any],
    operation_name: str | None,
    middleware: MiddlewareManager | None,
) -> UndineExecutionContext:
    context_or_errors = undine_settings.EXECUTION_CONTEXT_CLASS.build(
        schema=undine_settings.SCHEMA,
        document=document,
        root_value=root_value,
        context_value=context_value,
        raw_variable_values=variable_values,
        operation_name=operation_name,
        middleware=middleware,
    )

    if isinstance(context_or_errors, list):
        raise GraphQLErrorGroup(errors=context_or_errors)

    return context_or_errors


def _get_middleware_manager(lifecycle_hooks: list[LifecycleHook]) -> MiddlewareManager | None:
    hooks = [hook for hook in lifecycle_hooks if hook.__class__.resolve != LifecycleHook.resolve]
    return MiddlewareManager(*reversed(hooks)) if hooks else None


def _validate(
    document: DocumentNode,
    variables: dict[str, Any] | None = None,
    request: DjangoRequestProtocol | None = None,
) -> list[GraphQLError]:
    errors: list[GraphQLError] = []

    def on_error(error: GraphQLError) -> None:
        if len(errors) >= undine_settings.MAX_ERRORS:
            errors.append(GraphQLValidationAbortedError())
            raise GraphQLValidationAbortedError

        errors.append(error)

    type_info = TypeInfo(schema=undine_settings.SCHEMA)

    context = UndineValidationContext(
        schema=undine_settings.SCHEMA,
        document=document,
        variables=variables or {},
        request=request,
        type_info=type_info,
        on_error=on_error,
    )

    visitors = [rule(context) for rule in get_validation_rules(inside_request=request is not None)]

    with suppress(GraphQLValidationAbortedError):
        visit(document, TypeInfoVisitor(type_info, ParallelVisitor(visitors)))

    return errors


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


# Contexts


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


class UndineValidationContext(ValidationContext):
    """Custom GraphQL validation context class."""

    def __init__(  # noqa: PLR0917
        self,
        schema: GraphQLSchema,
        document: DocumentNode,
        variables: dict[str, Any],
        request: DjangoRequestProtocol | None,
        type_info: TypeInfo,
        on_error: Callable[[GraphQLError], None],
    ) -> None:
        super().__init__(schema=schema, ast=document, type_info=type_info, on_error=on_error)
        self.variables = variables
        self.request = request

    def variable_as_ast(self, variable: str, type_: GraphQLInputType) -> ValueNode | None:
        """Get the AST for the given variable."""
        value = self.variables.get(variable)
        if value is None:
            return None

        # If the variable is for an `OrderSet`, we need to convert the value to the python enum value.
        plain_type = get_underlying_type(type_)
        if isinstance(plain_type, GraphQLEnumType) and get_undine_orderset(plain_type) is not None:
            try:
                if isinstance(value, str):
                    value = plain_type.values[value].value
                elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                    value = [plain_type.values[item].value for item in value]
                else:
                    return None
            except Exception:  # noqa: BLE001
                return None

        try:
            return ast_from_value(value, type_)
        except Exception:  # noqa: BLE001
            return None
