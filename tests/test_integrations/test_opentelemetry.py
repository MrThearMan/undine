from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from tests.helpers import MockRequest, exact
from tests.test_integrations.helpers import (
    ExecutionStepBoomHook,
    ParseStepBoomHook,
    ValidationStepBoomHook,
    build_telemetry_schema,
    collect_spans,
    get_exception_events,
    get_parent_span_ids,
    get_span,
    get_span_attributes,
    run_telemetry_query_async,
    run_telemetry_query_sync,
    run_telemetry_subscription,
)
from undine.dataclasses import GraphQLHttpParams
from undine.execution import _get_middleware_manager  # noqa: PLC2701
from undine.hooks import LifecycleHookContext
from undine.integrations import opentelemetry as opentelemetry_module
from undine.integrations.opentelemetry import (
    OpenTelemetryFullHook,
    OpenTelemetryHook,
    never_skip_field_spans,
    no_traced_variables,
)
from undine.utils.graphql.utils import never_mask_error


def test_opentelemetry__records_spans_for_the_operation_steps(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query Greet",
    ]

    assert get_span_attributes(spans, "query Greet") == {
        "graphql.operation.name": "Greet",
        "graphql.operation.type": "query",
        "graphql.document": "query Greet {\n  greeting\n}",
    }

    operation_span = get_span(spans, "query Greet")
    assert operation_span.status.status_code == StatusCode.UNSET

    for step_name in ("graphql.parse", "graphql.validate", "graphql.execute"):
        step_span = get_span(spans, step_name)
        assert step_span.parent is not None
        assert step_span.parent.span_id == operation_span.context.span_id
        assert step_span.attributes == {}


def test_opentelemetry__unnamed_operation_is_named_by_its_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ greeting }")

    assert result.data == {"greeting": "hello"}
    assert get_span_attributes(spans, "query") == {
        "graphql.operation.type": "query",
        "graphql.document": "{\n  greeting\n}",
    }


def test_opentelemetry__operation_name_from_request_is_recorded(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    document = "query Greet { greeting } query Shout { greeting }"

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="Shout")

    assert result.data == {"greeting": "hello"}
    assert get_span_attributes(spans, "query Shout") == {
        "graphql.operation.name": "Shout",
        "graphql.operation.type": "query",
        "graphql.document": "query Greet {\n  greeting\n}\n\nquery Shout {\n  greeting\n}",
    }


def test_opentelemetry__mutation_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("mutation Shout { shout }")

    assert result.data == {"shout": "HELLO"}
    assert get_span_attributes(spans, "mutation Shout")["graphql.operation.type"] == "mutation"

    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "mutation Shout",
    ]


async def test_opentelemetry__subscription_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "graphql.execute",
        "graphql.execute",
        "subscription Countdown",
    ]

    operation_span = get_span(spans, "subscription Countdown")
    assert operation_span.attributes is not None
    assert operation_span.attributes["graphql.operation.type"] == "subscription"
    assert operation_span.status.status_code == StatusCode.UNSET


async def test_opentelemetry__subscription_results_stay_in_the_operation_trace(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    operation_span = get_span(spans, "subscription Countdown")
    operation_span_id = operation_span.context.span_id

    # Each result is executed once the operation span is no longer the current span, so a step span
    # that takes its parent from the current context becomes the root span of a trace of its own.
    assert {span.context.trace_id for span in spans} == {operation_span.context.trace_id}
    assert get_parent_span_ids(spans) == [
        operation_span_id,
        operation_span_id,
        operation_span_id,
        operation_span_id,
        operation_span_id,
        None,
    ]


async def test_opentelemetry__subscription_operation_span_covers_the_event_stream(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    operation_span = get_span(spans, "subscription Countdown")
    execution_spans = [span for span in spans if span.name == "graphql.execute"]
    assert len(execution_spans) == 3

    # The operation is not over when the event stream is created, but when the event stream ends.
    assert operation_span.start_time < min(span.start_time for span in execution_spans)  # type: ignore[operator,type-var]
    assert operation_span.end_time > max(span.end_time for span in execution_spans)  # type: ignore[operator,type-var]


def test_opentelemetry__failing_operation_marks_the_span(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]

    operation_span = get_span(spans, "query")
    assert operation_span.status.status_code == StatusCode.ERROR
    assert operation_span.status.description == "GraphQLError: kaboom"
    assert get_exception_events(operation_span) == [
        {"name": "exception", "type": "graphql.error.graphql_error.GraphQLError", "message": "kaboom"},
    ]


def test_opentelemetry__syntax_error_leaves_the_document_attributes_unset(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ greeting")

    assert result.errors is not None

    operation_span = get_span(spans, "graphql.operation")
    assert operation_span.attributes == {}
    assert operation_span.status.status_code == StatusCode.ERROR


def test_opentelemetry__document_without_an_operation_leaves_the_document_attributes_unset(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("fragment Greet on Query { greeting }")

    assert result.errors is not None

    operation_span = get_span(spans, "graphql.operation")
    assert operation_span.attributes == {}


async def test_opentelemetry__async_execution_records_the_same_spans(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = await run_telemetry_query_async("query Greet { asyncGreeting }")

    assert result.data == {"asyncGreeting": "async hello"}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query Greet",
    ]

    assert get_span_attributes(spans, "query Greet") == {
        "graphql.operation.name": "Greet",
        "graphql.operation.type": "query",
        "graphql.document": "query Greet {\n  asyncGreeting\n}",
    }

    operation_span = get_span(spans, "query Greet")
    operation_span_id = operation_span.context.span_id
    assert get_parent_span_ids(spans) == [
        operation_span_id,
        operation_span_id,
        operation_span_id,
        None,
    ]


async def test_opentelemetry__async_failing_operation_marks_the_span(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = await run_telemetry_query_async("{ asyncBoom }")

    assert [error.message for error in result.errors or []] == ["async kaboom"]

    operation_span = get_span(spans, "query")
    assert operation_span.status.status_code == StatusCode.ERROR
    assert operation_span.status.description == "GraphQLError: async kaboom"


# Unexpected failures


def test_opentelemetry__unexpected_parse_failure_still_marks_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook, ParseStepBoomHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_span(spans, "query Greet")
    assert operation_span.status.status_code == StatusCode.ERROR
    assert get_exception_events(operation_span) == [
        {"name": "exception", "type": "tests.test_integrations.helpers.StepBoomError", "message": ""},
    ]

    parse_span = get_span(spans, "graphql.parse")
    assert get_exception_events(parse_span) == [
        {"name": "exception", "type": "tests.test_integrations.helpers.StepBoomError", "message": ""},
    ]


def test_opentelemetry__unexpected_validation_failure_still_marks_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook, ValidationStepBoomHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_span(spans, "query Greet")
    assert operation_span.status.status_code == StatusCode.ERROR

    validation_span = get_span(spans, "graphql.validate")
    assert get_exception_events(validation_span) == [
        {"name": "exception", "type": "tests.test_integrations.helpers.StepBoomError", "message": ""},
    ]


def test_opentelemetry__unexpected_execution_failure_still_marks_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook, ExecutionStepBoomHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_span(spans, "query Greet")
    assert operation_span.status.status_code == StatusCode.ERROR

    execution_span = get_span(spans, "graphql.execute")
    assert get_exception_events(execution_span) == [
        {"name": "exception", "type": "tests.test_integrations.helpers.StepBoomError", "message": ""},
    ]


# Inline literals and variables


def test_opentelemetry__inline_literals_are_redacted(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    document = 'query Echo { echo(value: "alice@example.com") }'

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document)

    assert result.data == {"echo": "alice@example.com"}

    attributes = get_span_attributes(spans, "query Echo")
    assert attributes["graphql.document"] == 'query Echo {\n  echo(value: "***")\n}'
    assert "alice@example.com" not in str(attributes)


def test_opentelemetry__variable_values_are_not_recorded_by_default(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    attributes = get_span_attributes(spans, "query Echo")
    assert attributes == {
        "graphql.operation.name": "Echo",
        "graphql.operation.type": "query",
        "graphql.document": "query Echo($value: String!) {\n  echo(value: $value)\n}",
        "graphql.variables": '{"value": "***"}',
    }


def test_opentelemetry__variable_values_are_recorded_when_the_callback_opts_in(undine_settings) -> None:
    def traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
        return context.variables

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]
    undine_settings.OPENTELEMETRY_VARIABLES_CALLBACK = traced_variables

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    attributes = get_span_attributes(spans, "query Echo")
    assert attributes["graphql.variables"] == '{"value": "alice@example.com"}'


def test_opentelemetry__variables_are_left_out_when_the_callback_opts_out(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]
    undine_settings.OPENTELEMETRY_VARIABLES_CALLBACK = no_traced_variables

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    attributes = get_span_attributes(spans, "query Echo")
    assert "graphql.variables" not in attributes


# Extension point


def test_opentelemetry__span_callback_can_add_attributes_to_the_operation_span(undine_settings) -> None:
    def add_custom_attribute(span: Span, context: LifecycleHookContext) -> None:
        span.set_attribute("graphql.custom", "value")

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]
    undine_settings.OPENTELEMETRY_SPAN_CALLBACK = add_custom_attribute

    with collect_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}
    assert get_span_attributes(spans, "query Greet")["graphql.custom"] == "value"


def test_opentelemetry__span_callback_sees_the_execution_result(undine_settings) -> None:
    """The callback fires after execution, not right after parsing, so it can react to errors too."""

    def tag_with_error_count(span: Span, context: LifecycleHookContext) -> None:
        result = context.result
        error_count = len(result.errors or []) if result is not None else 0  # type: ignore[union-attr]
        span.set_attribute("graphql.error.count", error_count)

    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]
    undine_settings.OPENTELEMETRY_SPAN_CALLBACK = tag_with_error_count

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]
    assert get_span_attributes(spans, "query")["graphql.error.count"] == 1


# Field spans


def test_opentelemetry__no_field_spans_without_the_field_hook(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query",
    ]


def test_opentelemetry__field_hook_records_a_span_per_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "Query.people",
        "PersonType.name",
        "PersonType.name",
        "graphql.execute",
        "query",
    ]

    assert get_span_attributes(spans, "Query.people") == {
        "graphql.field.name": "people",
        "graphql.field.path": "Query.people",
        "graphql.field.parent.type": "Query",
        "graphql.path": "people",
    }

    name_spans = [span for span in spans if span.name == "PersonType.name"]
    assert len(name_spans) == 2
    assert {span.attributes["graphql.path"] for span in name_spans if span.attributes} == {
        "people.0.name",
        "people.1.name",
    }


def test_opentelemetry__field_spans_are_skipped_for_an_introspection_query(undine_settings) -> None:
    """An introspection query resolves a field per type and field in the schema."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    document = "query IntrospectionQuery { people { name } }"

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query IntrospectionQuery",
    ]


def test_opentelemetry__field_spans_of_an_introspection_query_when_the_predicate_opts_in(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]
    undine_settings.OPENTELEMETRY_SKIP_FIELD_SPANS_PREDICATE = never_skip_field_spans

    document = "query IntrospectionQuery { people { name } }"

    with collect_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "Query.people",
        "PersonType.name",
        "PersonType.name",
        "graphql.execute",
        "query IntrospectionQuery",
    ]


def test_opentelemetry__field_hook_marks_a_failing_field(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]

    field_span = get_span(spans, "Query.boom")
    assert field_span.status.status_code == StatusCode.ERROR
    assert get_exception_events(field_span) == [
        {"name": "exception", "type": "graphql.error.graphql_error.GraphQLError", "message": "kaboom"},
    ]


async def test_opentelemetry__field_hook_records_async_resolvers(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    with collect_spans() as spans:
        result = await run_telemetry_query_async("{ asyncGreeting }")

    assert result.data == {"asyncGreeting": "async hello"}

    assert [span.name for span in spans] == [
        "graphql.parse",
        "graphql.validate",
        "Query.asyncGreeting",
        "graphql.execute",
        "query",
    ]

    field_span = get_span(spans, "Query.asyncGreeting")

    end_time = field_span.end_time
    start_time = field_span.start_time

    assert end_time is not None
    assert start_time is not None

    assert field_span.status.status_code == StatusCode.UNSET
    assert end_time > start_time

    operation_span = get_span(spans, "query")
    operation_span_id = operation_span.context.span_id

    execution_span = get_span(spans, "graphql.execute")
    execution_span_id = execution_span.context.span_id

    assert get_parent_span_ids(spans) == [
        operation_span_id,
        operation_span_id,
        execution_span_id,
        operation_span_id,
        None,
    ]


async def test_opentelemetry__field_hook_marks_a_failing_async_field(undine_settings) -> None:
    undine_settings.ERROR_MASKING_PREDICATE = never_mask_error
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    with collect_spans() as spans:
        result = await run_telemetry_query_async("{ asyncBoom }")

    assert [error.message for error in result.errors or []] == ["async kaboom"]

    field_span = get_span(spans, "Query.asyncBoom")
    assert field_span.status.status_code == StatusCode.ERROR
    assert field_span.status.description == "GraphQLError: async kaboom"
    assert get_exception_events(field_span) == [
        {"name": "exception", "type": "graphql.error.graphql_error.GraphQLError", "message": "async kaboom"},
    ]


# Cost when not used


def test_opentelemetry__operation_hook_adds_no_field_middleware(undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    hooks = [hook for hook in context.lifecycle_hooks if isinstance(hook, OpenTelemetryHook)]
    assert _get_middleware_manager(hooks) is None


def test_opentelemetry__field_hook_adds_field_middleware(undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    assert _get_middleware_manager(context.lifecycle_hooks) is not None


# Optional dependency


def test_opentelemetry__hooks_work_without_a_configured_sdk(undine_settings, monkeypatch) -> None:
    """Without the OpenTelemetry SDK, the API hands out a no-op tracer. Operations must still run."""
    monkeypatch.setattr(trace, "get_tracer", lambda *args: trace.NoOpTracer())

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [OpenTelemetryFullHook]

    with collect_spans() as spans:
        result = run_telemetry_query_sync("{ greeting }")

    assert result.data == {"greeting": "hello"}
    assert spans == []


def test_opentelemetry__module_does_not_require_the_sdk(monkeypatch) -> None:
    """Undine instruments against `opentelemetry-api`, so importing the SDK must not be required."""
    monkeypatch.setitem(sys.modules, "opentelemetry.sdk", None)

    importlib.reload(opentelemetry_module)

    assert issubclass(opentelemetry_module.OpenTelemetryFullHook, opentelemetry_module.OpenTelemetryHook)


def test_opentelemetry__missing_dependency_gives_an_actionable_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", None)

    message = (
        "The OpenTelemetry lifecycle hooks require the 'opentelemetry-api' package. "
        "Install it with: pip install 'undine[opentelemetry]'"
    )

    try:
        with pytest.raises(ImportError, match=exact(message)):
            importlib.reload(opentelemetry_module)
    finally:
        monkeypatch.undo()
        importlib.reload(opentelemetry_module)
