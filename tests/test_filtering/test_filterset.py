import pytest
from django.db import models
from django.db.models import Q
from graphql import GraphQLInputField

from example_project.app.models import Person, Task, TaskType
from tests.helpers import MockGQLInfo
from undine.errors.exceptions import MissingModelError
from undine.filtering import Filter, FilterSet

CREATED_AT_FIELDS = [
    "createdAtContains",
    "createdAtDay",
    "createdAtEndswith",
    "createdAtExact",
    "createdAtGt",
    "createdAtGte",
    "createdAtIcontains",
    "createdAtIendswith",
    "createdAtIexact",
    "createdAtIn",
    "createdAtIregex",
    "createdAtIsnull",
    "createdAtIsoWeekDay",
    "createdAtIsoYear",
    "createdAtIstartswith",
    "createdAtLt",
    "createdAtLte",
    "createdAtMonth",
    "createdAtQuarter",
    "createdAtRange",
    "createdAtRegex",
    "createdAtStartswith",
    "createdAtWeek",
    "createdAtWeekDay",
    "createdAtYear",
]

NAME_FIELDS = [
    "nameContains",
    "nameEndswith",
    "nameExact",
    "nameGt",
    "nameGte",
    "nameIcontains",
    "nameIendswith",
    "nameIexact",
    "nameIn",
    "nameIregex",
    "nameIsnull",
    "nameIstartswith",
    "nameLt",
    "nameLte",
    "nameRange",
    "nameRegex",
    "nameStartswith",
]

PK_FIELDS = [
    "pkContains",
    "pkEndswith",
    "pkExact",
    "pkGt",
    "pkGte",
    "pkIcontains",
    "pkIendswith",
    "pkIexact",
    "pkIn",
    "pkIregex",
    "pkIsnull",
    "pkIstartswith",
    "pkLt",
    "pkLte",
    "pkRange",
    "pkRegex",
    "pkStartswith",
]

TYPE_FIELDS = [
    "typeContains",
    "typeEndswith",
    "typeExact",
    "typeGt",
    "typeGte",
    "typeIcontains",
    "typeIendswith",
    "typeIexact",
    "typeIn",
    "typeIregex",
    "typeIsnull",
    "typeIstartswith",
    "typeLt",
    "typeLte",
    "typeRange",
    "typeRegex",
    "typeStartswith",
]


def test_filterset__default():
    class MyFilterSet(FilterSet, model=Task):
        """Decription."""

    assert MyFilterSet.__model__ == Task
    assert MyFilterSet.__typename__ == "MyFilterSet"
    assert MyFilterSet.__extensions__ == {"undine_filter_input": MyFilterSet}

    filter_map = MyFilterSet.__filter_map__

    filters = CREATED_AT_FIELDS + NAME_FIELDS + PK_FIELDS + TYPE_FIELDS

    assert sorted(filter_map) == filters

    input_type = MyFilterSet.__input_type__()

    assert input_type.name == "MyFilterSet"
    assert input_type.extensions == {"undine_filter_input": MyFilterSet}
    assert input_type.description == "Decription."

    assert callable(input_type._fields)

    fields = input_type.fields

    assert all(field in fields for field in filters), set(filters) - set(fields)
    assert isinstance(fields["NOT"], GraphQLInputField)
    assert isinstance(fields["AND"], GraphQLInputField)
    assert isinstance(fields["OR"], GraphQLInputField)
    assert isinstance(fields["XOR"], GraphQLInputField)


def test_filterset__no_model():
    with pytest.raises(MissingModelError):

        class MyFilterSet(FilterSet): ...


def test_filterset__one_field():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "nameExact": "foo",
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo")]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__two_fields():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "nameExact": "foo",
        "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo"), Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__and_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "AND": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__or_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") | Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__xor_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "XOR": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [Q(name__exact="foo") ^ Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__not_block():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "NOT": {
            "nameExact": "foo",
            "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo"), ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__nested_blocks():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "nameExact": "foo",
                "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [~Q(name__exact="foo") | ~Q(type__in=[TaskType.BUG_FIX, TaskType.STORY])]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__nested_blocks__complex():
    class MyFilterSet(FilterSet, model=Task): ...

    data = {
        "OR": {
            "NOT": {
                "nameExact": "foo",
            },
            "AND": {
                "nameContains": "foo",
                "typeIn": [TaskType.BUG_FIX.value, TaskType.STORY.value],
                "NOT": {
                    "typeExact": TaskType.TASK.value,
                },
            },
        },
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [
        ~Q(name__exact="foo")
        | (Q(name__contains="foo") & Q(type__in=[TaskType.BUG_FIX, TaskType.STORY]) & ~Q(type__exact=TaskType.TASK)),
    ]
    assert results.distinct is False
    assert results.aliases == {}


def test_filterset__typename():
    class MyFilterSet(FilterSet, model=Task, typename="CustomName"): ...

    assert MyFilterSet.__typename__ == "CustomName"

    input_type = MyFilterSet.__input_type__()
    assert input_type.name == "CustomName"


def test_filterset__extensions():
    class MyFilterSet(FilterSet, model=Task, extensions={"foo": "bar"}): ...

    assert MyFilterSet.__extensions__ == {"foo": "bar", "undine_filter_input": MyFilterSet}

    input_type = MyFilterSet.__input_type__()
    assert input_type.extensions == {"foo": "bar", "undine_filter_input": MyFilterSet}


def test_filterset__no_auto():
    class MyFilterSet(FilterSet, model=Task, auto=False): ...

    assert MyFilterSet.__filter_map__ == {}


def test_filterset__exclude_fields():
    class MyFilterSet(FilterSet, model=Task, exclude=["pk"]): ...

    assert all(field in MyFilterSet.__filter_map__ for field in CREATED_AT_FIELDS)
    assert all(field in MyFilterSet.__filter_map__ for field in NAME_FIELDS)
    assert all(field not in MyFilterSet.__filter_map__ for field in PK_FIELDS)
    assert all(field in MyFilterSet.__filter_map__ for field in TYPE_FIELDS)


def test_filterset__exclude_fields__multiple():
    class MyFilterSet(FilterSet, model=Task, exclude=["pk", "name"]): ...

    assert all(field in MyFilterSet.__filter_map__ for field in CREATED_AT_FIELDS)
    assert all(field not in MyFilterSet.__filter_map__ for field in NAME_FIELDS)
    assert all(field not in MyFilterSet.__filter_map__ for field in PK_FIELDS)
    assert all(field in MyFilterSet.__filter_map__ for field in TYPE_FIELDS)


def test_filterset__expression():
    class MyFilterSet(FilterSet, model=Task, auto=False):
        assignee_count_lt = Filter(models.Count("assignees"), lookup_expr="lt")

    data = {
        "assigneeCountLt": 1,
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [models.Q(assignee_count_lt__lt=1)]
    assert results.distinct is False
    assert results.aliases == {"assignee_count_lt": models.Count("assignees")}


def test_filterset__subquery():
    sq = models.Subquery(Person.objects.values("name")[:1])

    class MyFilterSet(FilterSet, model=Task, auto=False):
        primary_assignee_name_in = Filter(sq, lookup_expr="in")

    data = {
        "primaryAssigneeNameIn": ["foo", "bar"],
    }

    results = MyFilterSet.__build__(filter_data=data, info=MockGQLInfo())

    assert results.filters == [models.Q(primary_assignee_name_in__in=["foo", "bar"])]
    assert results.distinct is False
    assert results.aliases == {"primary_assignee_name_in": sq}
