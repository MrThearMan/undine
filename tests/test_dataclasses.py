from __future__ import annotations

import dataclasses
import json
from typing import Any

from graphql import ExecutionResult, GraphQLError

from example_project.app.models import Comment, Project, Task
from undine import QueryType
from undine.dataclasses import (
    BulkCreateKwargs,
    CacheControlResults,
    CompletedEventDataSC,
    CompletedEventDC,
    CompletedEventSC,
    IncrementalDeliveryComplete,
    IncrementalDeliveryHeartbeat,
    IncrementalDeliveryResponse,
    KeepAliveSignalDC,
    LazyGenericForeignKey,
    LazyRelation,
    MultipartMixedHttpComplete,
    MultipartMixedHttpHeartbeat,
    MultipartMixedHttpResponse,
    NextEventDataSC,
    NextEventDC,
    NextEventSC,
)

# Distinct Connections mode


def test_next_event_dc__encode() -> None:
    payload = ExecutionResult(data={"hello": "world"})
    event = NextEventDC(data=payload)
    encoded = event.encode()

    assert encoded == 'event: next\ndata: {"data":{"hello":"world"}}\n\n'


def test_next_event_dc__str_matches_encode() -> None:
    payload = ExecutionResult(data={"value": 42})
    event = NextEventDC(data=payload)

    assert str(event) == event.encode()


def test_next_event_dc__encode_with_errors() -> None:
    payload = ExecutionResult(
        data=None,
        errors=[GraphQLError(message="something went wrong")],
    )
    event = NextEventDC(data=payload)
    encoded = event.encode()

    parsed_data = json.loads(encoded.split("data: ", 1)[1].strip())
    assert parsed_data["data"] is None
    assert parsed_data["errors"][0]["message"] == "something went wrong"


def test_completed_event_dc__encode() -> None:
    event = CompletedEventDC()
    encoded = event.encode()

    assert encoded == "event: complete\ndata: \n\n"


def test_completed_event_dc__str_matches_encode() -> None:
    event = CompletedEventDC()

    assert str(event) == event.encode()


def test_keep_alive_signal_dc__encode() -> None:
    signal = KeepAliveSignalDC()
    encoded = signal.encode()

    assert encoded == ":\n\n"


# Single Connection mode


def test_next_event_data_sc__encode() -> None:
    payload = ExecutionResult(data={"count": 1})
    event_data = NextEventDataSC(id="op-1", payload=payload)
    encoded = event_data.encode()

    parsed = json.loads(encoded)
    assert parsed == {"id": "op-1", "payload": {"data": {"count": 1}}}


def test_next_event_data_sc__str_matches_encode() -> None:
    payload = ExecutionResult(data={"x": "y"})
    event_data = NextEventDataSC(id="op-2", payload=payload)

    assert str(event_data) == event_data.encode()


def test_next_event_data_sc__encode_compact_json() -> None:
    payload = ExecutionResult(data={"a": "b"})
    event_data = NextEventDataSC(id="op-3", payload=payload)
    encoded = event_data.encode()

    assert " " not in encoded


def test_next_event_sc__encode() -> None:
    payload = ExecutionResult(data={"hello": "world"})
    event = NextEventSC(operation_id="op-1", payload=payload)
    encoded = event.encode()

    assert encoded.startswith("event: next\ndata: ")
    assert encoded.endswith("\n\n")

    data_json = encoded.split("data: ", 1)[1].strip()
    parsed = json.loads(data_json)
    assert parsed == {"id": "op-1", "payload": {"data": {"hello": "world"}}}


def test_next_event_sc__str_matches_encode() -> None:
    payload = ExecutionResult(data={"v": 1})
    event = NextEventSC(operation_id="op-2", payload=payload)

    assert str(event) == event.encode()


def test_completed_event_data_sc__encode() -> None:
    event_data = CompletedEventDataSC(id="op-done")
    encoded = event_data.encode()

    parsed = json.loads(encoded)
    assert parsed == {"id": "op-done"}


def test_completed_event_data_sc__str_matches_encode() -> None:
    event_data = CompletedEventDataSC(id="op-x")

    assert str(event_data) == event_data.encode()


def test_completed_event_sc__encode() -> None:
    event = CompletedEventSC(operation_id="op-fin")
    encoded = event.encode()

    assert encoded.startswith("event: complete\ndata: ")
    assert encoded.endswith("\n\n")

    data_json = encoded.split("data: ", 1)[1].strip()
    parsed = json.loads(data_json)
    assert parsed == {"id": "op-fin"}


def test_completed_event_sc__str_matches_encode() -> None:
    event = CompletedEventSC(operation_id="op-z")

    assert str(event) == event.encode()


# Multipart Mixed HTTP mode


def test_multipart_mixed_http_response__encode() -> None:
    payload = ExecutionResult(data={"count": 1})
    event_data = MultipartMixedHttpResponse(payload=payload)
    encoded = event_data.encode()

    assert encoded == '\r\n--graphql\r\nContent-Type: application/json\r\n\r\n{"payload":{"data":{"count":1}}}'


def test_multipart_mixed_http_complete__encode() -> None:
    event_data = MultipartMixedHttpComplete()
    encoded = event_data.encode()

    assert encoded == "\r\n--graphql--\r\n"


def test_multipart_mixed_http_heartbeat__encode() -> None:
    event_data = MultipartMixedHttpHeartbeat()
    encoded = event_data.encode()

    assert encoded == "\r\n--graphql\r\nContent-Type: application/json\r\n\r\n{}"


def test_multipart_mixed_http_response__formatted__with_errors() -> None:
    payload = ExecutionResult(data={"count": 1})
    errors = [GraphQLError("something went wrong")]
    event_data = MultipartMixedHttpResponse(payload=payload, errors=errors)
    formatted = event_data.formatted
    assert "errors" in formatted
    assert formatted["errors"][0]["message"] == "something went wrong"


# Incremental delivery over HTTP mode


@dataclasses.dataclass
class MockInitialIncrementalExecutionResult:
    data: dict[str, Any]
    pending: list[Any] = dataclasses.field(default_factory=list)
    has_next: bool = False

    @property
    def formatted(self) -> dict[str, Any]:
        return {"data": self.data, "pending": self.pending, "hasNext": self.has_next}


@dataclasses.dataclass
class MockIncrementalDeferResult:
    data: dict[str, Any]
    id: str

    @property
    def formatted(self) -> dict[str, Any]:
        return {"data": self.data, "id": self.id}


@dataclasses.dataclass
class MockSubsequentIncrementalExecutionResult:
    incremental: list[MockIncrementalDeferResult]
    has_next: bool = False

    @property
    def formatted(self) -> dict[str, Any]:
        return {"hasNext": self.has_next, "incremental": [item.formatted for item in self.incremental]}


def test_incremental_http_response__initial__encode() -> None:
    initial_result = MockInitialIncrementalExecutionResult(data={"count": 1})
    response = IncrementalDeliveryResponse(result=initial_result)
    encoded = response.encode()

    assert encoded == (
        '\r\n--graphql\r\nContent-Type: application/json\r\n\r\n{"data":{"count":1},"pending":[],"hasNext":false}'
    )


def test_incremental_http_response__subsequent__encode() -> None:
    defer_result = MockIncrementalDeferResult(data={"count": 1}, id="1")
    initial_result = MockSubsequentIncrementalExecutionResult(incremental=[defer_result])
    response = IncrementalDeliveryResponse(result=initial_result)
    encoded = response.encode()

    assert encoded == (
        "\r\n"
        "--graphql\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        '{"hasNext":false,"incremental":[{"data":{"count":1},"id":"1"}]}'
    )


def test_incremental_http_complete__encode() -> None:
    response = IncrementalDeliveryComplete()
    encoded = response.encode()

    assert encoded == "\r\n--graphql--\r\n"


def test_incremental_http_heartbeat__encode() -> None:
    response = IncrementalDeliveryHeartbeat()
    encoded = response.encode()

    assert encoded == '\r\n--graphql\r\nContent-Type: application/json\r\n\r\n{"hasNext": true}'


# BulkCreateKwargs


def test_bulk_create_kwargs__default() -> None:
    kwargs = BulkCreateKwargs()
    assert kwargs.update_fields is None
    assert kwargs.update_conflicts is False
    assert kwargs.unique_fields is None
    assert bool(kwargs) is False


def test_bulk_create_kwargs__with_update_fields() -> None:
    kwargs = BulkCreateKwargs(update_fields={"name"})
    assert kwargs.update_conflicts is True
    assert kwargs.unique_fields == {"pk"}
    assert bool(kwargs) is True


def test_bulk_create_kwargs__iter() -> None:
    kwargs = BulkCreateKwargs(update_fields={"name"})
    assert set(kwargs) == {"update_fields", "update_conflicts", "unique_fields"}


def test_bulk_create_kwargs__len() -> None:
    kwargs = BulkCreateKwargs()
    assert len(kwargs) == 3


def test_bulk_create_kwargs__getitem() -> None:
    kwargs = BulkCreateKwargs(update_fields={"name"})
    assert kwargs["update_conflicts"] is True


# CacheControlResults


def test_cache_control_results__with_time_and_private() -> None:
    result = CacheControlResults(cache_time=60, cache_per_user=True)
    assert result.to_cache_control_header() == "max-age=60, private"


def test_cache_control_results__time_only() -> None:
    result = CacheControlResults(cache_time=120, cache_per_user=False)
    assert result.to_cache_control_header() == "max-age=120"


def test_cache_control_results__empty() -> None:
    result = CacheControlResults(cache_time=0, cache_per_user=False)
    assert result.to_cache_control_header() == ""


# LazyRelation and LazyGenericForeignKey


def test_lazy_relation__get_type() -> None:
    class ProjectType(QueryType[Project]): ...

    field = Task._meta.get_field("project")
    lazy = LazyRelation(field=field)
    assert lazy.get_type() is ProjectType


def test_lazy_generic_foreign_key__get_types() -> None:
    class TaskType(QueryType[Task]): ...

    field = Comment._meta.get_field("target")
    lazy = LazyGenericForeignKey(field=field)
    types = lazy.get_types()
    assert TaskType in types
