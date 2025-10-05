from __future__ import annotations

import pytest
from django.db.models import Count, F, OrderBy, Subquery
from django.db.models.functions import Length
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Person, Task
from tests.helpers import mock_gql_info
from undine import DjangoExpression, GQLInfo, Order, OrderSet
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError
from undine.ordering import OrderSetMeta
from undine.utils.graphql.utils import get_underlying_type


def test_order__repr() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    assert repr(MyOrderSet.name) == "<undine.ordering.Order(ref=F(name))>"


def test_order__str() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    assert str(MyOrderSet.name) == "name"


def test_order__attributes() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    assert MyOrderSet.name.ref == F("name")
    assert MyOrderSet.name.nulls_first is None
    assert MyOrderSet.name.nulls_last is None
    assert MyOrderSet.name.description is None
    assert MyOrderSet.name.deprecation_reason is None
    assert MyOrderSet.name.schema_name == "name"
    assert MyOrderSet.name.directives == []
    assert MyOrderSet.name.extensions == {"undine_order": MyOrderSet.name}

    assert MyOrderSet.name.orderset == MyOrderSet
    assert MyOrderSet.name.name == "name"


def test_order__get_expression() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    expression = MyOrderSet.name.get_expression(descending=False)
    assert expression == OrderBy(F("name"))

    expression = MyOrderSet.name.get_expression(descending=True)
    assert expression == OrderBy(F("name"), descending=True)


def test_order__get_graphql_enum_value() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    enum_value = MyOrderSet.name.as_graphql_enum_value()
    assert enum_value.value == "name"
    assert enum_value.description is None
    assert enum_value.deprecation_reason is None
    assert enum_value.extensions == {"undine_order": MyOrderSet.name}


def test_order__schema_name() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(schema_name="val")

    assert MyOrderSet.name.schema_name == "val"

    assert str(MyOrderSet.name) == "val"


def test_order__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(directives=directives)

    assert MyOrderSet.name.directives == directives

    assert str(MyOrderSet.name) == 'name @value(value: "foo")'


def test_order__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyOrderSet(OrderSet[Task], auto=False):
            name = Order(directives=directives)

    # Model not cleaned up since error occurred in OrderSet class body.
    del OrderSetMeta.__models__


def test_order__directives__matmul() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order() @ ValueDirective(value="foo")

    assert MyOrderSet.name.directives == [ValueDirective(value="foo")]

    assert str(MyOrderSet.name) == 'name @value(value: "foo")'


def test_order__expression() -> None:
    expr = Length("name")

    class MyOrderSet(OrderSet[Task], auto=False):
        length = Order(expr)

    assert MyOrderSet.length.ref == expr

    expression = MyOrderSet.length.get_expression(descending=False)
    assert expression == OrderBy(expr)


def test_order__subquery() -> None:
    sq = Subquery(Person.objects.values("name")[:1])

    class MyOrderSet(OrderSet[Task], auto=False):
        primary_assignee_name = Order(sq)

    assert MyOrderSet.primary_assignee_name.ref == sq

    expression = MyOrderSet.primary_assignee_name.get_expression(descending=False)
    assert expression == OrderBy(sq)


def test_order__null_placement__first() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(null_placement="first")

    assert MyOrderSet.name.nulls_first is True
    assert MyOrderSet.name.nulls_last is None

    data = ["name_asc"]
    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())
    assert results.order_by == [OrderBy(F("name"), nulls_first=True)]


def test_order__null_placement__last() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(null_placement="last")

    assert MyOrderSet.name.nulls_first is None
    assert MyOrderSet.name.nulls_last is True

    data = ["name_asc"]
    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())
    assert results.order_by == [OrderBy(F("name"), nulls_last=True)]


def test_order__description() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(description="Description.")

    assert MyOrderSet.name.description == "Description."

    enum_value = MyOrderSet.name.as_graphql_enum_value()
    assert enum_value.description == "Description."

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.values["nameAsc"].description == "Description."
    assert enum_type.values["nameDesc"].description == "Description."


def test_order__description__variable(undine_settings) -> None:
    undine_settings.ENABLE_CLASS_ATTRIBUTE_DOCSTRINGS = True

    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()
        """Description."""

    assert MyOrderSet.name.description == "Description."

    enum_value = MyOrderSet.name.as_graphql_enum_value()
    assert enum_value.description == "Description."

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.values["nameAsc"].description == "Description."
    assert enum_type.values["nameDesc"].description == "Description."


def test_order__deprecation_reason() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(deprecation_reason="Use something else.")

    assert MyOrderSet.name.deprecation_reason == "Use something else."

    enum_value = MyOrderSet.name.as_graphql_enum_value()
    assert enum_value.deprecation_reason == "Use something else."

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.values["nameAsc"].deprecation_reason == "Use something else."
    assert enum_type.values["nameDesc"].deprecation_reason == "Use something else."


def test_order__extensions() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order(extensions={"foo": "bar"})

    assert MyOrderSet.name.extensions == {"foo": "bar", "undine_order": MyOrderSet.name}

    enum_value = MyOrderSet.name.as_graphql_enum_value()
    assert enum_value.extensions == {"foo": "bar", "undine_order": MyOrderSet.name}

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.values["nameAsc"].extensions == {"foo": "bar", "undine_order": MyOrderSet.name}
    assert enum_type.values["nameDesc"].extensions == {"foo": "bar", "undine_order": MyOrderSet.name}


def test_order__aliases() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

        @name.aliases
        def name_aliases(self, info: GQLInfo, descending: bool) -> dict[str, DjangoExpression]:
            return {"foo": Count("*")}

    data = ["name_asc"]

    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())

    assert results.order_by == [OrderBy(F("name"))]
    assert results.aliases == {"foo": Count("*")}
