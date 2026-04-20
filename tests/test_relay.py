from __future__ import annotations

import pytest
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from undine import InterfaceField, InterfaceType, QueryType, UnionType
from undine.exceptions import InterfaceFieldNodeIDError
from undine.relay import (
    Connection,
    NodeIDField,
    cursor_to_offset,
    decode_base64,
    encode_base64,
    from_global_id,
    offset_to_cursor,
    to_global_id,
)


def test_encode_base64() -> None:
    assert encode_base64("foo") == "Zm9v"


def test_decode_base64() -> None:
    assert decode_base64("Zm9v") == "foo"


def test_offset_to_cursor() -> None:
    assert offset_to_cursor("Test", 1) == "Y29ubmVjdGlvbjpUZXN0OjE="


def test_cursor_to_offset() -> None:
    assert cursor_to_offset("Test", "Y29ubmVjdGlvbjpUZXN0OjE=") == 1


def test_to_global_id() -> None:
    assert to_global_id("TaskType", 1) == "SUQ6VGFza1R5cGU6MQ=="


def test_from_global_id() -> None:
    assert from_global_id("SUQ6VGFza1R5cGU6MQ==") == ("TaskType", 1)


def test_from_global_id__string_id() -> None:
    assert from_global_id(to_global_id("TaskType", "abc")) == ("TaskType", "abc")


def test_connection__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    conn = Connection(TaskType)
    assert conn.query_type is TaskType
    assert conn.union_type is None
    assert conn.interface_type is None


def test_connection__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Searchable(UnionType[TaskType, ProjectType]): ...

    conn = Connection(Searchable)
    assert conn.query_type is None
    assert conn.union_type is Searchable
    assert conn.interface_type is None


def test_connection__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    conn = Connection(Named)
    assert conn.query_type is None
    assert conn.union_type is None
    assert conn.interface_type is Named


def test_node_id_field__check_inheritance__raises() -> None:
    class MyInterface(InterfaceType):
        id = InterfaceField(GraphQLNonNull(GraphQLString))

    node_field = NodeIDField()
    existing_field = MyInterface.__field_map__["id"]

    with pytest.raises(InterfaceFieldNodeIDError):
        node_field.check_inheritance(existing_field)


def test_node_id_field__check_inheritance__passes_for_node_id_field() -> None:
    class MyInterface(InterfaceType):
        id = NodeIDField()

    node_field = NodeIDField()
    existing_field = MyInterface.__field_map__["id"]

    node_field.check_inheritance(existing_field)  # should not raise
