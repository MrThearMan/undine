import pytest
from django.db import models

from example_project.app.models import Task
from tests.helpers import MockGQLInfo
from undine import Order, OrderSet
from undine.errors.exceptions import MissingModelError
from undine.optimizer.ast import get_underlying_type


def test_orderset__attributes():
    class MyOrderSet(OrderSet, model=Task):
        """Description."""

    assert MyOrderSet.__model__ == Task
    assert MyOrderSet.__typename__ == "MyOrderSet"
    assert MyOrderSet.__extensions__ == {"undine_orderset": MyOrderSet}
    assert sorted(MyOrderSet.__order_map__) == ["created_at", "name", "pk", "type"]


def test_orderset__enum_type():
    class MyOrderSet(OrderSet, model=Task):
        """Description."""

    input_type = MyOrderSet.__input_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.name == "MyOrderSet"
    assert sorted(enum_type.values) == [
        "createdAtAsc",
        "createdAtDesc",
        "nameAsc",
        "nameDesc",
        "pkAsc",
        "pkDesc",
        "typeAsc",
        "typeDesc",
    ]
    assert enum_type.description == "Description."
    assert enum_type.extensions == {"undine_orderset": MyOrderSet}


def test_filterset__no_model():
    with pytest.raises(MissingModelError):

        class MyOrderSet(OrderSet): ...


def test_orderset__one_field():
    class MyOrderSet(OrderSet, model=Task):
        name = Order()

    data = ["name_asc"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [
        models.OrderBy(models.F("name")),
    ]

    data = ["name_desc"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [
        models.OrderBy(models.F("name"), descending=True),
    ]


def test_orderset__two_fields():
    class MyOrderSet(OrderSet, model=Task):
        name = Order()

    data = ["name_asc", "pk_desc"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [
        models.OrderBy(models.F("name")),
        models.OrderBy(models.F("id"), descending=True),
    ]


def test_orderset__typename():
    class MyOrderSet(OrderSet, model=Task, typename="CustomName"): ...

    assert MyOrderSet.__typename__ == "CustomName"

    input_type = MyOrderSet.__input_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.name == "CustomName"


def test_orderset__extensions():
    class MyOrderSet(OrderSet, model=Task, extensions={"foo": "bar"}): ...

    assert MyOrderSet.__extensions__ == {"foo": "bar", "undine_orderset": MyOrderSet}

    input_type = MyOrderSet.__input_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.extensions == {"foo": "bar", "undine_orderset": MyOrderSet}


def test_filterset__no_auto():
    class MyOrderSet(OrderSet, model=Task, auto=False): ...

    assert MyOrderSet.__order_map__ == {}


def test_filterset__exclude():
    class MyOrderSet(OrderSet, model=Task, exclude=["name"]): ...

    assert "pk" in MyOrderSet.__order_map__
    assert "name" not in MyOrderSet.__order_map__
    assert "type" in MyOrderSet.__order_map__
    assert "created_at" in MyOrderSet.__order_map__


def test_filterset__exclude__multiple():
    class MyOrderSet(OrderSet, model=Task, exclude=["name", "pk"]): ...

    assert "pk" not in MyOrderSet.__order_map__
    assert "name" not in MyOrderSet.__order_map__
    assert "type" in MyOrderSet.__order_map__
    assert "created_at" in MyOrderSet.__order_map__
