from __future__ import annotations

from inspect import cleandoc

import pytest
from django.db.models import Count, Q, Subquery
from graphql import DirectiveLocation, GraphQLArgument, GraphQLInputField, GraphQLNonNull, GraphQLString

from example_project.app.models import Person, Task, TaskTypeChoices
from tests.helpers import mock_gql_info
from undine import Field, QueryType
from undine.converters import convert_to_graphql_argument_map
from undine.directives import Directive, DirectiveArgument
from undine.exceptions import DirectiveLocationError, MissingModelGenericError
from undine.filtering import Filter, FilterSet

CREATED_AT_FIELDS = (
    "createdAt",
    "createdAtDay",
    "createdAtGt",
    "createdAtGte",
    "createdAtIn",
    "createdAtIsoWeekDay",
    "createdAtIsoYear",
    "createdAtLt",
    "createdAtLte",
    "createdAtMonth",
    "createdAtQuarter",
    "createdAtRange",
    "createdAtWeek",
    "createdAtWeekDay",
    "createdAtYear",
)

NAME_FIELDS = (
    "name",
    "nameContains",
    "nameContainsExact",
    "nameEndsWithExact",
    "nameEndsWith",
    "nameExact",
    "nameIn",
    "nameStartsWith",
    "nameStartsWithExact",
)

PK_FIELDS = (
    "pk",
    "pkGt",
    "pkGte",
    "pkIn",
    "pkLt",
    "pkLte",
)

TYPE_FIELDS = (
    "type",
    "typeContains",
    "typeContainsExact",
    "typeEndsWith",
    "typeEndsWithExact",
    "typeExact",
    "typeIn",
    "typeStartsWith",
    "typeStartsWithExact",
)


def test_filterset__str() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    assert str(MyFilterSet) == cleandoc(
        """
        input MyFilterSet {
          name: String
          NOT: MyFilterSet
          AND: MyFilterSet
          OR: MyFilterSet
          XOR: MyFilterSet
        }
        """
    )


def test_filterset__attributes() -> None:
    class MyFilterSet(FilterSet[Task]):
        """Description."""

    assert MyFilterSet.__models__ == (Task,)
    assert MyFilterSet.__schema_name__ == "MyFilterSet"
    assert MyFilterSet.__directives__ == []
    assert MyFilterSet.__extensions__ == {"undine_filterset": MyFilterSet}
    assert MyFilterSet.__attribute_docstrings__ == {}


def test_filterset__input_type() -> None:
    class MyFilterSet(FilterSet[Task]):
        """Description."""

    input_type = MyFilterSet.__input_type__()

    assert input_type.name == "MyFilterSet"
    assert input_type.extensions == {"undine_filterset": MyFilterSet}
    assert input_type.description == "Description."

    assert callable(input_type._fields)

    fields = input_type.fields
    filters = CREATED_AT_FIELDS + NAME_FIELDS + PK_FIELDS + TYPE_FIELDS

    assert all(field in fields for field in filters), set(filters) - set(fields)
    assert isinstance(fields["NOT"], GraphQLInputField)
    assert isinstance(fields["AND"], GraphQLInputField)
    assert isinstance(fields["OR"], GraphQLInputField)
    assert isinstance(fields["XOR"], GraphQLInputField)


def test_filterset__no_model() -> None:
    with pytest.raises(MissingModelGenericError):

        class MyFilterSet(FilterSet): ...


def test_filterset__build__one_field() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "name": "foo",
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__iexact="foo")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__two_fields() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "name": "foo",
        "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__iexact="foo"), Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__and_block() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "AND": {
            "name": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__iexact="foo") & Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__or_block() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "OR": {
            "name": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__iexact="foo") | Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__xor_block() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "XOR": {
            "name": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__iexact="foo") ^ Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__not_block() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "NOT": {
            "name": "foo",
            "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [~Q(name__iexact="foo"), ~Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__nested_blocks() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "OR": {
            "NOT": {
                "name": "foo",
                "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [~Q(name__iexact="foo") | ~Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__build__nested_blocks__complex() -> None:
    class MyFilterSet(FilterSet[Task]): ...

    data = {
        "OR": {
            "NOT": {
                "name": "foo",
            },
            "AND": {
                "name_contains": "foo",
                "type_in": [TaskTypeChoices.BUG_FIX.value, TaskTypeChoices.STORY.value],
                "NOT": {
                    "type": TaskTypeChoices.TASK.value,
                },
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [
        ~Q(name__iexact="foo")
        | (
            Q(name__icontains="foo")
            & Q(type__in=[TaskTypeChoices.BUG_FIX, TaskTypeChoices.STORY])
            & ~Q(type__iexact=TaskTypeChoices.TASK)
        ),
    ]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__schema_name() -> None:
    class MyFilterSet(FilterSet[Task], schema_name="CustomName"): ...

    assert MyFilterSet.__schema_name__ == "CustomName"

    input_type = MyFilterSet.__input_type__()
    assert input_type.name == "CustomName"


def test_filterset__directives() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    class MyFilterSet(FilterSet[Task], directives=directives, auto=False):
        name = Filter()

    assert MyFilterSet.__directives__ == directives

    assert str(MyFilterSet) == cleandoc(
        """
        input MyFilterSet @value(value: "foo") {
          name: String
          NOT: MyFilterSet
          AND: MyFilterSet
          OR: MyFilterSet
          XOR: MyFilterSet
        }
        """
    )


def test_filterset__directives__not_applicable() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.ENUM], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    directives: list[Directive] = [ValueDirective(value="foo")]

    with pytest.raises(DirectiveLocationError):

        class MyFilterSet(FilterSet[Task], directives=directives): ...


def test_filterset__directives__decorator() -> None:
    class ValueDirective(Directive, locations=[DirectiveLocation.INPUT_OBJECT], schema_name="value"):
        value = DirectiveArgument(GraphQLNonNull(GraphQLString))

    @ValueDirective(value="foo")
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    assert MyFilterSet.__directives__ == [ValueDirective(value="foo")]

    assert str(MyFilterSet) == cleandoc(
        """
        input MyFilterSet @value(value: "foo") {
          name: String
          NOT: MyFilterSet
          AND: MyFilterSet
          OR: MyFilterSet
          XOR: MyFilterSet
        }
        """
    )


def test_filterset__extensions() -> None:
    class MyFilterSet(FilterSet[Task], extensions={"foo": "bar"}): ...

    assert MyFilterSet.__extensions__ == {"foo": "bar", "undine_filterset": MyFilterSet}

    input_type = MyFilterSet.__input_type__()
    assert input_type.extensions == {"foo": "bar", "undine_filterset": MyFilterSet}


def test_filterset__no_auto() -> None:
    class MyFilterSet(FilterSet[Task], auto=False): ...

    assert MyFilterSet.__filter_map__ == {}


def test_filterset__exclude() -> None:
    class MyFilterSet(FilterSet[Task], exclude=["pk"]): ...

    fields = MyFilterSet.__input_type__().fields

    assert all(field in fields for field in CREATED_AT_FIELDS)
    assert all(field in fields for field in NAME_FIELDS)
    assert all(field not in fields for field in PK_FIELDS)
    assert all(field in fields for field in TYPE_FIELDS)


def test_filterset__exclude__multiple() -> None:
    class MyFilterSet(FilterSet[Task], exclude=["pk", "name"]): ...

    fields = MyFilterSet.__input_type__().fields

    assert all(field in fields for field in CREATED_AT_FIELDS)
    assert all(field not in fields for field in NAME_FIELDS)
    assert all(field not in fields for field in PK_FIELDS)
    assert all(field in fields for field in TYPE_FIELDS)


def test_filterset__expression() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        assignee_count_lt = Filter(Count("assignees"), lookup="lt")

    data = {
        "assignee_count_lt": 1,
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(assignee_count_lt__lt=1)]
    assert results.distinct is False
    assert results.aliases == {"assignee_count_lt": Count("assignees")}


def test_filterset__subquery() -> None:
    sq = Subquery(Person.objects.values("name")[:1])

    class MyFilterSet(FilterSet[Task], auto=False):
        primary_assignee_name_in = Filter(sq, lookup="in")

    data = {
        "primary_assignee_name_in": ["foo", "bar"],
    }

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(primary_assignee_name_in__in=["foo", "bar"])]
    assert results.distinct is False
    assert results.aliases == {"primary_assignee_name_in": sq}


def test_filterset__distinct() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        assignee_name = Filter("assignees__name", distinct=True)

    data = {"assignee_name": "foo"}

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(assignees__name__exact="foo")]
    assert results.distinct is True
    assert results.aliases == {}


def test_filterset__many__any() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter(many=True)

    data = {"name": ["foo", "bar"]}

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__exact="foo") | Q(name__exact="bar")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__many__all() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter(many=True, match="all")

    data = {"name": ["foo", "bar"]}

    results = MyFilterSet.__build__(filter_data=data, info=mock_gql_info())

    assert results.filters == [Q(name__exact="foo") & Q(name__exact="bar")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__add_to_query_type() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    class TaskType(QueryType[Task], auto=False, filterset=MyFilterSet):
        name = Field()

    assert TaskType.__filterset__ == MyFilterSet

    args = convert_to_graphql_argument_map(TaskType, many=True, entrypoint=True)

    assert args == {
        "filter": GraphQLArgument(MyFilterSet.__input_type__()),
    }


def test_filterset__add_to_query_type__decorator() -> None:
    class MyFilterSet(FilterSet[Task], auto=False):
        name = Filter()

    @MyFilterSet
    class TaskType(QueryType[Task], auto=False):
        name = Field()

    assert TaskType.__filterset__ == MyFilterSet

    args = convert_to_graphql_argument_map(TaskType, many=True, entrypoint=True)

    assert args == {
        "filter": GraphQLArgument(MyFilterSet.__input_type__()),
    }
