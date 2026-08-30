from __future__ import annotations

import base64
import json
from textwrap import dedent
from typing import Any, AsyncGenerator, Generator

import freezegun
from django.http.request import HttpHeaders
from graphql import (
    ExecutionResult,
    GraphQLError,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)

from tests.helpers import MockRequest
from tests.test_federation._proto import reports_pb2
from undine.dataclasses import GraphQLHttpParams
from undine.execution import execute_graphql_http_async, execute_graphql_http_sync, execute_graphql_with_subscription
from undine.federation import tracing as tracing_module
from undine.federation.tracing import (
    TRACING_EXTENSION_KEY,
    TRACING_HEADER_NAME,
    TRACING_HEADER_VALUE,
    FederatedTracingHook,
)
from undine.hooks import LifecycleHook


def _headers(mapping: dict[str, str]) -> HttpHeaders:
    meta = {f"HTTP_{key.upper().replace('-', '_')}": value for key, value in mapping.items()}
    return HttpHeaders(meta)


def _build_schema() -> GraphQLSchema:
    return GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "greeting": GraphQLField(
                    GraphQLNonNull(GraphQLString),
                    resolve=lambda obj, info: "hello",  # noqa: ARG005
                ),
                "boom": GraphQLField(
                    GraphQLString,
                    resolve=lambda obj, info: (_ for _ in ()).throw(GraphQLError("kaboom")),  # noqa: ARG005
                ),
            },
        ),
    )


def _run_query(document: str, *, headers: dict[str, str]) -> ExecutionResult:
    params = GraphQLHttpParams(document=document, variables={}, operation_name=None, extensions={})
    request = MockRequest(method="POST", headers=_headers(headers))
    return execute_graphql_http_sync(params=params, request=request)


def _decode(encoded: str) -> reports_pb2.Trace:
    """Decode ftv1 output using Apollo's real protobuf `Trace` schema."""
    trace = reports_pb2.Trace()
    trace.ParseFromString(base64.b64decode(encoded))
    return trace


def _child_by_name(node: reports_pb2.Trace.Node, name: str) -> reports_pb2.Trace.Node:
    for child in node.child:
        if child.WhichOneof("id") == "response_name" and child.response_name == name:
            return child
    msg = f"No child with response_name={name!r}"
    raise KeyError(msg)


_FROZEN_TIME: str = "2024-01-15 12:00:00"


def test_federated_tracing__attaches_ftv1_when_header_present(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

        assert result.data == {"greeting": "hello"}
        assert result.extensions is not None
        assert TRACING_EXTENSION_KEY in result.extensions

        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "greeting"
            type: "String!"
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__no_extension_without_header(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ greeting }", headers={})

    assert result.data == {"greeting": "hello"}
    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


def test_federated_tracing__no_extension_when_header_value_mismatched(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: "something-else"})

    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


def test_federated_tracing__not_registered_means_no_tracing(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = []

    result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

    assert result.data == {"greeting": "hello"}
    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


def test_federated_tracing__decodable_trace_has_field_timings_and_types(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

    trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert trace.duration_ns > 0
    assert trace.start_time.seconds > 0
    assert (trace.end_time.seconds, trace.end_time.nanos) >= (trace.start_time.seconds, trace.start_time.nanos)

    greeting = _child_by_name(trace.root, "greeting")
    assert greeting.parent_type == "Query"
    assert greeting.type == "String!"
    assert greeting.start_time > 0
    assert greeting.end_time >= greeting.start_time


def test_federated_tracing__captures_errors_on_matching_node(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query("{ boom }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})
        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "boom"
            type: "String"
            error {
              message: "kaboom"
              json: "{\\"message\\":\\"kaboom\\",\\"path\\":[\\"boom\\"],\\"extensions\\":{\\"status_code\\":400}}"
            }
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__preserves_other_extensions(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()

    class ExtraExtensionHook(LifecycleHook):
        def on_operation(self) -> Generator[None, None, None]:
            yield
            result = self.context.result
            assert isinstance(result, ExecutionResult)
            extensions = dict(result.extensions or {})
            extensions["other"] = "value"
            result.extensions = extensions

    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook, ExtraExtensionHook]

    result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

    assert result.extensions is not None
    assert TRACING_EXTENSION_KEY in result.extensions
    assert result.extensions.get("other") == "value"


def test_federated_tracing__nested_paths_produce_child_nodes(undine_settings) -> None:
    def resolve_person(obj: Any, info: Any) -> dict[str, Any]:
        return {"name": "Ada"}

    nested_schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "person": GraphQLField(
                    GraphQLNonNull(
                        GraphQLObjectType(
                            "Person",
                            fields={"name": GraphQLField(GraphQLNonNull(GraphQLString))},
                        ),
                    ),
                    resolve=resolve_person,
                ),
            },
        ),
    )

    undine_settings.SCHEMA = nested_schema
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query("{ person { name } }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})
        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "person"
            type: "Person!"
            child {
              response_name: "name"
              type: "String!"
              parent_type: "Person"
            }
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__list_items_emit_index_nodes_including_zero(undine_settings) -> None:
    people = [{"name": "Ada"}, {"name": "Grace"}]

    def resolve_people(obj: Any, info: Any) -> list[dict[str, Any]]:
        return people

    person_type = GraphQLObjectType(
        "Person",
        fields={"name": GraphQLField(GraphQLNonNull(GraphQLString))},
    )
    nested_schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "people": GraphQLField(
                    GraphQLNonNull(GraphQLList(GraphQLNonNull(person_type))),
                    resolve=resolve_people,
                ),
            },
        ),
    )

    undine_settings.SCHEMA = nested_schema
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query("{ people { name } }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})
        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "people"
            type: "[Person!]!"
            child {
              index: 0
              child {
                response_name: "name"
                type: "String!"
                parent_type: "Person"
              }
            }
            child {
              index: 1
              child {
                response_name: "name"
                type: "String!"
                parent_type: "Person"
              }
            }
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__errors_when_protobuf_missing(undine_settings, monkeypatch) -> None:
    """Registering the hook and setting the header without `protobuf` installed must surface the error."""

    def _fake_require() -> None:
        msg = "protobuf missing"
        raise ImportError(msg)

    monkeypatch.setattr(tracing_module, "_require_protobuf", _fake_require)

    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ greeting }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

    assert result.errors is not None
    assert any("protobuf missing" in (err.message or "") for err in result.errors)
    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


def test_federated_tracing__does_not_check_protobuf_when_header_absent(undine_settings, monkeypatch) -> None:
    """No trigger header → no protobuf needed, so the hook must not raise."""

    def _fake_require() -> None:
        msg = "protobuf missing"
        raise ImportError(msg)

    monkeypatch.setattr(tracing_module, "_require_protobuf", _fake_require)

    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ greeting }", headers={})

    assert result.data == {"greeting": "hello"}
    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


async def test_federated_tracing__async_execution(undine_settings) -> None:
    async def resolve_async(obj: Any, info: Any) -> str:  # noqa: RUF029
        return "async-hello"

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "greeting": GraphQLField(GraphQLNonNull(GraphQLString), resolve=resolve_async),
            },
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    request = MockRequest(method="POST", headers=_headers({TRACING_HEADER_NAME: TRACING_HEADER_VALUE}))
    result = await execute_graphql_http_async(params=params, request=request)

    assert result.data == {"greeting": "async-hello"}
    trace = _decode(result.extensions[TRACING_EXTENSION_KEY])
    greeting = _child_by_name(trace.root, "greeting")
    assert greeting.start_time > 0
    assert greeting.end_time >= greeting.start_time


def test_federated_tracing__header_matching_is_case_insensitive(undine_settings) -> None:
    undine_settings.SCHEMA = _build_schema()
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query(
        "{ greeting }",
        headers={"Apollo-Federation-Include-Trace": TRACING_HEADER_VALUE},
    )

    assert result.data == {"greeting": "hello"}
    assert TRACING_EXTENSION_KEY in (result.extensions or {})


def test_federated_tracing__captures_multiple_errors_across_fields(undine_settings) -> None:
    def _raise_one(obj: Any, info: Any) -> Any:
        msg = "first"
        raise GraphQLError(msg)

    def _raise_two(obj: Any, info: Any) -> Any:
        msg = "second"
        raise GraphQLError(msg)

    schema = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "failingOne": GraphQLField(GraphQLString, resolve=_raise_one),
                "failingTwo": GraphQLField(GraphQLString, resolve=_raise_two),
            },
        ),
    )
    undine_settings.SCHEMA = schema
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query("{ failingOne failingTwo }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

        assert result.errors is not None
        assert {err.message for err in result.errors} == {"first", "second"}

        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "failingOne"
            type: "String"
            error {
              message: "first"
              json: "{\\"message\\":\\"first\\",\\"path\\":[\\"failingOne\\"],\\"extensions\\":{\\"status_code\\":400}}"
            }
            parent_type: "Query"
          }
          child {
            response_name: "failingTwo"
            type: "String"
            error {
              message: "second"
              json: "{\\"message\\":\\"second\\",\\"path\\":[\\"failingTwo\\"],\\"extensions\\":{\\"status_code\\":400}}"
            }
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__nested_error_attached_to_deep_node(undine_settings) -> None:
    def _raise_here(obj: Any, info: Any) -> Any:
        msg = "nested boom"
        raise GraphQLError(msg)

    person_type = GraphQLObjectType(
        "Person",
        fields={
            "name": GraphQLField(GraphQLNonNull(GraphQLString)),
            "failingField": GraphQLField(GraphQLString, resolve=_raise_here),
        },
    )
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "person": GraphQLField(
                    GraphQLNonNull(person_type),
                    resolve=lambda obj, info: {"name": "Ada"},  # noqa: ARG005
                ),
            },
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query(
            "{ person { name failingField } }",
            headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE},
        )
        assert result.errors is not None

        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    # Error attaches only to the failing node; the healthy sibling has no error entries.
    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "person"
            type: "Person!"
            child {
              response_name: "name"
              type: "String!"
              parent_type: "Person"
            }
            child {
              response_name: "failingField"
              type: "String"
              error {
                message: "nested boom"
                json: "{\\"message\\":\\"nested boom\\",\\"path\\":[\\"person\\",\\"failingField\\"],\\"extensions\\":{\\"status_code\\":400}}"
              }
              parent_type: "Person"
            }
            parent_type: "Query"
          }
        }
    """)


def test_federated_tracing__error_json_includes_path_and_locations(undine_settings) -> None:
    undine_settings.NO_ERROR_LOCATION = False

    def _raise_here(obj: Any, info: Any) -> Any:
        msg = "with path"
        raise GraphQLError(msg)

    person_type = GraphQLObjectType(
        "Person",
        fields={"failingField": GraphQLField(GraphQLString, resolve=_raise_here)},
    )
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "person": GraphQLField(
                    GraphQLNonNull(person_type),
                    resolve=lambda obj, info: {},  # noqa: ARG005
                ),
            },
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query(
        "{\n  person {\n    failingField\n  }\n}",
        headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE},
    )

    trace = _decode(result.extensions[TRACING_EXTENSION_KEY])
    failing = _child_by_name(_child_by_name(trace.root, "person"), "failingField")
    assert len(failing.error) == 1
    payload = json.loads(failing.error[0].json)
    assert payload["message"] == "with path"
    assert payload["path"] == ["person", "failingField"]
    assert payload["locations"][0]["line"] > 0
    assert payload["locations"][0]["column"] > 0


def test_federated_tracing__error_location_line_and_column_encoded(undine_settings) -> None:
    undine_settings.NO_ERROR_LOCATION = False

    def _raise_here(obj: Any, info: Any) -> Any:
        msg = "locate me"
        raise GraphQLError(msg)

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"failing": GraphQLField(GraphQLString, resolve=_raise_here)},
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        result = _run_query(
            "{\n  failing\n}",
            headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE},
        )
        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "failing"
            type: "String"
            error {
              message: "locate me"
              location {
                line: 2
                column: 3
              }
              json: "{\\"message\\":\\"locate me\\",\\"locations\\":[{\\"line\\":2,\\"column\\":3}],\\"path\\":[\\"failing\\"],\\"extensions\\":{\\"status_code\\":400}}"
            }
            parent_type: "Query"
          }
        }
    """)


async def test_federated_tracing__async_captures_errors(undine_settings) -> None:
    async def _raise(obj: Any, info: Any) -> Any:  # noqa: RUF029
        msg = "async boom"
        raise GraphQLError(msg)

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"failing": GraphQLField(GraphQLString, resolve=_raise)},
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    with freezegun.freeze_time(_FROZEN_TIME):
        params = GraphQLHttpParams(document="{ failing }", variables={}, operation_name=None, extensions={})
        request = MockRequest(method="POST", headers=_headers({TRACING_HEADER_NAME: TRACING_HEADER_VALUE}))
        result = await execute_graphql_http_async(params=params, request=request)

        assert result.errors is not None
        assert result.errors[0].message == "async boom"

        trace = _decode(result.extensions[TRACING_EXTENSION_KEY])

    assert str(trace) == dedent("""\
        end_time {
          seconds: 1705320000
        }
        start_time {
          seconds: 1705320000
        }
        root {
          child {
            response_name: "failing"
            type: "String"
            error {
              message: "async boom"
              json: "{\\"message\\":\\"async boom\\",\\"path\\":[\\"failing\\"],\\"extensions\\":{\\"status_code\\":400}}"
            }
            parent_type: "Query"
          }
        }
    """)


async def test_federated_tracing__async_on_operation__disabled_yields_without_attaching(undine_settings) -> None:
    """When the trigger header is absent, the async operation hook must yield without producing extensions."""

    async def resolve_async(obj: Any, info: Any) -> str:  # noqa: RUF029
        return "async-hello"

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"greeting": GraphQLField(GraphQLNonNull(GraphQLString), resolve=resolve_async)},
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    params = GraphQLHttpParams(document="{ greeting }", variables={}, operation_name=None, extensions={})
    request = MockRequest(method="POST", headers=_headers({}))
    result = await execute_graphql_http_async(params=params, request=request)

    assert result.data == {"greeting": "async-hello"}
    assert not (result.extensions or {}).get(TRACING_EXTENSION_KEY)


async def test_federated_tracing__subscription_stream__skips_extension_attachment(undine_settings) -> None:
    """
    Subscriptions produce a `GraphQLStream` rather than an `ExecutionResult`, so `_attach_trace`
    must not try to write the `ftv1` extension onto per-event results before iteration starts.
    """

    async def subscribe_countdown(obj: Any, info: Any) -> AsyncGenerator[int, None]:  # noqa: RUF029
        for i in range(3, 0, -1):
            yield i

    def resolve_countdown(payload: int, info: Any) -> int:
        return payload

    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={"noop": GraphQLField(GraphQLString)},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            fields={
                "countdown": GraphQLField(
                    GraphQLNonNull(GraphQLString),
                    resolve=resolve_countdown,
                    subscribe=subscribe_countdown,
                ),
            },
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    params = GraphQLHttpParams(
        document="subscription { countdown }",
        variables={},
        operation_name=None,
        extensions={},
    )
    request = MockRequest(method="WEBSOCKET", headers=_headers({TRACING_HEADER_NAME: TRACING_HEADER_VALUE}))
    stream = await execute_graphql_with_subscription(params=params, request=request)

    async for event in stream:
        assert not (event.extensions or {}).get(TRACING_EXTENSION_KEY)


def test_federated_tracing__error_on_null_list_item_bubbles_to_parent_node(undine_settings) -> None:
    """
    When a non-nullable list item is `null`, graphql-core adds an error at the list index path
    (e.g. `["people", 1]`) even though no resolver ran for that item. The tracing hook must
    walk that path up to a node it did resolve for (here: `["people"]`).
    """

    def resolve_people(obj: Any, info: Any) -> list[dict[str, Any] | None]:
        return [{"name": "Ada"}, None, {"name": "Grace"}]

    person_type = GraphQLObjectType(
        "Person",
        fields={"name": GraphQLField(GraphQLNonNull(GraphQLString))},
    )
    undine_settings.SCHEMA = GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            fields={
                "people": GraphQLField(
                    GraphQLList(GraphQLNonNull(person_type)),
                    resolve=resolve_people,
                ),
            },
        ),
    )
    undine_settings.LIFECYCLE_HOOKS = [FederatedTracingHook]

    result = _run_query("{ people { name } }", headers={TRACING_HEADER_NAME: TRACING_HEADER_VALUE})

    assert result.errors is not None
    assert any(err.path == ["people", 1] for err in result.errors)

    trace = _decode(result.extensions[TRACING_EXTENSION_KEY])
    people = _child_by_name(trace.root, "people")
    # The null-item error can't attach to `["people", 1]` (no such node), so it bubbles to `["people"]`.
    assert len(people.error) == 1
    assert "null" in people.error[0].message.lower()


def test_federation_trace_error__serialize__no_fields_produces_empty() -> None:
    error = tracing_module.FederationTraceError()

    assert error.SerializeToString() == b""


def test_federation_trace_error__serialize__line_only_encodes_line_tag() -> None:
    error = tracing_module.FederationTraceError(location_line=5, location_column=0)

    serialized = error.SerializeToString()

    # Location tag with only line encoded (column varint absent).
    assert serialized.startswith(b"\x12")


def test_federation_trace_error__serialize__column_only_encodes_column_tag() -> None:
    error = tracing_module.FederationTraceError(location_line=0, location_column=7)

    serialized = error.SerializeToString()

    # Location tag with only column encoded (line varint absent).
    assert serialized.startswith(b"\x12")


def test_federation_trace__serialize__before_start_and_end_times_are_set() -> None:
    """`start_time` and `end_time` are populated by the hook lifecycle; before that they stay `None`."""
    trace = tracing_module.FederationTrace()

    # Should emit only the required `root` field.
    assert trace.SerializeToString() == b"\x72\x00"
