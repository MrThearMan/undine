from __future__ import annotations

import json

from graphql import FormattedExecutionResult

from undine.dataclasses import (
    CompletedEventDC,
    CompletedEventDataSC,
    CompletedEventSC,
    KeepAliveSignalDC,
    NextEventDC,
    NextEventDataSC,
    NextEventSC,
)


# Distinct Connections mode


def test_next_event_dc__encode() -> None:
    payload = FormattedExecutionResult(data={"hello": "world"})
    event = NextEventDC(data=payload)
    encoded = event.encode()

    assert encoded == 'event: next\ndata: {"data":{"hello":"world"}}\n\n'


def test_next_event_dc__str_matches_encode() -> None:
    payload = FormattedExecutionResult(data={"value": 42})
    event = NextEventDC(data=payload)

    assert str(event) == event.encode()


def test_next_event_dc__encode_with_errors() -> None:
    payload = FormattedExecutionResult(
        data=None,
        errors=[{"message": "something went wrong"}],
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
    payload = FormattedExecutionResult(data={"count": 1})
    event_data = NextEventDataSC(id="op-1", payload=payload)
    encoded = event_data.encode()

    parsed = json.loads(encoded)
    assert parsed == {"id": "op-1", "payload": {"data": {"count": 1}}}


def test_next_event_data_sc__str_matches_encode() -> None:
    payload = FormattedExecutionResult(data={"x": "y"})
    event_data = NextEventDataSC(id="op-2", payload=payload)

    assert str(event_data) == event_data.encode()


def test_next_event_data_sc__encode_compact_json() -> None:
    payload = FormattedExecutionResult(data={"a": "b"})
    event_data = NextEventDataSC(id="op-3", payload=payload)
    encoded = event_data.encode()

    assert " " not in encoded


def test_next_event_sc__encode() -> None:
    payload = FormattedExecutionResult(data={"hello": "world"})
    event = NextEventSC(operation_id="op-1", payload=payload)
    encoded = event.encode()

    assert encoded.startswith("event: next\ndata: ")
    assert encoded.endswith("\n\n")

    data_json = encoded.split("data: ", 1)[1].strip()
    parsed = json.loads(data_json)
    assert parsed == {"id": "op-1", "payload": {"data": {"hello": "world"}}}


def test_next_event_sc__str_matches_encode() -> None:
    payload = FormattedExecutionResult(data={"v": 1})
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
