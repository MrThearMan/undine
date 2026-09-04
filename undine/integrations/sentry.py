from __future__ import annotations

import dataclasses
import json
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Self

from graphql import ExecutionResult, GraphQLError, OperationType

from undine.hooks import HookPriority, LifecycleHook
from undine.settings import undine_settings
from undine.utils.graphql.redaction import redact_document, redact_variables
from undine.utils.graphql.utils import get_operation_definition, get_unmasked_error
from undine.utils.logging import logger

try:
    import sentry_sdk
    from sentry_sdk import traces as sentry_traces
    from sentry_sdk.consts import OP
    from sentry_sdk.integrations.logging import ignore_logger
    from sentry_sdk.scope import should_send_default_pii
    from sentry_sdk.traces import SegmentNameSource
    from sentry_sdk.tracing import TransactionSource
    from sentry_sdk.tracing_utils import has_span_streaming_enabled
    from sentry_sdk.utils import capture_internal_exceptions, event_from_exception

except ImportError as import_error:  # pragma: no cover
    msg = "The Sentry lifecycle hooks require the 'sentry-sdk' package. Install it with: pip install 'undine[sentry]'"
    raise ImportError(msg) from import_error


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Generator

    from graphql import GraphQLFieldResolver
    from sentry_sdk._types import Event, Hint
    from sentry_sdk.traces import StreamedSpan
    from sentry_sdk.tracing import Span

    from undine.hooks import LifecycleHookContext
    from undine.typing import GQLInfo


__all__ = [
    "RecordedSpan",
    "SentryFullHook",
    "SentryHook",
]


SENTRY_ORIGIN: str = "auto.graphql.undine"
SENTRY_MECHANISM_TYPE: str = "undine"
SENTRY_BREADCRUMB_CATEGORY: str = "graphql.operation"

OPERATION_SPAN_NAME: str = "graphql.operation"
PARSE_SPAN_NAME: str = OP.GRAPHQL_PARSE
VALIDATION_SPAN_NAME: str = OP.GRAPHQL_VALIDATE
EXECUTION_SPAN_NAME: str = OP.GRAPHQL_EXECUTE

OPERATION_NAME_DATA: str = "graphql.operation.name"
OPERATION_TYPE_DATA: str = "graphql.operation.type"
DOCUMENT_DATA: str = "graphql.document"
VARIABLES_DATA: str = "graphql.variables"

OP_ATTRIBUTE: str = "sentry.op"
ORIGIN_ATTRIBUTE: str = "sentry.origin"
SEGMENT_NAME_SOURCE_ATTRIBUTE: str = "sentry.segment.name.source"

PATH_DATA: str = "graphql.path"
FIELD_NAME_DATA: str = "graphql.field.name"
FIELD_PATH_DATA: str = "graphql.field.path"
FIELD_PARENT_TYPE_DATA: str = "graphql.field.parent.type"


OPERATION_TYPE_TO_OP: dict[OperationType, str] = {
    OperationType.QUERY: OP.GRAPHQL_QUERY,
    OperationType.MUTATION: OP.GRAPHQL_MUTATION,
    OperationType.SUBSCRIPTION: OP.GRAPHQL_SUBSCRIPTION,
}

# Undine reports the failures it handles as Sentry events itself, with the GraphQL context attached.
# Without this, Sentry's logging integration would raise a second, poorer issue for the same failure.
ignore_logger(logger.name)


class RecordedSpan(Protocol):
    """
    One span recorded for a GraphQL operation.

    Sentry has two span APIs, and a client can only use the one its `trace_lifecycle`
    option selects. The hooks record through this interface so that they don't have to
    know which one is in use. The `SENTRY_SPAN_CALLBACK` setting receives it as well.
    """

    @property
    def sentry_span(self) -> Span | StreamedSpan:
        """The Sentry span itself, for the things the two span APIs don't share."""

    def start_child(self, *, op: str, name: str) -> RecordedSpan: ...

    def set_data(self, key: str, value: Any) -> None: ...

    def describe(self, *, op: str, name: str) -> None:
        """Set the operation and the name of the span, once the operation is known."""

    def name_trace(self, *, operation_name: str, op: str) -> None:
        """Name the whole trace after the operation, and give it the operation's type."""

    def finish(self) -> None: ...


class SentryHook(LifecycleHook):
    """
    Lifecycle hook that records a Sentry span for each GraphQL operation, with a child span for the
    parsing, validation and execution steps, names the transaction after the GraphQL operation,
    and reports failing operations as Sentry issues.
    """

    priority: ClassVar[int] = HookPriority.TRACING

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.operation_span: RecordedSpan | None = None
        self.parse_span: RecordedSpan | None = None
        self.validation_span: RecordedSpan | None = None
        self.execution_span: RecordedSpan | None = None

        self.operation_name: str | None = None

    def on_operation(self) -> Generator[None, None, None]:
        isolation_scope = sentry_sdk.get_isolation_scope()
        isolation_scope.add_event_processor(_make_request_event_processor(self))

        span = _start_operation_span()
        self.operation_span = span

        if self.context.operation_name is not None:
            span.set_data(OPERATION_NAME_DATA, self.context.operation_name)
            self.operation_name = self.context.operation_name

        variables = undine_settings.SENTRY_VARIABLES_CALLBACK(self.context)
        if variables:
            span.set_data(VARIABLES_DATA, json.dumps(variables, default=str))

        try:
            yield
        finally:
            _capture_result_errors(self.context)
            undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_parse(self) -> Generator[None, None, None]:
        parent: RecordedSpan = self.operation_span  # type: ignore[assignment]
        span = parent.start_child(op=OP.GRAPHQL_PARSE, name=PARSE_SPAN_NAME)
        self.parse_span = span

        try:
            yield
        finally:
            # The document is only available once parsing is complete.
            self._describe_operation()
            undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_validation(self) -> Generator[None, None, None]:
        parent: RecordedSpan = self.operation_span  # type: ignore[assignment]
        span = parent.start_child(op=OP.GRAPHQL_VALIDATE, name=VALIDATION_SPAN_NAME)
        self.validation_span = span

        try:
            yield
        finally:
            undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
            span.finish()

    def on_execution(self) -> Generator[None, None, None]:
        parent: RecordedSpan = self.operation_span  # type: ignore[assignment]
        span = parent.start_child(op=OP.GRAPHQL_EXECUTE, name=EXECUTION_SPAN_NAME)
        self.execution_span = span

        try:
            yield
        finally:
            undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
            span.finish()

    def _describe_operation(self) -> None:
        """Describe the operation span and name the transaction, now that the document is parsed."""
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
        op = OPERATION_TYPE_TO_OP[operation_type]

        self.operation_name = operation_name
        span: RecordedSpan = self.operation_span  # type: ignore[assignment]

        span.describe(op=op, name=_get_operation_span_name(operation_type, operation_name))

        span.set_data(OPERATION_TYPE_DATA, operation_type.value)
        span.set_data(DOCUMENT_DATA, redact_document(document))
        if operation_name is not None:
            span.set_data(OPERATION_NAME_DATA, operation_name)

        sentry_sdk.add_breadcrumb(
            category=SENTRY_BREADCRUMB_CATEGORY,
            data={"operation_name": operation_name, "operation_type": operation_type.value},
        )

        if operation_name is None:
            return

        span.name_trace(operation_name=operation_name, op=op)


class SentryFullHook(SentryHook):
    """Same as `SentryHook`, but also records a span for each resolved field."""

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.skip_field_spans: bool = False

    def on_execution(self) -> Generator[None, None, None]:
        # Called just before resolving starts since self.context can change during parsing and validation phases.
        self.skip_field_spans = undine_settings.SENTRY_SKIP_FIELD_SPANS_PREDICATE(self.context)
        yield from super().on_execution()

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:  # type: ignore[override]
        if self.skip_field_spans:
            return resolver(root, info, **kwargs)

        field_path = _get_field_path(info)

        parent: RecordedSpan = self.execution_span  # type: ignore[assignment]
        span = parent.start_child(op=OP.GRAPHQL_RESOLVE, name=field_path)

        span.set_data(FIELD_NAME_DATA, info.field_name)
        span.set_data(FIELD_PARENT_TYPE_DATA, info.parent_type.name)
        span.set_data(FIELD_PATH_DATA, field_path)
        span.set_data(PATH_DATA, _get_response_path(info))

        try:
            result = resolver(root, info, **kwargs)
        except BaseException:
            undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
            span.finish()
            raise

        if info.is_awaitable(result):
            return _await_field_result(result, span, self.context)

        undine_settings.SENTRY_SPAN_CALLBACK(span, self.context)
        span.finish()
        return result


async def _await_field_result(result: Awaitable[Any], span: RecordedSpan, context: LifecycleHookContext) -> Any:
    try:
        return await result
    finally:
        undine_settings.SENTRY_SPAN_CALLBACK(span, context)
        span.finish()


def _start_operation_span() -> RecordedSpan:
    client = sentry_sdk.get_client()
    if has_span_streaming_enabled(client.options):
        return _StreamedRecordedSpan.start_operation()
    return _TransactionRecordedSpan.start_operation()


@dataclasses.dataclass(kw_only=True, slots=True)
class _TransactionRecordedSpan:
    """Records a span with Sentry's transaction API."""

    sentry_span: Span

    @classmethod
    def start_operation(cls) -> Self:
        # Sentry only sends spans that belong to a transaction. Its Django integration starts one for
        # an HTTP request, but not for the WebSocket and SSE connections that subscriptions run on,
        # so the operation has to become a transaction of its own there.
        active_span = sentry_sdk.get_current_scope().span or sentry_sdk.get_isolation_scope().span

        if active_span is None:
            transaction = sentry_sdk.start_transaction(
                op=OP.GRAPHQL_QUERY,
                name=OPERATION_SPAN_NAME,
                origin=SENTRY_ORIGIN,
                source=TransactionSource.COMPONENT,
            )
            return cls(sentry_span=transaction)

        span = sentry_sdk.start_span(op=OP.GRAPHQL_QUERY, name=OPERATION_SPAN_NAME, origin=SENTRY_ORIGIN)
        return cls(sentry_span=span)

    def start_child(self, *, op: str, name: str) -> Self:
        child = self.sentry_span.start_child(op=op, name=name, origin=SENTRY_ORIGIN)
        return type(self)(sentry_span=child)

    def set_data(self, key: str, value: Any) -> None:
        self.sentry_span.set_data(key, value)

    def describe(self, *, op: str, name: str) -> None:
        self.sentry_span.op = op
        self.sentry_span.description = name

    def name_trace(self, *, operation_name: str, op: str) -> None:
        # Without this, every GraphQL request collapses into a single transaction for the HTTP route.
        # The scope carries the name onto the issues, and the transaction carries it onto the trace.
        sentry_sdk.get_current_scope().set_transaction_name(operation_name, source=TransactionSource.COMPONENT)

        transaction = self.sentry_span.containing_transaction
        if transaction is not None:
            transaction.name = operation_name
            transaction.source = TransactionSource.COMPONENT
            transaction.op = op

    def finish(self) -> None:
        self.sentry_span.finish()


@dataclasses.dataclass(kw_only=True, slots=True)
class _StreamedRecordedSpan:
    """Records a span with Sentry's span streaming API, which streams each span on its own."""

    sentry_span: StreamedSpan
    owns_segment: bool

    @classmethod
    def start_operation(cls) -> Self:
        # A span with no parent becomes the segment, which is what the whole trace is named after.
        owns_segment = sentry_traces.get_current_span() is None

        span = sentry_traces.start_span(
            name=OPERATION_SPAN_NAME,
            attributes={OP_ATTRIBUTE: OP.GRAPHQL_QUERY, ORIGIN_ATTRIBUTE: SENTRY_ORIGIN},
            active=False,
        )
        return cls(sentry_span=span, owns_segment=owns_segment)

    def start_child(self, *, op: str, name: str) -> Self:
        # The spans are not activated on the scope, since an operation can outlive the task that
        # started it, so each child names its parent instead.
        child = sentry_traces.start_span(
            name=name,
            attributes={OP_ATTRIBUTE: op, ORIGIN_ATTRIBUTE: SENTRY_ORIGIN},
            parent_span=self.sentry_span,
            active=False,
        )
        return type(self)(sentry_span=child, owns_segment=False)

    def set_data(self, key: str, value: Any) -> None:
        self.sentry_span.set_attribute(key, value)

    def describe(self, *, op: str, name: str) -> None:
        self.sentry_span.set_attribute(OP_ATTRIBUTE, op)
        self.sentry_span.name = name

    def name_trace(self, *, operation_name: str, op: str) -> None:
        if not self.owns_segment:
            sentry_sdk.get_current_scope().set_transaction_name(operation_name, source=SegmentNameSource.COMPONENT)
            return

        # The operation span is the segment, so its name is the name of the whole trace.
        self.sentry_span.name = operation_name
        self.sentry_span.set_attribute(SEGMENT_NAME_SOURCE_ATTRIBUTE, SegmentNameSource.COMPONENT.value)
        self.sentry_span.set_attribute(OP_ATTRIBUTE, op)

    def finish(self) -> None:
        self.sentry_span.end()


def _capture_result_errors(context: LifecycleHookContext) -> None:
    result = context.result
    if not isinstance(result, ExecutionResult) or not result.errors:
        return

    client_options = sentry_sdk.get_client().options

    for error in result.errors:
        if not undine_settings.SENTRY_REPORT_ERROR_PREDICATE(error):
            continue

        event, hint = event_from_exception(
            get_unmasked_error(error),
            client_options=client_options,
            mechanism={"type": SENTRY_MECHANISM_TYPE, "handled": False},
        )
        sentry_sdk.capture_event(event, hint=hint)


def _make_request_event_processor(hook: SentryHook) -> Callable[[Event, Hint], Event]:
    def event_processor(event: Event, hint: Hint) -> Event:
        # An event processor runs while an issue is being reported, so a failure here would replace
        # the issue with one about Undine. Sentry swallows and reports what happens in this block.
        with capture_internal_exceptions():
            request_data: dict[str, Any] = event.setdefault("request", {})
            # Sentry renders the request as a GraphQL operation instead of a raw body with this.
            request_data["api_target"] = "graphql"

            data = _get_graphql_request_data(hook)
            if data:
                request_data["data"] = data

        return event

    return event_processor


def _get_graphql_request_data(hook: SentryHook) -> dict[str, Any]:
    """The operation as it is shown on an issue, which is a different payload from the spans."""
    data: dict[str, Any] = {}

    if should_send_default_pii():
        data["query"] = hook.context.source
        if hook.context.variables:
            data["variables"] = hook.context.variables

    else:
        # Redacted, the operation still says what the client asked for, without the client's data.
        # A document is only available once parsing is complete, so a parse failure has none.
        if hook.context.document is not None:
            data["query"] = redact_document(hook.context.document)
        if hook.context.variables:
            data["variables"] = redact_variables(hook.context.variables)

    if hook.operation_name is not None:
        data["operationName"] = hook.operation_name

    return data


def _get_field_path(info: GQLInfo) -> str:
    return f"{info.parent_type}.{info.field_name}"


def _get_response_path(info: GQLInfo) -> str:
    return ".".join(str(part) for part in info.path.as_list())


def _get_operation_span_name(operation_type: OperationType, operation_name: str | None) -> str:
    if operation_name is None:
        return operation_type.value
    return f"{operation_type.value} {operation_name}"


# Setting defaults


def report_server_errors(error: GraphQLError) -> bool:
    """
    Report only errors that indicate a fault in the server.

    Client mistakes, like a validation error or a denied permission, are not incidents,
    so reporting them would only add noise to Sentry.
    """
    status_code = error.extensions.get("status_code", HTTPStatus.INTERNAL_SERVER_ERROR)  # type: ignore[union-attr]
    return status_code >= HTTPStatus.INTERNAL_SERVER_ERROR


def report_all_errors(error: GraphQLError) -> bool:
    """Set as the `SENTRY_REPORT_ERROR_PREDICATE` setting to report every GraphQL error to Sentry."""
    return True


def no_op_span_callback(span: RecordedSpan, context: LifecycleHookContext) -> None:
    """Add no attributes to the spans."""


def redacted_variables(context: LifecycleHookContext) -> dict[str, Any]:
    """Attach the name of each variable to traces, with its value redacted."""
    return redact_variables(context.variables)


def no_traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
    """Set as the `SENTRY_VARIABLES_CALLBACK` setting to attach no variables at all to traces."""
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
