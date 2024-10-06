from django.db import models
from django.db.models.functions import Length

from example_project.app.models import Person, Task
from tests.helpers import MockGQLInfo
from undine import Order, OrderSet


def test_order__simple():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    order = MyOrderSet.name

    assert repr(order) == "<undine.ordering.Order(ref=F(name))>"

    assert order.ref == models.F("name")
    assert order.nulls_first is None
    assert order.nulls_last is None
    assert order.single_direction is False
    assert order.description is None
    assert order.deprecation_reason is None
    assert order.extensions == {"undine_order": order}

    assert order.owner == MyOrderSet
    assert order.name == "name"

    expression = order.get_expression()
    assert expression == models.OrderBy(models.F("name"))

    enum_value = order.get_graphql_enum_value()
    assert enum_value.value == "name"
    assert enum_value.description is None
    assert enum_value.deprecation_reason is None
    assert enum_value.extensions == {"undine_order": order}


def test_order__expression():
    expr = Length("name")

    class MyOrderSet(OrderSet, model=Task, auto=False):
        length = Order(expr)

    order = MyOrderSet.length

    assert order.ref == expr

    expression = order.get_expression()
    assert expression == models.OrderBy(expr)


def test_order__subquery():
    sq = models.Subquery(Person.objects.values("name")[:1])

    class MyOrderSet(OrderSet, model=Task, auto=False):
        primary_assignee_name = Order(sq)

    order = MyOrderSet.primary_assignee_name

    assert order.ref == sq

    expression = order.get_expression()
    assert expression == models.OrderBy(sq)


def test_order__null_placement__first():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(null_placement="first")

    order = MyOrderSet.name

    assert order.nulls_first is True
    assert order.nulls_last is None

    data = ["name"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [models.OrderBy(models.F("name"), nulls_first=True)]


def test_order__null_placement__last():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(null_placement="last")

    order = MyOrderSet.name

    assert order.nulls_first is None
    assert order.nulls_last is True

    data = ["name"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [models.OrderBy(models.F("name"), nulls_last=True)]


def test_order__description():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(description="Description.")

    order = MyOrderSet.name

    assert order.description == "Description."

    enum_value = order.get_graphql_enum_value()
    assert enum_value.description == "Description."

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].description == "Description."
    assert enum_type.values["nameDesc"].description == "Description."


def test_order__deprecation_reason():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(deprecation_reason="Use something else.")

    order = MyOrderSet.name

    assert order.deprecation_reason == "Use something else."

    enum_value = order.get_graphql_enum_value()
    assert enum_value.deprecation_reason == "Use something else."

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].deprecation_reason == "Use something else."
    assert enum_type.values["nameDesc"].deprecation_reason == "Use something else."


def test_order__extensions():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(extensions={"foo": "bar"})

    order = MyOrderSet.name

    assert order.extensions == {"foo": "bar", "undine_order": order}

    enum_value = order.get_graphql_enum_value()
    assert enum_value.extensions == {"foo": "bar", "undine_order": order}

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].extensions == {"foo": "bar", "undine_order": order}
    assert enum_type.values["nameDesc"].extensions == {"foo": "bar", "undine_order": order}
