from __future__ import annotations

import os

SERVICE_NAME = "undine-example-project"
"""Name the example project's traces are grouped under in the tracing backend."""

OTEL_TRACING_HOOK = "undine.integrations.opentelemetry.OpenTelemetryFullHook"
"""Hook registered when OpenTelemetry tracing is on. The field hook is used to see per-resolver timings."""

DATADOG_TRACING_HOOK = "undine.integrations.datadog.DatadogFullHook"
"""Hook registered when Datadog tracing is on. The field hook is used to see per-resolver timings."""


def otel_tracing_enabled() -> bool:
    return os.getenv("OTEL_TRACING", "false").lower() == "true"


def datadog_tracing_enabled() -> bool:
    return os.getenv("DATADOG_TRACING", "false").lower() == "true"


def setup_otel_tracing() -> None:
    """Send spans to the local tracing backend started by `just otel-trace-up`."""
    # The OTLP exporter is a development dependency, so it must not be imported unless tracing is on.
    from opentelemetry import trace  # noqa: PLC0415
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: PLC0415
    from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415

    otlp_port = os.getenv("OTLP_PORT", "4318")
    exporter = OTLPSpanExporter(endpoint=f"http://localhost:{otlp_port}/v1/traces")

    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def setup_datadog_tracing() -> None:
    """Point ddtrace at the local Datadog test agent started by `just dd-trace-up`."""
    dd_port = os.getenv("DD_TRACE_AGENT_PORT", "8126")
    # Must be set before ddtrace's tracer singleton is first imported, since that is when it reads the agent URL.
    os.environ.setdefault("DD_TRACE_AGENT_URL", f"http://localhost:{dd_port}")
