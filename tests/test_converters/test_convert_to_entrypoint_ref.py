from __future__ import annotations

from typing import Any

import pytest
from graphql import GraphQLNonNull, GraphQLString

from example_project.app.models import Project, Task
from undine import Entrypoint, GQLInfo, InterfaceField, InterfaceType, MutationType, QueryType, RootType, UnionType
from undine.converters import convert_to_entrypoint_ref
from undine.exceptions import MissingEntrypointRefError
from undine.pagination import OffsetPagination
from undine.relay import Connection, Node


def test_convert_to_entrypoint_ref__undefined_type() -> None:

    with pytest.raises(MissingEntrypointRefError):

        class Query(RootType):
            example_1 = Entrypoint()


def test_convert_to_entrypoint_ref__function() -> None:
    def example_func_1(root: Any, info: GQLInfo) -> str:
        return "Hello World"

    def example_func_2(root: Any, info: GQLInfo) -> list[str]:
        return ["Hello World"]

    def example_func_3(root: Any, info: GQLInfo) -> str | None:
        return "Hello World"

    def example_func_4(root: Any, info: GQLInfo) -> list[str] | None:
        return ["Hello World"]

    class Query(RootType):
        example_1 = Entrypoint(example_func_1)
        example_2 = Entrypoint(example_func_2)
        example_3 = Entrypoint(example_func_3)
        example_4 = Entrypoint(example_func_4)

    assert convert_to_entrypoint_ref(example_func_1, caller=Query.example_1) == example_func_1
    assert Query.example_1.many is False
    assert Query.example_1.nullable is False

    assert convert_to_entrypoint_ref(example_func_2, caller=Query.example_2) == example_func_2
    assert Query.example_2.many is True
    assert Query.example_2.nullable is False

    assert convert_to_entrypoint_ref(example_func_3, caller=Query.example_3) == example_func_3
    assert Query.example_3.many is False
    assert Query.example_3.nullable is True

    assert convert_to_entrypoint_ref(example_func_4, caller=Query.example_4) == example_func_4
    assert Query.example_4.many is True
    assert Query.example_4.nullable is True


def test_convert_to_entrypoint_ref__query_type() -> None:
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        task = Entrypoint(TaskType)

    assert convert_to_entrypoint_ref(TaskType, caller=Query.task) == TaskType


def test_convert_to_entrypoint_ref__mutation_type() -> None:
    class TaskCreateMutation(MutationType[Task]): ...

    class Mutation(RootType):
        create_task = Entrypoint(TaskCreateMutation)

    assert convert_to_entrypoint_ref(TaskCreateMutation, caller=Mutation.create_task) == TaskCreateMutation


def test_convert_to_entrypoint_ref__union_type() -> None:
    class TaskType(QueryType[Task]): ...

    class ProjectType(QueryType[Project]): ...

    class Commentable(UnionType[TaskType, ProjectType]): ...

    class Query(RootType):
        comments = Entrypoint(Commentable)

    assert convert_to_entrypoint_ref(Commentable, caller=Query.comments) == Commentable
    assert Query.comments.many is True
    assert Query.comments.nullable is False


def test_convert_to_entrypoint_ref__interface_type() -> None:
    class Named(InterfaceType):
        name = InterfaceField(GraphQLNonNull(GraphQLString))

    @Named
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        named = Entrypoint(Named)

    assert convert_to_entrypoint_ref(Named, caller=Query.named) == Named
    assert Query.named.many is True
    assert Query.named.nullable is False


def test_convert_to_entrypoint_ref__interface_type__node() -> None:
    @Node
    class TaskType(QueryType[Task]): ...

    class Query(RootType):
        node = Entrypoint(Node)

    assert convert_to_entrypoint_ref(Node, caller=Query.node) == Node
    assert Query.node.many is False
    assert Query.node.nullable is False


def test_convert_to_entrypoint_ref__connection() -> None:
    class TaskType(QueryType[Task]): ...

    conn = Connection(TaskType)

    class Query(RootType):
        tasks = Entrypoint(conn)

    assert convert_to_entrypoint_ref(conn, caller=Query.tasks) == conn
    assert Query.tasks.many is False
    assert Query.tasks.nullable is False


def test_convert_to_entrypoint_ref__offset_pagination() -> None:
    class TaskType(QueryType[Task]): ...

    off = OffsetPagination(TaskType)

    class Query(RootType):
        tasks = Entrypoint(off)

    assert convert_to_entrypoint_ref(off, caller=Query.tasks) == off
    assert Query.tasks.many is True
    assert Query.tasks.nullable is False
