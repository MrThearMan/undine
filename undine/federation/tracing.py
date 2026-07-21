from __future__ import annotations

import base64
import dataclasses
import json
import time
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from graphql import ExecutionResult

from undine.hooks import LifecycleHook

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from google.protobuf.timestamp_pb2 import Timestamp
    from graphql import GraphQLError, GraphQLFieldResolver

    from undine.hooks import LifecycleHookContext
    from undine.typing import DjangoRequestProtocol, GQLInfo

__all__ = [
    "FederatedTracingHook",
]


TRACING_HEADER_NAME: str = "apollo-federation-include-trace"
"""Request header that opts into federated tracing per Apollo's ftv1 spec."""

TRACING_HEADER_VALUE: str = "ftv1"
"""Value of the trigger header that opts into federated tracing."""

TRACING_EXTENSION_KEY: str = "ftv1"
"""Key under GraphQL response `extensions` where the encoded trace is written."""


def _is_tracing_requested(request: DjangoRequestProtocol) -> bool:
    return request.headers.get(TRACING_HEADER_NAME) == TRACING_HEADER_VALUE


def _require_protobuf() -> None:
    try:
        import google.protobuf.timestamp_pb2  # noqa: F401, PLC0415
    except ImportError as error:
        msg = (
            "FederatedTracingHook requires the 'protobuf' package. "
            "Install it with: pip install 'undine[federation-tracing]'"
        )
        raise ImportError(msg) from error


class FederatedTracingHook(LifecycleHook):
    """Lifecycle hook implementing Apollo's Federated Tracing v1 (`ftv1`) protocol."""

    def __init__(self, context: LifecycleHookContext) -> None:
        super().__init__(context)

        self.enabled: bool = _is_tracing_requested(context.request)
        if self.enabled:
            _require_protobuf()

        root = FederationTraceNode()
        root_path: tuple[str | int, ...] = ()

        self.trace: FederationTrace = FederationTrace(root=root)
        self.nodes: dict[tuple[str | int, ...], FederationTraceNode] = {root_path: root}
        self.start_perf_counter_ns: int = 0

    def on_operation(self) -> Generator[None, None, None]:
        if not self.enabled:
            yield
            return

        self.trace.start_time = _make_timestamp(time.time_ns())
        self.start_perf_counter_ns = time.perf_counter_ns()
        try:
            yield
        finally:
            self._attach_trace()

    async def on_operation_async(self) -> AsyncGenerator[None, None]:
        if not self.enabled:
            yield
            return

        self.trace.start_time = _make_timestamp(time.time_ns())
        self.start_perf_counter_ns = time.perf_counter_ns()
        try:
            yield
        finally:
            self._attach_trace()

    def resolve(self, resolver: GraphQLFieldResolver, root: Any, info: GQLInfo, **kwargs: Any) -> Any:  # type: ignore[override]
        if not self.enabled:
            return resolver(root, info, **kwargs)

        node = self._ensure_node(tuple(info.path.as_list()))
        node.parent_type = str(info.parent_type)
        node.type = str(info.return_type)
        node.start_time = time.perf_counter_ns() - self.start_perf_counter_ns

        result = resolver(root, info, **kwargs)

        if isawaitable(result):

            async def _await_and_time() -> Any:
                try:
                    return await result
                finally:
                    node.end_time = time.perf_counter_ns() - self.start_perf_counter_ns

            return _await_and_time()

        node.end_time = time.perf_counter_ns() - self.start_perf_counter_ns
        return result

    def _ensure_node(self, path: tuple[str | int, ...]) -> FederationTraceNode:
        node = self.nodes.get(path)
        if node is not None:
            return node

        parent = self._ensure_node(path[:-1])
        node = FederationTraceNode()
        key = path[-1]

        if isinstance(key, int):
            node.index = key
        else:
            node.response_name = key

        parent.children.append(node)
        self.nodes[path] = node
        return node

    def _attach_trace(self) -> None:
        result = self.context.result
        if not isinstance(result, ExecutionResult):
            return

        self.trace.end_time = _make_timestamp(time.time_ns())
        self.trace.duration_ns = time.perf_counter_ns() - self.start_perf_counter_ns

        for error in result.errors or []:
            self._assign_error(error)

        trace_bytes = self.trace.SerializeToString()
        encoded = base64.b64encode(trace_bytes).decode("ascii")

        extensions = dict(result.extensions) if result.extensions else {}
        extensions[TRACING_EXTENSION_KEY] = encoded
        result.extensions = extensions

    def _assign_error(self, error: GraphQLError) -> None:
        path = tuple(error.path or ())
        node = self.nodes.get(path)

        while node is None and path:
            path = path[:-1]
            node = self.nodes.get(path)

        if node is None:  # pragma: no cover
            msg = "Could not find node for error"
            raise RuntimeError(msg)

        location_line = 0
        location_column = 0
        if error.locations:
            location_line = error.locations[0].line
            location_column = error.locations[0].column

        node.errors.append(
            FederationTraceError(
                message=error.message or "",
                location_line=location_line,
                location_column=location_column,
                json_error=json.dumps(error.formatted, separators=(",", ":")),
            ),
        )


# Implement minimal protobuf serialization for Apollo's FTV1 trace format.
# See: https://github.com/apollographql/apollo-server/blob/main/packages/usage-reporting-protobuf/src/reports.proto
#
# Protobuf tag encoding: (field_number << 3) | wire_type
# Wire type 0 = varint, wire type 2 = length-delimited (strings, bytes, embedded messages)

# Trace.Error
_ERROR_MESSAGE_TAG: bytes = b"\x0a"  # field 1, LEN
_ERROR_LOCATION_TAG: bytes = b"\x12"  # field 2, LEN (repeated Location)
_ERROR_JSON_TAG: bytes = b"\x22"  # field 4, LEN

# Trace.Location
_LOCATION_LINE_TAG: bytes = b"\x08"  # field 1, VARINT
_LOCATION_COLUMN_TAG: bytes = b"\x10"  # field 2, VARINT

# Trace.Node
_NODE_RESPONSE_NAME_TAG: bytes = b"\x0a"  # field 1, LEN  (oneof id)
_NODE_INDEX_TAG: bytes = b"\x10"  # field 2, VARINT (oneof id)
_NODE_TYPE_TAG: bytes = b"\x1a"  # field 3, LEN
_NODE_START_TIME_TAG: bytes = b"\x40"  # field 8, VARINT
_NODE_END_TIME_TAG: bytes = b"\x48"  # field 9, VARINT
_NODE_ERROR_TAG: bytes = b"\x5a"  # field 11, LEN (repeated Error)
_NODE_CHILD_TAG: bytes = b"\x62"  # field 12, LEN (repeated Node)
_NODE_PARENT_TYPE_TAG: bytes = b"\x6a"  # field 13, LEN

# Trace
_TRACE_END_TIME_TAG: bytes = b"\x1a"  # field 3, LEN (Timestamp)
_TRACE_START_TIME_TAG: bytes = b"\x22"  # field 4, LEN (Timestamp)
_TRACE_DURATION_NS_TAG: bytes = b"\x58"  # field 11, VARINT
_TRACE_ROOT_TAG: bytes = b"\x72"  # field 14, LEN (Node)

# Protobuf varints pack 7 data bits per byte; the high bit signals "another byte follows".
_VARINT_DATA_MASK: int = 0x7F
_VARINT_CONTINUATION_BIT: int = 0x80


@dataclasses.dataclass(kw_only=True, slots=True)
class FederationTraceError:
    message: str = ""
    location_line: int = 0
    location_column: int = 0
    json_error: str = ""

    def SerializeToString(self) -> bytes:  # noqa: N802
        parts: list[bytes] = []

        if self.message:
            data = self.message.encode("utf-8")
            data_length = _encode_varint(len(data))
            parts.extend((_ERROR_MESSAGE_TAG, data_length, data))

        if self.location_line or self.location_column:
            loc_parts: list[bytes] = []

            if self.location_line:
                line_varint = _encode_varint(self.location_line)
                loc_parts.extend((_LOCATION_LINE_TAG, line_varint))

            if self.location_column:
                column_varint = _encode_varint(self.location_column)
                loc_parts.extend((_LOCATION_COLUMN_TAG, column_varint))

            loc_bytes = b"".join(loc_parts)
            loc_length = _encode_varint(len(loc_bytes))
            parts.extend((_ERROR_LOCATION_TAG, loc_length, loc_bytes))

        if self.json_error:
            data = self.json_error.encode("utf-8")
            data_length = _encode_varint(len(data))
            parts.extend((_ERROR_JSON_TAG, data_length, data))

        return b"".join(parts)


@dataclasses.dataclass(kw_only=True, slots=True)
class FederationTraceNode:
    response_name: str | None = None
    index: int | None = None
    type: str | None = None
    parent_type: str | None = None
    start_time: int = 0
    end_time: int = 0
    children: list[FederationTraceNode] = dataclasses.field(default_factory=list)
    errors: list[FederationTraceError] = dataclasses.field(default_factory=list)

    def SerializeToString(self) -> bytes:  # noqa: N802
        parts: list[bytes] = []

        if self.response_name is not None:
            name_bytes = self.response_name.encode("utf-8")
            name_length = _encode_varint(len(name_bytes))
            parts.extend([_NODE_RESPONSE_NAME_TAG, name_length, name_bytes])
        elif self.index is not None:
            index_varint = _encode_varint(self.index)
            parts.extend([_NODE_INDEX_TAG, index_varint])

        if self.type:
            type_bytes = self.type.encode("utf-8")
            type_length = _encode_varint(len(type_bytes))
            parts.extend((_NODE_TYPE_TAG, type_length, type_bytes))

        if self.parent_type:
            pt_bytes = self.parent_type.encode("utf-8")
            pt_length = _encode_varint(len(pt_bytes))
            parts.extend((_NODE_PARENT_TYPE_TAG, pt_length, pt_bytes))

        if self.start_time:
            start_varint = _encode_varint(self.start_time)
            parts.extend((_NODE_START_TIME_TAG, start_varint))

        if self.end_time:
            end_varint = _encode_varint(self.end_time)
            parts.extend((_NODE_END_TIME_TAG, end_varint))

        for error in self.errors:
            error_bytes = error.SerializeToString()
            error_length = _encode_varint(len(error_bytes))
            parts.extend((_NODE_ERROR_TAG, error_length, error_bytes))

        for child in self.children:
            child_bytes = child.SerializeToString()
            child_length = _encode_varint(len(child_bytes))
            parts.extend((_NODE_CHILD_TAG, child_length, child_bytes))

        return b"".join(parts)


@dataclasses.dataclass(kw_only=True, slots=True)
class FederationTrace:
    start_time: Timestamp | None = None
    end_time: Timestamp | None = None
    duration_ns: int = 0
    root: FederationTraceNode | None = None

    def SerializeToString(self) -> bytes:  # noqa: N802
        parts: list[bytes] = []

        if self.start_time is not None:
            ts_bytes = self.start_time.SerializeToString()
            ts_length = _encode_varint(len(ts_bytes))
            parts.extend((_TRACE_START_TIME_TAG, ts_length, ts_bytes))

        if self.end_time is not None:
            ts_bytes = self.end_time.SerializeToString()
            ts_length = _encode_varint(len(ts_bytes))
            parts.extend((_TRACE_END_TIME_TAG, ts_length, ts_bytes))

        if self.duration_ns:
            duration_varint = _encode_varint(self.duration_ns)
            parts.extend((_TRACE_DURATION_NS_TAG, duration_varint))

        if self.root is not None:
            root_bytes = self.root.SerializeToString()
            root_length = _encode_varint(len(root_bytes))
            parts.extend((_TRACE_ROOT_TAG, root_length, root_bytes))

        return b"".join(parts)


def _encode_varint(value: int) -> bytes:
    parts: list[int] = []
    while value >= _VARINT_CONTINUATION_BIT:
        parts.append((value & _VARINT_DATA_MASK) | _VARINT_CONTINUATION_BIT)
        value >>= 7
    parts.append(value)
    return bytes(parts)


def _make_timestamp(wall_ns: int) -> Timestamp:
    from google.protobuf.timestamp_pb2 import Timestamp as _Timestamp  # noqa: PLC0415

    seconds, nanos = divmod(wall_ns, 1_000_000_000)
    ts = _Timestamp()
    ts.seconds = seconds
    ts.nanos = nanos
    return ts
