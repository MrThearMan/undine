from __future__ import annotations

import hashlib
import importlib
import sys
from typing import Any

import pytest
from ddtrace.trace import Span

from tests.helpers import MockRequest, exact
from tests.test_integrations.helpers import (
    ExecutionStepBoomHook,
    ParseStepBoomHook,
    ValidationStepBoomHook,
    build_telemetry_schema,
    collect_datadog_spans,
    get_datadog_span,
    get_datadog_span_tags,
    run_telemetry_query_async,
    run_telemetry_query_sync,
    run_telemetry_subscription,
)
from undine.dataclasses import GraphQLHttpParams
from undine.execution import _get_middleware_manager  # noqa: PLC2701
from undine.hooks import LifecycleHookContext
from undine.integrations import datadog as datadog_module
from undine.integrations.datadog import DatadogFullHook, DatadogHook, never_skip_field_spans, no_traced_variables


def _resource_hash(document: str) -> str:
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def test_datadog__records_spans_for_the_operation_steps(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query Greet { greeting }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document)

    assert result.data == {"greeting": "hello"}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query Greet",
    }

    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.span_type == "graphql"
    assert operation_span.service == "undine-example-project"
    assert operation_span.resource == f"Greet:{_resource_hash(document)}"
    assert get_datadog_span_tags(operation_span) == {
        "graphql.document": "query Greet {\n  greeting\n}",
        "graphql.operation.name": "Greet",
        "graphql.operation.type": "query",
    }

    for step_name in ("graphql.parse", "graphql.validate", "graphql.execute"):
        step_span = get_datadog_span(spans, step_name)
        assert step_span.span_type == "graphql"
        assert step_span.parent_id == operation_span.span_id
        assert get_datadog_span_tags(step_span) == {}


def test_datadog__service_name_is_configurable(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]
    undine_settings.DATADOG_SERVICE_NAME = "custom-service"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}
    assert get_datadog_span(spans, "query Greet").service == "custom-service"


def test_datadog__anonymous_operation_has_a_stable_resource_name(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "{ greeting }"

    with collect_datadog_spans() as spans:
        first = run_telemetry_query_sync(document)

    with collect_datadog_spans() as more_spans:
        second = run_telemetry_query_sync(document)

    assert first.data == {"greeting": "hello"}
    assert second.data == {"greeting": "hello"}

    first_span = get_datadog_span(spans, "query")
    second_span = get_datadog_span(more_spans, "query")

    expected_resource = _resource_hash(document)
    assert first_span.resource == expected_resource
    assert second_span.resource == expected_resource
    assert "graphql.operation.name" not in get_datadog_span_tags(first_span)


def test_datadog__resource_uses_the_requested_operation_in_a_multi_operation_document(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query Greet { greeting } query Shout { greeting }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="Shout")

    assert result.data == {"greeting": "hello"}
    operation_span = get_datadog_span(spans, "query Shout")
    assert operation_span.resource == f"Shout:{_resource_hash(document)}"
    assert get_datadog_span_tags(operation_span) == {
        "graphql.document": "query Greet {\n  greeting\n}\n\nquery Shout {\n  greeting\n}",
        "graphql.operation.name": "Shout",
        "graphql.operation.type": "query",
    }


def test_datadog__resource_uses_the_operations_own_name_even_without_a_client_supplied_one(undine_settings) -> None:
    """A client may omit `operationName` when the document has only one operation; the name is still known."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query Greet { greeting }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document)

    assert result.data == {"greeting": "hello"}
    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.resource == f"Greet:{_resource_hash(document)}"


def test_datadog__mutation_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("mutation Shout { shout }")

    assert result.data == {"shout": "HELLO"}
    assert get_datadog_span_tags(get_datadog_span(spans, "mutation Shout"))["graphql.operation.type"] == "mutation"


def test_datadog__operation_type_survives_a_leading_comment(undine_settings) -> None:
    """A naive `query.strip().startswith("mutation")` check is fooled by a leading comment."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "# a comment\nmutation Shout { shout }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document)

    assert result.data == {"shout": "HELLO"}
    assert get_datadog_span_tags(get_datadog_span(spans, "mutation Shout"))["graphql.operation.type"] == "mutation"


def test_datadog__operation_type_of_non_first_operation_in_a_multi_operation_document(undine_settings) -> None:
    """A naive string check on the whole document would misdetect the type of the executed operation."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query First { greeting } mutation Second { shout }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="Second")

    assert result.data == {"shout": "HELLO"}
    assert get_datadog_span_tags(get_datadog_span(spans, "mutation Second"))["graphql.operation.type"] == "mutation"


def test_datadog__syntax_error_leaves_the_operation_span_generic(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ greeting")

    assert result.errors is not None

    operation_span = get_datadog_span(spans, "graphql.operation")
    assert get_datadog_span_tags(operation_span) == {}


def test_datadog__document_without_an_operation_leaves_the_operation_span_generic(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("fragment Greet on Query { greeting }")

    assert result.errors is not None

    operation_span = get_datadog_span(spans, "graphql.operation")
    assert get_datadog_span_tags(operation_span) == {}


async def test_datadog__subscription_operation_type(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    with collect_datadog_spans() as spans:
        results = await run_telemetry_subscription("subscription Countdown { countdown }")

    assert [result.data for result in results] == [{"countdown": 2}, {"countdown": 1}]

    operation_span = get_datadog_span(spans, "subscription Countdown")
    assert get_datadog_span_tags(operation_span)["graphql.operation.type"] == "subscription"


async def test_datadog__async_execution_records_the_same_spans(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query Greet { asyncGreeting }"

    with collect_datadog_spans() as spans:
        result = await run_telemetry_query_async(document)

    assert result.data == {"asyncGreeting": "async hello"}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query Greet",
    }

    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.resource == f"Greet:{_resource_hash(document)}"

    for step_name in ("graphql.parse", "graphql.validate", "graphql.execute"):
        assert get_datadog_span(spans, step_name).parent_id == operation_span.span_id


# Unexpected failures


def test_datadog__unexpected_parse_failure_still_finishes_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook, ParseStepBoomHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.duration is not None
    parse_span = get_datadog_span(spans, "graphql.parse")
    assert parse_span.duration is not None


def test_datadog__unexpected_validation_failure_still_finishes_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook, ValidationStepBoomHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.duration is not None
    validation_span = get_datadog_span(spans, "graphql.validate")
    assert validation_span.duration is not None


def test_datadog__unexpected_execution_failure_still_finishes_the_operation_span(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook, ExecutionStepBoomHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert [error.message for error in result.errors or []] == ["Unexpected error."]

    operation_span = get_datadog_span(spans, "query Greet")
    assert operation_span.duration is not None
    execution_span = get_datadog_span(spans, "graphql.execute")
    assert execution_span.duration is not None


# Sensitive data


def test_datadog__inline_literals_are_not_recorded(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = 'query Echo { echo(value: "alice@example.com") }'

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document)

    assert result.data == {"echo": "alice@example.com"}

    operation_span = get_datadog_span(spans, "query Echo")
    assert "alice@example.com" not in str(get_datadog_span_tags(operation_span))


def test_datadog__variable_values_are_not_recorded(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    operation_span = get_datadog_span(spans, "query Echo")
    assert get_datadog_span_tags(operation_span) == {
        "graphql.document": "query Echo($value: String!) {\n  echo(value: $value)\n}",
        "graphql.operation.name": "Echo",
        "graphql.operation.type": "query",
        "graphql.variables": '{"value": "***"}',
    }


def test_datadog__variable_values_are_recorded_when_the_callback_opts_in(undine_settings) -> None:
    def traced_variables(context: LifecycleHookContext) -> dict[str, Any]:
        return context.variables

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]
    undine_settings.DATADOG_VARIABLES_CALLBACK = traced_variables

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    operation_span = get_datadog_span(spans, "query Echo")
    assert get_datadog_span_tags(operation_span)["graphql.variables"] == '{"value": "alice@example.com"}'


def test_datadog__variables_are_left_out_when_the_callback_opts_out(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]
    undine_settings.DATADOG_VARIABLES_CALLBACK = no_traced_variables

    document = "query Echo($value: String!) { echo(value: $value) }"
    variables = {"value": "alice@example.com"}

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, variables=variables)

    assert result.data == {"echo": "alice@example.com"}

    operation_span = get_datadog_span(spans, "query Echo")
    assert "graphql.variables" not in get_datadog_span_tags(operation_span)


# Field spans


def test_datadog__no_field_spans_without_the_field_hook(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query",
    }


def test_datadog__field_hook_records_a_span_per_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ people { name } }")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query",
        "Query.people",
        "PersonType.name",
    }

    execution_span = get_datadog_span(spans, "graphql.execute")
    people_span = get_datadog_span(spans, "Query.people")
    assert people_span.parent_id == execution_span.span_id
    assert get_datadog_span_tags(people_span) == {
        "graphql.field.name": "people",
        "graphql.field.parent.type": "Query",
        "graphql.field.path": "Query.people",
        "graphql.path": "people",
    }

    name_spans = [span for span in spans if span.name == "PersonType.name"]
    assert len(name_spans) == 2
    assert {get_datadog_span_tags(span)["graphql.path"] for span in name_spans} == {
        "people.0.name",
        "people.1.name",
    }


async def test_datadog__field_hook_records_async_resolvers(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    with collect_datadog_spans() as spans:
        result = await run_telemetry_query_async("{ asyncGreeting }")

    assert result.data == {"asyncGreeting": "async hello"}
    field_span = get_datadog_span(spans, "Query.asyncGreeting")
    assert field_span.duration is not None


def test_datadog__field_spans_are_skipped_for_an_introspection_query(undine_settings) -> None:
    """An introspection query resolves a field per type and field in the schema."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    document = "query IntrospectionQuery { people { name } }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query IntrospectionQuery",
    }


def test_datadog__field_spans_of_an_introspection_query_when_the_predicate_opts_in(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]
    undine_settings.DATADOG_SKIP_FIELD_SPANS_PREDICATE = never_skip_field_spans

    document = "query IntrospectionQuery { people { name } }"

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync(document, operation_name="IntrospectionQuery")

    assert result.data == {"people": [{"name": "Ada"}, {"name": "Grace"}]}
    assert {span.name for span in spans} == {
        "graphql.parse",
        "graphql.validate",
        "graphql.execute",
        "query IntrospectionQuery",
        "Query.people",
        "PersonType.name",
    }


def test_datadog__field_hook_finishes_the_span_of_a_failing_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]

    field_span = get_datadog_span(spans, "Query.boom")
    assert field_span.duration is not None


async def test_datadog__field_hook_finishes_the_span_of_a_failing_async_field(undine_settings) -> None:
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    with collect_datadog_spans() as spans:
        result = await run_telemetry_query_async("{ asyncBoom }")

    assert [error.message for error in result.errors or []] == ["async kaboom"]

    field_span = get_datadog_span(spans, "Query.asyncBoom")
    assert field_span.duration is not None


# Cost when not used


def test_datadog__operation_hook_adds_no_field_middleware(undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    hooks = [hook for hook in context.lifecycle_hooks if isinstance(hook, DatadogHook)]
    assert _get_middleware_manager(hooks) is None


def test_datadog__field_hook_adds_field_middleware(undine_settings) -> None:
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    context = LifecycleHookContext.from_graphql_params(params=params, request=MockRequest(method="POST"))

    assert _get_middleware_manager(context.lifecycle_hooks) is not None


# Extension point


def test_datadog__span_callback_can_add_tags_to_the_operation_span(undine_settings) -> None:
    def add_custom_tag(span: Span, context: LifecycleHookContext) -> None:
        span.set_tag("graphql.custom", "value")

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]
    undine_settings.DATADOG_SPAN_CALLBACK = add_custom_tag

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("query Greet { greeting }")

    assert result.data == {"greeting": "hello"}
    operation_span = get_datadog_span(spans, "query Greet")
    assert get_datadog_span_tags(operation_span)["graphql.custom"] == "value"


def test_datadog__span_callback_sees_the_execution_result(undine_settings) -> None:
    """The callback fires after execution, not right after parsing, so it can react to errors too."""

    def tag_with_error_count(span: Span, context: LifecycleHookContext) -> None:
        result = context.result
        error_count = len(result.errors or []) if result is not None else 0  # type: ignore[union-attr]
        span.set_tag("graphql.error.count", str(error_count))

    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogHook]
    undine_settings.DATADOG_SPAN_CALLBACK = tag_with_error_count

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ boom }")

    assert [error.message for error in result.errors or []] == ["kaboom"]
    operation_span = get_datadog_span(spans, "query")
    assert get_datadog_span_tags(operation_span)["graphql.error.count"] == "1"


# Optional dependency


def test_datadog__module_does_not_require_the_agent(undine_settings, monkeypatch) -> None:
    """Without a reachable Datadog agent, spans must still be created and operations must still run."""
    undine_settings.SCHEMA = build_telemetry_schema()
    undine_settings.ADDITIONAL_LIFECYCLE_HOOKS = [DatadogFullHook]

    with collect_datadog_spans() as spans:
        result = run_telemetry_query_sync("{ greeting }")

    assert result.data == {"greeting": "hello"}
    assert spans != []


def test_datadog__missing_dependency_gives_an_actionable_error(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "ddtrace", None)
    monkeypatch.setitem(sys.modules, "ddtrace.trace", None)

    message = (
        "The Datadog lifecycle hooks require the 'ddtrace' package. Install it with: pip install 'undine[datadog]'"
    )

    try:
        with pytest.raises(ImportError, match=exact(message)):
            importlib.reload(datadog_module)
    finally:
        monkeypatch.undo()
        importlib.reload(datadog_module)
