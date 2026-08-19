from __future__ import annotations

from collections import namedtuple

import pytest

from example_project.app.models import Task
from tests.factories import TaskFactory
from tests.helpers import mock_gql_info
from undine import QueryType
from undine.relay import to_global_id
from undine.resolvers import GlobalIDResolver
from undine.resolvers.query import NamedTupleFieldResolver, TypedDictFieldResolver


def test_resolvers__typed_dict_field_resolver() -> None:
    resolver = TypedDictFieldResolver(key="my_key")
    result = resolver(root={"my_key": "value"}, info=mock_gql_info())
    assert result == "value"


def test_resolvers__typed_dict_field_resolver__missing_key() -> None:
    resolver = TypedDictFieldResolver(key="missing")
    result = resolver(root={"other": "value"}, info=mock_gql_info())
    assert result is None


def test_resolvers__named_tuple_field_resolver() -> None:
    Point = namedtuple("Point", ["x", "y"])  # noqa: PYI024
    point = Point(x=10, y=20)

    resolver = NamedTupleFieldResolver(attr="x")
    result = resolver(root=point, info=mock_gql_info())
    assert result == 10


def test_resolvers__named_tuple_field_resolver__missing_attr() -> None:
    resolver = NamedTupleFieldResolver(attr="z")
    result = resolver(root=object(), info=mock_gql_info())
    assert result is None


@pytest.mark.django_db
def test_resolvers__global_id_resolver() -> None:
    class TaskType(QueryType[Task]): ...

    task = TaskFactory.create()

    resolver = GlobalIDResolver(typename=TaskType.__schema_name__)

    object_id = to_global_id(typename=TaskType.__schema_name__, object_id=task.pk)

    assert resolver(root=task, info=mock_gql_info()) == object_id
