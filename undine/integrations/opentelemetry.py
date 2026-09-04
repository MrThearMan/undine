from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from graphql import ExecutionResult, GraphQLError

from undine.hooks import HookPriority, LifecycleHook
from undine.settings import undine_settings
from undine.utils.graphql.redaction import redact_document, redact_variables
from undine.utils.graphql.utils import get_operation_definition

try:
    from opentelemetry import trace

except ImportError as import_error:  # pragma: no cover
    msg = (
        "The OpenTelemetry lifecycle hooks require the 'opentelemetry-api' package. "
        "Install it with: pip install 'undine[opentelemetry]'"
    )
    raise ImportError(msg) from import_error


if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator

    from graphql import GraphQLFieldResolver, OperationType

    from undine.hooks import LifecycleHookContext
    from undine.typing import GQLInfo


__all__ = [
    "OpenTelemetryFullHook",
    "OpenTelemetryHook",
]


OPEN_TELEMETRY_TRACER_NAME: str = "undine"

OPERATION_SPAN_NAME: str = "graphql.operation"
PARSE_SPAN_NAME: str = "graphql.parse"
VALIDATION_SPAN_NAME: str = "graphql.validate"
EXECUTION_SPAN_NAME: str = "graphql.execute"

OPERATION_NAME_ATTRIBUTE: str = "graphql.operation.name"
OPERATION_TYPE_ATTRIBUTE: str = "graphql.operation.type"
DOCUMENT_ATTRIBUTE: str = "graphql.document"
VARIABLES_ATTRIBUTE: str = "graphql.variables"

PATH_ATTRIBUTE: str = "graphql.path"
FIELD_NAME_ATTRIBUTE: str = "graphql.field.name"
FIELD_PATH_ATTRIBUTE: str = "graphql.field.path"
FIELD_PARENT_TYPE_ATTRIBUTE: str = "graphql.field.parent.type"


class OpenTelemetryHook(LifecycleHook):
    """
    Lifecycle hook that records an OpenTelemetry span for each GraphQL operation,
    with a child span for the parsing, validation and execution steps.
    """

    priority: ClassVar[int] = HookPriority.TRACING

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.tracer: trace.Tracer = trace.get_tracer(OPEN_TELEMETRY_TRACER_NAME)
        self.operation_span: trace.Span | None = None
        self.parse_span: trace.Span | None = None
        self.validation_span: trace.Span | None = None
        self.execution_span: trace.Span | None = None

    def on_operation(self) -> Generator[None, None, None]:
        span = self._create_span(OPERATION_SPAN_NAME)
        self.operation_span = span

        if self.context.operation_name is not None:
            span.set_attribute(OPERATION_NAME_ATTRIBUTE, self.context.operation_name)

        variables = undine_settings.OPENTELEMETRY_VARIABLES_CALLBACK(self.context)
        if variables:
            span.set_attribute(VARIABLES_ATTRIBUTE, json.dumps(variables, default=str))

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            _set_failing_if_error_result(span, self.context)
            undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
            span.end()

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
            undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
            span.end()

    def on_validation(self) -> Generator[None, None, None]:
        span = self._create_span(VALIDATION_SPAN_NAME, parent=self.operation_span)
        self.validation_span = span

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
            span.end()

    def on_execution(self) -> Generator[None, None, None]:
        span = self._create_span(EXECUTION_SPAN_NAME, parent=self.operation_span)
        self.execution_span = span

        try:
            yield
        except BaseException as error:
            _set_failing(error, span)
            raise
        finally:
            undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
            span.end()

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

        span.set_attribute(OPERATION_TYPE_ATTRIBUTE, operation_type.value)
        span.set_attribute(DOCUMENT_ATTRIBUTE, redact_document(document))
        if operation_name is not None:
            span.set_attribute(OPERATION_NAME_ATTRIBUTE, operation_name)

        span.update_name(_get_operation_span_name(operation_type, operation_name))

    def _create_span(self, name: str, *, parent: trace.Span | None = None) -> trace.Span:
        return self.tracer.start_span(name, context=trace.set_span_in_context(parent) if parent else None)


class OpenTelemetryFullHook(OpenTelemetryHook):
    """Same as `OpenTelemetryHook`, but also records a span for each resolved field."""

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.skip_field_spans: bool = False

    def on_execution(self) -> Generator[None, None, None]:
        self.skip_field_spans = undine_settings.OPENTELEMETRY_SKIP_FIELD_SPANS_PREDICATE(self.context)
        yield from super().on_execution()

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:  # type: ignore[override]
        if self.skip_field_spans:
            return resolver(root, info, **kwargs)

        field_path = _get_field_path(info)

        span = self._create_span(field_path, parent=self.execution_span)

        span.set_attribute(FIELD_NAME_ATTRIBUTE, info.field_name)
        span.set_attribute(FIELD_PARENT_TYPE_ATTRIBUTE, info.parent_type.name)
        span.set_attribute(FIELD_PATH_ATTRIBUTE, field_path)
        span.set_attribute(PATH_ATTRIBUTE, _get_response_path(info))

        try:
            result = resolver(root, info, **kwargs)
        except BaseException as error:
            _set_failing(error, span)
            undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
            span.end()
            raise

        if info.is_awaitable(result):
            return _await_field_result(result, span, self.context)

        undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, self.context)
        span.end()
        return result


async def _await_field_result(result: Awaitable[Any], span: trace.Span, context: LifecycleHookContext) -> Any:
    try:
        return await result

    except BaseException as error:
        _set_failing(error, span)
        raise

    finally:
        undine_settings.OPENTELEMETRY_SPAN_CALLBACK(span, context)
        span.end()


def _set_failing(error: BaseException, span: trace.Span) -> None:
    span.record_exception(error)
    span.set_status(trace.Status(trace.StatusCode.ERROR, _get_status_description(error)))


def _set_failing_if_error_result(span: trace.Span, context: LifecycleHookContext) -> None:
    result = context.result
    if not isinstance(result, ExecutionResult) or not result.errors:
        return

    description: list[str] = []
    for error in result.errors:
        span.record_exception(error)
        description.append(_get_status_description(error))

    span.set_status(trace.Status(trace.StatusCode.ERROR, "\n\n".join(description)))


def _get_field_path(info: GQLInfo) -> str:
    return f"{info.parent_type}.{info.field_name}"


def _get_response_path(info: GQLInfo) -> str:
    return ".".join(str(part) for part in info.path.as_list())


def _get_operation_span_name(operation_type: OperationType, operation_name: str | None) -> str:
    if operation_name is None:
        return operation_type.value
    return f"{operation_type.value} {operation_name}"


def _get_status_description(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


# Setting defaults


def no_op_span_callback(span: trace.Span, context: LifecycleHookContext) -> None:
    """Add no attributes to the spans."""


def redacted_variables(context: LifecycleHookContext) -> dict[str, Any]:
    """Attach the name of each variable to traces, with its value redacted."""
    return redact_variables(context.variables)


def no_traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
    """Set as the `OPENTELEMETRY_VARIABLES_CALLBACK` setting to attach no variables at all to traces."""
    return {}


def skip_introspection_queries(context: LifecycleHookContext) -> bool:
    """
    Record an introspection query without its field spans.

    An introspection query resolves a field for every type and field in the schema, so a span
    for each one buries the operations that say something about the service.
    """
    return context.operation_name == "IntrospectionQuery"


def never_skip_field_spans(context: LifecycleHookContext) -> bool:
    """Record a field span for every operation, however many fields it resolves."""
    return False
