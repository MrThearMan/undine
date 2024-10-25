from django.db import models
from django.db.models.functions import Length

from example_project.app.models import Person, Task
from tests.helpers import MockGQLInfo
from undine import Order, OrderSet


def test_order__repr():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    assert repr(MyOrderSet.name) == "<undine.ordering.Order(ref=F(name))>"


def test_order__attributes():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    assert MyOrderSet.name.ref == models.F("name")
    assert MyOrderSet.name.nulls_first is None
    assert MyOrderSet.name.nulls_last is None
    assert MyOrderSet.name.single_direction is False
    assert MyOrderSet.name.description is None
    assert MyOrderSet.name.deprecation_reason is None
    assert MyOrderSet.name.extensions == {"undine_order": MyOrderSet.name}
    assert MyOrderSet.name.owner == MyOrderSet
    assert MyOrderSet.name.name == "name"


def test_order__get_expression():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    expression = MyOrderSet.name.get_expression()
    assert expression == models.OrderBy(models.F("name"))


def test_order__get_graphql_enum_value():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order()

    enum_value = MyOrderSet.name.get_graphql_enum_value()
    assert enum_value.value == "name"
    assert enum_value.description is None
    assert enum_value.deprecation_reason is None
    assert enum_value.extensions == {"undine_order": MyOrderSet.name}


def test_order__expression():
    expr = Length("name")

    class MyOrderSet(OrderSet, model=Task, auto=False):
        length = Order(expr)

    assert MyOrderSet.length.ref == expr

    expression = MyOrderSet.length.get_expression()
    assert expression == models.OrderBy(expr)


def test_order__subquery():
    sq = models.Subquery(Person.objects.values("name")[:1])

    class MyOrderSet(OrderSet, model=Task, auto=False):
        primary_assignee_name = Order(sq)

    assert MyOrderSet.primary_assignee_name.ref == sq

    expression = MyOrderSet.primary_assignee_name.get_expression()
    assert expression == models.OrderBy(sq)


def test_order__null_placement__first():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(null_placement="first")

    assert MyOrderSet.name.nulls_first is True
    assert MyOrderSet.name.nulls_last is None

    data = ["name"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [models.OrderBy(models.F("name"), nulls_first=True)]


def test_order__null_placement__last():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(null_placement="last")

    assert MyOrderSet.name.nulls_first is None
    assert MyOrderSet.name.nulls_last is True

    data = ["name"]
    results = MyOrderSet.__build__(order_data=data, info=MockGQLInfo())
    assert results.order_by == [models.OrderBy(models.F("name"), nulls_last=True)]


def test_order__description():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(description="Description.")

    assert MyOrderSet.name.description == "Description."

    enum_value = MyOrderSet.name.get_graphql_enum_value()
    assert enum_value.description == "Description."

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].description == "Description."
    assert enum_type.values["nameDesc"].description == "Description."


def test_order__deprecation_reason():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(deprecation_reason="Use something else.")

    assert MyOrderSet.name.deprecation_reason == "Use something else."

    enum_value = MyOrderSet.name.get_graphql_enum_value()
    assert enum_value.deprecation_reason == "Use something else."

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].deprecation_reason == "Use something else."
    assert enum_type.values["nameDesc"].deprecation_reason == "Use something else."


def test_order__extensions():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(extensions={"foo": "bar"})

    assert MyOrderSet.name.extensions == {"foo": "bar", "undine_order": MyOrderSet.name}

    enum_value = MyOrderSet.name.get_graphql_enum_value()
    assert enum_value.extensions == {"foo": "bar", "undine_order": MyOrderSet.name}

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["nameAsc"].extensions == {"foo": "bar", "undine_order": MyOrderSet.name}
    assert enum_type.values["nameDesc"].extensions == {"foo": "bar", "undine_order": MyOrderSet.name}


def test_order__single_direction():
    class MyOrderSet(OrderSet, model=Task, auto=False):
        name = Order(single_direction=True)

    assert MyOrderSet.name.single_direction is True

    enum_type = MyOrderSet.__enum_type__()
    assert enum_type.values["name"] == MyOrderSet.name.get_graphql_enum_value()
