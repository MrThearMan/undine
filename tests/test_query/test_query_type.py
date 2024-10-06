import pytest

from example_project.app.models import Project, Task
from tests.helpers import MockGQLInfo
from undine import FilterSet, OrderSet, QueryType
from undine.errors.exceptions import MissingModelError
from undine.registry import REGISTRY


def test_query_type__simple():
    assert Task not in REGISTRY

    class MyQueryType(QueryType, model=Task):
        """Description."""

    assert Task in REGISTRY
    assert REGISTRY[Task] == MyQueryType

    assert MyQueryType.__model__ == Task
    assert MyQueryType.__filterset__ is None
    assert MyQueryType.__orderset__ is None
    assert MyQueryType.__lookup_field__ == "pk"
    assert MyQueryType.__typename__ == "MyQueryType"
    assert MyQueryType.__extensions__ == {"undine_type": MyQueryType}

    assert sorted(MyQueryType.__field_map__) == [
        "acceptanceCriteria",
        "assignees",
        "comments",
        "createdAt",
        "name",
        "pk",
        "project",
        "relatedTasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
    ]

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "MyQueryType"
    assert output_type.description == "Description."
    assert output_type.is_type_of == MyQueryType.__is_type_of__
    assert output_type.extensions == {"undine_type": MyQueryType}

    assert callable(output_type._fields)


def test_query_type__no_model():
    with pytest.raises(MissingModelError):

        class MyQueryType(QueryType): ...


def test_query_type__is_type_of():
    class MyQueryType(QueryType, model=Task): ...

    assert MyQueryType.__is_type_of__(Task(), MockGQLInfo()) is True
    assert MyQueryType.__is_type_of__(Project(), MockGQLInfo()) is False


def test_query_type__filterset():
    class MyFilterSet(FilterSet, model=Task): ...

    class MyQueryType(QueryType, model=Task, filterset=MyFilterSet): ...

    assert MyQueryType.__filterset__ == MyFilterSet


def test_query_type__filterset__default():
    class MyQueryType(QueryType, model=Task, filterset=True): ...

    assert MyQueryType.__filterset__ is not None
    assert MyQueryType.__filterset__.__name__ == "TaskFilterSet"
    assert MyQueryType.__filterset__.__model__ == Task


def test_query_type__orderset():
    class MyOrderSet(OrderSet, model=Task): ...

    class MyQueryType(QueryType, model=Task, orderset=MyOrderSet): ...

    assert MyQueryType.__orderset__ == MyOrderSet


def test_query_type__orderset__default():
    class MyQueryType(QueryType, model=Task, orderset=True): ...

    assert MyQueryType.__orderset__ is not None
    assert MyQueryType.__orderset__.__name__ == "TaskOrderSet"
    assert MyQueryType.__orderset__.__model__ == Task


def test_query_type__lookup_field():
    class MyQueryType(QueryType, model=Task, lookup_field="name"): ...

    assert MyQueryType.__lookup_field__ == "name"


def test_query_type__no_auto():
    class MyQueryType(QueryType, model=Task, auto=False): ...

    assert MyQueryType.__field_map__ == {}


def test_query_type__exclude():
    class MyQueryType(QueryType, model=Task, exclude=["name"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" in MyQueryType.__field_map__


def test_query_type__exclude__multiple():
    class MyQueryType(QueryType, model=Task, exclude=["name", "pk"]): ...

    assert "name" not in MyQueryType.__field_map__
    assert "pk" not in MyQueryType.__field_map__


def test_query_type__dont_register():
    assert Task not in REGISTRY

    class MyQueryType(QueryType, model=Task, register=False): ...

    assert Task not in REGISTRY


def test_query_type__typename():
    class MyQueryType(QueryType, model=Task, typename="CustomName"): ...

    assert MyQueryType.__typename__ == "CustomName"

    output_type = MyQueryType.__output_type__()
    assert output_type.name == "CustomName"


# TODO: Resolve one
# TODO: Resolve many
# TODO: Optimization
