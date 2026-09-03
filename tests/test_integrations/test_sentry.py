from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.traces import StreamedSpan

from tests.helpers import MockRequest, exact
from tests.test_integrations.helpers import (
    SENTRY_HTTP_TRANSACTION_NAME,
    ExecutionStepBoomHook,
    build_telemetry_schema,
    collect_sentry_payloads,
    collect_sentry_payloads_with_span_streaming,
    collect_sentry_payloads_with_span_streaming_without_a_segment,
    collect_sentry_payloads_without_a_transaction,
    collect_sentry_payloads_without_tracing,
    get_sentry_span,
    get_sentry_span_data,
    get_sentry_span_names,
    get_sentry_streamed_span,
    get_sentry_streamed_span_attributes,
    get_sentry_streamed_span_names,
    get_sentry_transaction,
    run_telemetry_query_async,
    run_telemetry_query_sync,
    run_telemetry_subscription,
)
from undine.dataclasses import GraphQLHttpParams
from undine.execution import _get_middleware_manager  # noqa: PLC2701
from undine.hooks import LifecycleHookContext
from undine.integrations import sentry as sentry_module
from undine.integrations.sentry import (
    RecordedSpan,
    SentryFullHook,
    SentryHook,
    never_skip_field_spans,
    no_traced_variables,
    report_all_errors,
)


def test_sentry__records_spans_for_the_operation_steps(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query Greet",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
    ]

    operation_span = get_sentry_span(transaction, "query Greet")
    assert operation_span["op"] == "graphql.query"
    assert operation_span["origin"] == "auto.graphql.undine"
    assert get_sentry_span_data(operation_span) == {
        "graphql.document": "query Greet {\n  greeting\n}",
        "graphql.operation.name": "Greet",
        "graphql.operation.type": "query",
    }

    for step_name in ["graphql.parse", "graphql.validate"]:
        step_span = get_sentry_span(transaction, step_name)
        assert step_span["op"] == step_name
        assert step_span["parent_span_id"] == operation_span["span_id"]
        assert get_sentry_span_data(step_span) == {}

    execution_span = get_sentry_span(transaction, "graphql.execute")
    assert execution_span["op"] == "graphql.execute"
    assert execution_span["parent_span_id"] == operation_span["span_id"]


def test_sentry__names_the_transaction_after_the_operation(undine_settings) -> None:
    """Without this, every GraphQL request collapses into one transaction for the HTTP route."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Greet"
    assert transaction["transaction_info"] == {"source": "component"}
    assert transaction["contexts"]["trace"]["op"] == "graphql.query"


def test_sentry__mutation_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("mutation Shout { shout }")

    assert result.data == {"shout": "HELLO"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Shout"
    assert transaction["contexts"]["trace"]["op"] == "graphql.mutation"
    assert get_sentry_span(transaction, "mutation Shout")["op"] == "graphql.mutation"


async def test_sentry__subscription_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Countdown"
    assert transaction["contexts"]["trace"]["op"] == "graphql.subscription"
    assert get_sentry_span(transaction, "subscription Countdown")["op"] == "graphql.subscription"


async def test_sentry__subscription_starts_its_own_transaction(undine_settings) -> None:
    """A subscription arrives on a connection that Sentry doesn't start a transaction for."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_without_a_transaction() as payloads:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Countdown"
    assert transaction["transaction_info"] == {"source": "component"}
    assert get_sentry_span_names(transaction) == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "graphql.execute",
        "graphql.execute",
    ]

    # The operation is the transaction itself, so what other connections put on the operation span
    # is in the trace context instead.
    trace_context = transaction["contexts"]["trace"]
    assert trace_context["op"] == "graphql.subscription"
    assert trace_context["origin"] == "auto.graphql.undine"
    assert trace_context["description"] == "subscription Countdown"
    assert get_sentry_span_data(trace_context) == {
        "graphql.document": "subscription Countdown {\n  countdown\n}",
        "graphql.operation.name": "Countdown",
        "graphql.operation.type": "subscription",
    }


def test_sentry__operation_type_survives_a_leading_comment(undine_settings) -> None:
    """A naive `query.strip().startswith("mutation")` check is fooled by a leading comment."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("# a comment\nmutation Shout { shout }")

    assert result.data == {"shout": "HELLO"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["contexts"]["trace"]["op"] == "graphql.mutation"
    assert get_sentry_span_data(get_sentry_span(transaction, "mutation Shout"))["graphql.operation.type"] == "mutation"


def test_sentry__operation_type_of_non_first_operation_in_a_multi_operation_document(undine_settings) -> None:
    """A naive string check on the whole document would misdetect the type of the executed operation."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    document = "query First { greeting } mutation Second { shout }"

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, operation_name="Second")

    assert result.data == {"shout": "HELLO"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Second"
    assert transaction["contexts"]["trace"]["op"] == "graphql.mutation"
    assert get_sentry_span_data(get_sentry_span(transaction, "mutation Second"))["graphql.operation.type"] == "mutation"


def test_sentry__anonymous_operation_keeps_the_route_transaction_name(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("{ greeting }")

    assert result.data == {"greeting": "hello"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == SENTRY_HTTP_TRANSACTION_NAME
    assert get_sentry_span_data(get_sentry_span(transaction, "query")) == {
        "graphql.document": "{\n  greeting\n}",
        "graphql.operation.type": "query",
    }


def test_sentry__syntax_error_leaves_the_operation_span_generic(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("{ greeting")

    assert result.errors is not None

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "graphql.operation")) == {}


def test_sentry__document_without_an_operation_leaves_the_operation_span_generic(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("fragment Greet on Query { greeting }")

    assert result.errors is not None

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "graphql.operation")) == {}


async def test_sentry__async_execution_records_the_same_spans(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = await run_telemetry_query_async("query Greet { asyncGreeting }")

    assert result.data == {"asyncGreeting": "async hello"}

    transaction = get_sentry_transaction(payloads)
    assert transaction["transaction"] == "Greet"
    assert get_sentry_span_names(transaction) == [
        "query Greet",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
    ]

    operation_span = get_sentry_span(transaction, "query Greet")
    for step_name in ["graphql.parse", "graphql.validate", "graphql.execute"]:
        assert get_sentry_span(transaction, step_name)["parent_span_id"] == operation_span["span_id"]


def test_sentry__unexpected_step_failure_still_finishes_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook, ExecutionStepBoomHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query Greet",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
    ]


# Error capture


def test_sentry__failing_resolver_is_reported_as_an_issue(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Crash { crash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    assert len(payloads.events) == 1
    event = payloads.events[0]

    assert event["transaction"] == "Crash"
    assert event["request"] == {
        "api_target": "graphql",
        "data": {"query": "query Crash {\n  crash\n}", "operationName": "Crash"},
    }

    exception = event["exception"]["values"][-1]
    assert exception["type"] == "RuntimeError"
    assert exception["value"] == "the database is on fire"
    assert exception["mechanism"] == {"type": "undine", "handled": False}


def test_sentry__client_errors_are_not_reported(undine_settings) -> None:
    """Reporting every GraphQL error is how an error tracker turns into noise."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Missing { notAField }")

    assert [error.message for error in result.errors or []] == ["Cannot query field 'notAField' on type 'Query'."]
    assert payloads.events == []


def test_sentry__deliberate_graphql_errors_are_not_reported(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Boom { boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]
    assert payloads.events == []


def test_sentry__error_predicate_can_report_every_error(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_REPORT_ERROR_PREDICATE = report_all_errors

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Boom { boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]

    assert len(payloads.events) == 1
    exception = payloads.events[0]["exception"]["values"][-1]
    assert exception["type"] == "GraphQLError"
    assert exception["value"] == "kaboom"


async def test_sentry__failing_async_resolver_is_reported_as_an_issue(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = await run_telemetry_query_async("query Crash { asyncCrash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    assert len(payloads.events) == 1
    exception = payloads.events[0]["exception"]["values"][-1]
    assert exception["type"] == "RuntimeError"
    assert exception["value"] == "the async database is on fire"


def test_sentry__span_streaming__records_spans_for_the_operation_steps(undine_settings) -> None:
    """Sentry's span streaming mode has a span API of its own, and streams each span separately."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_with_span_streaming() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    # The spans are streamed in the order they end, so the operation span comes after its children.
    assert get_sentry_streamed_span_names(payloads) == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query Greet",
        "Greet",
    ]

    operation_span = get_sentry_streamed_span(payloads, "query Greet")
    assert get_sentry_streamed_span_attributes(operation_span) == {
        "sentry.op": "graphql.query",
        "sentry.origin": "auto.graphql.undine",
        "graphql.document": "query Greet {\n  greeting\n}",
        "graphql.operation.name": "Greet",
        "graphql.operation.type": "query",
    }

    segment_span = get_sentry_streamed_span(payloads, "Greet")
    assert operation_span["parent_span_id"] == segment_span["span_id"]

    for step_name in ["graphql.parse", "graphql.validate", "graphql.execute"]:
        step_span = get_sentry_streamed_span(payloads, step_name)
        assert step_span["parent_span_id"] == operation_span["span_id"]
        assert get_sentry_streamed_span_attributes(step_span) == {
            "sentry.op": step_name,
            "sentry.origin": "auto.graphql.undine",
        }


def test_sentry__span_streaming__names_the_segment_after_the_operation(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_with_span_streaming() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    segment_span = get_sentry_streamed_span(payloads, "Greet")
    assert segment_span["is_segment"] is True
    assert get_sentry_streamed_span_attributes(segment_span)["sentry.segment.name.source"] == "component"


async def test_sentry__span_streaming__subscription_becomes_the_segment(undine_settings) -> None:
    """A subscription arrives on a connection that Sentry doesn't start a segment for."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_with_span_streaming_without_a_segment() as payloads:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    assert get_sentry_streamed_span_names(payloads) == [
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "graphql.execute",
        "graphql.execute",
        "Countdown",
    ]

    segment_span = get_sentry_streamed_span(payloads, "Countdown")
    assert segment_span["is_segment"] is True
    assert segment_span.get("parent_span_id") is None
    assert get_sentry_streamed_span_attributes(segment_span) == {
        "sentry.op": "graphql.subscription",
        "sentry.origin": "auto.graphql.undine",
        "sentry.segment.name.source": "component",
        "graphql.document": "subscription Countdown {\n  countdown\n}",
        "graphql.operation.name": "Countdown",
        "graphql.operation.type": "subscription",
    }


def test_sentry__spans_are_not_recorded_when_sentry_is_instrumented_by_opentelemetry(undine_settings) -> None:
    """With `instrumenter="otel"`, the Sentry SDK leaves the spans to OpenTelemetry."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_without_a_transaction(instrumenter="otel") as payloads:
        result = run_telemetry_query_sync("query Crash { crash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]
    assert payloads.transactions == []

    # The issues are Undine's own, so they are reported either way.
    assert len(payloads.events) == 1
    assert payloads.events[0]["transaction"] == "Crash"


def test_sentry__error_is_reported_without_sentry_tracing(undine_settings) -> None:
    """An application that only uses Sentry for issues still gets the operation name on the issue."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads_without_tracing() as payloads:
        result = run_telemetry_query_sync("query Crash { crash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]
    assert payloads.transactions == []

    assert len(payloads.events) == 1
    assert payloads.events[0]["transaction"] == "Crash"


def test_sentry__failure_is_not_reported_twice_through_the_logging_integration(undine_settings) -> None:
    """Undine logs the errors it masks. Sentry's logging integration must not raise a second issue for it."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads(integrations=[LoggingIntegration()]) as payloads:
        result = run_telemetry_query_sync("query Crash { crash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    assert len(payloads.events) == 1
    assert payloads.events[0]["exception"]["values"][-1]["type"] == "RuntimeError"


# Extension point


def test_sentry__span_callback_can_add_data_to_every_span(undine_settings) -> None:
    def add_custom_data(span: RecordedSpan, context: LifecycleHookContext) -> None:
        span.set_data("graphql.custom", "value")

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_SPAN_CALLBACK = add_custom_data

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "query Greet"))["graphql.custom"] == "value"
    assert get_sentry_span_data(get_sentry_span(transaction, "graphql.parse"))["graphql.custom"] == "value"


def test_sentry__span_callback_can_add_data_to_a_streamed_span(undine_settings) -> None:
    """The same callback works in either span mode, since it doesn't touch the Sentry span itself."""

    def add_custom_data(span: RecordedSpan, context: LifecycleHookContext) -> None:
        span.set_data("graphql.custom", "value")

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_SPAN_CALLBACK = add_custom_data

    with collect_sentry_payloads_with_span_streaming() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    operation_span = get_sentry_streamed_span(payloads, "query Greet")
    assert get_sentry_streamed_span_attributes(operation_span)["graphql.custom"] == "value"


def test_sentry__span_callback_can_reach_the_streamed_sentry_span(undine_settings) -> None:
    """`sentry_span` is the way to the things the two span APIs don't share."""

    def tag_with_the_span_name(span: RecordedSpan, context: LifecycleHookContext) -> None:
        sentry_span: StreamedSpan = span.sentry_span  # type: ignore[assignment]
        sentry_span.set_attribute("graphql.custom", sentry_span.name)

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_SPAN_CALLBACK = tag_with_the_span_name

    with collect_sentry_payloads_with_span_streaming() as payloads:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}

    operation_span = get_sentry_streamed_span(payloads, "query Greet")
    assert get_sentry_streamed_span_attributes(operation_span)["graphql.custom"] == "query Greet"


def test_sentry__span_callback_sees_the_execution_result(undine_settings) -> None:
    """The callback fires after execution, not right after parsing, so it can react to errors too."""

    def tag_with_error_count(span: RecordedSpan, context: LifecycleHookContext) -> None:
        result = context.result
        error_count = len(result.errors or []) if result is not None else 0  # type: ignore[union-attr]
        span.set_data("graphql.error.count", error_count)

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_SPAN_CALLBACK = tag_with_error_count

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("query Crash { crash }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "query Crash"))["graphql.error.count"] == 1


# Sensitive data


def test_sentry__inline_literals_are_not_recorded(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync('query Echo { echo(value: "alice@example.com") crash }')

    assert result.data == {"echo": "alice@example.com", "crash": None}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "query Echo")) == {
        "graphql.document": 'query Echo {\n  echo(value: "***")\n  crash\n}',
        "graphql.operation.name": "Echo",
        "graphql.operation.type": "query",
    }

    assert len(payloads.events) == 1
    assert payloads.events[0]["request"] == {
        "api_target": "graphql",
        "data": {"query": 'query Echo {\n  echo(value: "***")\n  crash\n}', "operationName": "Echo"},
    }


def test_sentry__variable_values_are_not_recorded(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    document = "query Echo($value: String!) { echo(value: $value) crash }"
    variables = {"value": "alice@example.com"}

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com", "crash": None}

    redacted_document = "query Echo($value: String!) {\n  echo(value: $value)\n  crash\n}"

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_data(get_sentry_span(transaction, "query Echo")) == {
        "graphql.document": redacted_document,
        "graphql.operation.name": "Echo",
        "graphql.operation.type": "query",
        "graphql.variables": '{"value": "***"}',
    }

    assert len(payloads.events) == 1
    assert payloads.events[0]["request"] == {
        "api_target": "graphql",
        "data": {
            "query": redacted_document,
            "variables": {"value": "***"},
            "operationName": "Echo",
        },
    }


def test_sentry__variable_values_are_recorded_when_the_callback_opts_in(undine_settings) -> None:
    def traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
        return context.variables

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_VARIABLES_CALLBACK = traced_variables

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    transaction = get_sentry_transaction(payloads)
    operation_span = get_sentry_span(transaction, "query Echo")
    assert get_sentry_span_data(operation_span)["graphql.variables"] == '{"value": "alice@example.com"}'


def test_sentry__variables_are_left_out_of_spans_when_the_callback_opts_out(undine_settings) -> None:
    """The callback only controls the spans. An issue still carries the redacted variables."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_VARIABLES_CALLBACK = no_traced_variables

    document = "query Echo($value: String!) { echo(value: $value) crash }"
    variables = {"value": "alice@example.com"}

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com", "crash": None}

    transaction = get_sentry_transaction(payloads)
    assert "graphql.variables" not in get_sentry_span_data(get_sentry_span(transaction, "query Echo"))

    assert len(payloads.events) == 1
    assert payloads.events[0]["request"]["data"]["variables"] == {"value": "***"}


def test_sentry__document_and_variables_are_recorded_with_pii_enabled(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    document = "query Echo($value: String!) { echo(value: $value) crash }"
    variables = {"value": "alice@example.com"}

    with collect_sentry_payloads(send_default_pii=True) as payloads:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com", "crash": None}

    assert len(payloads.events) == 1
    assert payloads.events[0]["request"] == {
        "api_target": "graphql",
        "data": {
            "query": document,
            "variables": variables,
            "operationName": "Echo",
        },
    }


def test_sentry__issue_carries_no_query_when_the_document_does_not_parse(undine_settings) -> None:
    """A document is only available once parsing is complete, and the raw source is not safe to send."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]
    undine_settings.SENTRY_REPORT_ERROR_PREDICATE = report_all_errors

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync('query Echo { echo(value: "alice@example.com"', operation_name="Echo")

    assert result.data is None

    assert len(payloads.events) == 1
    assert payloads.events[0]["request"] == {"api_target": "graphql", "data": {"operationName": "Echo"}}


def test_sentry__span_document_stays_redacted_with_pii_enabled(undine_settings) -> None:
    """The span attribute is always redacted, so traces keep a bounded set of values."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads(send_default_pii=True) as payloads:
        result = run_telemetry_query_sync('query Echo { echo(value: "alice@example.com") }')

    assert result.data == {"echo": "alice@example.com"}

    transaction = get_sentry_transaction(payloads)
    span_data = get_sentry_span_data(get_sentry_span(transaction, "query Echo"))
    assert span_data["graphql.document"] == 'query Echo {\n  echo(value: "***")\n}'


# Field spans


def test_sentry__no_field_spans_without_the_field_hook(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
    ]


def test_sentry__field_hook_records_a_span_per_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "Query.people",
        "PersonType.name",
        "PersonType.name",
    ]


def test_sentry__field_spans_are_skipped_for_an_introspection_query(undine_settings) -> None:
    """An introspection query resolves a field per type and field in the schema."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    document = "query IntrospectionQuery { people { name } }"

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query IntrospectionQuery",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
    ]


def test_sentry__field_spans_of_an_introspection_query_when_the_predicate_opts_in(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]
    undine_settings.SENTRY_SKIP_FIELD_SPANS_PREDICATE = never_skip_field_spans

    document = "query IntrospectionQuery { people { name } }"

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}

    transaction = get_sentry_transaction(payloads)
    assert get_sentry_span_names(transaction) == [
        "query IntrospectionQuery",
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "Query.people",
        "PersonType.name",
        "PersonType.name",
    ]

    execution_span = get_sentry_span(transaction, "graphql.execute")
    people_span = get_sentry_span(transaction, "Query.people")
    assert people_span["op"] == "graphql.resolve"
    assert people_span["parent_span_id"] == execution_span["span_id"]
    assert get_sentry_span_data(people_span) == {
        "graphql.field.name": "people",
        "graphql.field.parent.type": "Query",
        "graphql.field.path": "Query.people",
        "graphql.path": "people",
    }

    name_spans = [span for span in transaction["spans"] if span["description"] == "PersonType.name"]
    assert {get_sentry_span_data(span)["graphql.path"] for span in name_spans} == {"people.0.name", "people.1.name"}


async def test_sentry__field_hook_records_async_resolvers(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    with collect_sentry_payloads() as payloads:
        result = await run_telemetry_query_async("{ asyncGreeting }")

    assert result.data == {"asyncGreeting": "async hello"}

    transaction = get_sentry_transaction(payloads)
    field_span = get_sentry_span(transaction, "Query.asyncGreeting")
    assert get_sentry_span_data(field_span)["graphql.path"] == "asyncGreeting"


def test_sentry__field_hook_finishes_the_span_of_a_failing_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    with collect_sentry_payloads() as payloads:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]

    transaction = get_sentry_transaction(payloads)
    field_span = get_sentry_span(transaction, "Query.boom")
    assert get_sentry_span_data(field_span)["graphql.path"] == "boom"


async def test_sentry__field_hook_finishes_the_span_of_a_failing_async_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    with collect_sentry_payloads() as payloads:
        result = await run_telemetry_query_async("{ asyncBoom }")

    assert [error.message for error in result.errors or []] == ["async kaboom"]

    transaction = get_sentry_transaction(payloads)
    field_span = get_sentry_span(transaction, "Query.asyncBoom")
    assert get_sentry_span_data(field_span)["graphql.path"] == "asyncBoom"


# Cost when not used


def test_sentry__operation_hook_adds_no_field_middleware(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [SentryHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    assert _get_middleware_manager(context.lifecycle_hooks) is None


def test_sentry__field_hook_adds_field_middleware(undine_settings) -> None:
    undine_settings.LIFECYCLE_HOOKS = [SentryFullHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    assert _get_middleware_manager(context.lifecycle_hooks) is not None


# Optional dependency


def test_sentry__missing_dependency_gives_an_actionable_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    monkeypatch.setitem(sys.modules, "sentry_sdk.consts", None)

    message = (
        "The Sentry lifecycle hooks require the 'sentry-sdk' package. Install it with: pip install 'undine[sentry]'"
    )

    try:
        with pytest.raises(ImportError, match=exact(message)):
            importlib.reload(sentry_module)
    finally:
        monkeypatch.undo()
        importlib.reload(sentry_module)
