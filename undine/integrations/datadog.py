from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from graphql import ExecutionResult, GraphQLError

from undine.hooks import LifecycleHook
from undine.settings import undine_settings
from undine.utils.graphql.redaction import redact_document
from undine.utils.graphql.utils import get_operation_definition

try:
    from ddtrace import trace

except ImportError as import_error:  # pragma: no cover
    msg = "The Datadog lifecycle hooks require the 'ddtrace' package. Install it with: pip install 'undine[datadog]'"
    raise ImportError(msg) from import_error


if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator

    from graphql import GraphQLFieldResolver, OperationType

    from undine.hooks import LifecycleHookContext
    from undine.typing import GQLInfo


__all__ = [
    "DatadogFullHook",
    "DatadogHook",
]


DATADOG_SPAN_TYPE: str = "graphql"

OPERATION_SPAN_NAME: str = "graphql.operation"
PARSE_SPAN_NAME: str = "graphql.parse"
VALIDATION_SPAN_NAME: str = "graphql.validate"
EXECUTION_SPAN_NAME: str = "graphql.execute"

OPERATION_NAME_TAG: str = "graphql.operation.name"
OPERATION_TYPE_TAG: str = "graphql.operation.type"
DOCUMENT_TAG: str = "graphql.document"
VARIABLES_TAG: str = "graphql.variables"

PATH_TAG: str = "graphql.path"
FIELD_NAME_TAG: str = "graphql.field.name"
FIELD_PATH_TAG: str = "graphql.field.path"
FIELD_PARENT_TYPE_TAG: str = "graphql.field.parent.type"


class DatadogHook(LifecycleHook):
    """
    Lifecycle hook that records a Datadog span for each GraphQL operation,
    with a child span for the parsing, validation and execution steps.
    """

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.tracer: trace.Tracer = trace.tracer
        self.operation_span: trace.Span | None = None
        self.parse_span: trace.Span | None = None
        self.validation_span: trace.Span | None = None
        self.execution_span: trace.Span | None = None

    def on_operation(self) -> Generator[None, None, None]:
        resource = _get_resource_name(self.context.source, self.context.operation_name)
        span = self._create_span(OPERATION_SPAN_NAME, service=undine_settings.DATADOG_SERVICE_NAME, resource=resource)
        self.operation_span = span

        if self.context.operation_name is not None:
            span.set_tag(OPERATION_NAME_TAG, self.context.operation_name)

        variables = undine_settings.DATADOG_VARIABLES_CALLBACK(self.context)
        if variables:
            span.set_tag(VARIABLES_TAG, json.dumps(variables, default=str))

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            _set_failing_if_error_result(span, self.context)
            undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_parse(self) -> Generator[None, None, None]:
        span = self._create_span(PARSE_SPAN_NAME, parent=self.operation_span)
        self.parse_span = span

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            # The document is only available once parsing is complete.
            self._describe_operation()
            undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_validation(self) -> Generator[None, None, None]:
        span = self._create_span(VALIDATION_SPAN_NAME, parent=self.operation_span)
        self.validation_span = span

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_execution(self) -> Generator[None, None, None]:
        span = self._create_span(EXECUTION_SPAN_NAME, parent=self.operation_span)
        self.execution_span = span

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
            span.finish()

    def _describe_operation(self) -> None:
        """Add the attributes that require the parsed document to the operation span."""
        document = self.context.document
        if document is None:
            return

        try:
            operation_definition = get_operation_definition(document, self.context.operation_name)
        except GraphQLError:
            # The operation the client asked for doesn't exist. Validation reports this to the client.
            return

        operation_type: OperationType = operation_definition.operation
        operation_name = operation_definition.name.value if operation_definition.name is not None else None

        span: trace.Span = self.operation_span  # type: ignore[assignment]

        span.set_tag(OPERATION_TYPE_TAG, operation_type.value)
        span.set_tag(DOCUMENT_TAG, redact_document(document))
        if operation_name is not None:
            span.set_tag(OPERATION_NAME_TAG, operation_name)

        span.name = _get_operation_span_name(operation_type, operation_name)
        span.resource = _get_resource_name(self.context.source, operation_name)

    def _create_span(
        self,
        name: str,
        *,
        parent: trace.Span | trace.Context | None = None,
        service: str | None = None,
        resource: str | None = None,
    ) -> trace.Span:
        if parent is None:
            parent = self.tracer.context_provider.active()
        return self.tracer.start_span(
            name,
            child_of=parent,
            service=service,
            resource=resource,
            span_type=DATADOG_SPAN_TYPE,
            activate=False,
        )


class DatadogFullHook(DatadogHook):
    """Same as `DatadogHook`, but also records a span for each resolved field."""

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:  # type: ignore[override]
        field_path = _get_field_path(info)

        span = self._create_span(field_path, parent=self.execution_span)

        span.set_tag(FIELD_NAME_TAG, info.field_name)
        span.set_tag(FIELD_PARENT_TYPE_TAG, info.parent_type.name)
        span.set_tag(FIELD_PATH_TAG, field_path)
        span.set_tag(PATH_TAG, _get_response_path(info))

        try:
            result = resolver(root, info, **kwargs)
        except BaseException as error:
            _set_failing(error, span)
            undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
            span.finish()
            raise

        if info.is_awaitable(result):
            return _await_field_result(result, span, self.context)

        undine_settings.DATADOG_SPAN_CALLBACK(span, self.context)
        span.finish()
        return result


async def _await_field_result(result: Awaitable[Any], span: trace.Span, context: LifecycleHookContext) -> Any:
    try:
        return await result

    except BaseException as error:
        _set_failing(error, span)
        raise

    finally:
        undine_settings.DATADOG_SPAN_CALLBACK(span, context)
        span.finish()


def _set_failing(error: BaseException, span: trace.Span) -> None:
    span.record_exception(error)


def _set_failing_if_error_result(span: trace.Span, context: LifecycleHookContext) -> None:
    result = context.result
    if not isinstance(result, ExecutionResult) or not result.errors:
        return

    for error in result.errors:
        span.record_exception(error)


def _get_resource_name(source: str, operation_name: str | None) -> str:
    query_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if operation_name:
        return f"{operation_name}:{query_hash}"
    return query_hash


def _get_field_path(info: GQLInfo) -> str:
    return f"{info.parent_type}.{info.field_name}"


def _get_response_path(info: GQLInfo) -> str:
    return ".".join(str(part) for part in info.path.as_list())


def _get_operation_span_name(operation_type: OperationType, operation_name: str | None) -> str:
    if operation_name is None:
        return operation_type.value
    return f"{operation_type.value} {operation_name}"


# Setting defaults


def no_op_span_callback(span: trace.Span, context: LifecycleHookContext) -> None:
    """Add no tags to the operation span."""


def no_traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
    """Attach no variables to traces, since they can contain sensitive data."""
    return {}
