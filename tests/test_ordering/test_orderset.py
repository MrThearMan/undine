from __future__ import annotations

from inspect import cleandoc

import pytest
from django.db.models import F, OrderBy
from graphql import DirectiveLocation, GraphQLNonNull, GraphQLString

from example_project.app.models import Task
from tests.helpers import mock_gql_info
from undine import Order, OrderSet
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, MissingModelGenericError
from undine.utils.graphql.utils import get_underlying_type


def test_orderset__str() -> None:
    class MyOrderSet(OrderSet[Task], auto=False):
        name = Order()

    assert str(MyOrderSet) == cleandoc(
        """
        enum MyOrderSet {
          nameAsc
          nameDesc
        }
        """
    )


def test_orderset__attributes() -> None:
    class MyOrderSet(OrderSet[Task]):
        """Description."""

    assert MyOrderSet.__model__ == Task
    assert sorted(MyOrderSet.__order_map__) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "created_at",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "name",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]
    assert MyOrderSet.__schema_name__ == "MyOrderSet"
    assert MyOrderSet.__directives__ == []
    assert MyOrderSet.__extensions__ == {"undine_orderset": MyOrderSet}
    assert MyOrderSet.__attribute_docstrings__ == {}


def test_orderset__enum_type() -> None:
    class MyOrderSet(OrderSet[Task]):
        """Description."""

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.name == "MyOrderSet"
    assert sorted(enum_type.values) == [
        "acceptancecriteriaAsc",
        "acceptancecriteriaDesc",
        "assigneesAsc",
        "assigneesDesc",
        "attachmentAsc",
        "attachmentDesc",
        "checkTimeAsc",
        "checkTimeDesc",
        "commentsAsc",
        "commentsDesc",
        "contactEmailAsc",
        "contactEmailDesc",
        "createdAtAsc",
        "createdAtDesc",
        "demoUrlAsc",
        "demoUrlDesc",
        "doneAsc",
        "doneDesc",
        "dueByAsc",
        "dueByDesc",
        "externalUuidAsc",
        "externalUuidDesc",
        "extraDataAsc",
        "extraDataDesc",
        "imageAsc",
        "imageDesc",
        "nameAsc",
        "nameDesc",
        "objectiveAsc",
        "objectiveDesc",
        "pkAsc",
        "pkDesc",
        "pointsAsc",
        "pointsDesc",
        "progressAsc",
        "progressDesc",
        "projectAsc",
        "projectDesc",
        "relatedTasksAsc",
        "relatedTasksDesc",
        "reportsAsc",
        "reportsDesc",
        "requestAsc",
        "requestDesc",
        "resultAsc",
        "resultDesc",
        "stepsAsc",
        "stepsDesc",
        "typeAsc",
        "typeDesc",
        "workedHoursAsc",
        "workedHoursDesc",
    ]
    assert enum_type.description == "Description."
    assert enum_type.extensions == {"undine_orderset": MyOrderSet}


def test_filterset__no_model() -> None:
    with pytest.raises(MissingModelGenericError):

        class MyOrderSet(OrderSet): ...


def test_orderset__one_field() -> None:
    class MyOrderSet(OrderSet[Task]):
        name = Order()

    data = ["name_asc"]
    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())
    assert results.order_by == [
        OrderBy(F("name")),
    ]

    data = ["name_desc"]
    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())
    assert results.order_by == [
        OrderBy(F("name"), descending=True),
    ]


def test_orderset__two_fields() -> None:
    class MyOrderSet(OrderSet[Task]):
        name = Order()

    data = ["name_asc", "pk_desc"]
    results = MyOrderSet.__build__(order_data=data, info=mock_gql_info())
    assert results.order_by == [
        OrderBy(F("name")),
        OrderBy(F("id"), descending=True),
    ]


def test_orderset__schema_name() -> None:
    class MyOrderSet(OrderSet[Task], schema_name="CustomName"): ...

    assert MyOrderSet.__schema_name__ == "CustomName"

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.name == "CustomName"


def test_orderset__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyOrderSet(OrderSet[Task], directives=directives, auto=False):
        name = Order()

    assert MyOrderSet.__directives__ == directives

    assert str(MyOrderSet) == cleandoc(
        """
        enum MyOrderSet @value(value: "foo") {
          nameAsc
          nameDesc
        }
        """
    )


def test_orderset__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM_VALUE], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyOrderSet(OrderSet[Task], directives=directives): ...


def test_orderset__extensions() -> None:
    class MyOrderSet(OrderSet[Task], extensions={"foo": "bar"}): ...

    assert MyOrderSet.__extensions__ == {"foo": "bar", "undine_orderset": MyOrderSet}

    input_type = MyOrderSet.__enum_type__()
    enum_type = get_underlying_type(input_type)
    assert enum_type.extensions == {"foo": "bar", "undine_orderset": MyOrderSet}


def test_filterset__no_auto() -> None:
    class MyOrderSet(OrderSet[Task], auto=False): ...

    assert MyOrderSet.__order_map__ == {}


def test_filterset__exclude() -> None:
    class MyOrderSet(OrderSet[Task], exclude=["name"]): ...

    assert "pk" in MyOrderSet.__order_map__
    assert "name" not in MyOrderSet.__order_map__
    assert "type" in MyOrderSet.__order_map__
    assert "created_at" in MyOrderSet.__order_map__


def test_filterset__exclude__multiple() -> None:
    class MyOrderSet(OrderSet[Task], exclude=["name", "pk"]): ...

    assert "pk" not in MyOrderSet.__order_map__
    assert "name" not in MyOrderSet.__order_map__
    assert "type" in MyOrderSet.__order_map__
    assert "created_at" in MyOrderSet.__order_map__
