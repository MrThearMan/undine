from collections.abc import Sequence

from google.protobuf.message import Message
from google.protobuf.timestamp_pb2 import Timestamp

class Trace(Message):
    class Location(Message):
        line: int
        column: int

    class Error(Message):
        message: str
        location: Sequence[Trace.Location]
        time_ns: int
        json: str

    class Node(Message):
        response_name: str
        index: int
        type: str
        parent_type: str
        start_time: int
        end_time: int
        error: Sequence[Trace.Error]
        child: Sequence[Trace.Node]

        def WhichOneof(self, oneof_group: str) -> str | None: ...

    start_time: Timestamp
    end_time: Timestamp
    duration_ns: int
    root: Trace.Node

    def __init__(self) -> None: ...
    def ParseFromString(self, serialized: bytes) -> int: ...
